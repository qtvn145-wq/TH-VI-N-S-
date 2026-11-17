# CSDL sách điện tử — schema 3

| Bảng | Dữ liệu |
| --- | --- |
| users, sessions | Tài khoản reader/librarian và phiên đăng nhập |
| books | Tiêu đề, mô tả, bìa, archived |
| authors, categories | Tác giả và chủ đề |
| book_authors, book_categories | Quan hệ nhiều-nhiều |
| ebooks | book_id duy nhất, revision, page_count |
| reading_progress | Khóa user_id/book_id, revision và page |
| favorites | Khóa user_id/book_id, thời điểm lưu |

PDF lưu trong EBOOK_DIR dưới tên ngẫu nhiên `{revision}.pdf`; ảnh trang `{revision}-{page}.jpg`. Bìa ở MEDIA_DIR. Không sử dụng tên tệp người dùng làm đường dẫn lưu.

Cài mới chạy 000_ebook_fresh.sql. Nâng từ schema 1 chạy 002 rồi 003; từ schema 2 chạy 003. Migration 001/002 chỉ phục vụ nâng cấp cũ. Các bảng lịch sử cũ không bị xóa khi nâng cấp, và không được dùng bởi chương trình sách điện tử.
