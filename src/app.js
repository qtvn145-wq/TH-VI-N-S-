import {api,setToken,coverUrl} from './api.js';
import {openReader,closeReader} from './reader.js';
const $=s=>document.querySelector(s), app=$('#app'), dialog=$('#dialog');
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let user=null,authors=[],categories=[],page=0,route='books',generation=0,books=[],noticeTimer;
const filters={q:'',author:'',category_id:'',readable_only:'',sort:''};
const staff=()=>user?.role==='librarian';
const names=(ids,list)=>ids.map(id=>list.find(x=>x.id===id)?.name||`#${id}`).join(', ');
function notify(message){$('#notice').textContent=message;clearTimeout(noticeTimer);noticeTimer=setTimeout(()=>$('#notice').textContent='',6500);}
function heading(kicker,title,description=''){return `<div class="eyebrow">${kicker}</div><h1>${title}</h1><p class="muted">${description}</p>`;}
function shell(){
 const links=[['books','▤','Sách điện tử'],...(user?[['favorites','♡','Sách yêu thích']]:[]),...(staff()?[['manage','▥','Quản lý sách'],['authors','◇','Tác giả'],['categories','⊞','Chủ đề'],['accounts','♙','Quản lý tài khoản']]:[])];
 app.innerHTML=`<div class="layout"><aside><div class="brand"><span class="logo">▤</span><div>Thư viện số<small>KHOA CÔNG NGHỆ THÔNG TIN</small></div></div><div><p class="eyebrow">${staff()?'Không gian quản trị':'Không gian bạn đọc'}</p><nav>${links.map(([id,icon,title])=>`<button data-nav="${id}" class="${route===id?'active':''}"><span>${icon}</span>${title}</button>`).join('')}</nav></div><footer>Tri thức mở ra những khả năng mới.<br>Thư viện Khoa CNTT · Cổng trực tuyến</footer></aside><div class="main"><header><div><strong>Thư viện sách điện tử</strong><br><small>Khám phá · Mở sách · Đọc mỗi ngày</small></div><div class="user">${user?`<span class="avatar">${esc(user.name.slice(0,1))}</span><div>${esc(user.name)}<br><small>${staff()?'Quản trị':'Bạn đọc'}</small></div><button id="logout">Đăng xuất</button>`:'<button data-nav="login">Đăng nhập</button>'}</div></header><main id="content" aria-live="polite"><div class="empty">Đang tải dữ liệu…</div></main></div></div>`;
 app.querySelectorAll('[data-nav]').forEach(b=>b.onclick=()=>go(b.dataset.nav));
 if($('#logout')) $('#logout').onclick=async()=>{try{await api('/auth/logout','POST');setToken('');user=null;go('books');}catch(e){notify(e.message);}};
}
function go(next){closeReader();dialog.close();location.hash=next;if(route===next)render();}
window.addEventListener('hashchange',()=>{route=readRoute();page=0;render();});
window.addEventListener('session-expired',()=>{user=null;dialog.close();go('login');notify('Phiên hết hạn. Vui lòng đăng nhập lại.');});
function mount(html,gen){if(gen!==generation)return false;$('#content').innerHTML=html;return true;}
function openModal(title,html){dialog.innerHTML=`<div class="row space"><h2>${title}</h2><button id="close" aria-label="Đóng">✕</button></div>${html}`;$('#close').onclick=()=>dialog.close();dialog.showModal();}
function formError(form,e){let box=form.querySelector('.error');if(!box){box=document.createElement('div');box.className='error';form.prepend(box);}box.textContent=e.message;}
async function submit(form,fn){const buttons=[...form.querySelectorAll('button')];buttons.forEach(b=>b.disabled=true);try{await fn();}catch(e){formError(form,e);}finally{buttons.forEach(b=>b.disabled=false);}}
function pager(count){return `<div class="pager"><button id="prev" ${page===0?'disabled':''}>← Trước</button><span>Trang ${page+1}</span><button id="next" ${count<12?'disabled':''}>Tiếp →</button></div>`;}
function bindPager(){if($('#prev'))$('#prev').onclick=()=>{page--;render();};if($('#next'))$('#next').onclick=()=>{page++;render();};}
function table(headers,rows){return `<div class="table-wrap"><table><thead><tr>${headers.map(h=>`<th>${h}</th>`).join('')}</tr></thead><tbody>${rows.join('')}</tbody></table></div>${rows.length?'':'<div class="empty">Chưa có dữ liệu phù hợp.</div>'}`;}
async function action(path,method='POST',body,message='Đã cập nhật thành công.'){await api(path,method,body);notify(message);dialog.close();await render();}
function confirmAction(title,description,fn){openModal(title,`<p>${esc(description)}</p><form class="form"><div class="error" role="alert"></div><button class="primary">Xác nhận</button></form>`);dialog.querySelector('form').onsubmit=e=>{e.preventDefault();submit(e.target,fn);};}
function art(b){const colors=['#305647','#355b71','#986749','#655575','#697747','#2a6869'];return b.cover_url?`<img src="${esc(coverUrl(b.cover_url))}" alt="Bìa ${esc(b.title)}">`:`<div class="book-art" style="--book-color:${colors[b.id%colors.length]}"><small>KHOA CNTT / ${String(b.id).padStart(3,'0')}</small><span>${esc(b.title)}</span><small>THƯ VIỆN SỐ</small></div>`;}
async function catalog(gen,manage=false){
 const qs=new URLSearchParams({limit:13,offset:page*12});Object.entries(filters).forEach(([k,v])=>{if(v)qs.set(k,v);});
 const result=await api('/books?'+qs);if(gen!==generation)return;const data=result.slice(0,12);books=data;
 mount(`${manage?heading('Quản trị danh mục','Quản lý đầu sách','Quản lý đầu sách, ảnh bìa và tệp PDF cho bạn đọc trực tuyến.'):`<section class="hero"><div><div class="eyebrow">Khám phá kho tri thức</div><h1>Cuốn sách tiếp theo của bạn.</h1><p class="muted">Tìm giáo trình, tài liệu và những ý tưởng mới.<br>Mở sách trực tuyến và lật từng trang ngay trên màn hình.</p></div><div class="hero-mark" aria-hidden="true">❧</div></section>`}
 <div class="row space"><h2>${manage?'Danh mục đầu sách':'Khám phá sách'}</h2>${manage?'<button id="new-book" class="primary">+ Thêm đầu sách</button>':'<span class="muted">Đọc trực tuyến · PDF · Lật trang</span>'}</div>
 <form id="search" class="toolbar"><label>Tên sách<input name="q" value="${esc(filters.q)}" placeholder="Tên sách có dấu hoặc không dấu…"></label><label>Tác giả<input name="author" value="${esc(filters.author)}" placeholder="Tên tác giả…"></label><label>Chủ đề<select name="category_id"><option value="">Tất cả chủ đề</option>${categories.map(c=>`<option value="${c.id}" ${String(c.id)===filters.category_id?'selected':''}>${esc(c.name)}</option>`).join('')}</select></label><label>Tình trạng<select name="readable_only"><option value="">Tất cả sách</option><option value="true" ${filters.readable_only==='true'?'selected':''}>Có sách để đọc</option></select></label><label>Sắp xếp<select name="sort">${[['','Theo mã sách'],['newest','Mới bổ sung'],['title','Tên sách A–Z']].map(([v,t])=>`<option value="${v}" ${filters.sort===v?'selected':''}>${t}</option>`).join('')}</select></label><button class="primary">Tìm kiếm</button><button type="button" id="clear">Xóa lọc</button></form>
 <div class="grid">${data.map(b=>`<article class="card"><div class="cover">${art(b)}</div><div class="card-body"><div class="eyebrow">${esc(names(b.category_ids,categories)||'Tài liệu')}</div><h3>${esc(b.title)}</h3><div class="muted">${esc(names(b.author_ids,authors)||'Chưa cập nhật tác giả')}</div><div class="card-actions"><span class="tag ${b.page_count?'':'warn'}">${b.page_count?`${b.page_count} trang`:'Chưa có PDF'}</span><button data-book="${b.id}">${manage?'Quản lý →':'Chi tiết →'}</button></div></div></article>`).join('')}</div>${data.length?'':'<div class="empty">Không tìm thấy sách. Hãy thử từ khóa hoặc chủ đề khác.</div>'}${pager(result.length>12?12:0)}`,gen);
 $('#search').onsubmit=e=>{e.preventDefault();Object.assign(filters,Object.fromEntries(new FormData(e.target)));page=0;render();};$('#clear').onclick=()=>{Object.keys(filters).forEach(k=>filters[k]='');page=0;render();};bindPager();
 document.querySelectorAll('[data-book]').forEach(b=>b.onclick=()=>manage?editBook(books.find(x=>x.id===+b.dataset.book)):detail(+b.dataset.book));if(manage)$('#new-book').onclick=()=>editBook();
}
async function detail(id){try{
 const [b,saved]=await Promise.all([api('/books/'+id),user?api('/favorites/'+id):Promise.resolve(null)]);
 openModal(esc(b.title),`<div class="detail-cover cover">${art(b)}</div><p>${esc(b.description||'Chưa có mô tả.')}</p><p><strong>Tác giả:</strong> ${esc(names(b.author_ids,authors))}<br><strong>Chủ đề:</strong> ${esc(names(b.category_ids,categories))}</p><p class="tag">${b.page_count?b.page_count+' trang':'Chưa có tệp PDF'}</p><div class="row" style="clear:both">${b.page_count?'<button id="read-book" class="primary">Mở sách →</button>':''}${user?`<button id="favorite-toggle" aria-pressed="${saved.ok}">${saved.ok?'♥ Bỏ yêu thích':'♡ Lưu yêu thích'}</button>`:''}</div>`);
 if($('#read-book'))$('#read-book').onclick=()=>{dialog.close();openReader(b,user,notify);};
 if($('#favorite-toggle'))$('#favorite-toggle').onclick=async e=>{const button=e.currentTarget;button.disabled=true;try{await api('/favorites/'+id,saved.ok?'DELETE':'PUT');saved.ok=!saved.ok;button.textContent=saved.ok?'♥ Bỏ yêu thích':'♡ Lưu yêu thích';button.setAttribute('aria-pressed',String(saved.ok));if(route==='favorites')await favoritesScreen(generation);}catch(error){notify(error.message);}finally{button.disabled=false;}};
 }catch(e){notify(e.message);}}
async function favoritesScreen(gen){
 const result=await api('/favorites?'+new URLSearchParams({limit:13,offset:page*12}));
 if(gen!==generation)return;
 if(!result.length&&page>0){page--;return favoritesScreen(gen);}
 const data=result.slice(0,12);
 if(!mount(`${heading('Tủ sách cá nhân','Sách yêu thích','Lưu những cuốn sách muốn đọc tiếp. Danh sách được lưu riêng theo tài khoản.')}<div class="grid">${data.map(b=>`<article class="card"><div class="cover">${art(b)}</div><div class="card-body"><h3>${esc(b.title)}</h3><p class="muted">${esc(names(b.author_ids,authors))}</p><div class="card-actions"><span class="tag ${b.page_count?'':'warn'}">${b.page_count} trang</span><button data-book="${b.id}">Chi tiết →</button></div></div></article>`).join('')}</div>${data.length?'':'<div class="empty">Chưa có sách yêu thích. Mở chi tiết sách và chọn “Lưu yêu thích”.</div>'}${pager(result.length>12?12:0)}`,gen))return;
 bindPager();document.querySelectorAll('[data-book]').forEach(b=>b.onclick=()=>detail(+b.dataset.book));
}
async function auth(gen,register=false){mount(`<div class="auth panel">${heading('Thư viện số',register?'Tạo tài khoản bạn đọc':'Chào mừng trở lại',register?'Đăng ký để lưu sách yêu thích và tiếp tục đọc trên thiết bị khác.':'Đăng nhập để tiếp tục hành trình khám phá.')}<form id="auth" class="form"><div class="error" role="alert"></div>${register?'<label>Họ và tên<input name="name" required maxlength="150" autocomplete="name"></label>':''}<label>Email<input type="email" name="email" required maxlength="254" autocomplete="username"></label><label>Mật khẩu<input type="password" name="password" required minlength="10" maxlength="128" autocomplete="${register?'new-password':'current-password'}"></label><p class="hint">Mật khẩu từ 10 đến 128 ký tự.</p><button class="primary">${register?'Đăng ký':'Đăng nhập'}</button>${register?'':'<button type="button" id="forgot-password">Quên mật khẩu?</button>'}<button type="button" id="switch-auth">${register?'Đã có tài khoản? Đăng nhập':'Chưa có tài khoản? Đăng ký'}</button></form></div>`,gen);if($('#forgot-password'))$('#forgot-password').onclick=()=>go('forgot-password');$('#switch-auth').onclick=()=>go(register?'login':'register');$('#auth').onsubmit=e=>{e.preventDefault();submit(e.target,async()=>{const body=Object.fromEntries(new FormData(e.target));if(register){await api('/auth/register','POST',body);notify('Đã tạo tài khoản. Bạn có thể đăng nhập.');go('login');return;}const data=await api('/auth/login','POST',body);setToken(data.access_token);user=await api('/auth/me');go(staff()?'manage':'books');});};}
async function catalogNames(gen,kind){const data=await api('/catalog/'+kind);if(!mount(`${heading('Quản trị danh mục',kind==='authors'?'Tác giả':'Chủ đề','Thêm, sửa và quản lý danh mục dùng cho đầu sách.')}<div class="panel"><form id="add-name" class="toolbar"><label>Tên mới<input name="name" required maxlength="150" placeholder="Nhập tên…"></label><button class="primary">+ Thêm</button><div class="error" role="alert"></div></form>${table(['ID','Tên','Thao tác'],data.map(x=>`<tr><td>#${x.id}</td><td>${esc(x.name)}</td><td><button data-edit="${x.id}">Sửa</button><button class="danger" data-delete="${x.id}">Xóa</button></td></tr>`))}</div>`,gen))return;
 $('#add-name').onsubmit=e=>{e.preventDefault();submit(e.target,()=>action('/catalog/'+kind,'POST',Object.fromEntries(new FormData(e.target))));};
 document.querySelectorAll('[data-delete]').forEach(b=>b.onclick=()=>confirmAction('Xóa danh mục','Máy chủ sẽ từ chối nếu danh mục đang được sử dụng.',()=>action(`/catalog/${kind}/${b.dataset.delete}`,'DELETE')));
 document.querySelectorAll('[data-edit]').forEach(b=>b.onclick=()=>{const x=data.find(x=>x.id===+b.dataset.edit);openModal('Sửa tên',`<form class="form"><label>Tên<input name="name" required maxlength="150" value="${esc(x.name)}"></label><div class="error" role="alert"></div><button class="primary">Lưu thay đổi</button></form>`);dialog.querySelector('form').onsubmit=e=>{e.preventDefault();submit(e.target,()=>action(`/catalog/${kind}/${x.id}`,'PUT',Object.fromEntries(new FormData(e.target))));};});}
function editBook(b){openModal(b?'Quản lý đầu sách':'Thêm đầu sách',`<form id="book-form" class="form"><div class="error" role="alert"></div><label>Tên sách<input name="title" required maxlength="300" value="${esc(b?.title||'')}"></label><label>Mô tả<textarea name="description" maxlength="5000">${esc(b?.description||'')}</textarea></label><div class="split"><label>Tác giả<select name="author_ids" multiple>${authors.map(a=>`<option value="${a.id}" ${b?.author_ids.includes(a.id)?'selected':''}>${esc(a.name)}</option>`).join('')}</select></label><label>Chủ đề<select name="category_ids" multiple>${categories.map(c=>`<option value="${c.id}" ${b?.category_ids.includes(c.id)?'selected':''}>${esc(c.name)}</option>`).join('')}</select></label></div><span class="hint">Giữ Ctrl (Windows) / Cmd (macOS) để chọn nhiều mục. Thêm danh mục mới ở màn hình Tác giả hoặc Chủ đề.</span><button class="primary">${b?'Lưu thông tin':'Tạo đầu sách'}</button></form>${b?`<hr><form id="ebook-form" class="form"><label>Tệp sách PDF · tối đa 25 MiB / 500 trang<input type="file" name="file" accept="application/pdf,.pdf" required></label><p class="hint">${b.page_count?`Hiện có ${b.page_count} trang. Tải tệp mới sẽ thay nội dung sách và đặt lại tiến độ đọc.`:'Chọn PDF để bạn đọc có thể mở sách trực tuyến.'}</p><div class="error" role="alert"></div><button class="primary">Tải sách PDF</button></form><hr><div class="row"><button id="delete-book" class="danger">Xóa đầu sách</button></div><form id="cover-form" class="form" style="margin-top:20px"><label>Tải ảnh bìa · PNG, JPEG, WebP · tối đa 5 MiB<input type="file" name="file" accept="image/png,image/jpeg,image/webp" required></label><div class="error" role="alert"></div><button>Tải ảnh lên</button></form>`:''}`);
 $('#book-form').onsubmit=e=>{e.preventDefault();submit(e.target,async()=>{const f=new FormData(e.target),body={title:f.get('title'),description:f.get('description'),author_ids:f.getAll('author_ids').map(Number),category_ids:f.getAll('category_ids').map(Number)};const saved=await api(b?'/books/'+b.id:'/books',b?'PUT':'POST',body);notify('Đã lưu đầu sách.');dialog.close();await render();editBook(saved);});};
 if(b){$('#ebook-form').onsubmit=e=>{e.preventDefault();submit(e.target,async()=>{const form=new FormData(e.target);if(form.get('file').size>25*1024*1024)throw new Error('Tệp PDF vượt quá 25 MiB.');await action('/books/'+b.id+'/ebook','POST',form,'Đã tải sách PDF.');});};$('#delete-book').onclick=()=>confirmAction('Xóa đầu sách',`Xóa “${b.title}”? Sách sẽ được ẩn khỏi thư viện; tệp và dữ liệu cũ được giữ lại.`,()=>action('/books/'+b.id,'DELETE'));$('#cover-form').onsubmit=e=>{e.preventDefault();submit(e.target,async()=>{const f=new FormData(e.target),file=f.get('file');if(file.size>5*1024*1024)throw new Error('Ảnh vượt quá 5 MiB.');if(!['image/png','image/jpeg','image/webp'].includes(file.type))throw new Error('Chỉ chấp nhận PNG, JPEG hoặc WebP.');await action('/books/'+b.id+'/cover','POST',f,'Đã tải ảnh bìa.');});};}
}
let accountQuery='';
const roleLabel=role=>role==='librarian'?'Quản trị (thủ thư)':'Bạn đọc';
async function accountsScreen(gen){
 const result=await api('/admin/users?'+new URLSearchParams({q:accountQuery,limit:13,offset:page*12}));
 if(gen!==generation)return;
 if(!result.length&&page>0){page--;return accountsScreen(gen);}
 const data=result.slice(0,12);
 if(!mount(`${heading('Quản trị hệ thống','Quản lý tài khoản','Thêm, sửa thông tin, phân quyền và đặt lại mật khẩu. Quản trị (thủ thư) được quản lý sách và tài khoản.')}<div class="row space"><h2>Danh sách tài khoản</h2><button id="new-account" class="primary">+ Thêm tài khoản</button></div><form id="account-search" class="toolbar"><label>Tìm tên hoặc email<input name="q" maxlength="254" value="${esc(accountQuery)}" placeholder="Nhập tên hoặc email…"></label><button class="primary">Tìm kiếm</button></form>${table(['ID','Họ và tên','Email','Vai trò','Thao tác'],data.map(x=>`<tr><td>#${x.id}</td><td>${esc(x.name)}${x.id===user.id?' <span class="tag">Bạn</span>':''}</td><td>${esc(x.email)}</td><td>${roleLabel(x.role)}</td><td><div class="row"><button data-account-edit="${x.id}">Sửa</button><button data-account-password="${x.id}">Đổi mật khẩu</button><button class="danger" data-account-delete="${x.id}" ${x.id===user.id?'disabled title="Không thể xóa tài khoản đang đăng nhập"':''}>Xóa</button></div></td></tr>`))}${pager(result.length>12?12:0)}`,gen))return;
 bindPager();$('#new-account').onclick=()=>editAccount();
 $('#account-search').onsubmit=e=>{e.preventDefault();accountQuery=new FormData(e.target).get('q');page=0;render();};
 data.forEach(x=>{
  $(`[data-account-edit="${x.id}"]`).onclick=()=>editAccount(x);
  $(`[data-account-password="${x.id}"]`).onclick=()=>accountPassword(x);
  $(`[data-account-delete="${x.id}"]`).onclick=()=>confirmAction('Xóa tài khoản',`Xóa tài khoản ${x.email}? Sách yêu thích và tiến độ đọc của tài khoản sẽ bị xóa. Không thể hoàn tác.`,()=>action('/admin/users/'+x.id,'DELETE',undefined,'Đã xóa tài khoản.'));
 });
}
function accountSignedOut(){setToken('');user=null;dialog.close();go('login');notify('Đã cập nhật tài khoản. Vui lòng đăng nhập lại bằng thông tin mới.');}
function editAccount(account){
 openModal(account?'Sửa tài khoản':'Thêm tài khoản',`<form id="account-form" class="form"><div class="error" role="alert"></div><label>Họ và tên<input name="name" required maxlength="150" value="${esc(account?.name||'')}" autocomplete="off"></label><label>Email<input name="email" type="email" required maxlength="254" value="${esc(account?.email||'')}" autocomplete="off"></label><label>Vai trò<select name="role">${['reader','librarian'].map(role=>`<option value="${role}" ${account?.role===role?'selected':''}>${roleLabel(role)}</option>`).join('')}</select></label>${account?'<p class="hint">Đổi email hoặc vai trò sẽ đăng xuất tài khoản này khỏi các thiết bị. Dùng “Đổi mật khẩu” để đặt mật khẩu mới.</p>':'<label>Mật khẩu<input name="password" type="password" required minlength="10" maxlength="128" autocomplete="new-password"></label><p class="hint">Mật khẩu từ 10 đến 128 ký tự.</p>'}<button class="primary">${account?'Lưu thay đổi':'Tạo tài khoản'}</button></form>`);
 $('#account-form').onsubmit=e=>{e.preventDefault();submit(e.target,async()=>{
  const body=Object.fromEntries(new FormData(e.target));
  const saved=await api('/admin/users'+(account?'/'+account.id:''),account?'PUT':'POST',body);
  if(account?.id===user.id){
   if(saved.email!==user.email||saved.role!==user.role){accountSignedOut();return;}
   user=saved;
  }
  dialog.close();notify(account?'Đã cập nhật tài khoản.':'Đã tạo tài khoản.');await render();
 });};
}
function accountPassword(account){
 openModal('Đặt lại mật khẩu',`<p>Tài khoản: <strong>${esc(account.email)}</strong></p><form id="password-form" class="form"><div class="error" role="alert"></div><label>Mật khẩu mới<input name="password" type="password" required minlength="10" maxlength="128" autocomplete="new-password"></label><label>Nhập lại mật khẩu mới<input name="confirm" type="password" required minlength="10" maxlength="128" autocomplete="new-password"></label><p class="hint">Từ 10 đến 128 ký tự. Các phiên đăng nhập hiện tại của tài khoản sẽ hết hiệu lực.</p><button class="primary">Lưu mật khẩu mới</button></form>`);
 $('#password-form').onsubmit=e=>{e.preventDefault();submit(e.target,async()=>{
  const form=new FormData(e.target);if(form.get('password')!==form.get('confirm'))throw new Error('Mật khẩu nhập lại không khớp.');
  await api('/admin/users/'+account.id+'/password','PUT',{password:form.get('password')});
  if(account.id===user.id){accountSignedOut();return;}
  dialog.close();notify('Đã đặt lại mật khẩu và đăng xuất các phiên cũ.');
 });};
}

let resetToken='';
function readRoute(){
 const fragment=location.hash.slice(1)||'books';
 if(fragment.startsWith('reset-password?')){
  resetToken=new URLSearchParams(fragment.split('?')[1]).get('token')||'';
  history.replaceState(null,'',location.pathname+location.search+'#reset-password');
  return 'reset-password';
 }
 return fragment;
}
async function passwordScreen(gen,reset=false){
 if(!mount(`<div class="auth panel">${heading('Khôi phục tài khoản',reset?'Đặt mật khẩu mới':'Quên mật khẩu?',reset?'Nhập mật khẩu mới cho tài khoản của bạn.':'Nhập email đã đăng ký để nhận liên kết đặt lại mật khẩu.')}<form id="password-recovery" class="form"><div class="error" role="alert"></div>${reset?'<label>Mật khẩu mới<input name="password" type="password" required minlength="10" maxlength="128" autocomplete="new-password"></label><label>Nhập lại mật khẩu<input name="confirm" type="password" required minlength="10" maxlength="128" autocomplete="new-password"></label><p class="hint">Từ 10 đến 128 ký tự. Liên kết chỉ dùng một lần, có hiệu lực 15 phút.</p>':'<label>Email<input name="email" type="email" required maxlength="254" autocomplete="email"></label>'}<button class="primary">${reset?'Lưu mật khẩu mới':'Gửi liên kết đặt lại'}</button><button id="back-login" type="button">Quay lại đăng nhập</button></form></div>`,gen))return;
 $('#back-login').onclick=()=>go('login');
 if(reset&&!/^[A-Za-z0-9_-]{43}$/.test(resetToken)){
  $('#password-recovery').innerHTML='<p class="error">Liên kết không hợp lệ. Hãy mở lại liên kết trong email hoặc yêu cầu liên kết mới.</p><button type="button" id="request-new-link">Gửi liên kết mới</button>';
  $('#request-new-link').onclick=()=>go('forgot-password');return;
 }
 $('#password-recovery').onsubmit=e=>{e.preventDefault();submit(e.target,async()=>{
  const form=new FormData(e.target);
  if(reset){
   if(form.get('password')!==form.get('confirm'))throw new Error('Mật khẩu nhập lại không khớp.');
   await api('/auth/reset-password','POST',{token:resetToken,password:form.get('password')});
   resetToken='';setToken('');user=null;go('login');notify('Đã đổi mật khẩu. Hãy đăng nhập bằng mật khẩu mới.');
  }else{
   await api('/auth/forgot-password','POST',{email:form.get('email')});
   e.target.innerHTML='<p role="status">Nếu email này đã đăng ký, liên kết đặt lại sẽ được gửi đến hộp thư. Hãy kiểm tra cả thư rác. Nếu chưa nhận được, chờ ít nhất 60 giây rồi thử lại.</p><button type="button" id="recovery-login">Quay lại đăng nhập</button><button type="button" id="recovery-again">Thử lại</button>';
   $('#recovery-login').onclick=()=>go('login');$('#recovery-again').onclick=()=>render();
  }
 });};
}

async function render(){closeReader();const gen=++generation;shell();try{if(!['books','login','register','forgot-password','reset-password'].includes(route)&&!user){go('login');return;}if(['manage','authors','categories','accounts'].includes(route)&&!staff()){mount('<div class="error">Bạn không có quyền truy cập màn hình này.</div>',gen);return;}
 [authors,categories]=await Promise.all([api('/catalog/authors'),api('/catalog/categories')]);if(gen!==generation)return;
 switch(route){case 'books':case 'manage':await catalog(gen,route==='manage');break;case 'login':case 'register':await auth(gen,route==='register');break;case 'favorites':await favoritesScreen(gen);break;case 'accounts':await accountsScreen(gen);break;case 'forgot-password':case 'reset-password':await passwordScreen(gen,route==='reset-password');break;case 'authors':case 'categories':await catalogNames(gen,route);break;default:mount('<div class="empty">Không tìm thấy màn hình.</div>',gen);}
 }catch(e){if(mount(`<div class="error" role="alert">${esc(e.message)}</div><p><button id="retry">Thử tải lại</button></p>`,gen))$('#retry').onclick=()=>render();}}
async function boot(){if(sessionStorage.getItem('library.session')){try{user=await api('/auth/me');}catch(e){notify(e.message);}}route=readRoute();await render();}
boot();
