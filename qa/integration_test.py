import os, tempfile, unittest, json, io
from pathlib import Path
scratch=tempfile.TemporaryDirectory()
os.environ['DATABASE_PATH']=scratch.name+'/test.sqlite3'
os.environ['MEDIA_DIR']=scratch.name+'/covers'
from fastapi.testclient import TestClient
from serve import app
from app.db import connect
from app.security import password_hash
from PIL import Image
class FrontendIntegration(unittest.TestCase):
 def test_full_flow(self):
  with TestClient(app) as c:
   self.assertEqual(c.get('/').status_code,200)
   for file in ['app.js','api.js','config.js','style.css']: self.assertEqual(c.get('/ui/'+file).status_code,200)
   with connect(True) as db: db.execute('INSERT INTO users(email,name,password_hash,role) VALUES (?,?,?,?)',('staff@test.local','Thủ thư',password_hash('Testing2026!'),'librarian'))
   def login(email): return {'Authorization':'Bearer '+c.post('/api/v1/auth/login',json={'email':email,'password':'Testing2026!'}).json()['access_token']}
   c.post('/api/v1/auth/register',json={'email':'reader@test.local','name':'Bạn đọc','password':'Testing2026!'})
   s=login('staff@test.local');r=login('reader@test.local')
   b=c.post('/api/v1/books',headers=s,json={'title':'Sách kiểm tra'}).json()
   c.post(f"/api/v1/books/{b['id']}/copies",headers=s,json={'barcode':'BAR-001'})
   loan=c.post('/api/v1/loans',headers=r,json={'book_id':b['id']}).json()
   self.assertEqual(loan['book_title'],'Sách kiểm tra');self.assertEqual(loan['barcode'],'BAR-001');self.assertEqual(loan['reader_name'],'Bạn đọc')
   self.assertEqual(c.post(f"/api/v1/loans/{loan['id']}/handover",headers=s).json()['status'],'borrowed')
   self.assertEqual(c.post(f"/api/v1/loans/{loan['id']}/return",headers=s).json()['status'],'returned')
   out=io.BytesIO();Image.new('RGB',(10,10)).save(out,'PNG')
   result=c.post(f"/api/v1/books/{b['id']}/cover",headers=s,files={'file':('cover.png',out.getvalue(),'image/png')})
   self.assertEqual(result.status_code,200);self.assertEqual(c.get(result.json()['cover_url']).status_code,200)
   self.assertEqual(c.post('/api/v1/books',headers=r,json={'title':'Forbidden'}).status_code,403)
   schema=json.loads(Path('docs/openapi.json').read_text());self.assertEqual(schema,app.openapi())
if __name__=='__main__': unittest.main()
