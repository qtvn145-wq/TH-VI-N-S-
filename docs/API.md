# Hợp đồng tích hợp Front end v1

Base URL chạy local: `http://localhost:8081/api/v1`. Swagger: `/docs`; ReDoc: `/redoc`; JSON: `/openapi.json`. Bản chụp schema nằm trong `docs/openapi.json` và được sinh từ chính mã nguồn. Mọi request body dùng JSON, trừ upload dùng multipart/form-data trường `file`.

Đăng ký chỉ tạo reader. CLI tạo thủ thư. Login trả `{access_token,token_type:"bearer",expires_in:28800}`. Gửi `Authorization: Bearer <access_token>`. Token opaque có hạn 8 giờ, có thể thu hồi bằng logout; không phải JWT. Không có refresh token. Không lưu password hoặc token vào URL.

| Nhóm | Method và đường dẫn (sau /api/v1) | Quyền / mục đích |
|---|---|---|
| Auth | POST /auth/register; POST /auth/login | Công khai; đăng ký, đăng nhập |
| Auth | GET /auth/me; POST /auth/logout | Đã đăng nhập |
| Danh mục | GET /books?q=&author=&category_id=&limit=20&offset=0 | Công khai; tên sách/tác giả không phân biệt hoa thường, có dấu |
| Danh mục | GET /books/{id} | Chi tiết, author_ids, category_ids, available_copies |
| Danh mục | GET /catalog/{kind} | kind là authors hoặc categories; ánh xạ ID sang tên |
| Quản lý | POST /books; PUT /books/{id}; DELETE /books/{id} | Thủ thư; PUT thay toàn bộ trường chỉnh sửa |
| Quản lý | POST /catalog/{kind}; PUT hoặc DELETE /catalog/{kind}/{id} | Thủ thư |
| Bản sách | GET hoặc POST /books/{id}/copies; PUT /copies/{id} | Thủ thư; mã vạch, thanh lý |
| Ảnh bìa | POST /books/{id}/cover | Thủ thư; PNG/JPEG/WebP tối đa 5 MiB, kiểm tra giải mã, chuyển JPEG |
| Mượn | POST /loans | Đã đăng nhập; body {"book_id":1}; trả 201 và loan |
| Lịch sử | GET /loans?status=&limit=20&offset=0 | Bạn đọc xem của mình; thủ thư xem toàn bộ |
| Mượn | POST /loans/{id}/cancel | Chủ phiếu hoặc thủ thư, chỉ reserved |
| Mượn | POST /loans/{id}/handover; POST /loans/{id}/return | Chỉ thủ thư, kiểm tra trạng thái |
| Phạt | GET /fines | Bạn đọc xem của mình; thủ thư xem toàn bộ |
| Phạt | POST /fines/{id}/pay | Thủ thư ghi nhận đã thu tiền; không tích hợp cổng thanh toán |
| Hàng đợi | POST /waitlist; GET /waitlist; DELETE /waitlist/{id} | Body book_id; bạn đọc quản lý của mình; thủ thư được xem/xóa toàn bộ |
| Thống kê | GET /stats | Thủ thư; số đầu sách, đang mượn, quá hạn, tổng phạt chưa thu |
| Vận hành | GET /health | Kiểm tra truy cập DB |

GET books/loans trả array; limit tối đa 100, offset >= 0, chưa có total. GET fines/catalog/waitlist chưa phân trang; bản MVP cần thêm phân trang khi dữ liệu lớn. LoanOut có overdue_days và estimated_fine; phiếu đã trả giữ nguyên mức phạt, còn trạng thái thu tiền xem fines. Ảnh lấy từ origin API + cover_url. Mã vạch là chuỗi, không tự tạo ảnh mã vạch.

Ví dụ tạo đầu sách:
```json
{"title":"Cơ sở dữ liệu","description":"Giáo trình","author_ids":[1],"category_ids":[1]}
```
Ví dụ tạo bản: `{"barcode":"CNTT-000001"}`. PUT bản: `{"barcode":"CNTT-000001","retired":false}`.

Luồng giao diện: tìm sách → chọn book_id → POST loans → hiển thị reserved → thủ thư handover → borrowed/due_date → thủ thư return → returned + fines. Bạn đọc không được tự giao/trả sách. Lượt chờ chỉ được thêm khi hết bản; sau khi có bản, người đầu hàng đợi gọi POST loans.

| HTTP / detail | Hiển thị gợi ý |
|---|---|
| 401 / INVALID_CREDENTIALS hoặc INVALID_SESSION | Thông tin sai hoặc phiên hết hạn, đăng nhập lại |
| 403 / LIBRARIAN_REQUIRED hoặc FORBIDDEN | Không đủ quyền |
| 404 / NOT_FOUND | Đối tượng không tồn tại |
| 409 / NO_COPY_AVAILABLE | Hết sách, có thể tham gia hàng đợi |
| 409 / LOAN_LIMIT_REACHED | Đã giữ/mượn tối đa 3 cuốn |
| 409 / QUEUE_PRIORITY | Bản sách ưu tiên người đầu hàng đợi |
| 409 / INVALID_LOAN_STATE | Trạng thái đã thay đổi, tải lại phiếu |
| 409 / DATA_CONFLICT | Trùng email/mã vạch/tên/lượt chờ hoặc dữ liệu còn tham chiếu |
| 409 / COPY_IN_USE; ALREADY_PAID; COPY_AVAILABLE | Không thể thanh lý; đã thu phạt; vẫn còn bản để đặt |
| 413 / FILE_TOO_LARGE; 415 / INVALID_IMAGE | Ảnh vượt giới hạn hoặc định dạng/nội dung không hợp lệ |
| 422 | Lỗi kiểm chứng trường; detail là array chuẩn FastAPI |

Các lỗi nghiệp vụ trả `{"detail":"CODE"}`. Khi thiếu Bearer header, framework trả lỗi xác thực chuẩn. Sau request timeout không tự retry POST tạo loan: tải lại lịch sử trước vì chưa có Idempotency-Key. Giao/trả lặp trả 409, không tăng tiền phạt hoặc tạo thêm phiếu.
