# Thư viện số Khoa CNTT — Front end tích hợp API

## Chạy thử trên Ubuntu / WSL, giữ cổng 8081

Giải nén, mở terminal trong thư mục `thu_vien_so`:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python demo.py
```

Mở http://localhost:8081 trên trình duyệt Windows. Swagger ở http://localhost:8081/docs.

| Vai trò | Email | Mật khẩu demo |
|---|---|---|
| Bạn đọc | reader@demo.local | ThuVienDemo2026! |
| Thủ thư | librarian@demo.local | ThuVienDemo2026! |

Demo dùng API thật và SQLite riêng `data/demo.sqlite3`, có 8 đầu sách minh họa, một sách hết bản và một lượt mượn quá hạn. Không gọi SMTP. Dữ liệu được giữ sau khi khởi động lại. Chỉ seed khi DB chưa có người dùng. Để tạo một bộ demo mới, chọn đường dẫn mới: `DEMO_DATABASE_PATH=data/demo2.sqlite3 python demo.py`.

Chế độ demo chỉ lắng nghe 127.0.0.1. Các tài khoản trên chỉ dành cho thử nghiệm.

## Chạy với dữ liệu của dự án

Làm theo README.md để cài môi trường, source .env, khởi tạo DB và tạo thủ thư. Thay lệnh khởi động bằng:

```bash
uvicorn serve:app --host 0.0.0.0 --port 8081
```

Bạn đọc đăng ký trên giao diện. Không chạy demo.py cho cơ sở dữ liệu thật. Không cần Node, npm hoặc CDN để chạy giao diện. Đây là HTML/CSS và JavaScript ES modules thuần, không dùng React/TypeScript; chưa có stack Front end nào được chốt nên bản này ưu tiên chạy chung trực tiếp với FastAPI.

## Mã nguồn

- frontend/index.html: khung ứng dụng, dialog, thông báo.
- frontend/style.css: giao diện responsive bạn đọc / thủ thư.
- frontend/app.js: màn hình, điều hướng hash, biểu mẫu, thao tác nghiệp vụ.
- frontend/api.js: Bearer session, JSON/multipart, timeout, thông báo lỗi tiếng Việt.
- frontend/config.js: API base URL; mặc định /api/v1 trên cùng origin.
- serve.py: bổ sung phục vụ tệp tĩnh và trang /; giữ nguyên các endpoint API.
- demo.py: dữ liệu chạy thử riêng.
- docs/FRONTEND_API_MAPPING.md: đối chiếu màn hình với API và phần mở rộng.
- qa/: kiểm tra tích hợp, lớp API client và kịch bản trình duyệt.

Frontend không cần bước build; có thể phục vụ nguyên thư mục bằng web server. Khi tách frontend, giữ asset tại /ui/, trỏ index.html tại /, đặt window.LIBRARY_API_BASE trong config.js đến origin API và thêm origin frontend vào CORS_ORIGINS. Không mở index.html trực tiếp bằng file://.

## Các màn hình

Bạn đọc: tra cứu (tên / tác giả / chủ đề), chi tiết, đăng ký / đăng nhập, phiếu mượn với bộ lọc trạng thái và phân trang, hạn trả, tiền phạt, hàng đợi.

Thủ thư: tổng quan, xác nhận giao / nhận trả / hủy phiếu, ghi nhận đã thu tiền phạt, quản lý đầu sách, ảnh bìa, bản sách và mã vạch, tác giả, chủ đề, hàng đợi.

Các danh sách books và loans dùng 12 mục/trang. API chưa có total: nút Tiếp dựa trên số bản ghi trả về; trang cuối đủ 12 mục có thể dẫn sang trang trống, có nút Trước. Fines / waitlist / tác giả / chủ đề theo API hiện tại chưa phân trang.

Mã vạch được nhập hoặc dùng máy quét kiểu bàn phím ở trường mã vạch. Chưa có camera quét barcode và chưa có endpoint tìm phiếu theo barcode. Màn giao nhận đối chiếu mã vạch trên phiếu đã được API cấp, không chọn lại bản khác.

## Luồng kiểm tra thủ công

1. Đăng nhập bạn đọc, tìm “Cơ sở dữ liệu”, mở chi tiết, đặt mượn.
2. Mở Phiếu mượn: thấy tên sách, mã vạch và Chờ nhận sách.
3. Đặt thêm sách đến đủ 3 cuốn (demo đã có một cuốn đang mượn); đặt tiếp phải báo vượt giới hạn.
4. Chọn Học máy với Python đang hết bản, tham gia hàng đợi; xem vị trí ở Hàng đợi.
5. Đăng xuất; đăng nhập thủ thư; mở Giao & nhận trả, xác nhận giao phiếu vừa tạo.
6. Kiểm tra trạng thái Đang mượn và hạn trả. Nhận trả phiếu quá hạn ban đầu, mở Tiền phạt và ghi nhận đã thu sau khi xác nhận.
7. Quản lý đầu sách → thêm sách → lưu → thêm bản với mã vạch riêng → tải ảnh PNG/JPEG/WebP <=5 MiB.
8. Sửa tác giả / chủ đề, kiểm tra dữ liệu ở màn Tra cứu. Thử mã vạch trùng và ảnh quá 5 MiB để kiểm tra lỗi.
9. Thu nhỏ màn hình để kiểm tra thanh điều hướng, thẻ sách, biểu mẫu và cuộn ngang bảng.

## Kiểm thử đã chạy

- 12 kiểm thử nghiệp vụ Back end: PASS.
- qa/integration_test.py: PASS; phục vụ frontend, phân quyền, đặt/giao/trả, dữ liệu mở rộng của phiếu, upload và đọc ảnh, OpenAPI khớp mã nguồn.
- qa/api_client_test.mjs: PASS; URL, Bearer, JSON, multipart, lỗi nghiệp vụ, hết phiên, lỗi mạng khi ghi và URL ảnh.
- node --check cho app.js / api.js: PASS.
- Kiểm thử trình duyệt chưa chạy được: Chromium bị môi trường thực thi chặn tạo socket. Chưa xác minh trực quan desktop/mobile; không có ảnh chụp màn hình đã kiểm chứng.

Lệnh lặp lại:
```bash
python -m unittest discover -s tests -v
PYTHONPATH=. python qa/integration_test.py
node qa/api_client_test.mjs
```

Kịch bản trình duyệt (cần demo DB mới, máy có Chromium):
```bash
pip install playwright
playwright install chromium
# Terminal 1: DEMO_DATABASE_PATH=data/qa-new.sqlite3 python demo.py
# Terminal 2:
python qa/browser_test.py
```

Kịch bản trình duyệt thay đổi dữ liệu demo. Chưa kiểm tra deploy máy chủ thật, HTTPS hoặc tích hợp CI/CD; gói này chạy thử local.

## Phiên và xử lý lỗi

Session token lưu sessionStorage, không lưu mật khẩu. API kiểm tra quyền cuối cùng; ẩn menu không thay thế phân quyền. Hết phiên chuyển về đăng nhập. Biểu mẫu chặn nhấn gửi lặp trong khi xử lý, giữ lỗi trong dialog. Khi POST lỗi mạng/timeout, không tự gửi lại: tải lại danh sách trước để tránh trùng thao tác. Dữ liệu văn bản API được escape trước khi hiển thị HTML. Phạt, số bản còn và giới hạn mượn do Back end quyết định.
