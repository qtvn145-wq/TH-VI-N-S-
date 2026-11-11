# Đối chiếu Front end / OpenAPI

Đã đọc docs/openapi.json, docs/API.md, app/schemas.py và app/main.py của ZIP đầu vào trước tích hợp. Prefix /api/v1.

| Màn hình | Endpoint | Trường dùng / hành vi |
|---|---|---|
| Đăng nhập / đăng ký | POST auth/login, auth/register; GET auth/me; POST auth/logout | email,password,name; access_token, role reader/librarian; opaque session, không phải JWT |
| Tra cứu | GET books; GET catalog/authors, catalog/categories | q,author,category_id,limit,offset; title,description,cover_url,author_ids,category_ids,available_copies |
| Chi tiết | GET books/{id}; POST loans | book_id; API tự chọn copy, reserved giữ chỗ ngay |
| Phiếu mượn | GET loans?status=&limit=&offset= | status,reserved_at,borrowed_at,due_date,returned_at,overdue_days,estimated_fine và trường hiển thị mở rộng |
| Hủy yêu cầu | POST loans/{id}/cancel | Chỉ reserved; bạn đọc sở hữu hoặc thủ thư |
| Giao / trả | POST loans/{id}/handover, loans/{id}/return | Không gửi body; thủ thư xác nhận bản đã được cấp |
| Tiền phạt | GET fines; POST fines/{id}/pay | loan_id,amount,paid_at; ghi nhận đã thu, không thanh toán online |
| Hàng đợi | GET/POST waitlist; DELETE waitlist/{id}; GET books/{id} | book_id,user_id,position,created_at; chỉ tham gia khi hết bản; tự đặt khi có bản và tới lượt |
| Đầu sách | POST books; PUT/DELETE books/{id} | title,description,author_ids,category_ids; PUT đầy đủ trường chỉnh sửa |
| Ảnh bìa | POST books/{id}/cover | multipart field file; <=5 MiB; URL từ origin API + cover_url |
| Bản sách | GET/POST books/{id}/copies; PUT copies/{id} | barcode,retired,loan_status; không có DELETE copy |
| Tác giả / chủ đề | GET/POST catalog/{kind}; PUT/DELETE catalog/{kind}/{id} | authors/categories; id,name |
| Tổng quan | GET stats | books,borrowed,overdue,unpaid_fines |

## Bổ sung tương thích cho LoanOut

ZIP đầu vào chỉ trả user_id và copy_id. Bạn đọc không được GET copies; không có GET user theo ID. Vì vậy không thể nối tên sách/mã vạch/tên người đọc chỉ bằng các API gốc.

Bản bàn giao thêm bốn trường tùy chọn cho LoanOut: book_id, book_title, barcode, reader_name. Hàm loan_out truy vấn các quan hệ có sẵn để trả dữ liệu; các endpoint và kiểm tra quyền không đổi. Thay đổi tại app/schemas.py và app/main.py; docs/openapi.json được sinh lại. Frontend có fallback hiển thị mã ID nếu kết nối Back end gốc chưa bổ sung.

Khi ghép với nhánh Back end riêng, chuyển hai thay đổi này hoặc dùng backend đã kèm gói. Lịch sử hiển thị tên sách/tên người đọc hiện tại, không phải bản chụp tên tại thời điểm mượn.

## Quyết định nghiệp vụ xác nhận từ mã nguồn

- Giới hạn 3 = reserved + borrowed, không gồm waitlist.
- Ngày trả bắt đầu khi handover; fine do server tính, frontend chỉ định dạng VND.
- reserved đã gắn copy_id, không chọn lại copy khi giao.
- returned giữ estimated_fine; paid_at lấy từ fines, không suy ra đã trả tiền từ trạng thái phiếu.
- Không có API gia hạn, từ chối với lý do, tìm user theo email, tìm loan theo barcode hay refresh token; không tạo thao tác giả cho các chức năng này.
