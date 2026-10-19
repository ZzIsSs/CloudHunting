# test_integration.py
"""
Kiểm thử tích hợp toàn hệ thống theo kịch bản demo (material/demo_app.md).
Gửi đúng các request mà frontend gửi, đi qua API Gateway.

Cách chạy (cần bật đủ 6 service + Gateway, ví dụ bằng `python start_all.py`):
    python test_integration.py                                    # máy local
    python test_integration.py https://cloudhuntting.onrender.com  # bản deploy

Lưu ý: mỗi lần chạy sẽ tạo thật 1 tài khoản test, 1 đánh giá và 1 ticket
trong database của hệ thống được kiểm thử.
"""
import requests
import uuid
import sys

# Đảm bảo hiển thị ký tự tiếng Việt UTF-8 không bị lỗi trên Windows console
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except AttributeError:
    pass

BASE_URL = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "http://127.0.0.1:8000"
TIMEOUT = 90  # S1 gọi API Open-Meteo nên có thể chậm

results = []


def step(name, response, describe=None):
    """In kết quả một bước; bước đạt khi status code < 300."""
    passed = response.status_code < 300
    detail = ""
    if passed and describe:
        try:
            detail = describe(response)
        except Exception as e:
            detail = f"(không đọc được response: {e})"
    elif not passed:
        detail = response.text[:200]
    results.append(passed)
    print(f"{'✅' if passed else '❌'} [{response.status_code}] {name}  {detail}")
    return response


def run_tests():
    print("=" * 60)
    print(f"   KIỂM THỬ TÍCH HỢP QUA GATEWAY: {BASE_URL}")
    print("=" * 60)

    # 0. Gateway + trạng thái 6 service
    r = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
    health = r.json() if r.status_code == 200 else {}
    offline = [k for k, v in health.get("services", {}).items() if v.get("status") != "online"]
    results.append(r.status_code == 200 and not offline)
    print(f"{'✅' if results[-1] else '❌'} [{r.status_code}] GET /health  {health.get('summary', r.text[:100])}"
          + (f"  offline: {offline}" if offline else ""))

    # 1. Frontend
    r = step("GET / (trang chủ)", requests.get(f"{BASE_URL}/", timeout=TIMEOUT))
    bundles = [p for p in r.text.split('"') if p.startswith("/assets/") and p.endswith(".js")]
    if bundles:
        step(f"GET {bundles[0]}", requests.get(f"{BASE_URL}{bundles[0]}", timeout=TIMEOUT),
             lambda r: f"{len(r.content)} bytes")

    # 2. Đăng ký + đăng nhập (S3)
    username = f"test_{uuid.uuid4().hex[:8]}"
    password = "Test@12345"
    step("POST /auth/register", requests.post(f"{BASE_URL}/auth/register", json={
        "email": f"{username}@example.com",
        "username": username,
        "password": password,
        "display_name": "Tester",
    }, timeout=TIMEOUT))
    r = step("POST /auth/login", requests.post(f"{BASE_URL}/auth/login", data={
        "username": username,
        "password": password,
    }, timeout=TIMEOUT), lambda r: "nhận được access_token" if r.json().get("access_token") else "THIẾU access_token")
    token = r.json().get("access_token", "") if r.status_code == 200 else ""
    headers = {"Authorization": f"Bearer {token}"}

    # 3. Nhập điểm khảo sát + bán kính -> các điểm săn mây có điểm số (S1)
    step("POST /api/s1/predict", requests.post(f"{BASE_URL}/api/s1/predict", json={
        "location_name": "Chợ Đà Lạt",
        "radius_km": 15,
        "forecast_hours": 0,
    }, headers=headers, timeout=TIMEOUT), lambda r: f"{r.json().get('total_spots_found')} điểm")

    # 4. Vị trí các điểm + tiện ích xung quanh (S2)
    step("GET /api/v1/spots", requests.get(f"{BASE_URL}/api/v1/spots", headers=headers, timeout=TIMEOUT),
         lambda r: f"{len(r.json())} điểm")
    step("GET /api/v1/places/nearby", requests.get(f"{BASE_URL}/api/v1/places/nearby", params={
        "lat": 11.9404, "lon": 108.4583, "radius_km": 5, "per_page": 5,
    }, headers=headers, timeout=TIMEOUT), lambda r: f"{r.json().get('total')} tiện ích")

    # 5. Đánh giá địa điểm (S4)
    step("GET /content/reviews/location/1", requests.get(
        f"{BASE_URL}/content/reviews/location/1", headers=headers, timeout=TIMEOUT),
        lambda r: f"{len(r.json())} đánh giá")
    step("POST /content/reviews", requests.post(f"{BASE_URL}/content/reviews", json={
        "location_id": 1,
        "location_name": "Đồi Đa Phú",
        "rating": 5,
        "comment": "Đánh giá tạo bởi test_integration.py",
    }, headers=headers, timeout=TIMEOUT))

    # 6. Lịch trình AI + thông báo (S6)
    step("POST /api/s6/recommend", requests.post(f"{BASE_URL}/api/s6/recommend", json={
        "user_id": username,
        "start_time": "04:30",
        "start_location": "Trung tâm",
        "max_distance_km": 30.0,
        "travel_style": "Sống ảo nhẹ nhàng",
        "preferred_vibe": "Thương mại",
        "vehicle_type": "xe máy",
        "selected_location": "Đồi Đa Phú",
    }, headers=headers, timeout=TIMEOUT), lambda r: f"{len(r.json().get('timeline', []))} bước trong lịch trình")
    step("GET /api/s6/notifications", requests.get(
        f"{BASE_URL}/api/s6/notifications", headers=headers, timeout=TIMEOUT),
        lambda r: f"{len(r.json())} thông báo")

    # 7. Góp ý cho hệ thống bằng ticket (S4)
    step("POST /content/tickets", requests.post(f"{BASE_URL}/content/tickets", json={
        "title": "Góp ý từ test_integration.py",
        "description": "Ticket tạo tự động khi kiểm thử",
    }, headers=headers, timeout=TIMEOUT))
    step("GET /content/tickets", requests.get(f"{BASE_URL}/content/tickets", headers=headers, timeout=TIMEOUT),
         lambda r: f"{len(r.json())} ticket")

    print("=" * 60)
    print(f"   KẾT QUẢ: {sum(results)}/{len(results)} bước đạt")
    print("=" * 60)
    return all(results)


if __name__ == "__main__":
    try:
        ok = run_tests()
    except requests.exceptions.ConnectionError:
        print(f"❌ Không kết nối được tới {BASE_URL}. Hãy bật hệ thống trước (python start_all.py).")
        ok = False
    sys.exit(0 if ok else 1)
