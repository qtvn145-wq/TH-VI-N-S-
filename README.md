# THƯ VIỆN SỐ — Sách điện tử

Ứng dụng tra cứu, quản lý và đọc sách PDF trên trình duyệt. Bộ mã nguồn gồm ba phần **backend**, **frontend** và **devops**, được giải nén vào cùng một thư mục dự án.

Phiên bản này tập trung vào sách điện tử: không sử dụng quy trình mượn sách, trả sách, hạn trả hoặc tiền phạt. Cơ sở dữ liệu nâng cấp từ phiên bản cũ có thể vẫn giữ bảng lịch sử của chức năng mượn trả.

## 1. Công nghệ và ngôn ngữ

| Thành phần | Ngôn ngữ / công nghệ | Vai trò |
| --- | --- | --- |
| Backend | Python, FastAPI, Uvicorn | API, xác thực, phân quyền, xử lý dữ liệu |
| Kiểm tra dữ liệu | Pydantic | Kiểm tra nội dung gửi lên API |
| Cơ sở dữ liệu | SQLite, SQL, thư viện `sqlite3` | Lưu sách, người dùng, phiên đăng nhập và tiến độ đọc |
| Xử lý PDF | pypdfium2 | Kết xuất trang PDF thành ảnh để đọc trên web |
| Xử lý ảnh | Pillow | Kiểm tra và xử lý ảnh bìa |
| Frontend | HTML5, CSS3, JavaScript ES Modules | Giao diện, gọi API bằng Fetch, hiệu ứng chuyển trang |
| Web server | Nginx | Phục vụ giao diện và chuyển tiếp yêu cầu tới backend |
| Đóng gói | Docker, Docker Compose | Chạy các dịch vụ trong container |
| Vận hành | Bash, Python, GitHub Actions | Kiểm tra, sao lưu và hỗ trợ triển khai |
| Truy cập Internet | Cloudflare Tunnel (`cloudflared`) | Chuyển tiếp HTTPS công khai đến web đang chạy trên máy |
| HTTPS tùy chọn | Caddy và các tệp Compose bổ sung | Triển khai có tên miền; không bắt buộc khi dùng Quick Tunnel |

Frontend không dùng React/Vue và không cần bước build bằng npm để chạy. Node.js/npm phục vụ kiểm tra mã và chạy kiểm thử. Backend không dùng SQLAlchemy hoặc JWT; xác thực sử dụng token phiên đăng nhập.

Các phiên bản thư viện Python nằm trong `backend/requirements.txt`; dùng `backend/requirements.lock` khi cài đặt để đồng nhất môi trường.

## 2. Cấu trúc ba phần

```text
thuvienso/
├── README.md
├── backend/                 # API, cơ sở dữ liệu, migration, kiểm thử, Dockerfile
├── frontend/                # HTML, CSS, JavaScript, kiểm thử, Dockerfile
├── devops/                  # Cấu hình triển khai, Nginx, script vận hành
├── docs/                    # Tài liệu bổ sung
├── qa/                      # Kiểm thử tích hợp
├── compose.yaml             # Cấu hình Docker chính
├── compose.tunnel.yaml      # Cloudflare Quick Tunnel
├── compose.prod.yaml        # Cấu hình triển khai bổ sung
├── compose.https-local.yaml
├── .env.example             # Mẫu biến môi trường
├── serve.py                 # Chạy API và giao diện bằng Python
└── demo.py
```

Giữ nguyên tên thư mục `backend`, `frontend`, `devops`; không đổi thành `back-end` hoặc `front-end`, vì đường dẫn import và cấu hình Docker đang dùng tên hiện tại.

**Giải nén lần đầu:** chạy tại thư mục chứa ba ZIP, thay tên tệp nếu bản tải về có hậu tố `(1)`.

```bash
mkdir -p ~/thuvienso
unzip Backend_Ebook.zip -d ~/thuvienso
unzip Frontend_Ebook.zip -d ~/thuvienso
unzip DevOps_Ebook.zip -d ~/thuvienso
cd ~/thuvienso
```

Ba ZIP phải cùng ghép vào một thư mục, không đặt mỗi ZIP trong một thư mục dự án độc lập. Đặt README này tại `~/thuvienso/README.md`. Các lệnh bên dưới mặc định chạy từ thư mục gốc này.

## 3. Chức năng và phân quyền

- Tra cứu sách theo tên, tác giả, chủ đề; lọc và sắp xếp danh sách.
- Đọc PDF với hiệu ứng chuyển trang, chế độ một trang/hai trang, nút tiến/lùi ở hai bên, phím mũi tên và thao tác chạm.
- Thu phóng theo các mốc 25%, 50%, 75%, 100%, 125%, 150%, 175%, 200%; mặc định 100% tương ứng khung trang được căn vừa vùng đọc.
- Chế độ toàn màn hình, lưu tiến độ đọc và danh sách yêu thích.
- Đăng ký, đăng nhập và quên mật khẩu qua email khi đã cấu hình SMTP.
- Quản lý sách, tác giả, chủ đề, ảnh bìa và tệp PDF.
- Quản lý tài khoản: tìm kiếm, thêm, sửa thông tin, đổi vai trò, đặt mật khẩu mới và xóa tài khoản theo điều kiện của hệ thống.

| Vai trò trong dữ liệu | Quyền |
| --- | --- |
| `reader` | Tài khoản bạn đọc: đọc sách, quản lý yêu thích và tiến độ cá nhân |
| `librarian` | Quản trị/thủ thư: quyền bạn đọc, quản lý nội dung và tài khoản |

**Chưa có vai trò `admin` tách biệt.** Mục quản trị trên giao diện hiện thuộc tài khoản `librarian`. Hệ thống bảo vệ tài khoản thủ thư cuối cùng và không cho tự xóa tài khoản đang dùng; liên kết dữ liệu lịch sử có thể ngăn xóa một số tài khoản.

Trình đọc hiện kết xuất trang PDF thành ảnh, không phải trình đọc EPUB hoặc công cụ tìm kiếm/sao chép văn bản trong PDF.

## 4. Cách chương trình hoạt động

Khi chạy Docker, trình duyệt mở cổng 8081 của máy. Nginx trả về giao diện và chuyển các yêu cầu `/api/` sang FastAPI ở cổng 8000 trong mạng Docker. Backend kiểm tra dữ liệu, xác thực quyền rồi đọc/ghi SQLite hoặc xử lý tệp sách.

Khi mở sách, backend kết xuất trang PDF thành ảnh và lưu bộ nhớ đệm trên đĩa. Frontend tải ảnh trang, bố trí vùng đọc và thực hiện hiệu ứng chuyển trang. Tiến độ của người dùng đăng nhập được lưu vào cơ sở dữ liệu; khách đọc sử dụng lưu trữ cục bộ của trình duyệt.

Cloudflare Tunnel bổ sung một đường truy cập HTTPS từ Internet đến dịch vụ `web:80`. Máy WSL vẫn xử lý ứng dụng và lưu dữ liệu; Tunnel không chuyển ứng dụng thành một máy chủ chạy độc lập trên Cloudflare.

## 5. Cơ sở dữ liệu và nơi lưu dữ liệu

Các bảng chính gồm `users`, `sessions`, `books`, `authors`, `categories`, `book_authors`, `book_categories`, `favorites`, `ebooks`, `reading_progress`, `password_resets`, `reset_limits`.

Tài khoản nằm trong bảng `users`. Mật khẩu được băm bằng scrypt, không lưu mật khẩu gốc. Token phiên và token đặt lại mật khẩu được lưu dưới dạng băm. Liên kết đặt lại mật khẩu có hiệu lực 15 phút, dùng một lần.

| Dữ liệu | Chạy Python trực tiếp, mặc định | Chạy Docker, đường dẫn trong container |
| --- | --- | --- |
| SQLite | `data/library.db` | `/data/library.db` |
| Ảnh bìa | `data/covers/` | `/data/covers/` |
| PDF và bộ nhớ đệm trang | `data/ebooks/` | `/data/ebooks/` |

Docker lưu thư mục `/data` trong volume `library_data`; với tên project mặc định, tên volume thực tế là `thu-vien-so_library_data`.

**Python trực tiếp và Docker mặc định dùng hai nơi lưu dữ liệu khác nhau.** Tạo tài khoản ở Python không tự tạo tài khoản trong Docker và ngược lại. Nên chọn Docker làm cách chạy chính nếu muốn sử dụng Tunnel theo hướng dẫn bên dưới.

Xem thông tin volume:

```bash
docker volume inspect thu-vien-so_library_data
```

Không sửa trực tiếp SQLite khi dịch vụ đang ghi dữ liệu. Dùng giao diện quản trị để quản lý tài khoản và sách.

## 6. Môi trường chạy

- Windows 10/11 với Ubuntu qua WSL2, hoặc máy Linux.
- Docker Engine và Docker Compose v2; trên Windows có thể dùng Docker Desktop bật WSL Integration cho Ubuntu.
- Nếu chạy Python trực tiếp: khuyến nghị Python 3.12 và môi trường ảo `venv`.
- Node.js/npm chỉ cần khi chạy kiểm thử frontend.
- Trình duyệt hiện đại; kết nối Internet để tải image, thư viện và sử dụng Tunnel.

Kiểm tra môi trường Docker:

```bash
docker --version
docker compose version
docker info
```

Nếu dùng Docker Desktop, cần mở Docker Desktop trước khi chạy lệnh trong WSL.

## 7. Chạy bằng Docker — cách khuyến nghị

### 7.1. Tạo cấu hình

```bash
cd ~/thuvienso
test -f .env || cp .env.example .env
bash devops/scripts/setup.sh
nano .env
```

Cấu hình cơ bản khi chạy nội bộ:

```dotenv
HTTP_PORT=8081
PUBLIC_ORIGIN=http://localhost:8081
IMAGE_TAG=local
BACKUP_DIR=./backups
SMTP_HOST=
SMTP_PORT=587
SMTP_SECURITY=starttls
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM=
```

Giữ lại `.env` đang sử dụng nếu đã cấu hình. Các giá trị SMTP trống nghĩa là chưa gửi được email quên mật khẩu. Không đưa `.env`, mật khẩu SMTP hoặc dữ liệu tài khoản lên Git.

### 7.2. Khởi động

```bash
docker compose up -d --build --wait
```

Dịch vụ `migrate` khởi tạo/nâng cấp cấu trúc SQLite rồi thoát. Sau khi migration thành công, `backend` và `web` chạy. `migrate` kết thúc với mã 0 là bình thường.

Mở:

- Website: http://localhost:8081
- Tài liệu API: http://localhost:8081/docs
- Kiểm tra hoạt động: http://localhost:8081/api/v1/health

### 7.3. Tạo tài khoản quản trị/thủ thư đầu tiên

```bash
docker compose run --rm --no-deps backend python -m backend.app.cli librarian
```

Nhập email, tên và mật khẩu ít nhất 10 ký tự. Terminal không hiện ký tự khi nhập mật khẩu.

Lệnh này **tạo mới**, không cập nhật tài khoản. Nếu email đã tồn tại sẽ gặp `UNIQUE constraint failed: users.email`. Sau khi đăng nhập bằng thủ thư, dùng mục quản lý tài khoản để thêm, sửa, đổi mật khẩu hoặc xóa người dùng.

### 7.4. Kiểm tra, dừng và chạy lại

```bash
curl -fsS http://localhost:8081/api/v1/health
bash devops/scripts/smoke.sh http://localhost:8081
docker compose ps
docker compose logs --tail=100 backend web
docker compose logs --tail=100 migrate
```

Health trả về `{"status":"ok"}` cho biết API đang phản hồi; vẫn cần kiểm tra đăng nhập, mở sách và email để xác nhận các chức năng tương ứng.

```bash
# Dừng dịch vụ
docker compose stop

# Chạy lại
docker compose up -d --wait

# Sau khi thay đổi mã nguồn
docker compose up -d --build --wait
```

`docker compose down` giữ volume theo mặc định. **Không thêm `-v` nếu muốn giữ dữ liệu**, vì tùy chọn đó xóa volume của dự án.

## 8. Chạy Python trực tiếp — lựa chọn thay thế

Nếu Docker đang chiếm cổng 8081, dừng trước:

```bash
docker compose stop
```

Với Python 3.12 đã cài:

```bash
cd ~/thuvienso
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements.lock
python -m backend.app.cli init
python -m backend.app.cli librarian
uvicorn serve:app --host 127.0.0.1 --port 8081
```

Chỉ tạo thủ thư khi chưa có tài khoản phù hợp trong cơ sở dữ liệu này. Mở http://localhost:8081 và giữ terminal Uvicorn hoạt động. Nhấn `Ctrl+C` để dừng.

`serve.py` phục vụ cả frontend và API. Chạy riêng `backend.app.main:app` không thay thế đầy đủ vai trò phục vụ giao diện của `serve.py`.

Python trực tiếp **không tự đọc `.env`**. Nếu dùng SMTP hoặc địa chỉ công khai, cần truyền các biến môi trường tương ứng cho tiến trình trước khi chạy Uvicorn. Các lệnh Tunnel Docker ở mục tiếp theo áp dụng cho cách chạy Docker tại mục 7.

## 9. Công khai bằng Cloudflare Quick Tunnel miễn phí

Quick Tunnel tạo địa chỉ tạm dạng `https://TEN-NGAU-NHIEN.trycloudflare.com`, không cần đăng ký tên miền. Đây là hình thức thử nghiệm, không bảo đảm thời gian hoạt động. Khi tạo lại Tunnel, địa chỉ có thể thay đổi.

### 9.1. Cách A: Chạy Tunnel trong terminal

Khởi động ứng dụng ở mục 7, sau đó mở terminal WSL khác:

```bash
cd ~/thuvienso
docker run --rm -it \
  --network thu-vien-so_default \
  cloudflare/cloudflared:latest \
  tunnel --no-autoupdate --url http://web:80
```

Đợi log hiển thị URL `https://…trycloudflare.com` và dòng `Registered tunnel connection`, rồi mở URL đó. Kiểm tra thêm từ điện thoại dùng mạng di động để xác nhận truy cập bên ngoài.

- `web:80` là dịch vụ Nginx trong mạng Docker; không đổi thành `localhost:8081` bên trong container Tunnel.
- `thu-vien-so_default` là mạng của project mặc định; nếu tự đổi tên project thì phải dùng tên mạng tương ứng.
- Giữ terminal này mở. `Ctrl+C` dừng Tunnel và container sẽ bị xóa do sử dụng `--rm`.

### 9.2. Cập nhật địa chỉ công khai của ứng dụng

Mở terminal khác, sửa `.env`:

```bash
cd ~/thuvienso
nano .env
```

Thay bằng URL **vừa nhận được**, không giữ nguyên tên ví dụ:

```dotenv
PUBLIC_ORIGIN=https://TEN-TUNNEL.trycloudflare.com
```

Áp dụng cấu hình:

```bash
docker compose up -d --wait
```

`PUBLIC_ORIGIN` được dùng để tạo liên kết email quên mật khẩu và cấu hình origin. Chỉ `docker compose restart` không áp dụng giá trị môi trường mới. Khi địa chỉ Tunnel đổi, phải cập nhật lại biến này.

### 9.3. Cách B: Chạy Tunnel nền bằng Compose

Dùng cách này **thay cho cách A**. Nếu cách A đang chạy, nhấn `Ctrl+C` trong terminal của Tunnel trước.

```bash
cd ~/thuvienso
docker compose -f compose.yaml -f compose.tunnel.yaml up -d --build --wait
docker compose -f compose.yaml -f compose.tunnel.yaml logs --tail=100 -f tunnel
```

Lấy URL từ log. `Ctrl+C` lúc đang xem log chỉ thoát chế độ xem, Tunnel nền vẫn chạy.

Sửa `PUBLIC_ORIGIN` trong `.env` rồi áp dụng với đủ hai tệp:

```bash
docker compose -f compose.yaml -f compose.tunnel.yaml up -d --wait
```

Các lệnh quản lý:

```bash
# Xem trạng thái
docker compose -f compose.yaml -f compose.tunnel.yaml ps

# Xem log Tunnel
docker compose -f compose.yaml -f compose.tunnel.yaml logs --tail=100 tunnel

# Dừng riêng Tunnel
docker compose -f compose.yaml -f compose.tunnel.yaml stop tunnel

# Chạy lại các dịch vụ
docker compose -f compose.yaml -f compose.tunnel.yaml up -d --wait

# Dừng toàn bộ ứng dụng và Tunnel
docker compose -f compose.yaml -f compose.tunnel.yaml stop
```

Sau mỗi lần khởi động lại Tunnel, xem log để kiểm tra địa chỉ và cập nhật `PUBLIC_ORIGIN` nếu đổi. Chế độ chạy nền không giữ ứng dụng trực tuyến khi Windows ngủ, WSL/Docker bị tắt hoặc máy mất mạng.

### 9.4. Nếu mạng QUIC thường xuyên bị ngắt

Nếu sau lỗi timeout có dòng `Registered tunnel connection` mới, Tunnel đã tự kết nối lại. Chỉ khi lỗi lặp lại gây gián đoạn, có thể dừng Tunnel hiện tại rồi thử HTTP/2:

```bash
docker run --rm -it \
  --network thu-vien-so_default \
  cloudflare/cloudflared:latest \
  tunnel --no-autoupdate --protocol http2 --url http://web:80
```

Đây là một lần tạo Tunnel mới, vì vậy lấy lại URL và cập nhật `.env`. Nếu chạy bằng Compose, có thể thêm `--protocol, http2` vào danh sách `command` của dịch vụ `tunnel` rồi áp dụng lại hai tệp Compose.

## 10. Cấu hình email quên mật khẩu

Điền thông tin thật do nhà cung cấp SMTP cấp trong `.env`:

```dotenv
PUBLIC_ORIGIN=https://TEN-TUNNEL.trycloudflare.com
SMTP_HOST=smtp.nha-cung-cap.example
SMTP_PORT=587
SMTP_SECURITY=starttls
SMTP_USER=ten-dang-nhap-smtp
SMTP_PASSWORD=mat-khau-smtp
SMTP_FROM=thu-vien@ten-mien-cua-ban.example
```

Các giá trị trên là mẫu, không dùng để gửi email thật. `SMTP_FROM` phải là địa chỉ được nhà cung cấp cho phép. Nếu nhà cung cấp yêu cầu SMTP SSL cổng 465, dùng `SMTP_PORT=465` và `SMTP_SECURITY=ssl`. Một số dịch vụ yêu cầu mật khẩu ứng dụng thay cho mật khẩu đăng nhập thông thường.

Áp dụng lại Compose theo chế độ đang chạy ở mục 7 hoặc 9.3. Thử chức năng **Quên mật khẩu** bằng email của tài khoản đang tồn tại; kiểm tra hộp thư và thư rác. Liên kết phải dùng URL công khai hiện tại. Việc hiện thông báo đã tiếp nhận yêu cầu không tự chứng minh email đã gửi thành công.

## 11. Sao lưu và kiểm thử

Sao lưu dữ liệu Docker:

```bash
bash devops/scripts/ops.sh backup
```

Script tạm dừng backend trong lúc sao lưu, sau đó chạy lại. Bản sao lưu gồm SQLite, ảnh bìa và dữ liệu ebook, mặc định nằm trong `backups/`. Nên sao chép bản sao lưu sang nơi khác nếu cần bảo vệ trước sự cố ổ đĩa.

Để chạy bộ kiểm tra mã nguồn, cài Python, các thư viện trong `requirements.lock`, Node.js và npm, sau đó:

```bash
source .venv/bin/activate
bash devops/scripts/check.sh
```

Script chạy kiểm thử backend, DevOps, tích hợp, kiểm tra JavaScript và cú pháp các script Bash. Kiểm thử này không thay thế việc thử gửi email SMTP thật hoặc truy cập Tunnel từ Internet.

## 12. Lỗi thường gặp

| Hiện tượng | Cách xử lý |
| --- | --- |
| `address already in use` trên 8081 | Có dịch vụ đang giữ cổng. Dừng bản Docker hoặc Uvicorn cũ trước khi khởi động bản khác. |
| `UNIQUE constraint failed: users.email` | Email đã tồn tại. Lệnh CLI chỉ tạo mới; dùng giao diện quản trị để sửa tài khoản. |
| Tạo tài khoản nhưng không đăng nhập được ở bản khác | Kiểm tra có đang dùng nhầm dữ liệu Python và Docker hay không. |
| Tunnel báo 502 | Kiểm tra health nội bộ, trạng thái `web`/`backend`, tên mạng Docker và đích `http://web:80`. |
| Timeout QUIC rồi đăng ký kết nối lại | Tunnel đã tự phục hồi; chỉ đổi giao thức nếu lỗi liên tục. |
| Link quên mật khẩu trỏ về localhost | Sửa `PUBLIC_ORIGIN`, áp dụng lại Compose, rồi yêu cầu email mới. |
| Không nhận được email | Kiểm tra SMTP, thư rác và log backend; không chia sẻ mật khẩu SMTP trong log/chụp màn hình. |
| `migrate` không còn chạy | Bình thường nếu kết thúc mã 0; nếu lỗi, xem log `migrate`. |
| Cảnh báo orphan container | Kiểm tra có container cấu hình cũ hoặc đang bỏ sót tệp Compose Tunnel; dùng nhất quán các tệp Compose của chế độ đã chọn. |
| `/favicon.ico` trả 404 | Thiếu biểu tượng tab; riêng lỗi này không đồng nghĩa API hoặc trình đọc bị hỏng. |

## 13. Tài liệu tham khảo

- Cloudflare Quick Tunnels: https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/
- Tham số chạy cloudflared: https://developers.cloudflare.com/tunnel/reference/run-parameters/
- Cấu hình giao thức Tunnel: https://developers.cloudflare.com/tunnel/configuration/

README mô tả cấu hình có trong ba gói Backend_Ebook, Frontend_Ebook và DevOps_Ebook đã đối chiếu. URL `trycloudflare.com` được tạo trong mỗi lần chạy, không phải địa chỉ cố định đi kèm mã nguồn.
