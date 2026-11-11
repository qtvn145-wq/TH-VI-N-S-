import assert from 'node:assert/strict';
const values=new Map();globalThis.sessionStorage={getItem:k=>values.get(k),setItem:(k,v)=>values.set(k,v),removeItem:k=>values.delete(k)};
globalThis.window={LIBRARY_API_BASE:'/api/v1',dispatchEvent:()=>{}};globalThis.location={href:'http://localhost:8081/'};
const {api,setToken,coverUrl}=await import('../frontend/api.js');
let seen;setToken('test-session');
globalThis.fetch=async(url,init)=>{seen={url,init};return {ok:true,json:async()=>({id:1})};};
assert.deepEqual(await api('/loans','POST',{book_id:2}),{id:1});assert.equal(seen.url,'/api/v1/loans');assert.equal(seen.init.headers.Authorization,'Bearer test-session');assert.equal(seen.init.body,'{"book_id":2}');
const form=new FormData();form.append('file',new Blob(['abc']),'cover.png');await api('/books/1/cover','POST',form);assert.equal(seen.init.body,form);assert.equal(seen.init.headers['Content-Type'],undefined);
for(const [code,text] of [['NO_COPY_AVAILABLE','hết bản'],['LOAN_LIMIT_REACHED','giới hạn 3 cuốn'],['QUEUE_PRIORITY','ưu tiên'],['INVALID_LOAN_STATE','Trạng thái']]){globalThis.fetch=async()=>({ok:false,status:409,json:async()=>({detail:code})});await assert.rejects(()=>api('/loans','POST',{book_id:2}),e=>e.message.includes(text));}
globalThis.fetch=async()=>({ok:false,status:401,json:async()=>({detail:'INVALID_SESSION'})});await assert.rejects(()=>api('/auth/me'));assert.equal(values.has('library.session'),false);
globalThis.fetch=async()=>{throw new TypeError('network');};await assert.rejects(()=>api('/loans','POST',{book_id:2}),e=>e.message.includes('kiểm tra trước'));
assert.equal(coverUrl('/media/a.jpg'),'http://localhost:8081/media/a.jpg');assert.equal(coverUrl('javascript:alert(1)'),'');
console.log('PASS: API URL, Bearer session, JSON body, multipart, 4 business errors, expired session, uncertain mutation, image URL');
