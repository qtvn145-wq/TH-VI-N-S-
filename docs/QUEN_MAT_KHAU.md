# Quên mật khẩu qua email

Tại Đăng nhập → Quên mật khẩu? → nhập email → mở liên kết trong email → nhập mật khẩu mới hai lần → đăng nhập lại. Áp dụng cho bạn đọc và quản trị/thủ thư.

Liên kết có hiệu lực 15 phút, chỉ dùng một lần. CSDL lưu hash token; token không được trả trong API hoặc ghi vào log. Đổi mật khẩu thu hồi mọi phiên đăng nhập và liên kết khôi phục. Đổi email hoặc mật khẩu qua quản trị cũng làm liên kết trước đó mất hiệu lực. API dùng thông báo chung, không tiết lộ email đã đăng ký hay chưa. Giới hạn gửi: mỗi email tối đa 5 yêu cầu/giờ, cách nhau ít nhất 60 giây; toàn hệ thống tối đa 100 yêu cầu/giờ.

## Cấu hình Docker

Giữ file `.env` hiện tại, thêm/cập nhật các biến sau bằng thông tin máy chủ SMTP do nhà cung cấp email cấp:

```dotenv
PUBLIC_ORIGIN=http://localhost:8081
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_SECURITY=starttls
SMTP_USER=dia-chi-hoac-ten-dang-nhap-smtp
SMTP_PASSWORD=mat-khau-smtp
SMTP_FROM=thu-vien@example.com
```

Các giá trị trên chỉ minh họa, phải thay bằng thông tin thật. `SMTP_FROM` phải là địa chỉ được nhà cung cấp cho phép gửi. Nếu nhà cung cấp dùng TLS trực tiếp, đặt `SMTP_SECURITY=ssl`, thường dùng cổng 465. Không hỗ trợ gửi mật khẩu SMTP qua kết nối không mã hóa. Không đưa `.env` lên Git hoặc gửi mật khẩu SMTP trong chat.

`PUBLIC_ORIGIN` là địa chỉ người nhận truy cập được. Khi dùng tên miền/Cloudflare, thay bằng `https://ten-mien-cua-ban` (không có đường dẫn, query hoặc dấu #). `localhost` chỉ phù hợp khi mở email trên chính máy đang chạy ứng dụng. Địa chỉ này được cấu hình cố định; không lấy từ header Host của yêu cầu.

Giải nén cả ba gói mới vào thư mục gốc dự án, ghi đè mã nguồn. Sao lưu dữ liệu trước khi nâng cấp schema. Sau đó:

```bash
docker compose up -d --build --wait
```

Dịch vụ migrate tự nâng schema từ 3 lên 4, thêm bảng khôi phục mật khẩu và giới hạn gửi; giữ nguyên sách và tài khoản. Không cần tạo lại thủ thư. Nhấn Ctrl+Shift+R sau cập nhật.

Nếu chưa cấu hình SMTP, API trả 503 và giao diện hướng dẫn liên hệ quản trị viên. Nếu cấu hình đủ nhưng SMTP từ chối gửi, kiểm tra `docker compose logs --tail=100 backend`; log báo lỗi gửi chung, không ghi thông tin bí mật. Người dùng kiểm tra cả thư rác và thử lại sau 60 giây. Tác vụ gửi chạy trong tiến trình backend; nếu tiến trình bị dừng giữa lúc gửi thì cần yêu cầu lại, chưa có hàng đợi email bền vững.

## Chạy Python trực tiếp

Python không tự đọc `.env`. Khai báo các biến trên trong môi trường chạy Uvicorn (hoặc EnvironmentFile của systemd). Khởi động lại ứng dụng; AUTO_MIGRATE mặc định true sẽ nâng schema. Giữ cùng DATABASE_PATH đang sử dụng.

## Kiểm tra email thật sau cấu hình

1. Chọn Quên mật khẩu với email của tài khoản bạn kiểm soát.
2. Kiểm tra thư nhận được và tên miền trong liên kết.
3. Mở liên kết, đặt mật khẩu mới, đăng nhập thành công.
4. Mở lại liên kết đã dùng: máy chủ phải từ chối.

Kiểm thử tự động dùng SMTP giả lập; việc nhận email thật phụ thuộc cấu hình và nhà cung cấp của bạn.
