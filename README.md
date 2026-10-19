# ☁️ Cloud Hunting System (Hệ thống Săn Mây)

Hệ thống tự động thu thập dữ liệu thời tiết, phân tích chỉ số và tích hợp AI để gợi ý địa điểm, thời gian săn mây lý tưởng tại Đà Lạt.

👉 **Bản deploy:** https://cloudhuntting.onrender.com
*(Render gói miễn phí: lần truy cập đầu sau khi site "ngủ" có thể mất vài phút để đủ 6 service.)*

Dự án được xây dựng theo kiến trúc **Monorepo (Modular Monolith)**, gom toàn bộ các thành phần vào một kho lưu trữ thống nhất để dễ dàng phát triển và triển khai.

---

# 🏗️ Kiến trúc Hệ thống (6 Modules)

Dự án được chia thành **6 phân hệ (module)** chạy thành các service FastAPI riêng, phía trước là một **API Gateway** (port 8000) phục vụ cả giao diện web lẫn chuyển tiếp request:

| Service | Port | Đường dẫn qua Gateway | Chức năng |
|---|---|---|---|
| **S1** Chỉ số | 8001 | `/api/s1/*` | Lấy dữ liệu thời tiết từ Open-Meteo, mô hình AI dự báo xác suất có mây cho các điểm săn mây |
| **S2** Đặt chỗ | 8002 | `/api/v1/*` | Danh sách điểm săn mây, tìm tiện ích xung quanh (cafe, nhà nghỉ, nhà hàng...) trên bản đồ |
| **S3** Auth | 8003 | `/auth/*` | Đăng ký/đăng nhập, cấp JWT, phân quyền User/Moderator/Admin |
| **S4** Nội dung | 8004 | `/content/*` | Đánh giá địa điểm (thích, bình luận, kiểm duyệt), bài viết, ticket hỗ trợ |
| **S5** Thống kê | 8005 | `/api/s5/*` | Lưu lịch sử dự báo, thống kê và xu hướng theo địa điểm |
| **S6** Gợi ý | 8006 | `/api/s6/*` | Gợi ý lịch trình cá nhân hóa, phương án dự phòng (Plan B), thông báo cơ hội săn mây |
| **Gateway** | 8000 | `/`, `/health`, `/docs` | Phục vụ frontend React, chuyển tiếp API, dashboard sức khỏe hệ thống |

---

# 📂 Cấu trúc Thư mục

Mã nguồn trong `src/` được chia phân khu rành mạch theo từng Module để tránh xung đột code khi làm việc nhóm:

```txt
CloudHunting/
├── src/                       # Source code backend (Python/FastAPI)
│   ├── gateway/               # API Gateway (port 8000)
│   ├── s1_metrics/            # [S1] Thời tiết + mô hình AI dự báo mây
│   ├── s2_booking/            # [S2] Điểm săn mây, tiện ích xung quanh
│   ├── s3_auth/               # [S3] JWT, phân quyền, middleware
│   ├── s4_content/            # [S4] Đánh giá, bài viết, ticket hỗ trợ
│   ├── s5_statistics/         # [S5] Thống kê, lưu lịch sử
│   ├── s6_recommend/          # [S6] Gợi ý lịch trình cá nhân hóa
│   ├── shared/                # Code dùng chung (config DB, dữ liệu hotspot...)
│   └── utils/
├── frontend/
│   ├── cloud-hunting-app/     # Frontend React + Vite (dist/ được Gateway phục vụ)
│   └── index.html, js/, css/  # Giao diện HTML/JS bản đầu (không còn được Gateway phục vụ)
├── Doc/                       # Tài liệu thiết kế
├── 24120397/                  # Bộ nộp bài (tài liệu, danh sách nhóm, link)
├── notebooks/                 # Jupyter Notebook (huấn luyện mô hình AI, EDA)
├── pic/                       # Ảnh các điểm săn mây
├── start_all.py               # Khởi động toàn bộ hệ thống trên Windows
├── render.yaml, render_start.sh  # Cấu hình deploy Render
├── test_integration.py        # Kiểm thử tích hợp theo kịch bản demo
└── requirements.txt           # Danh sách thư viện Python
```

---

# ⚙️ Yêu cầu Hệ thống (Prerequisites)

- Python 3.10 trở lên (bản deploy dùng 3.11)
- Git
- Node.js 20.19+ hoặc 22.12+ *(chỉ cần khi sửa frontend)*

---

# 🚀 Hướng dẫn Cài đặt & Khởi chạy

## Bước 1: Clone kho mã nguồn về máy

```bash
git clone https://github.com/ZzIsSs/CloudHunting.git
cd CloudHunting
```

## Bước 2: Tạo môi trường ảo và cài thư viện

```bash
python -m venv venv
.\venv\Scripts\activate          # Windows
# source venv/bin/activate       # macOS / Linux
pip install -r requirements.txt
```

## Bước 3: Tạo file cấu hình `.env`

```bash
copy .env.example .env           # Windows
# cp .env.example .env           # macOS / Linux
```

Đổi `JWT_SECRET` thành một chuỗi ngẫu nhiên. Các biến còn lại đã có giá trị mặc định cho môi trường local.

## Bước 4: Khởi động hệ thống

**Windows:** chạy một lệnh, mỗi service mở trong một cửa sổ console riêng:

```bash
python start_all.py
```

**macOS / Linux:** chạy từng service (mỗi lệnh một terminal, hoặc thêm `&` để chạy nền):

```bash
uvicorn src.s3_auth.main:app --port 8003
uvicorn src.s4_content.main:app --port 8004
uvicorn src.s5_statistics.main:app --port 8005
uvicorn src.s1_metrics.main:app --port 8001
uvicorn src.s2_booking.main:app --port 8002
uvicorn src.s6_recommend.main:app --port 8006
uvicorn src.gateway.main:app --port 8000
```

## Bước 5: Truy cập

- 🌐 Web App: http://127.0.0.1:8000
- 📖 Swagger UI (toàn bộ API qua Gateway): http://127.0.0.1:8000/docs
- ❤️ Sức khỏe hệ thống: http://127.0.0.1:8000/health (phải báo `6/6 services đang hoạt động`)
- Swagger riêng từng service: `http://127.0.0.1:<port>/docs` (port xem bảng ở trên)

---

# 🧪 Kiểm thử

Sau khi hệ thống đã chạy đủ 6/6 service:

```bash
python test_integration.py                                     # máy local
python test_integration.py https://cloudhuntting.onrender.com  # bản deploy
```

Script đi qua Gateway theo đúng kịch bản demo: đăng ký → đăng nhập → dự báo các điểm săn mây → tiện ích xung quanh → đánh giá → lịch trình AI → gửi ticket góp ý. Mỗi lần chạy sẽ tạo thật 1 tài khoản test, 1 đánh giá và 1 ticket.

---

# 🎨 Phát triển Frontend

```bash
cd frontend/cloud-hunting-app
npm install
npm run dev      # http://localhost:5173, tự chuyển /api, /auth, /content sang Gateway port 8000
npm run build    # build ra dist/ — commit dist/ để Gateway và Render dùng bản mới
```

Frontend gọi API bằng đường dẫn tương đối (`/api/...`, `/auth/...`, `/content/...`), **không** ghi cứng `http://127.0.0.1:8000`, để chạy được cả ở máy local lẫn bản deploy.

---

# ☁️ Deploy (Render)

Render đọc `render.yaml`: cài thư viện bằng `pip install -r requirements.txt`, rồi chạy `render_start.sh` để khởi động 6 service nội bộ và Gateway trên cổng `$PORT`. Render dùng `/health` làm health check.
