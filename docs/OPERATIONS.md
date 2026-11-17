# Vận hành thư viện sách điện tử

## Thành phần

Compose ở gốc giữ project name `thu-vien-so`, volume `library_data`, cổng host mặc định 8081. Backend dùng FastAPI và PDFium; web dùng Nginx. Migration chạy trước backend. Chỉ web mở cổng host; API không mở trực tiếp.

Dữ liệu trong container: `/data/library.db`, `/data/covers/`, `/data/ebooks/`. SQLite phù hợp triển khai nhỏ trên một máy; không chia sẻ volume SQLite giữa nhiều máy chủ.

## Sao lưu

```bash
bash devops/scripts/ops.sh backup
```

Lệnh dừng backend, sao lưu SQLite + ảnh bìa + PDF/ảnh trang, kiểm checksum và khởi động lại backend. Archive ở `backups/`, giữ 14 ngày sau lần sao lưu thành công. Sao lưu chứa các phiên bản PDF cũ; theo dõi dung lượng ổ đĩa. `BACKUP_REMOTE` có thể dùng với rsync như script hiện có.

Khôi phục phải dùng **volume rỗng**, không ghi đè dữ liệu đang chạy. Dừng các tiến trình ghi, chọn volume đích riêng qua Compose override rồi chạy:

```bash
docker compose run --rm --no-deps maintenance python devops/scripts/backup.py restore TEN_FILE_BACKUP.tar.gz
```

Kiểm tra sách, ảnh bìa, mở PDF và tiến độ sau khôi phục. Không downgrade mã nguồn cũ trên schema 3; rollback cần khôi phục backup tương ứng với mã cũ.

## Lịch tự động

```bash
sudo bash devops/scripts/install-timers.sh
sudo systemctl enable --now library-backup.timer library-monitor.timer
```

Chỉ có backup và monitor. Installer không tự bật timer. WSL cần systemd/Docker hoạt động để sử dụng lịch này. Monitor mặc định kiểm tra http://localhost:8081, ổ đĩa <85%, backup mới hơn 26 giờ.

Nếu nâng cấp từ phiên bản có nhắc hạn, tắt `library-reminders.timer` và dừng `library-reminders.service` đã cài trên host. Bộ mã mới không gửi email hay có cấu hình SMTP; việc xóa file khỏi repo không tự gỡ unit cũ trên host.

## Build và HTTPS

Build context là gốc dự án; Dockerfile tại `backend/Dockerfile` và `frontend/Dockerfile`. Nginx cho phép upload 26 MiB (PDF 25 MiB + multipart), chờ API 75 giây. Ảnh trang được cache trên đĩa; bản này không dùng CDN.

`compose.prod.yaml` bổ sung Caddy HTTPS (DOMAIN/ACME_EMAIL thật); `compose.https-local.yaml` phục vụ HTTPS nội bộ cổng 8443. `compose.tunnel.yaml` là tùy chọn tunnel; không cần cho chạy local. Không tự triển khai công khai trong gói bàn giao.

```bash
bash devops/scripts/setup.sh
docker compose config --quiet
docker compose up -d --build --wait
bash devops/scripts/smoke.sh
```

CI chạy kiểm thử, build Compose, smoke và backup. Deploy chỉ qua workflow_dispatch, inputs.deploy và environment production đã cấu hình. Chưa xác nhận build Docker trong môi trường bàn giao vì không có Docker.
