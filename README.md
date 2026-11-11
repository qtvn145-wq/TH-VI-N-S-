# Back end — Thư viện số Khoa CNTT

Bản mới độc lập, không sử dụng tài liệu cũ. Workspace ban đầu không có mã nguồn/CSDL được cung cấp, vì vậy không có hệ thống cũ để rà soát. Đây là MVP chạy được bằng FastAPI + SQLite; không tuyên bố đã triển khai production.

## Chạy trên Ubuntu/WSL

Python 3.12. Giải nén rồi vào thư mục dự án:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
set -a
source .env
set +a
python -m app.cli init
python -m app.cli librarian
uvicorn app.main:app --host 0.0.0.0 --port 8081
```

`.env` không tự nạp: dùng lệnh source như trên hoặc công cụ triển khai cấp biến môi trường. Mật khẩu thủ thư được nhập kín qua CLI; không có tài khoản/mật khẩu mặc định. Bạn đọc đăng ký qua API. Truy cập http://localhost:8081/docs, dùng auth/login rồi nút Authorize để nhập access_token. Health: http://localhost:8081/api/v1/health.

## Các tệp bàn giao

- docs/ERD.md: sơ đồ quan hệ Mermaid, quy tắc trạng thái/ràng buộc.
- docs/API.md: danh sách endpoint, quyền, luồng tích hợp và lỗi giao diện.
- docs/openapi.json: OpenAPI sinh tự động từ mã nguồn.
- migrations/001_initial.sql: CSDL có khóa ngoại, CHECK và unique index.
- app/: mã API, kết nối giao dịch, xác thực, CLI và tác vụ email.
- tests/test_api.py: kiểm thử nghiệp vụ bằng unittest + TestClient.
- docs/TEST_RESULTS.txt: kết quả chạy thực tế.

```bash
python -m unittest discover -s tests -v
python -c "import json; from app.main import app; print(json.dumps(app.openapi(),ensure_ascii=False,indent=2))" > docs/openapi.json
```

Kiểm thử tạo DB tạm, không sửa dữ liệu thật. Ảnh kiểm thử lưu trong MEDIA_DIR; có thể đặt MEDIA_DIR riêng khi chạy test.

## Nhắc hạn

```bash
python -m app.cli reminders
python -m app.cli reminders --send
```

Mặc định chỉ dry-run, không gửi. --send cần SMTP_HOST, SMTP_PORT (587), SMTP_FROM và tùy chọn SMTP_USER/SMTP_PASSWORD; dùng STARTTLS và xác minh chứng chỉ. Chọn loan đang borrowed, hạn trong ngày mai hoặc sớm hơn; mỗi loan tối đa một dấu gửi thành công/ngày. Không có SMTP thật được cung cấp, nên chưa kiểm tra gửi mail end-to-end và chưa gửi email nào.

Chạy một worker vào 08:00 hằng ngày bằng cron/systemd của máy chủ, với thư mục làm việc, venv và biến môi trường như ứng dụng. Việc cài lịch do DevOps thực hiện. Tác vụ giữ transaction khi gửi để tránh worker chồng nhau; không phù hợp tải lớn. SMTP không đảm bảo exactly-once: crash sau khi SMTP nhận nhưng trước commit có thể gửi trùng khi thử lại. Cần outbox/queue chuyên dụng nếu triển khai lớn.

## Phạm vi và các quyết định cần chốt

- Mặc định 14 ngày, 2.000 VND/ngày, cấu hình qua env. Ba cuốn bao gồm reserved + borrowed; hàng đợi không chiếm suất. Hạn bắt đầu khi giao.
- FIFO hiện yêu cầu người đầu tự đặt, không tự cấp sách hoặc email báo có sách. Chưa tự hết hạn chỗ giữ/lượt chờ. Thủ thư xử lý các lượt bị bỏ quên.
- SQLite dùng WAL và khóa ghi cho triển khai một máy với tải nhỏ. Tìm tiếng Việt dùng casefold trong ứng dụng, phân biệt dấu; không tối ưu kho dữ liệu lớn. Khi chuyển PostgreSQL cần migration mới và khóa hàng user/copy, chạy lại kiểm thử tranh chấp, không chỉ đổi chuỗi kết nối.
- Authentication dùng mật khẩu scrypt, session token ngẫu nhiên lưu hash và hết hạn; đăng ký không nhận role. Chưa có reset mật khẩu/xác minh email/khóa tài khoản/rate limit. Cần reverse proxy HTTPS và rate limit đăng nhập/đăng ký trước khi công khai.
- CSDL/ảnh ở data/; phải sao lưu cả hai. Không commit .env, data hoặc mật khẩu. Ảnh được giải mã và mã hóa lại; ảnh cũ khi thay chưa tự dọn để tránh mất tham chiếu trong khi phục hồi.
- Không có API xóa lịch sử mượn, không xóa copy từng được dùng. Không có bulk import, gia hạn, mất/hỏng sách, miễn phạt hoặc thanh toán trực tuyến trong phạm vi này.

Tài liệu kỹ thuật tham khảo: https://fastapi.tiangolo.com/tutorial/request-files/ và https://fastapi.tiangolo.com/reference/security/. Thiết kế session và nghiệp vụ là quyết định riêng của dự án.
