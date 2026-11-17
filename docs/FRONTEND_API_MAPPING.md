# Giao diện → API

| Màn hình | API |
| --- | --- |
| Tra cứu | GET /books, /catalog/authors, /catalog/categories |
| Chi tiết | GET /books/{id}, /favorites/{id} khi đăng nhập |
| Mở sách | GET /books/{id}/pages/{page}?v=revision |
| Tiếp tục đọc | GET/PUT /books/{id}/progress; khách dùng localStorage |
| Yêu thích | GET /favorites; PUT/DELETE /favorites/{id} |
| Quản trị | POST/PUT/DELETE /books, /catalog; POST /books/{id}/ebook và /cover |
| Tài khoản | /auth/register, /auth/login, /auth/me, /auth/logout |

Prefix chung /api/v1. Không có màn hình hay API mượn trả/tiền phạt/thông báo.
