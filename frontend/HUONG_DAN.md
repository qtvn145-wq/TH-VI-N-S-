# Front end sách điện tử

Giải nén cùng Backend_Ebook.zip và DevOps_Ebook.zip. Không cần npm install hay build để chạy giao diện.

- src/app.js: danh mục, đăng nhập, yêu thích, quản trị PDF.
- src/reader.js: một/hai trang, hoạt ảnh lật, phóng to, toàn màn hình, phím mũi tên/vuốt.
- src/api.js: kết nối API và session.
- styles/style.css: responsive, hoạt ảnh và reduced motion.

Chạy qua Compose hoặc `uvicorn serve:app --port 8081` tại gốc. Không mở index.html bằng file://. Có thể chỉnh LIBRARY_API_BASE trong config.js khi chạy khác origin; backend phải cho phép CORS của origin đó.

Kiểm thử: `npm --prefix frontend run check`, `npm --prefix frontend test`.

## Quản lý tài khoản

Đăng nhập thủ thư → Quản lý tài khoản. Tìm tên/email, thêm, sửa tên/email/vai trò, đổi mật khẩu có xác nhận hai lần, hoặc xóa sau xác nhận. Quản trị (thủ thư) được quản lý cả sách và tài khoản. Khi đổi email/vai trò/mật khẩu của chính mình, đăng nhập lại. Hệ thống giữ ít nhất một quản trị viên và không cho tự xóa tài khoản đang đăng nhập.

## Không gian đọc — cập nhật kích thước và điều khiển

- Mặc định 100%: hiển thị trọn trang/cặp trang, vừa cả chiều ngang và chiều cao vùng đọc, không cần cuộn. Tự tính lại theo kích thước ảnh PDF khi chuyển trang, đổi chế độ, thay kích thước cửa sổ hoặc toàn màn hình. Giữ đúng tỷ lệ ảnh; khoảng trống hai bên phụ thuộc tỷ lệ trang. Thanh tên sách và công cụ gộp một hàng trên máy tính, thông báo chỉ hiện khi tải hoặc có lỗi. Trên 100% mới cần cuộn để xem phần phóng lớn.
- Bấm nút ở mép phải để tiến trang, mép trái để lùi trang. Có thể dùng phím ←/→ khi không nhập liệu. Chế độ hai trang chuyển cả cặp trang.
- Chọn 25%, 50%, 75%, 100%, 125%, 150%, 175%, 200%; nút −/+ thay đổi 25% mỗi lần. Mở sách mới đặt lại 100%. Trên 100% có thể cuộn ngang/dọc; tắt cử chỉ vuốt chuyển trang để tránh lật nhầm khi cuộn.
- Toàn màn hình áp dụng cho tài liệu web, không gọi trên dialog. Nút hiển thị đúng trạng thái vào/thoát; đóng sách sẽ thoát chế độ toàn màn hình do sách mở. Nếu trình duyệt chặn tính năng, có hướng dẫn dùng F11 trên máy tính.

Cập nhật: giải nén Frontend_Ebook.zip vào thư mục gốc dự án, ghi đè frontend/. Docker: `docker compose up -d --build web`, sau đó Ctrl+Shift+R. Nếu chạy Python trực tiếp, tải lại trang bằng Ctrl+Shift+R.

## Quên mật khẩu

Đăng nhập → Quên mật khẩu? → nhập email đã đăng ký. Mở liên kết trong email trong 15 phút, nhập mật khẩu mới hai lần. Đổi thành công sẽ đăng xuất các phiên cũ. Nếu thiếu cấu hình gửi thư, giao diện báo liên hệ quản trị viên. Cần cập nhật cả Back end và DevOps để dùng chức năng này; xem docs/QUEN_MAT_KHAU.md trong gói DevOps.
