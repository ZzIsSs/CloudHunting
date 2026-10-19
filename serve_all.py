"""
Chay toan bo he thong CloudHunting trong MOT tien trinh Python (dung cho Render).

Moi service S1-S6 chay uvicorn trong mot thread rieng (event loop rieng),
Gateway chay o thread chinh. Cac service van goi nhau qua HTTP 127.0.0.1:800x
nhu khi chay rieng le, nhung thu vien (FastAPI, SQLAlchemy, pandas, sklearn...)
chi nap mot lan thay vi 7 lan -> vua RAM 512 MB cua Render free tier.

Chay: python serve_all.py   (Gateway nghe tai $PORT, mac dinh 8000)
"""
import importlib
import os
import threading
import time

import uvicorn

# Danh sach service noi bo (theo thu tu khoi dong giong start_all.py)
SERVICES = [
    {"name": "S3 Auth",       "module": "src.s3_auth.main",       "port": 8003},
    {"name": "S4 Content",    "module": "src.s4_content.main",    "port": 8004},
    {"name": "S5 Statistics", "module": "src.s5_statistics.main", "port": 8005},
    {"name": "S1 Metrics",    "module": "src.s1_metrics.main",    "port": 8001},
    {"name": "S2 Booking",    "module": "src.s2_booking.main",    "port": 8002},
    {"name": "S6 Recommend",  "module": "src.s6_recommend.main",  "port": 8006},
]
GATEWAY_PORT = int(os.getenv("PORT", "8000"))
STARTUP_TIMEOUT = 120  # giay toi da cho cac service san sang truoc khi mo Gateway


def main():
    print("=" * 55)
    print("   CloudHunting - Khoi dong (1 tien trinh)")
    print("=" * 55)

    servers = []
    for svc in SERVICES:
        # Import tuan tu o thread chinh de tranh import dong thoi giua cac thread
        app = importlib.import_module(svc["module"]).app
        # Service noi bo chi nghe 127.0.0.1: chi Gateway can mo ra ngoai
        server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=svc["port"]))
        thread = threading.Thread(target=server.run, name=svc["name"], daemon=True)
        thread.start()
        servers.append((svc, server, thread))
        print(f"  ✓ {svc['name']} (port {svc['port']})")

    # Cho cac service chay xong lifespan startup (bo qua service da loi/thoat)
    deadline = time.time() + STARTUP_TIMEOUT
    while time.time() < deadline and any(not s.started and t.is_alive() for _, s, t in servers):
        time.sleep(0.5)
    not_ready = [svc["name"] for svc, server, _ in servers if not server.started]
    if not_ready:
        print(f"  ⚠️ Chua san sang: {', '.join(not_ready)}")

    gateway = importlib.import_module("src.gateway.main").app
    print(f"  ✓ Gateway (port {GATEWAY_PORT}) - Day la port chinh")
    print("=" * 55)
    # Gateway chay o thread chinh nen nhan tin hieu tat (SIGTERM/Ctrl+C);
    # khi Gateway dung, tien trinh thoat va cac thread service (daemon) dung theo.
    uvicorn.Server(uvicorn.Config(gateway, host="0.0.0.0", port=GATEWAY_PORT)).run()


if __name__ == "__main__":
    main()
