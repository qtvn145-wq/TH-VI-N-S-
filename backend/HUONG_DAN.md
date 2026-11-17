# Back end sách điện tử

Giải nén cùng Frontend_Ebook.zip và DevOps_Ebook.zip vào cùng thư mục gốc.
Từ thư mục gốc: `pip install -r backend/requirements.lock`, `python -m backend.app.cli init`, `python -m backend.app.cli librarian`, `uvicorn serve:app --port 8081`.

API độc lập: `uvicorn backend.app.main:app --host 127.0.0.1 --port 8000`. Biến môi trường DATABASE_PATH, MEDIA_DIR, EBOOK_DIR điều khiển lưu trữ. Giữ working directory là thư mục chứa backend/ vì worker PDF gọi module backend.app.pdf_worker.

Upload PDF 25 MiB/500 trang. Đọc trang công khai; quản lý PDF chỉ dành cho librarian. Phân quyền favorites/progress theo session. PDFium xử lý trong tiến trình con có timeout. Cài mới không có bảng mượn/trả; nâng cấp giữ dữ liệu lịch sử cũ.

Kiểm thử: `python -m unittest discover -s backend/tests -v`.
