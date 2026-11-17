# API sách điện tử

Prefix `/api/v1`. Swagger tại `/docs`. Chi tiết schema và mã lỗi trong `openapi.json` (được sinh từ mã hiện tại).

| API | Quyền | Mục đích |
| --- | --- | --- |
| POST /auth/register | Công khai | Tạo tài khoản reader |
| POST /auth/login | Công khai | Nhận Bearer session 8 giờ |
| GET /auth/me; POST /auth/logout | Đã đăng nhập | Tài khoản/đăng xuất |
| GET /books | Công khai | q, author, category_id, readable_only, sort=id/newest/title, limit/offset |
| GET /books/{id} | Công khai | Thông tin + page_count + ebook_revision |
| POST /books; PUT /books/{id}; DELETE /books/{id} | librarian | Thêm/sửa/ẩn sách |
| GET /catalog/{kind} | Công khai | authors hoặc categories |
| POST/PUT/DELETE /catalog/{kind}[/{id}] | librarian | Quản trị danh mục |
| POST /books/{id}/cover | librarian | Multipart file JPEG/PNG/WebP <=5 MiB |
| POST /books/{id}/ebook | librarian | Multipart file PDF <=25 MiB, <=500 trang |
| GET /books/{id}/ebook | Công khai | book_id, page_count, revision |
| GET /books/{id}/pages/{page}?v={revision} | Công khai | JPEG của trang, đánh số từ 1 |
| GET /favorites | Đã đăng nhập | Danh sách yêu thích riêng, phân trang |
| GET/PUT/DELETE /favorites/{id} | Đã đăng nhập | Trạng thái/lưu/bỏ yêu thích |
| GET /books/{id}/progress | Đã đăng nhập | Trang gần nhất, mặc định 1 |
| PUT /books/{id}/progress | Đã đăng nhập | JSON {page, revision}; phải đúng phiên bản PDF |
| GET /health | Công khai | Kiểm tra schema 3 |

Không có API loans, fines, copies, waitlist hoặc reminders. Tệp PDF được xử lý trong tiến trình con với thời gian tối đa 20 giây mỗi bước; Linux áp dụng thêm giới hạn CPU/bộ nhớ. Giới hạn trang và kích thước được kiểm tra trước khi công bố. JavaScript trong PDF không được chạy trên trình duyệt; người đọc nhận ảnh trang.

Thay PDF tạo revision mới và đặt lại tiến độ đọc. Trang/tiến độ yêu cầu revision cũ trả 409. Trang ngoài phạm vi trả 404 (ảnh) hoặc 422 (tiến độ). PDF sai/hỏng/có mật khẩu/vượt giới hạn trang trả 415 hoặc 422, quá lớn trả 413. PDF và ảnh cache cũ được giữ; sao lưu chứa cả chúng. Chưa có công cụ tự dọn phiên bản cũ.

Quyền đọc là công khai cho sách chưa bị ẩn. Không có DRM/chống chụp màn hình; không dùng cơ chế này như một giải pháp kiểm soát bản quyền.

## Quản lý tài khoản (chỉ librarian)

| Phương thức | Đường dẫn | Chức năng |
|---|---|---|
| GET | `/api/v1/admin/users?q=&limit=13&offset=0` | Danh sách, tìm theo tên/email, phân trang |
| POST | `/api/v1/admin/users` | Tạo: email, name, password, role |
| PUT | `/api/v1/admin/users/{id}` | Sửa: email, name, role |
| PUT | `/api/v1/admin/users/{id}/password` | Đặt lại mật khẩu: password |
| DELETE | `/api/v1/admin/users/{id}` | Xóa tài khoản và dữ liệu cá nhân liên quan |

Danh sách/kết quả tài khoản chỉ chứa id, email, name, role. Không trả password_hash. Vai trò hợp lệ: reader, librarian. Đăng ký công khai vẫn chỉ tạo reader. Xung đột trả 409: EMAIL_EXISTS, LAST_ADMIN, CANNOT_DELETE_SELF, ACCOUNT_HAS_HISTORY. Đổi email/vai trò/mật khẩu thu hồi phiên. Các thao tác ghi được thực hiện trong transaction; lỗi xóa do lịch sử cũ sẽ rollback toàn bộ.

## Khôi phục mật khẩu

- `POST /api/v1/auth/forgot-password` — `{email}`; trả 202 `{ok:true}` cho cả email tồn tại/không tồn tại và yêu cầu bị giới hạn. Chưa cấu hình SMTP: 503 `RESET_EMAIL_UNAVAILABLE`.
- `POST /api/v1/auth/reset-password` — `{token,password}`; thành công 200 `{ok:true}`, liên kết không hợp lệ/hết hạn/đã dùng: 400 `RESET_LINK_INVALID`. Mật khẩu 10–128 ký tự.
- Liên kết gửi qua email: `PUBLIC_ORIGIN/#reset-password?token=...`; token được bỏ khỏi thanh địa chỉ sau khi giao diện đọc được, không đưa vào query gửi tới web server. Không cần đăng nhập để sử dụng hai API.

Xem [cấu hình gửi email](QUEN_MAT_KHAU.md).
