export const base = (window.LIBRARY_API_BASE || '/api/v1').replace(/\/$/, '');
let token = sessionStorage.getItem('library.session') || '';
export const setToken = value => { token = value; value ? sessionStorage.setItem('library.session',value) : sessionStorage.removeItem('library.session'); };
const messages = {
 RESET_EMAIL_UNAVAILABLE:'Chức năng gửi email chưa được cấu hình. Vui lòng liên hệ quản trị viên để đặt lại mật khẩu.',RESET_LINK_INVALID:'Liên kết không hợp lệ, đã hết hạn hoặc đã được sử dụng. Hãy yêu cầu liên kết mới.',
 EMAIL_EXISTS:'Email đã được sử dụng. Hãy chọn email khác.',LAST_ADMIN:'Phải giữ lại ít nhất một quản trị viên. Hãy tạo hoặc cấp quyền cho tài khoản khác trước.',CANNOT_DELETE_SELF:'Không thể xóa tài khoản đang đăng nhập.',ACCOUNT_HAS_HISTORY:'Tài khoản có dữ liệu lịch sử liên quan nên chưa thể xóa.',
 INVALID_CREDENTIALS:'Email hoặc mật khẩu không đúng.',INVALID_SESSION:'Phiên đăng nhập đã hết hạn.',
 LIBRARIAN_REQUIRED:'Chỉ quản trị viên được thực hiện thao tác này.',FORBIDDEN:'Bạn không có quyền truy cập.',NOT_FOUND:'Không tìm thấy sách hoặc sách đã được ẩn.',
 DATA_CONFLICT:'Dữ liệu bị trùng hoặc danh mục đang được sử dụng.',FILE_TOO_LARGE:'Ảnh vượt quá 5 MiB.',INVALID_IMAGE:'Chọn ảnh JPEG, PNG hoặc WebP hợp lệ.',
 PDF_TOO_LARGE:'PDF vượt quá 25 MiB.',INVALID_PDF:'PDF không hợp lệ, có mật khẩu hoặc vượt giới hạn 500 trang/kích thước trang.',PDF_TOO_COMPLEX:'PDF quá phức tạp, không thể xử lý trong thời gian cho phép.',
 EBOOK_NOT_FOUND:'Sách chưa có PDF hoặc tệp không còn tồn tại.',EBOOK_CHANGED:'Nội dung sách vừa thay đổi. Hãy đóng và mở lại sách.',PAGE_NOT_FOUND:'Trang không tồn tại.'
};
export async function api(path, method='GET', body) {
 const controller = new AbortController(); const timer=setTimeout(()=>controller.abort(),path.endsWith('/ebook')&&method==='POST'?60000:30000);
 try {
  const headers={}; if(token) headers.Authorization=`Bearer ${token}`;
  if(body && !(body instanceof FormData)) headers['Content-Type']='application/json';
  const response=await fetch(base+path,{method,headers,body:body instanceof FormData?body:body?JSON.stringify(body):undefined,signal:controller.signal});
  const data=await response.json().catch(()=>null);
  if(!response.ok){
   if(response.status===401 && path!='/auth/login'){setToken('');window.dispatchEvent(new Event('session-expired'));}
   const detail=data?.detail;
   const fields={email:'Email',password:'Mật khẩu',name:'Tên',title:'Tên sách',barcode:'Mã vạch',description:'Mô tả'};
   const message=Array.isArray(detail)?detail.map(e=>`${fields[e.loc.at(-1)]||e.loc.at(-1)}: ${e.msg}`).join('\n'):messages[detail] || `Yêu cầu thất bại (HTTP ${response.status}). Vui lòng thử lại.`;
   throw new Error(message);
  }
  return data;
 } catch(e) {
  if(e.name==='AbortError'||e instanceof TypeError) throw new Error(method==='GET'?'Không kết nối được máy chủ. Kiểm tra kết nối và thử lại.':'Chưa xác định được kết quả gửi yêu cầu. Hãy tải lại danh sách để kiểm tra trước khi gửi lại.');
  throw e;
 } finally{clearTimeout(timer);}
}
export function coverUrl(path){if(!path)return '';const url=new URL(path,new URL(base,location.href));return ['http:','https:'].includes(url.protocol)?url.href:'';}
