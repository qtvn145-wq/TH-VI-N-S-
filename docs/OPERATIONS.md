# DevOps — Thư viện số Khoa CNTT

Hướng dẫn vận hành cho bản tích hợp Front end, Back end và DevOps trên `main`.
Bắt đầu từ [README chung](../README.md); cấu hình thực tế trong repo là nguồn tham chiếu.

## 1. Kết quả rà soát

| Thành phần | Mã nguồn hiện tại | Lệnh / cấu hình |
|---|---|---|
| API | FastAPI, Python; `app/main.py` | `uvicorn app.main:app --host 0.0.0.0 --port 8000` |
| Giao diện | HTML/CSS/JS thuần trong `frontend/` | Nginx phục vụ `/` và `/ui/`; không có npm build |
| Bản chạy gộp cũ | `serve.py` | `uvicorn serve:app --host 0.0.0.0 --port 8081` |
| Database | SQLite, truy vấn trực tiếp bằng sqlite3 | `DATABASE_PATH`; không hỗ trợ PostgreSQL/MySQL bằng đổi URL |
| Migration | `migrations/001_initial.sql`, `PRAGMA user_version=1` | `python -m app.cli init` |
| Ảnh bìa | `MEDIA_DIR`, URL `/media/...` | Volume `/data/covers` |
| Xác thực | Bearer session, hash token trong database | Không dùng JWT, không cần JWT_SECRET |
| Nhắc hạn | CLI SMTP STARTTLS | `python -m app.cli reminders [--send]` |
| Kiểm thử | unittest + Node API client test | Lệnh ở mục 9 |

SQLite là database nhúng, được đóng gói qua Python runtime và lưu trên volume
`library_data`, cùng với ảnh bìa. Không tạo container PostgreSQL giả vì mã nguồn
hiện tại không tương thích. Cấu hình này dành cho một máy chủ, một API worker;
không scale nhiều host và không đặt SQLite trên NFS. Chuyển CSDL cần sửa backend.

## 2. Chạy thử trên Ubuntu/WSL

Cần Docker Engine + Docker Compose v2 có `--wait`, hoặc Docker Desktop tích hợp WSL.
Chạy trong thư mục đã giải nén, nơi có `compose.yaml`:

```bash
bash scripts/setup.sh
docker compose config --quiet
docker compose up -d --build --wait
bash scripts/smoke.sh http://localhost:8081
docker compose run --rm --no-deps backend python -m app.cli librarian
```

Mở http://localhost:8081, Swagger http://localhost:8081/docs.
Lệnh tạo thủ thư yêu cầu nhập email, tên và mật khẩu tối thiểu 10 ký tự.
Không tự tạo tài khoản demo trên production.

```bash
docker compose ps
docker compose logs --tail=100 backend web
docker compose stop
```

`docker compose down` giữ volume. **Không dùng `down -v` nếu cần giữ dữ liệu.**
Giao diện và API cùng origin, nên `frontend/config.js` giữ `/api/v1`.
Backend không mở cổng ra host; cổng web chỉ bind `127.0.0.1:8081`.

## 3. Biến môi trường và secrets

`bash scripts/setup.sh` tạo `.env` từ `deploy/env.example`, thư mục secrets và backups.
Compose đọc `.env`; Python chạy trực tiếp không tự đọc tệp này.

| Tên | Ý nghĩa / mặc định |
|---|---|
| HTTP_PORT | Cổng local 8081 |
| IMAGE_TAG | Tag ảnh local; giữ `local` khi dùng pipeline đi kèm |
| PUBLIC_ORIGIN | `http://localhost:8081`; đổi sang URL HTTPS khi production |
| DATABASE_PATH | Compose cố định `/data/library.db` |
| MEDIA_DIR | Compose cố định `/data/covers` |
| AUTO_MIGRATE | Compose đặt false; service migrate chạy trước API |
| LOAN_DAYS | 14 |
| DAILY_FINE | 2000 VND/ngày |
| SMTP_HOST, SMTP_PORT | Máy chủ SMTP và cổng STARTTLS; thường 587 |
| SMTP_FROM, SMTP_USER | Địa chỉ gửi và tài khoản SMTP |
| SMTP_PASSWORD_FILE | `/run/secrets/smtp_password`, chỉ mount cho reminders |
| BACKUP_DIR | `./backups`; giữ mặc định để monitor/offsite hoạt động đồng bộ |
| DOMAIN, ACME_EMAIL | Tên miền thật và email cấp chứng chỉ |
| COMPOSE_FILE | Production: `compose.yaml:compose.prod.yaml` |

Ghi SMTP password vào `secrets/smtp_password.txt` bằng trình soạn thảo,
không đưa password vào lệnh shell hoặc Git. Thư mục secrets quyền 700;
tệp secret quyền 644 để UID 10001 trong container đọc được qua bind mount.
Compose secrets ở đây là tệp mount, không phải kho secrets mã hóa.
`.env`, secrets, database và backups đã được bỏ qua bởi Git và Docker build context.

SMTP hiện hỗ trợ STARTTLS, không hỗ trợ implicit TLS cổng 465.
Chỉ chạy thử xem danh sách đếm, không gửi:

```bash
docker compose run --rm --no-deps reminders
```

Sau khi cấu hình SMTP, gửi thực tế bằng `bash scripts/ops.sh reminders`.
Một phiếu tối đa một email/ngày khi thành công; SMTP nhận thư rồi tiến trình chết
trước commit vẫn có thể gây gửi trùng khi chạy lại. Không bật nhiều lịch nhắc hạn.

## 4. Máy chủ và HTTPS

1. Chuẩn bị Ubuntu có Docker Engine/Compose, dung lượng cho ảnh Docker và backups.
2. Đặt bản mã nguồn tại `/opt/thu-vien-so`; chạy setup, sửa `.env`.
3. Trỏ DNS A (và AAAA nếu dùng IPv6) của tên miền về máy chủ.
4. Mở inbound TCP 80/443; SSH giới hạn theo IP quản trị. Không mở port API/SQLite.
5. Thêm vào `.env` (thay giá trị ví dụ):

```dotenv
COMPOSE_FILE=compose.yaml:compose.prod.yaml
DOMAIN=library.example.edu.vn
ACME_EMAIL=admin@example.edu.vn
PUBLIC_ORIGIN=https://library.example.edu.vn
```

```bash
docker compose up -d --build --wait
docker compose logs --tail=100 proxy
bash scripts/smoke.sh https://library.example.edu.vn
curl -I http://library.example.edu.vn
```

Caddy xin/gia hạn chứng chỉ tự động, HTTP chuyển sang HTTPS. Giữ volume
`caddy_data` để lưu chứng chỉ. Không dùng `curl -k` để kiểm tra nghiệm thu.
Cần thêm kiểm tra đăng nhập, đặt mượn, giao/trả, ảnh bìa trên trình duyệt.
Chưa có máy chủ/tên miền trong yêu cầu này, nên HTTPS công khai chưa được nghiệm thu.

## 5. Migration và cập nhật

Migration ban đầu idempotent, phiên bản schema hiện chỉ có số 1. Khi thêm schema
mới phải bổ sung migration có phiên bản và điều chỉnh readiness; không sửa âm thầm
SQL đã áp dụng hoặc chỉ tăng `user_version`. API tự migrate khi chạy trực tiếp;
trong Compose migration là bước riêng, thất bại thì API không khởi động mới.

Sau lần triển khai đầu, cập nhật source đã kiểm tra rồi chạy:

```bash
bash scripts/ops.sh deploy
bash scripts/smoke.sh
```

Lệnh build trước, dừng ghi, sao lưu, migrate rồi khởi động API/web.
Có downtime ngắn. Nếu migrate hoặc khởi động thất bại, kiểm tra logs và giữ API
ngừng cho đến khi xác minh schema; không tự chạy ảnh cũ trên schema mới.
Khi đổi Caddyfile, chạy `docker compose up -d proxy` và
`docker compose exec proxy caddy reload --config /etc/caddy/Caddyfile`.

## 6. Sao lưu, lịch và giám sát

```bash
bash scripts/ops.sh backup
sudo bash scripts/install-timers.sh
sudo systemctl enable --now library-backup.timer library-monitor.timer
# Chỉ bật sau khi gửi email thử thành công:
# sudo systemctl enable --now library-reminders.timer
systemctl list-timers 'library-*'
journalctl -u library-backup.service -u library-reminders.service -u library-monitor.service --since today
```

Installer dùng đúng đường dẫn checkout hiện tại và bỏ phụ thuộc docker.service nếu chạy Docker Desktop qua WSL. Chỉ bật timer reminders sau khi SMTP đã hoạt động. Máy WSL muốn dùng timer phải
bật systemd và đang chạy; máy tắt không thể sao lưu/gửi thư đúng giờ.

- Backup: 02:00 giờ Việt Nam, lưu 14 ngày; xóa bản cũ chỉ sau khi có bản mới thành công.
- Nhắc hạn: 08:00 giờ Việt Nam, gồm sắp hạn và quá hạn theo logic backend.
- Monitor: 5 phút/lần, kiểm tra UI, JS, API/database, dung lượng đĩa <85%, backup <26 giờ.
- Lỗi monitor thể hiện ở trạng thái failed và journal; chưa có kênh cảnh báo từ xa được cấu hình.
- Log container stdout/stderr, xoay tối đa 3 tệp x 10 MB/container. Không log secrets.
- Compose healthcheck đánh dấu unhealthy; `restart: unless-stopped` chỉ giúp khi tiến trình
  thoát, không tự restart container chỉ vì unhealthy. Điều tra lỗi thay vì giả định tự sửa.

Backup dừng API, khóa vận hành chung tránh gửi email/cập nhật đồng thời,
snapshot SQLite bằng API backup, chép cả covers, kiểm tra integrity + foreign keys,
ghi checksum vào archive. Không sao chép riêng database đang chạy và bỏ quên WAL.
Dừng API tránh database/ảnh lệch nhau; việc truy cập trực tiếp volume bên ngoài các
script này không được khóa. Archive chứa dữ liệu người dùng, phải bảo vệ như database.

Sao lưu ngoài máy chủ: cấu hình SSH của root tới nơi nhận, kiểm tra host key,
và tạo `/etc/library-backup.env` quyền 600:

```dotenv
BACKUP_REMOTE=backupuser@backup-host:/srv/backups/thu-vien-so/
```

Cài rsync trên hai máy. Timer backup sẽ rsync sau khi khởi động lại API;
lỗi rsync khiến service báo thất bại. Nơi nhận phải có chính sách lưu/xóa riêng,
script không xóa bản từ xa. Khi chưa cấu hình nơi nhận, bản sao chỉ nằm cùng máy,
không bảo vệ trước hỏng/mất máy chủ. RPO mục tiêu 24 giờ; RTO cần đo qua diễn tập.

## 7. Phục hồi vào môi trường riêng

Không ghi đè volume đang sử dụng. Giữ production và thử vào project recovery:

```bash
# Chỉ base Compose, cổng khác để tránh production; BACKUP_DIR là nơi chứa archive.
export COMPOSE_FILE=compose.yaml
export COMPOSE_PROJECT_NAME=thu-vien-recovery
export HTTP_PORT=8082
export BACKUP_DIR=./backups
docker compose run --rm --no-deps maintenance python scripts/backup.py restore library-YYYYMMDDTHHMMSSffffffZ.tar.gz
docker compose up -d --no-build --wait
bash scripts/smoke.sh http://localhost:8082
```

Thay đúng tên archive từ `ls backups`. Dùng images/source tương ứng thời điểm backup.
Phục hồi từ chối volume không rỗng, kiểm tra checksum/integrity và trả ownership UID 10001.
Sau đó kiểm tra số lượng users/books/loans/fines, đăng nhập, xem ảnh bìa và lịch sử.
Không gửi email từ recovery. Khi hoàn tất, `docker compose down` (giữ volume recovery).
Dùng shell mới để trở lại production, tránh giữ nhầm biến recovery.

Chuyển production sang dữ liệu đã phục hồi cần thời gian bảo trì: dừng API và timers,
giữ volume cũ, trỏ dịch vụ tới volume đã nghiệm thu qua Compose override rồi khởi động,
kiểm tra HTTPS và nghiệp vụ trước khi bật timers. Không khôi phục riêng DB nếu ảnh khác
thời điểm. Nếu rollback qua migration không tương thích, dùng cả images/source cũ
và bộ backup cùng thời điểm; các giao dịch sau backup không tự được khôi phục.

## 8. CI/CD

`.github/workflows/devops.yml` chạy kiểm tra khi push main hoặc mở PR; triển khai SSH chỉ khi chạy thủ công:

- Push main / PR: chạy Python tests, Node test, build hai images, Compose smoke,
  thử backup, lưu artifact source và images đã test. Không deploy tự động.
- Chạy thủ công workflow trên main với `deploy=true`: tải đúng images đã test,
  SSH truyền release, backup trước cập nhật, migrate, restart và kiểm tra HTTPS.
- GitHub Environment `production`: nên đặt người duyệt triển khai.
- Secrets: `DEPLOY_TARGET` dạng `user@host`, `DEPLOY_SSH_KEY`,
  `DEPLOY_KNOWN_HOSTS` chứa host key đã xác minh ngoài kênh SSH đang kết nối.
- Variable `PUBLIC_URL`: URL HTTPS thật, không dấu `/` cuối.
- Máy chủ phải đã bootstrap tại `/opt/thu-vien-so`, có `.env` production,
  images ban đầu, secrets SMTP; tài khoản deploy có quyền Docker và ghi thư mục này.
- Đảm bảo root timers và deploy user cùng đọc/ghi `.ops.lock`; có thể dùng cùng
  tài khoản vận hành hoặc thiết lập group/quyền tệp phù hợp trước khi bật pipeline.
- Pipeline không chạy demo/seed, không đưa secrets máy chủ vào artifact.

Ảnh ứng dụng CI hiện dùng tag local theo yêu cầu đơn giản của repo; artifacts của từng
workflow run giữ 14 ngày, lưu lại artifact trước mỗi bản phát hành quan trọng để rollback.
Base images Python/Nginx/Caddy vẫn là tags cập nhật; ứng dụng có `requirements.lock`.
Trước production quan trọng nên chốt base-image digest sau khi đã build/test trên máy đích.

## 9. Kiểm thử và giới hạn nghiệm thu

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.lock
.venv/bin/python -m unittest discover -s tests -v
node qa/api_client_test.mjs
```

Tests bổ sung: backup/restore database + ảnh, từ chối ghi đè, health khi chưa migrate,
SMTP đọc secret file, mật khẩu Gmail có khoảng trắng và không gửi lặp trong ngày. SMTP trong test được mock.
Xem `docs/DEVOPS_VALIDATION.txt` để biết phần đã chạy thật.

Tài liệu chính thức đã đối chiếu:
- https://docs.docker.com/compose/how-tos/startup-order/
- https://docs.docker.com/compose/how-tos/use-secrets/
- https://caddyserver.com/docs/automatic-https
