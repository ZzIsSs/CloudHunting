"""
Gateway Routes: Đăng ký tất cả proxy routes và endpoint health check.
"""
import asyncio

from fastapi import APIRouter, Request
from .config import SERVICES
from .proxy import proxy_request, check_service_health

router = APIRouter()

# ─── Proxy Routes: Tự động tạo route cho từng service ────────────────────────

@router.api_route("/api/s1/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"], tags=["S1 - Dự báo Săn Mây"])
async def proxy_s1(request: Request, path: str):
    """Chuyển tiếp request đến Service 1 (Metrics & AI Prediction)"""
    svc = SERVICES["s1_metrics"]
    target_url = f"{svc['url']}{svc['prefix']}/{path}"
    print(f"[Gateway] -> S1 Metrics: {request.method} /{path}")
    return await proxy_request(request, target_url)

@router.api_route("/api/v1/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"], tags=["S2 - Đặt chỗ"])
async def proxy_s2(request: Request, path: str):
    """Chuyển tiếp request đến Service 2 (Booking)"""
    svc = SERVICES["s2_booking"]
    target_url = f"{svc['url']}{svc['prefix']}/{path}"
    print(f"[Gateway] -> S2 Booking: {request.method} /{path}")
    return await proxy_request(request, target_url)

@router.api_route("/auth/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"], tags=["S3 - Xác thực"])
async def proxy_s3(request: Request, path: str):
    """Chuyển tiếp request đến Service 3 (Auth)"""
    svc = SERVICES["s3_auth"]
    target_url = f"{svc['url']}{svc['prefix']}/{path}"
    print(f"[Gateway] -> S3 Auth: {request.method} /{path}")
    return await proxy_request(request, target_url)

@router.api_route("/content/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"], tags=["S4 - Nội dung & CSKH"])
async def proxy_s4(request: Request, path: str):
    """Chuyển tiếp request đến Service 4 (Content)"""
    svc = SERVICES["s4_content"]
    target_url = f"{svc['url']}{svc['prefix']}/{path}"
    print(f"[Gateway] -> S4 Content: {request.method} /{path}")
    return await proxy_request(request, target_url)

@router.api_route("/api/s5/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"], tags=["S5 - Thống kê"])
async def proxy_s5(request: Request, path: str):
    """Chuyển tiếp request đến Service 5 (Statistics)"""
    svc = SERVICES["s5_statistics"]
    target_url = f"{svc['url']}{svc['prefix']}/{path}"
    print(f"[Gateway] -> S5 Statistics: {request.method} /{path}")
    return await proxy_request(request, target_url)

@router.api_route("/api/s6/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"], tags=["S6 - Gợi ý Lộ trình"])
async def proxy_s6(request: Request, path: str):
    """Chuyển tiếp request đến Service 6 (Recommend)"""
    svc = SERVICES["s6_recommend"]
    target_url = f"{svc['url']}{svc['prefix']}/{path}"
    print(f"[Gateway] -> S6 Recommend: {request.method} /{path}")
    return await proxy_request(request, target_url)

# ─── Health Check: Dashboard sức khỏe toàn hệ thống ──────────────────────────

@router.get("/health", tags=["Gateway"])
async def health_check():
    """
    Kiểm tra sức khỏe toàn bộ hệ thống.
    Trả về trạng thái (online/offline) và thời gian phản hồi của từng service.
    """
    # Kiểm tra song song cả 6 service để tổng thời gian chỉ bằng service chậm nhất
    checks = await asyncio.gather(*(check_service_health(svc["url"]) for svc in SERVICES.values()))
    results = {
        key: {"name": svc["name"], "url": svc["url"], **check}
        for (key, svc), check in zip(SERVICES.items(), checks)
    }

    online_count = sum(1 for s in results.values() if s.get("status") == "online")
    total_count = len(results)
    
    return {
        "gateway": "online",
        "summary": f"{online_count}/{total_count} services đang hoạt động",
        "services": results
    }
