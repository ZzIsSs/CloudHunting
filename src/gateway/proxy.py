"""
Proxy Module: Chuyển tiếp (forward) request từ Gateway đến backend service.
Sử dụng httpx (async) để đảm bảo hiệu suất cao.
"""
import httpx
import time
from fastapi import Request, Response

# Client HTTP dùng chung (connection pooling)
_client = httpx.AsyncClient(timeout=30.0)

# Timeout cho mỗi lần kiểm tra sức khỏe service. Giữ ngắn để /health
# (Render dùng làm health check) luôn trả lời nhanh kể cả khi service đang khởi động.
HEALTH_TIMEOUT = 1.5

async def proxy_request(request: Request, target_url: str) -> Response:
    """
    Chuyển tiếp toàn bộ request (method, headers, body, query params)
    đến target_url và trả về response nguyên vẹn.
    """
    # Xây dựng URL đích
    url = target_url
    if request.query_params:
        url += f"?{request.query_params}"
    
    # Đọc body từ request gốc
    body = await request.body()
    
    # Lọc headers (loại bỏ hop-by-hop headers không nên forward)
    skip_headers = {"host", "transfer-encoding", "connection"}
    headers = {
        key: value for key, value in request.headers.items()
        if key.lower() not in skip_headers
    }
    
    try:
        start_time = time.time()
        
        # Gửi request đến backend service
        response = await _client.request(
            method=request.method,
            url=url,
            headers=headers,
            content=body,
        )
        
        elapsed_ms = round((time.time() - start_time) * 1000)
        print(f"  [OK] [{request.method}] {url} -> {response.status_code} ({elapsed_ms}ms)")
        
        # Trả response về client (giữ nguyên status code, headers, body)
        response_headers = dict(response.headers)
        response_headers.pop("transfer-encoding", None)
        response_headers.pop("content-encoding", None)
        
        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=response_headers,
        )
        
    except httpx.ConnectError:
        print(f"  [FAIL] [{request.method}] {url} -> Service offline!")
        return Response(
            content=f'{{"detail": "Service tại {target_url} đang offline. Vui lòng thử lại sau."}}',
            status_code=503,
            media_type="application/json",
        )
    except httpx.TimeoutException:
        print(f"  [TIMEOUT] [{request.method}] {url} -> Timeout!")
        return Response(
            content=f'{{"detail": "Service tại {target_url} phản hồi quá chậm (timeout 30s)."}}',
            status_code=504,
            media_type="application/json",
        )
    except Exception as e:
        print(f"  [ERROR] [{request.method}] {url} -> {e}")
        return Response(
            content=f'{{"detail": "Lỗi Gateway: {str(e)}"}}',
            status_code=502,
            media_type="application/json",
        )


async def check_service_health(service_url: str) -> dict:
    """
    Kiểm tra sức khỏe của một service bằng cách gọi GET /health hoặc GET /.
    Trả về dict chứa trạng thái (online/offline) và thời gian phản hồi.
    """
    try:
        start_time = time.time()
        response = await _client.get(f"{service_url}/health", timeout=HEALTH_TIMEOUT)
        elapsed_ms = round((time.time() - start_time) * 1000)
        return {
            "status": "online",
            "response_time_ms": elapsed_ms,
            "http_code": response.status_code
        }
    except Exception:
        # Thử lại với đường dẫn gốc /
        try:
            start_time = time.time()
            response = await _client.get(f"{service_url}/", timeout=HEALTH_TIMEOUT)
            elapsed_ms = round((time.time() - start_time) * 1000)
            return {
                "status": "online",
                "response_time_ms": elapsed_ms,
                "http_code": response.status_code
            }
        except Exception as e:
            return {
                "status": "offline",
                "error": str(e)
            }
