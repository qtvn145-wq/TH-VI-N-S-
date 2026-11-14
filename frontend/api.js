export const base = (window.LIBRARY_API_BASE || '/api/v1').replace(/\/$/, '');
let token = sessionStorage.getItem('library.session') || '';
export const setToken = value => { token = value; value ? sessionStorage.setItem('library.session',value) : sessionStorage.removeItem('library.session'); };
const messages = {
 INVALID_CREDENTIALS:'Email hoặc mật khẩu không đúng.',INVALID_SESSION:'Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.',
 LIBRARIAN_REQUIRED:'Chức năng này chỉ dành cho thủ thư.',FORBIDDEN:'Bạn không có quyền thực hiện thao tác này.',NOT_FOUND:'Dữ liệu không còn tồn tại.',
 NO_COPY_AVAILABLE:'Sách hiện đã hết bản có thể mượn. Bạn có thể tham gia hàng đợi.',LOAN_LIMIT_REACHED:'Bạn đã đạt giới hạn 3 cuốn (gồm đang giữ chỗ và đang mượn).',
 QUEUE_PRIORITY:'Bản sách đang được ưu tiên cho bạn đọc đầu hàng đợi.',INVALID_LOAN_STATE:'Trạng thái phiếu đã thay đổi. Hãy tải lại danh sách.',
 DATA_CONFLICT:'Dữ liệu bị trùng hoặc đang được sử dụng. Kiểm tra email, tên, mã vạch và các dữ liệu liên quan.',COPY_IN_USE:'Bản sách đang được giữ hoặc mượn, không thể thanh lý.',
 ALREADY_PAID:'Khoản phạt này đã được thu.',COPY_AVAILABLE:'Sách còn bản có thể mượn. Hãy đặt mượn trực tiếp.',FILE_TOO_LARGE:'Ảnh phải nhỏ hơn hoặc bằng 5 MiB.',INVALID_IMAGE:'Chọn ảnh JPEG, PNG hoặc WebP hợp lệ.'
};
export async function api(path, method='GET', body) {
 const controller = new AbortController(); const timer=setTimeout(()=>controller.abort(),20000);
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
