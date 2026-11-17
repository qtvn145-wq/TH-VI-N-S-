# Kết quả kiểm tra bản sách điện tử

- 9 kiểm thử Back end đạt: upload PDF, ảnh trang thật, cache ảnh, phân quyền, PDF sai/quá lớn/quá nhiều trang, biên số trang, revision cũ, tiến độ riêng từng tài khoản, thay PDF đặt lại tiến độ, tra cứu/yêu thích, ẩn sách và nâng cấp CSDL.
- 2 kiểm thử DevOps đạt: health check và sao lưu/khôi phục CSDL, ảnh bìa, PDF; từ chối ghi đè dữ liệu đang có.
- 1 kiểm thử tích hợp HTTP đạt: phục vụ asset Front end, đăng nhập, tải PDF, đọc trang, lưu tiến độ và đồng bộ OpenAPI.
- Cú pháp JavaScript/shell và bộ kiểm thử API client đạt.
- Kiểm thử DOM mô phỏng trình đọc: chế độ hai/một trang, trước/sau, trang cuối, lưu tiến độ khách, phóng to, lỗi PDF thay đổi, đóng trình đọc và tiếp tục đọc bằng tài khoản.

Chưa kiểm chứng hình ảnh hoạt ảnh trong trình duyệt thật hoặc build/chạy Docker tại môi trường này. Kiểm thử DOM không thay thế kiểm tra hiển thị trên Chrome/Edge/điện thoại. CI và README có lệnh kiểm tra khi chạy trên máy của bạn.

PDF mẫu trong demo.py do chương trình tự tạo, không sao chép nội dung từ trang tham khảo. Trang tham khảo trước đó chỉ hiện màn hình tải trong phiên kiểm tra; hiệu ứng lật sách ở bản này được triển khai theo yêu cầu, không khẳng định sao chép chính xác giao diện của trang đó.
