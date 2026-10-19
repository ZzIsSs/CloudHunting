#!/bin/bash
# ═══════════════════════════════════════════════════════════
#  CloudHunting - Render.com Start Script
#  Khoi dong tat ca 6 microservices trong 1 process group
# ══════════════════════════════════════════════════════════

echo "🚀 Dang khoi dong he thong CloudHunting..."

# [Railway Persistent Volume] Tạo symbolic links để lưu trữ các file SQLite vào ổ đĩa /data
# Việc này giúp dữ liệu không bị mất khi container khởi động lại trên Railway
if [ -d "/data" ]; then
    echo "  🔄 Setting up database volumes..."
    ln -sf /data/app.db app.db
    ln -sf /data/cloud_hunting.db cloud_hunting.db
    ln -sf /data/s6_preferences.db s6_preferences.db
else
    echo "  ⚠️ Running on Free Tier (No /data persistent volume detected). Using local SQLite."
fi

# [Render Free Tier: 512 MB RAM, 0.1 CPU] Giam RAM/CPU cho 7 tien trinh Python
# numpy/sklearn mac dinh tao thread pool theo so CPU cua may chu -> gioi han 1 thread
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
# glibc mac dinh tao nhieu vung nho (arena) cho moi thread -> gioi han 2
export MALLOC_ARENA_MAX=2
# S6 quet co hoi san may moi 15 phut thay vi 1 phut (moi lan quet goi S1 cho tat ca dia diem)
export S6_SCAN_INTERVAL_MINUTES=${S6_SCAN_INTERVAL_MINUTES:-15}

# Khoi dong cac service noi bo (chay ngam)
uvicorn src.s3_auth.main:app --host 0.0.0.0 --port 8003 &
echo "  ✓ S3 Auth (port 8003)"

uvicorn src.s4_content.main:app --host 0.0.0.0 --port 8004 &
echo "  ✓ S4 Content (port 8004)"

uvicorn src.s5_statistics.main:app --host 0.0.0.0 --port 8005 &
echo "  ✓ S5 Statistics (port 8005)"

sleep 2  # Cho S3, S4 va S5 san sang truoc


uvicorn src.s1_metrics.main:app --host 0.0.0.0 --port 8001 &
echo "  ✓ S1 Metrics (port 8001)"

uvicorn src.s2_booking.main:app --host 0.0.0.0 --port 8002 &
echo "  ✓ S2 Booking (port 8002)"

uvicorn src.s6_recommend.main:app --host 0.0.0.0 --port 8006 &
echo "  ✓ S6 Recommend (port 8006)"

sleep 2  # Cho cac service san sang

# Khoi dong Gateway (bind vao $PORT cua Render)
# Render chi expose 1 port duy nhat qua bien $PORT
GATEWAY_PORT=${PORT:-8000}
echo "  ✓ Gateway (port $GATEWAY_PORT) - Day la port chinh"
echo "═══════════════════════════════════════════════════════"
echo "  He thong da san sang!"
echo "═══════════════════════════════════════════════════════"

uvicorn src.gateway.main:app --host 0.0.0.0 --port $GATEWAY_PORT
