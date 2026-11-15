# Thư viện số Khoa CNTT

Ứng dụng quản lý thư viện với hai vai trò **bạn đọc** (sinh viên, giảng viên) và **thủ thư**. Nhánh `main` chứa đầy đủ giao diện, API, migration, kiểm thử và cấu hình DevOps.

## Chức năng

| Vai trò | Chức năng |
|---|---|
| Bạn đọc | Đăng ký/đăng nhập; tra cứu tên sách, tác giả, chủ đề; xem số bản còn; đặt/hủy mượn; xem lịch sử, hạn trả và tiền phạt; tham gia hàng đợi |
| Thủ thư | Quản lý đầu sách, tác giả, chủ đề, bản sách có mã vạch và ảnh bìa; xác nhận giao/nhận trả; ghi nhận thu tiền phạt; xem thống kê |
| Vận hành | Docker Compose, migration trước API, volume dữ liệu, health check, log xoay vòng, backup/restore, lịch nhắc hạn SMTP, HTTPS, CI và triển khai thủ công |

**Quy tắc:** tối đa 3 cuốn gồm cả đang đặt và đang mượn. Hạn trả bắt đầu khi giao sách; mặc định 14 ngày, phạt 2.000 VND/ngày quá hạn. Quy tắc và quyền truy cập được kiểm tra ở backend.

## Công nghệ và kiến trúc

| Thành phần | Công nghệ / địa chỉ |
|---|---|
| Front end | HTML, CSS, JavaScript ES modules; không cần npm build |
| Back end | Python 3.12, FastAPI, Uvicorn; `/api/v1` |
| CSDL | SQLite WAL, giao dịch ghi; lưu `/data/library.db` trong Compose |
| Ảnh bìa | Volume `/data/covers`; phục vụ qua `/media/` |
| Xác thực | Mật khẩu scrypt; Bearer session 8 giờ, chỉ lưu hash token trong DB |
| Web server | Nginx phục vụ UI và chuyển tiếp API; Caddy cho HTTPS |
| Email | SMTP STARTTLS, mặc định cổng 587 |
| CI/CD | GitHub Actions; deploy SSH phải chạy thủ công trên `main` |

Trình duyệt truy cập Nginx; các đường dẫn API và ảnh được chuyển tới FastAPI. SQLite là database nhúng nên không cần container CSDL riêng. Bản này phù hợp một máy chủ, một API worker; không chia volume SQLite qua NFS hoặc scale nhiều máy.

## 1. Chạy nhanh bằng Docker trên Ubuntu/WSL

Cài Docker Engine + Compose v2 hoặc Docker Desktop tích hợp với Ubuntu WSL. Kiểm tra `docker info` và `docker compose version` trước khi chạy.

```bash
git clone https://github.com/qtvn145-wq/TH-VI-N-S-.git
cd TH-VI-N-S-
bash scripts/setup.sh
docker compose config --quiet
docker compose up -d --build --wait
bash scripts/smoke.sh http://localhost:8081
```

Nếu đã có thư mục dự án, vào thư mục đó; không cần clone lặp lại. Setup giữ nguyên `.env` và secret đã có. Front end không cần Node khi chạy bằng Docker.

| Địa chỉ | Mục đích |
|---|---|
| http://localhost:8081 | Giao diện bạn đọc/thủ thư |
| http://localhost:8081/docs | Swagger tương tác |
| http://localhost:8081/openapi.json | OpenAPI từ ứng dụng |
| http://localhost:8081/api/v1/health | Kiểm tra API và schema database |

### Tạo tài khoản thủ thư

```bash
docker compose run --rm --no-deps backend python -m app.cli librarian
```

Nhập email, tên và mật khẩu ít nhất 10 ký tự. Mật khẩu không hiện khi nhập. Không có tài khoản mặc định trong bản triển khai. Bạn đọc tự đăng ký trên giao diện.

Nếu terminal báo lỗi Unicode khi nhập tên, kiểm tra bộ gõ/UTF-8 hoặc nhập tên không dấu. Email đã tồn tại sẽ không được tạo lần hai.

### Các lệnh thường dùng

```bash
docker compose ps -a
docker compose logs --tail=100 backend web
docker compose stop
docker compose up -d --wait
```

`migrate` thoát với mã 0 là bình thường; `backend` và `web` cần healthy. Database/ảnh nằm trong named volume, được giữ khi thay container. **Không dùng `docker compose down -v` khi cần giữ dữ liệu.**

## 2. Chạy trực tiếp bằng Python

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.lock
cp -n .env.example .env
set -a
source .env
set +a
python -m app.cli init
python -m app.cli librarian
uvicorn serve:app --host 127.0.0.1 --port 8081
```

Đây là cách chạy thay thế Docker; không chạy đồng thời hai bản chiếm cổng 8081. `serve:app` phục vụ cả UI và API; `app.main:app` chỉ phục vụ API. Python không tự đọc `.env`. Nếu `.env` đang chứa cấu hình Compose, dùng môi trường riêng khi chạy Python để tránh nhầm đường dẫn database.

Muốn demo có dữ liệu mẫu riêng: `python demo.py`. Tài khoản demo: `reader@demo.local` (bạn đọc), `librarian@demo.local` (thủ thư); mật khẩu chung `ThuVienDemo2026!`. Không dùng tài khoản demo khi công khai. Demo dùng `data/demo.sqlite3`, không tự thêm dữ liệu vào database Compose.

## 3. Cấu hình và secrets

- Chạy Python: mẫu `.env.example`.
- Chạy Docker: `scripts/setup.sh` tạo `.env` từ `deploy/env.example`.
- Không commit `.env`, `secrets/`, `data/` hoặc `backups/`.

| Biến | Giá trị / ý nghĩa |
|---|---|
| HTTP_PORT | `8081`, chỉ bind loopback trong cấu hình mặc định |
| PUBLIC_ORIGIN | `http://localhost:8081`, đổi nếu frontend cần origin khác |
| DATABASE_PATH | Compose: `/data/library.db`; Python: `data/library.db` |
| MEDIA_DIR | Compose: `/data/covers`; Python: `data/covers` |
| LOAN_DAYS / DAILY_FINE | `14` / `2000` |
| AUTO_MIGRATE | Compose đặt `false`; service migrate chạy riêng trước backend |
| SMTP_HOST / SMTP_PORT | Máy chủ email / `587` |
| SMTP_FROM / SMTP_USER | Địa chỉ người gửi / tài khoản SMTP |
| SMTP_PASSWORD_FILE | Secret file, Compose mount vào `/run/secrets/smtp_password` |
| BACKUP_DIR | `./backups`; giữ mặc định cho monitor và offsite script |
| DOMAIN / ACME_EMAIL | Dùng khi triển khai HTTPS với tên miền thật |
| IMAGE_TAG | `local`; pipeline đi kèm dùng tag này |

### Gmail cá nhân

Bật xác minh 2 bước và tạo [mật khẩu ứng dụng](https://myaccount.google.com/apppasswords) cho đúng tài khoản. Mật khẩu ứng dụng có 16 ký tự, không phải mật khẩu đăng nhập Google hay thư viện.

Sửa các dòng hiện có trong `.env` (thay địa chỉ minh họa bằng Gmail của bạn):

```dotenv
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_FROM=your-account@gmail.com
SMTP_USER=your-account@gmail.com
```

Lưu mật khẩu bằng `nano secrets/smtp_password.txt`. Không ghi mật khẩu trong README/lệnh Git. Secret directory quyền 700; file quyền 644 để UID container đọc được qua bind mount. Đây là secret dạng tệp, không phải kho secrets mã hóa. Backend bỏ khoảng trắng phân nhóm của Gmail; các nhà cung cấp khác giữ nguyên khoảng trắng trong mật khẩu.

```bash
# Chỉ đếm phiếu đủ điều kiện; chưa xác minh kết nối SMTP:
docker compose run --rm --no-deps reminders

# Gửi một thư thật về chính SMTP_USER:
docker compose run --rm --no-deps reminders python scripts/smtp-test.py
```

Chỉ bật lịch gửi sau khi đã nhận thư thử. Tác vụ gửi nhắc hạn thật:

```bash
bash scripts/ops.sh reminders
```

Tác vụ chọn phiếu đang mượn có hạn trả ngày mai hoặc sớm hơn, đánh dấu tối đa một lần/phiếu/ngày khi gửi thành công. Nếu SMTP nhận thư rồi tiến trình chết trước khi commit, thử lại có thể gửi trùng. Không dùng nhiều worker gửi email. Cổng 465 implicit TLS chưa được triển khai.

## 4. Sao lưu, phục hồi và lịch tự động

### Backup

```bash
bash scripts/ops.sh backup
sudo ls -lht backups/
```

Backup dừng API trong thời gian ngắn, snapshot SQLite, chép ảnh bìa, kiểm tra integrity/foreign keys và checksum, sau đó chạy lại API. Giữ 14 ngày; chỉ xóa archive cũ sau khi tạo bản mới thành công. Lưu thêm ở máy khác nếu cần bảo vệ khi hỏng ổ cứng.

### Cài lịch trên Linux hoặc WSL có systemd

```bash
sudo bash scripts/install-timers.sh
sudo systemctl enable --now library-backup.timer library-monitor.timer
# Chỉ sau khi SMTP đã kiểm tra thành công:
sudo systemctl enable --now library-reminders.timer
systemctl list-timers 'library-*'
```

Installer tự dùng đường dẫn checkout hiện tại. Nếu Docker chạy qua Docker Desktop và WSL không có `docker.service`, installer bỏ phụ thuộc đó. Máy/WSL và Docker phải đang hoạt động; không đảm bảo lịch chạy đúng giờ khi máy ngủ.

| Timer | Lịch giờ Việt Nam |
|---|---|
| Backup | 02:00 mỗi ngày |
| Nhắc hạn | 08:00 mỗi ngày |
| Monitor | Mỗi 5 phút |

Monitor kiểm tra web/API, dung lượng đĩa và độ mới backup (<26 giờ). Cần chạy backup lần đầu trước khi bật monitor. Log Docker xoay 3 file × 10 MB/container. Chưa cấu hình cảnh báo gửi ra ngoài.

```bash
sudo systemctl start library-backup.service
sudo systemctl restart library-monitor.service
sudo journalctl -u library-monitor.service -n 20 --no-pager
systemctl show library-monitor.service -p Result -p ExecMainStatus
```

`Result=success`, `ExecMainStatus=0` là đạt; lỗi cũ còn trong journal không có nghĩa lần chạy mới vẫn lỗi.

### Diễn tập phục hồi

Dùng terminal riêng; không ghi đè volume production. Lệnh đầu tiên hỏi đúng tên archive hiện có:

```bash
sudo ls -lt backups/
read -r -p 'Nhập tên file backup đầy đủ: ' backup_file
export COMPOSE_FILE=compose.yaml
export COMPOSE_PROJECT_NAME=thu-vien-recovery
export HTTP_PORT=8082
export BACKUP_DIR=./backups
docker compose run --rm --no-deps maintenance python scripts/backup.py restore "$backup_file"
docker compose up -d --no-build --wait
bash scripts/smoke.sh http://localhost:8082
```

Mở http://localhost:8082 kiểm tra tài khoản, sách, ảnh, lịch sử. Restore kiểm tra checksum và từ chối volume không rỗng. Dùng source/images tương thích thời điểm backup; không gửi email từ recovery.

Khi kiểm tra xong, trong terminal recovery:

```bash
docker compose down
unset COMPOSE_FILE COMPOSE_PROJECT_NAME HTTP_PORT BACKUP_DIR
```

Chi tiết backup ngoài máy, rollback và phục hồi production: [Hướng dẫn vận hành](docs/OPERATIONS.md).

## 5. HTTPS và chia sẻ qua Internet

### Demo công khai bằng Cloudflare Quick Tunnel

```bash
docker compose -f compose.yaml -f compose.tunnel.yaml up -d
docker compose -f compose.yaml -f compose.tunnel.yaml logs --tail=50 tunnel
```

Lấy link `https://...trycloudflare.com` trong log. Người ở ngoài mạng có thể truy cập khi máy bạn và Docker đang chạy. Tunnel nối tới `web:80` nội bộ, không phụ thuộc chuyển tiếp cổng 8081. Không cần cài chứng chỉ trên máy người xem.

Ai có link có thể mở trang công khai và đăng ký bạn đọc; các chức năng còn lại vẫn kiểm tra quyền. Dùng dữ liệu thử khi demo. Quick Tunnel không có đảm bảo uptime và link có thể đổi khi tiến trình được khởi tạo lại; không coi là hosting production. Dừng chia sẻ:

```bash
docker compose -f compose.yaml -f compose.tunnel.yaml stop tunnel
```

Nếu trước đó chạy tunnel bằng `docker run --name thu-vien-tunnel`, dừng tunnel cũ bằng `docker stop thu-vien-tunnel` trước khi chuyển sang cách Compose. Không ghi link demo tạm thời vào cấu hình API; frontend dùng đường dẫn cùng origin `/api/v1`.

### HTTPS chỉ trên máy cá nhân

```bash
docker compose -f compose.yaml -f compose.https-local.yaml up -d
docker compose -f compose.yaml -f compose.https-local.yaml cp \
  local-proxy:/data/caddy/pki/authorities/local/root.crt ./library-local-root.crt
curl --cacert ./library-local-root.crt https://localhost:8443/api/v1/health
```

Caddy tạo CA nội bộ. Nếu chứng chỉ chưa xuất hiện, xem log `local-proxy` rồi thử sao chép lại. Muốn Chrome trên Windows tin cậy, mở `library-local-root.crt` bằng Windows và cài vào **Current User → Trusted Root Certification Authorities**, sau đó mở lại trình duyệt. Chỉ cài CA do chính bản Caddy của bạn tạo. Địa chỉ https://localhost:8443 không phải link chia sẻ cho máy khác.

### Máy chủ + tên miền thật

Trỏ DNS về máy chủ, cho phép TCP 80/443, cấu hình `.env`:

```dotenv
COMPOSE_FILE=compose.yaml:compose.prod.yaml
DOMAIN=library.example.edu.vn
ACME_EMAIL=admin@example.edu.vn
PUBLIC_ORIGIN=https://library.example.edu.vn
```

Thay bằng tên miền/email thật rồi chạy `docker compose up -d --build --wait`. Caddy cấp/gia hạn chứng chỉ; giữ volume chứng chỉ. Kiểm tra `bash scripts/smoke.sh https://TEN_MIEN_THAT` mà không dùng `curl -k`. Đọc [OPERATIONS.md](docs/OPERATIONS.md) trước khi triển khai máy chủ.

## 6. CI/CD

Workflow [.github/workflows/devops.yml](.github/workflows/devops.yml):

- **Push main / PR:** kiểm thử Python, tích hợp UI/API, Node API client; build Docker; khởi động Compose; smoke test; backup; lưu artifact source và images đã kiểm thử (14 ngày).
- **Triển khai:** chỉ khi chạy `workflow_dispatch` trên main với `deploy=true`. Push code không tự triển khai máy chủ.
- GitHub Environment `production`; secrets `DEPLOY_TARGET` (`user@host`), `DEPLOY_SSH_KEY`, `DEPLOY_KNOWN_HOSTS`; variable `PUBLIC_URL`.
- Máy chủ phải bootstrap trước tại `/opt/thu-vien-so`, có `.env` production và secrets riêng. Deployment dừng ghi, backup, nạp images đã test, migrate, chạy lại và kiểm tra HTTPS.
- Không bật deploy khi mới có WSL/Quick Tunnel; đó không phải máy chủ SSH đã cấu hình cho pipeline.

Dependencies Python được chốt trong `requirements.lock`. Base images dùng tag; cần chốt digest và kiểm thử trên nền tảng đích cho vận hành production nghiêm ngặt. Xem kết quả CI thực tế trong tab **Actions**, không suy luận CI đạt chỉ vì file workflow tồn tại.

## 7. Kiểm thử

```bash
python -m unittest discover -s tests -v
PYTHONPATH=. python qa/integration_test.py
node qa/api_client_test.mjs
```

Dùng Python environment đã cài `requirements.lock`, Node 24 cho test JavaScript. Tests sử dụng database tạm; không chạy script demo trên dữ liệu thật. OpenAPI tĩnh nằm ở [docs/openapi.json](docs/openapi.json); test tích hợp so sánh với mã nguồn.

Kiểm tra thủ công trước khi nghiệm thu:

1. Thủ thư tạo tác giả/chủ đề, đầu sách, bản sách có mã vạch và ảnh bìa.
2. Bạn đọc tìm sách, đặt mượn; thử hết sách và vượt 3 cuốn.
3. Thủ thư xác nhận giao; bạn đọc thấy hạn trả.
4. Thủ thư nhận trả; số bản còn và lịch sử cập nhật, tiền phạt tính theo hạn.
5. Kiểm tra quyền: bạn đọc không quản lý danh mục và không xem lịch sử người khác.
6. Thử backup/restore, email SMTP và health qua địa chỉ HTTPS.

Browser test tùy chọn: cài Playwright/Chromium, chạy demo mới riêng rồi chạy `python qa/browser_test.py`. Kịch bản thay đổi dữ liệu demo; không chạy trên production.

## 8. Khắc phục lỗi thường gặp

| Triệu chứng | Kiểm tra / xử lý |
|---|---|
| `200/CHDIR` trong systemd | Chạy lại `sudo bash scripts/install-timers.sh` từ checkout đang dùng |
| `Unit docker.service not found` trên WSL | Đảm bảo Docker Desktop chạy, `sudo docker info` thành công; chạy installer ở trên |
| Tạo thủ thư lỗi Unicode | Kiểm tra UTF-8/bộ gõ, thử tên không dấu |
| SMTP không đăng nhập được | Đúng tài khoản; Gmail dùng app password, không dùng mật khẩu thường; thử script SMTP và đọc mã lỗi |
| `FileNotFoundError` khi restore | Dùng đúng tên archive trong `backups/`, không dùng chữ tên mẫu |
| Restore yêu cầu volume rỗng | Dùng project recovery riêng; không xóa volume chính |
| Monitor báo lỗi backup cũ | Chạy backup, kiểm tra log và mốc thời gian archive |

Nếu 8081 bị reset nhưng container healthy:

```bash
docker compose -p thu-vien-so -f compose.yaml port web 80
docker compose -p thu-vien-so -f compose.yaml exec -T web wget -qO- http://web:80/api/v1/health
curl -4 --noproxy '*' --max-time 10 http://127.0.0.1:8081/api/v1/health
```

Nếu nội bộ tốt, thử tạo lại riêng web (gián đoạn ngắn, giữ dữ liệu):

```bash
docker compose -p thu-vien-so -f compose.yaml up -d --no-deps --force-recreate web
```

Cảnh báo orphan có thể là proxy/tunnel từ Compose bổ sung; không xóa hàng loạt khi chưa biết container nào đang dùng. Dòng health nội bộ thành công không thay thế kiểm tra từ trình duyệt bên ngoài.

## 9. Cấu trúc và giới hạn

| Đường dẫn | Nội dung |
|---|---|
| `frontend/` | Giao diện hai vai trò, API client, cấu hình cùng origin |
| `app/`, `serve.py`, `demo.py` | API, CLI, phục vụ UI trực tiếp, dữ liệu demo riêng |
| `migrations/` | Schema SQL; hiện phiên bản 1 |
| `tests/`, `qa/` | Nghiệp vụ, DevOps, tích hợp và browser test |
| `Dockerfile`, `frontend/Dockerfile` | Images backend và web |
| `compose*.yaml`, `deploy/`, `scripts/` | Triển khai, HTTPS, tunnel, SMTP, backup và systemd |
| `docs/` | ERD, API, đối chiếu màn hình, hướng dẫn vận hành |

Tài liệu: [ERD](docs/ERD.md) · [API](docs/API.md) · [Đối chiếu Front end/API](docs/FRONTEND_API_MAPPING.md) · [Vận hành](docs/OPERATIONS.md).

Giới hạn MVP: chưa có reset mật khẩu/xác minh email/rate limit đăng nhập; hàng đợi FIFO cần người đứng đầu tự đặt, chưa tự hết hạn lượt chờ; chưa có gia hạn, mất/hỏng sách hay thanh toán online. Mã vạch nhập tay hoặc bằng máy quét kiểu bàn phím, chưa quét camera. Tìm kiếm tiếng Việt phân biệt dấu; danh sách một số loại chưa phân trang. Cần bổ sung biện pháp vận hành và bảo mật tương ứng trước khi dùng với dữ liệu thật ở quy mô lớn.

Tài liệu chính thức: [Docker Compose](https://docs.docker.com/compose/) · [Caddy HTTPS](https://caddyserver.com/docs/automatic-https) · [Cloudflare Quick Tunnels](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/) · [Google app passwords](https://support.google.com/accounts/answer/185833).
