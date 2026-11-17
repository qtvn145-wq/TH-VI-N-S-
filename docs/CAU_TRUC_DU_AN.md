# Ba phần tách riêng

| Gói | Nội dung |
| --- | --- |
| Backend_Ebook.zip | backend/app, migrations, tests, requirements, Dockerfile, hướng dẫn backend |
| Frontend_Ebook.zip | frontend/src, styles, tests, index/config, Dockerfile, hướng dẫn frontend |
| DevOps_Ebook.zip | devops/deploy, scripts, tests; cùng compose*.yaml, CI, docs, QA, serve.py, demo.py và README ở gốc |

Giải nén ba gói vào cùng một thư mục mới. Không tạo thêm một lớp thư mục Backend_Ebook/Frontend_Ebook/DevOps_Ebook: thư mục gốc phải trực tiếp có backend/, frontend/, devops/ và compose.yaml.

Front end gọi `/api/v1`, không truy cập CSDL. `reader.js` xử lý lật trang, phóng to, phím tắt, vuốt và tiến độ; `api.js` xử lý session và lỗi. Back end trả JPEG cho từng trang PDF. DevOps nối web với backend, lưu volume và sao lưu dữ liệu.

Chạy thử có sách mẫu: cài backend/requirements.lock rồi `python demo.py` tại gốc. Chạy thật: theo README, tạo tài khoản quản trị của bạn và upload PDF.
