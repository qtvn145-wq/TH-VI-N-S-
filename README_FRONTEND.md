# Frontend — THƯ VIỆN SỐ

Giao diện web tra cứu và đọc sách điện tử PDF, dành cho bạn đọc và quản trị/thủ thư. Tài liệu này có thể đặt tại `frontend/README.md`. Các lệnh bên dưới chạy từ **thư mục gốc `~/thuvienso`**, nơi chứa ba phần `backend/`, `frontend/`, `devops/`.

## 1. Công nghệ và môi trường

| Thành phần | Công nghệ |
| --- | --- |
| Cấu trúc trang | HTML5 |
| Giao diện và hiệu ứng | CSS3 |
| Logic giao diện | JavaScript ES Modules |
| Gọi backend | Fetch API, JSON và FormData |
| Lưu trạng thái trên trình duyệt | sessionStorage/localStorage tùy loại dữ liệu |
| Phục vụ trong Docker | Nginx |
| Kiểm tra mã | Node.js và npm |

Frontend không dùng React/Vue, không cần npm build để chạy. Backend sử dụng Python/FastAPI và SQLite; frontend **không truy cập SQLite trực tiếp**, mà gọi API.

Môi trường: trình duyệt hiện đại, Linux hoặc Ubuntu trong WSL2 trên Windows. Cần Docker/Compose nếu chạy bộ ứng dụng bằng container; cần Python nếu dùng `serve.py`. Node.js/npm chỉ cần cho kiểm thử frontend.

## 2. Cấu trúc mã nguồn

| Đường dẫn trong `frontend/` | Nội dung |
| --- | --- |
| `index.html` | Trang HTML chính |
| `config.js` | Cấu hình địa chỉ API |
| `src/app.js` | Điều khiển giao diện, tài khoản, danh mục và quản trị |
| `src/api.js` | Gửi yêu cầu API và xử lý phản hồi |
| `src/reader.js` | Không gian đọc sách, chuyển trang, thu phóng, toàn màn hình |
| `styles/style.css` | Bố cục và kiểu hiển thị |
| `tests/` | Kiểm thử frontend |
| `package.json` | Lệnh kiểm tra JavaScript và kiểm thử |
| `Dockerfile` | Đóng gói frontend với Nginx |

## 3. Chức năng

### Bạn đọc

- Tìm kiếm sách theo tên, tác giả; lọc theo chủ đề và sắp xếp.
- Xem thông tin sách và mở PDF để đọc.
- Quản lý sách yêu thích và tiếp tục đọc từ tiến độ đã lưu.
- Đăng ký, đăng nhập, đăng xuất và yêu cầu đặt lại mật khẩu.

### Không gian đọc PDF

- Hiển thị một trang hoặc hai trang.
- Nút chuyển trang ở hai bên vùng đọc; hỗ trợ phím mũi tên và thao tác chạm.
- Hiệu ứng chuyển trang, thanh công cụ gọn để dành diện tích cho sách.
- Các mức thu phóng: **25%, 50%, 75%, 100%, 125%, 150%, 175%, 200%**.
- Mặc định 100% được tính theo khung trang căn vừa vùng đọc; tăng mức phóng có thể cần cuộn.
- Chế độ toàn màn hình tùy hỗ trợ của trình duyệt.

Trang PDF được backend kết xuất thành ảnh. Trình đọc này không cung cấp lớp văn bản PDF để chọn/copy hoặc tìm kiếm nội dung trong trang, và không phải trình đọc EPUB.

### Quản trị/thủ thư

- Quản lý sách, tác giả và chủ đề.
- Tải ảnh bìa và tệp PDF.
- Quản lý tài khoản: tìm kiếm, thêm, sửa thông tin, đổi vai trò, đặt mật khẩu mới và xóa theo điều kiện hệ thống.

Hai vai trò hiện có là `reader` và `librarian`. Chức năng quản trị thuộc `librarian`, chưa có `admin` riêng. Backend quyết định quyền thực tế của mỗi yêu cầu.

Không có chức năng mượn sách, hạn trả, tiền phạt hoặc nhắc trả sách trong giao diện ebook này.

## 4. Cách hoạt động và dữ liệu

Trình duyệt tải HTML/CSS/JavaScript. `src/api.js` gửi yêu cầu tới FastAPI. Backend trả dữ liệu sách, tài khoản hoặc ảnh trang PDF; frontend hiển thị kết quả và cập nhật trạng thái giao diện.

- Cơ sở dữ liệu chính là SQLite ở backend, không nằm trong thư mục frontend.
- Tiến độ người dùng đăng nhập được lưu ở backend; tiến độ khách đọc lưu cục bộ trên trình duyệt.
- Token phiên đăng nhập lưu ở sessionStorage; mật khẩu không được dùng làm dữ liệu lưu trữ lâu dài của frontend.
- Chức năng quên mật khẩu cần backend có SMTP hoạt động và `PUBLIC_ORIGIN` đúng địa chỉ website.

## 5. Chạy cả frontend và backend bằng Docker

Đây là cách sử dụng đầy đủ ứng dụng. Cần giải nén cả ba ZIP vào cùng thư mục trước:

```bash
cd ~/thuvienso
test -f .env || cp .env.example .env
bash devops/scripts/setup.sh
docker compose up -d --build --wait
```

Mở http://localhost:8081.

Nếu chưa có thủ thư, tạo một lần:

```bash
docker compose run --rm --no-deps backend python -m backend.app.cli librarian
```

Nhập email chưa tồn tại, tên và mật khẩu từ 10 ký tự. Đăng nhập tài khoản này để sử dụng phần quản trị.

Nginx phục vụ giao diện và chuyển `/api/` đến backend trong mạng Docker. Không cần chạy npm hoặc máy chủ frontend riêng trong chế độ này.

```bash
# Kiểm tra API qua web
curl -fsS http://localhost:8081/api/v1/health

# Xem log
docker compose logs --tail=100 web backend

# Sau khi sửa mã frontend
docker compose up -d --build --wait

# Dừng ứng dụng
docker compose stop
```

## 6. Chạy cả giao diện và API bằng Python

Với Python 3.12 đã cài, từ thư mục gốc:

```bash
cd ~/thuvienso
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements.lock
python -m backend.app.cli init
python -m backend.app.cli librarian
uvicorn serve:app --host 127.0.0.1 --port 8081
```

Bỏ qua bước tạo thủ thư nếu đã có tài khoản trong dữ liệu Python. Mở http://localhost:8081. Giữ terminal chạy, nhấn `Ctrl+C` để dừng.

`serve.py` tại gốc dự án phục vụ cả trang chủ, tệp frontend dưới `/ui/` và API. Nếu Docker đang giữ cổng 8081, chạy `docker compose stop` trước.

Dữ liệu Python mặc định ở `data/`; dữ liệu Docker ở volume riêng. Do đó tài khoản/sách giữa hai cách chạy không tự đồng bộ.

## 7. Cấu hình kết nối API

Mặc định trong `frontend/config.js`:

```javascript
window.LIBRARY_API_BASE = '/api/v1';
```

Đây là cấu hình cùng origin: frontend và API được truy cập qua cùng địa chỉ, phù hợp với Nginx, `serve.py` và Cloudflare Tunnel của dự án. Khi URL Tunnel đổi, không cần sửa cấu hình tương đối này.

Nếu triển khai giao diện và API ở hai origin khác nhau, cần đồng thời:

1. Đặt `LIBRARY_API_BASE` thành URL API đầy đủ, ví dụ `https://api.ten-mien.example/api/v1`.
2. Cho phép origin frontend trong biến `CORS_ORIGINS` của backend.
3. Dùng HTTPS cho API nếu frontend chạy HTTPS; kiểm tra lại đường dẫn ảnh bìa và trang sách.

Đây là cấu hình triển khai bổ sung, không phải chế độ mặc định. Không mở trực tiếp `index.html` bằng `file://` vì ES Modules và các yêu cầu API cần môi trường web phù hợp.

## 8. Mở website qua Cloudflare Quick Tunnel

Sau khi ứng dụng Docker tại mục 5 hoạt động, mở terminal WSL khác:

```bash
docker run --rm -it \
  --network thu-vien-so_default \
  cloudflare/cloudflared:latest \
  tunnel --no-autoupdate --url http://web:80
```

Mở URL `https://…trycloudflare.com` xuất hiện trong log. Đường dẫn này phục vụ cả frontend và API thông qua Nginx. Giữ terminal mở; `Ctrl+C` dừng Tunnel.

Sửa `.env` ở gốc dự án, thay URL mẫu bằng URL vừa nhận được:

```dotenv
PUBLIC_ORIGIN=https://TEN-TUNNEL.trycloudflare.com
```

Áp dụng:

```bash
docker compose up -d --wait
```

`PUBLIC_ORIGIN` giúp backend tạo đúng liên kết quên mật khẩu; không phải biến sửa trực tiếp giao diện. Khi tạo lại Tunnel có URL mới, cần cập nhật lại biến này.

Quick Tunnel là địa chỉ tạm dùng thử. Website chỉ hoạt động khi máy bật, WSL/Docker đang chạy và có mạng. Hướng dẫn chạy Tunnel nền bằng Compose có trong README chính.

## 9. Kiểm thử frontend

Với Node.js và npm đã cài, từ gốc dự án:

```bash
npm --prefix frontend run check
npm --prefix frontend test
```

Lệnh đầu kiểm tra cú pháp JavaScript; lệnh sau chạy kiểm thử API client. Không có bước build ứng dụng bằng npm.

Kiểm tra thủ công trên trình duyệt:

- Tra cứu sách và mở một PDF đã tải lên.
- Thử một trang/hai trang, các mốc thu phóng và toàn màn hình.
- Thử chuyển trang bằng nút trái/phải và phím mũi tên.
- Đăng nhập, lưu yêu thích, đọc tiếp từ tiến độ đã lưu.
- Kiểm tra quyền quản trị với tài khoản `librarian`.
- Gửi yêu cầu quên mật khẩu sau khi cấu hình SMTP.

## 10. Lỗi thường gặp

| Hiện tượng | Kiểm tra |
| --- | --- |
| Không tải được danh sách sách | API health, tab Network trong Developer Tools và cấu hình `LIBRARY_API_BASE` |
| Lỗi CORS | Origin frontend có được phép trong `CORS_ORIGINS` của backend hay không |
| `/ui/app.js` trả 404 | Dùng đúng HTML của bộ mã mới; mã hiện tại nằm trong `frontend/src/`, không tự đổi đường dẫn |
| Sửa mã nhưng giao diện chưa đổi | Build lại Docker image và tải lại trang, kiểm tra cache trình duyệt |
| Không thấy mục quản trị | Tài khoản cần vai trò `librarian` |
| Đăng nhập được ở Python nhưng không được ở Docker | Hai môi trường mặc định dùng cơ sở dữ liệu khác nhau |
| Email đặt lại mật khẩu trỏ về localhost | Cập nhật `PUBLIC_ORIGIN` và áp dụng lại Compose, sau đó yêu cầu email mới |
| Tunnel báo 502 | Kiểm tra `web`/`backend`, mạng Docker và đích `http://web:80` |

Tài liệu Tunnel: https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/
