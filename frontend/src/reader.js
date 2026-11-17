import {api,base} from './api.js';

let dispose=null;
export function closeReader(){if(dispose){const close=dispose;dispose=null;close();}}
export async function openReader(book,user,notify){
 closeReader();
 const modal=document.createElement('dialog');modal.className='reader';
 modal.innerHTML=`<div class="reader-top"><div class="reader-header"><div><h2></h2></div></div><div class="reader-toolbar"><form class="reader-jump"><label>Trang <input type="number" min="1" max="${book.page_count}" value="1" aria-label="Số trang"></label><span>/ ${book.page_count}</span><button>Đến</button></form><label class="reader-mode">Chế độ <select aria-label="Chế độ đọc"><option value="1">Một trang</option><option value="2">Hai trang</option></select></label><div class="reader-zoom"><button data-zoom-out aria-label="Thu nhỏ 25%">−</button><label><span class="sr-only">Tỷ lệ phóng to</span><select data-zoom aria-label="Tỷ lệ phóng to">${[25,50,75,100,125,150,175,200].map(value=>`<option value="${value}" ${value===100?'selected':''}>${value}%</option>`).join('')}</select></label><button data-zoom-in aria-label="Phóng to 25%">+</button></div><button data-full aria-label="Toàn màn hình" aria-pressed="false">⛶ Toàn màn hình</button><button data-close aria-label="Đóng sách" title="Đóng sách">✕</button></div></div><div class="reader-message" role="status" aria-live="polite"></div><div class="reader-body"><button class="reader-edge reader-edge-left" data-prev aria-label="Trang trước" title="Trang trước (←)">❮</button><div class="reader-viewport" tabindex="0" aria-label="Trang sách. Dùng phím mũi tên để lật trang."><div class="reader-stage"></div></div><button class="reader-edge reader-edge-right" data-next aria-label="Trang sau" title="Trang sau (→)">❯</button></div><div class="reader-footer"><span data-progress>Đang mở sách…</span><span>← → lật trang · Vuốt ngang để chuyển · Esc đóng</span></div>`;
 modal.querySelector('h2').textContent=book.title;
 document.body.append(modal);modal.showModal();
 const previousOverflow=document.body.style.overflow;document.body.style.overflow='hidden';
 const events=new AbortController(),stage=modal.querySelector('.reader-stage'),view=modal.querySelector('.reader-viewport'),message=modal.querySelector('.reader-message'),input=modal.querySelector('input'),mode=modal.querySelector('.reader-mode select');
 const prev=modal.querySelector('[data-prev]'),next=modal.querySelector('[data-next]');
 let page=1,spread=window.innerWidth>=900?2:1,busy=false,closed=false,zoom=100,ownsFullscreen=false,fullBusy=false,urls=[],pending=null,saveChain=Promise.resolve(),startX=null,startY=null,pageRatio=1,resizeObserver=null;
 mode.value=String(spread);
 const key=`ebook.${user?'user-'+user.id:'guest'}.${book.id}.${book.ebook_revision}`;
 const setMessage=text=>{message.textContent=text;};
 const save=()=>{
  const current=page;
  if(user){saveChain=saveChain.then(()=>api(`/books/${book.id}/progress`,'PUT',{page:current,revision:book.ebook_revision})).catch(()=>{if(!closed)setMessage('Đã mở trang. Chưa lưu được tiến độ lên tài khoản.');});}
  else{try{localStorage.setItem(key,String(current));}catch{setMessage('Trình duyệt không cho lưu trang đang đọc.');}}
 };
 const updateControls=()=>{prev.disabled=busy||page===1;next.disabled=busy||page+spread>book.page_count;input.value=page;mode.disabled=busy;modal.querySelector('.reader-jump button').disabled=busy;};
 async function fetchPage(number,signal){
  const response=await fetch(`${base}/books/${book.id}/pages/${number}?v=${encodeURIComponent(book.ebook_revision)}`,{signal});
  if(!response.ok)throw new Error(response.status===409?'Nội dung sách đã đổi. Đóng và mở lại sách để đọc bản mới.':'Không tải được trang sách. Hãy thử lại.');
  const url=URL.createObjectURL(await response.blob());
  const img=new Image();img.src=url;img.alt=`${book.title} — trang ${number}`;
  try{await img.decode();}catch(e){URL.revokeObjectURL(url);throw e;}
  return {img,url};
 }
 async function show(target,animate=true){
  if(busy||closed)return;
  target=Math.max(1,Math.min(book.page_count,Math.trunc(Number(target)||1)));
  busy=true;updateControls();setMessage('Đang tải trang…');
  pending=new AbortController();const timer=setTimeout(()=>pending?.abort(),35000);let loaded=[];
  try{
   // Sequential loading avoids extra rendering processes on small servers.
   for(let n=target;n<Math.min(target+spread,book.page_count+1);n++)loaded.push(await fetchPage(n,pending.signal));
   if(closed){loaded.forEach(x=>URL.revokeObjectURL(x.url));return;}
   const old=stage.querySelector('.reader-pages'),overlay=old?.cloneNode(true);
   const pages=document.createElement('div');pages.className='reader-pages';pages.style.setProperty('--spread',spread);
   loaded.forEach(({img},i)=>{const sheet=document.createElement('div');sheet.className='sheet';sheet.append(img);const label=document.createElement('span');label.className='folio';label.textContent=target+i;sheet.append(label);pages.append(sheet);});
   if(loaded.length<spread){const blank=document.createElement('div');blank.className='sheet blank';blank.textContent='Hết sách';pages.append(blank);}
   const ratios=loaded.map(({img})=>img.naturalWidth/img.naturalHeight||0.707);
   if(ratios.length<spread)ratios.push(ratios[0]);
   pageRatio=ratios.reduce((sum,r)=>sum+r,0);
   pages.style.gridTemplateColumns=ratios.map(r=>r+'fr').join(' ');
   stage.replaceChildren(pages);fitPages();
   if(animate&&overlay&&!window.matchMedia('(prefers-reduced-motion: reduce)').matches){
    overlay.setAttribute('aria-hidden','true');overlay.classList.add('turn-overlay',target>=page?'turn-next':'turn-prev');stage.append(overlay);
    await new Promise(resolve=>setTimeout(resolve,560));overlay.remove();
   }
   if(closed){loaded.forEach(x=>URL.revokeObjectURL(x.url));return;}
   urls.forEach(URL.revokeObjectURL);urls=loaded.map(x=>x.url);
   page=target;input.value=page;view.scrollTop=0;view.scrollLeft=Math.max(0,(view.scrollWidth-view.clientWidth)/2);
   modal.querySelector('[data-progress]').textContent=`Trang ${page}${spread===2&&page<book.page_count?'–'+(page+1):''} / ${book.page_count}`;
   setMessage('');save();
  }catch(error){loaded.forEach(x=>URL.revokeObjectURL(x.url));if(!closed)setMessage(error.name==='AbortError'?'Tải trang quá lâu. Bấm Đến để thử lại.':error.message);}
  finally{clearTimeout(timer);busy=false;if(!closed)updateControls();}
 }
 function close(){closed=true;resizeObserver?.disconnect();document.body.style.overflow=previousOverflow;if(ownsFullscreen&&document.fullscreenElement)document.exitFullscreen().catch(()=>{});pending?.abort();events.abort();urls.forEach(URL.revokeObjectURL);modal.close();modal.remove();}
 dispose=close;
 modal.querySelector('[data-close]').onclick=closeReader;
 modal.addEventListener('cancel',e=>{e.preventDefault();closeReader();},{signal:events.signal});
 prev.onclick=()=>show(page-spread);next.onclick=()=>show(page+spread);
 modal.querySelector('form').onsubmit=e=>{e.preventDefault();show(input.value);};
 mode.onchange=()=>{spread=Number(mode.value);show(page,false);};
 const zoomSelect=modal.querySelector('[data-zoom]'),zoomOut=modal.querySelector('[data-zoom-out]'),zoomIn=modal.querySelector('[data-zoom-in]'),full=modal.querySelector('[data-full]');
 function fitPages(){
  // Fit both axes, using decoded PDF page proportions rather than viewport width alone.
  const width=Math.max(1,view.clientWidth-8),height=Math.max(1,view.clientHeight-8);
  const fittedHeight=Math.min(height,width/pageRatio);
  const h=Math.floor(fittedHeight*zoom/100),w=Math.floor(h*pageRatio);
  stage.style.width=w+'px';stage.style.height=h+'px';
  stage.style.marginTop=Math.max(0,Math.floor((view.clientHeight-h)/2))+'px';
  view.style.overflow=zoom<=100?'hidden':'auto';
  if(zoom<=100){view.scrollTop=0;view.scrollLeft=0;}
 }
 if(typeof ResizeObserver!=='undefined'){resizeObserver=new ResizeObserver(()=>fitPages());resizeObserver.observe(view);}
 window.addEventListener('resize',fitPages,{signal:events.signal});
 function setZoom(value){
  const old=zoom;zoom=Math.max(25,Math.min(200,Math.round(Number(value)/25)*25));
  fitPages();zoomSelect.value=String(zoom);zoomOut.disabled=zoom===25;zoomIn.disabled=zoom===200;
  view.scrollLeft=Math.max(0,(view.scrollLeft+view.clientWidth/2)*zoom/old-view.clientWidth/2);
  view.scrollTop=Math.max(0,(view.scrollTop+view.clientHeight/2)*zoom/old-view.clientHeight/2);
 }
 zoomSelect.onchange=()=>setZoom(zoomSelect.value);
 zoomOut.onclick=()=>setZoom(zoom-25);zoomIn.onclick=()=>setZoom(zoom+25);setZoom(100);
 function syncFullscreen(){
  const active=!!document.fullscreenElement;
  modal.classList.toggle('reader-fullscreen',active);
  full.textContent=active?'⛶ Thoát toàn màn hình':'⛶ Toàn màn hình';
  full.setAttribute('aria-label',active?'Thoát toàn màn hình':'Toàn màn hình');full.setAttribute('aria-pressed',String(active));
  if(!active)ownsFullscreen=false;
 }
 document.addEventListener('fullscreenchange',syncFullscreen,{signal:events.signal});syncFullscreen();
 full.onclick=async()=>{
  if(fullBusy)return;fullBusy=true;full.disabled=true;
  try{
   if(document.fullscreenElement)await document.exitFullscreen();
   else if(document.documentElement.requestFullscreen&&document.fullscreenEnabled!==false){
    // A dialog itself is not a valid Fullscreen API target; fullscreen its document.
    await document.documentElement.requestFullscreen();ownsFullscreen=true;
    if(closed){await document.exitFullscreen();return;}
   }else{setMessage('Trình duyệt không hỗ trợ toàn màn hình ở đây. Trên máy tính, bạn có thể dùng F11.');}
   if(!closed)syncFullscreen();
  }catch{if(!closed)setMessage('Không thể bật toàn màn hình. Hãy thử mở trang trực tiếp hoặc dùng F11 trên máy tính.');}
  finally{fullBusy=false;if(!closed)full.disabled=false;}
 };
 modal.addEventListener('keydown',e=>{if(['INPUT','SELECT','TEXTAREA'].includes(e.target.tagName))return;if(e.key==='ArrowRight'){e.preventDefault();show(page+spread);}if(e.key==='ArrowLeft'){e.preventDefault();show(page-spread);}},{signal:events.signal});
 view.addEventListener('touchstart',e=>{startX=e.touches.length===1?e.touches[0].clientX:null;startY=e.touches.length===1?e.touches[0].clientY:null;},{passive:true,signal:events.signal});
 view.addEventListener('touchend',e=>{if(startX===null||zoom>100)return;const delta=e.changedTouches[0].clientX-startX,vertical=e.changedTouches[0].clientY-startY;startX=null;if(Math.abs(delta)>65&&Math.abs(delta)>Math.abs(vertical)*1.5)show(page+(delta<0?spread:-spread));},{passive:true,signal:events.signal});
 try{
  if(user){const saved=await api(`/books/${book.id}/progress`);if(saved.revision===book.ebook_revision)page=saved.page;}
  else{try{page=Number(localStorage.getItem(key))||1;}catch{}}
 }catch{notify('Chưa lấy được tiến độ cũ; mở sách từ trang đầu.');}
 if(!closed)await show(page,false);
}
