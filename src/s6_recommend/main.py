from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import contextlib
import os
from apscheduler.schedulers.background import BackgroundScheduler

from .routes import router as s6_router
from .database import init_db, SessionLocal
from .services import scan_and_notify_opportunities

# Chu kỳ quét cơ hội săn mây (phút). Mỗi lần quét gọi S1 cho tất cả địa điểm,
# nên trên Render (0.1 CPU) đặt lớn hơn qua biến môi trường (xem render_start.sh).
SCAN_INTERVAL_MINUTES = int(os.getenv("S6_SCAN_INTERVAL_MINUTES", "1"))

def scheduled_scan():
    db = SessionLocal()
    try:
        scan_and_notify_opportunities(db)
    finally:
        db.close()

@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    # Khởi tạo bảng DB khi chạy
    init_db()
    print("🚀 [Service 6] Đã sẵn sàng. Đã khởi tạo cấu trúc dữ liệu.")
    
    # Bật bộ quét ngầm
    scheduler = BackgroundScheduler()
    scheduler.add_job(scheduled_scan, "interval", minutes=SCAN_INTERVAL_MINUTES)
    scheduler.start()
    print(f"⏰ [Service 6] Bộ quét cảnh báo tự động đã bật ({SCAN_INTERVAL_MINUTES} phút/lần).")
    
    yield
    print("🛑 [Service 6] Đang tắt Server...")
    scheduler.shutdown()

app = FastAPI(
    title="Cloud Hunting - Service 6",
    description="Microservice Đề xuất lộ trình cá nhân hóa",
    version="1.0.0",
    lifespan=lifespan
)

# Cấu hình CORS để Front-end có thể gọi được API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(s6_router, prefix="/api/s6", tags=["Recommendation"])

if __name__ == "__main__":
    import uvicorn
    # Chạy Service 6 ở port 8006
    uvicorn.run("src.s6_recommend.main:app", host="0.0.0.0", port=8006, reload=True)
