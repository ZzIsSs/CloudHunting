#!/bin/bash
# ═══════════════════════════════════════════════════════════
#  CloudHunting - Render.com Start Script
#  Khoi dong tat ca 6 microservices + Gateway trong 1 tien trinh (serve_all.py)
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

# [Render Free Tier: 512 MB RAM, 0.1 CPU] Giam RAM/CPU
# numpy/sklearn mac dinh tao thread pool theo so CPU cua may chu -> gioi han 1 thread
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
# glibc mac dinh tao nhieu vung nho (arena) cho moi thread -> gioi han 2
export MALLOC_ARENA_MAX=2
# S6 quet co hoi san may moi 15 phut thay vi 1 phut (moi lan quet goi S1 cho tat ca dia diem)
export S6_SCAN_INTERVAL_MINUTES=${S6_SCAN_INTERVAL_MINUTES:-15}

# Khoi dong 6 service (thread rieng, chi nghe 127.0.0.1) + Gateway (bind vao $PORT cua Render)
# trong cung 1 tien trinh: 7 tien trinh uvicorn rieng le vuot 512 MB RAM (Render bao MLE)
exec python serve_all.py
