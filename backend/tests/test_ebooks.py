import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import pypdfium2 as pdfium
from fastapi.testclient import TestClient
from PIL import Image
from backend.app.main import app
from backend.app.db import connect,migrate

class EbookTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory()
  self.env=patch.dict(os.environ,{'DATABASE_PATH':self.temp.name+'/db.sqlite','EBOOK_DIR':self.temp.name+'/ebooks','AUTO_MIGRATE':'true'})
  self.env.start();self.client=TestClient(app);self.client.__enter__()
  self.reader=self.account('reader');self.other=self.account('other');self.staff=self.account('staff')
  with connect(True) as db: db.execute("UPDATE users SET role='librarian' WHERE email='staff@test.local'")
  self.book=self.client.post('/api/v1/books',headers=self.staff,json={'title':'Đường đến tri thức'}).json()['id']
 def tearDown(self):
  self.client.__exit__(None,None,None);self.env.stop();self.temp.cleanup()
 def account(self,name):
  body={'email':name+'@test.local','name':name,'password':'Testing-12345'}
  self.assertEqual(self.client.post('/api/v1/auth/register',json=body).status_code,201)
  body.pop('name');token=self.client.post('/api/v1/auth/login',json=body).json()['access_token']
  return {'Authorization':'Bearer '+token}
 def pdf(self,pages=3):
  with pdfium.PdfDocument.new() as doc:
   for _ in range(pages): doc.new_page(200,300).close()
   out=io.BytesIO();doc.save(out);return out.getvalue()
 def upload(self,raw=None,headers=None):
  return self.client.post(f'/api/v1/books/{self.book}/ebook',headers=headers or self.staff,files={'file':('book.pdf',self.pdf() if raw is None else raw,'application/pdf')})
 def test_upload_metadata_and_page_images(self):
  result=self.upload();self.assertEqual(result.status_code,200,result.text);meta=result.json()
  self.assertEqual(meta['page_count'],3)
  r=self.client.get(f'/api/v1/books/{self.book}/pages/2',params={'v':meta['revision']})
  self.assertEqual(r.status_code,200);self.assertEqual(r.headers['content-type'],'image/jpeg')
  image=Image.open(io.BytesIO(r.content));self.assertLessEqual(image.width,1600);self.assertLessEqual(image.height,2000)
  self.assertEqual(self.client.get(f'/api/v1/books/{self.book}/pages/2',params={'v':meta['revision']}).content,r.content)
  self.assertEqual(self.client.get(f'/api/v1/books/{self.book}').json()['page_count'],3)
 def test_upload_validation_and_permissions(self):
  self.assertEqual(self.upload(headers=self.reader).status_code,403)
  self.assertEqual(self.upload(b'not pdf').status_code,415)
  self.assertEqual(self.upload(b'%PDF-broken').status_code,422)
  self.assertEqual(self.upload(self.pdf(501)).status_code,422)
  self.assertEqual(self.upload(b'%PDF-'+b'x'*(25*1024*1024)).status_code,413)
  self.assertEqual(list(Path(self.temp.name+'/ebooks').glob('*.pdf')),[])
 def test_page_boundaries_missing_and_stale_revision(self):
  self.assertEqual(self.client.get(f'/api/v1/books/{self.book}/ebook').status_code,404)
  meta=self.upload().json()
  for page in [0,-1,4]:self.assertEqual(self.client.get(f'/api/v1/books/{self.book}/pages/{page}',params={'v':meta['revision']}).status_code,404)
  self.assertEqual(self.client.get(f'/api/v1/books/{self.book}/pages/1',params={'v':'0'*32}).status_code,409)
 def test_progress_is_private_bounded_and_reset_on_replace(self):
  meta=self.upload().json();url=f'/api/v1/books/{self.book}/progress';body={'page':3,'revision':meta['revision']}
  self.assertEqual(self.client.put(url,json=body).status_code,401)
  self.assertEqual(self.client.put(url,json=body,headers=self.reader).status_code,200)
  self.assertEqual(self.client.get(url,headers=self.reader).json()['page'],3)
  self.assertEqual(self.client.get(url,headers=self.other).json()['page'],1)
  self.assertEqual(self.client.put(url,json={**body,'page':4},headers=self.reader).status_code,422)
  self.assertEqual(self.client.put(url,json={**body,'page':0},headers=self.reader).status_code,422)
  replacement=self.upload().json();self.assertNotEqual(replacement['revision'],meta['revision'])
  self.assertEqual(self.client.get(url,headers=self.reader).json()['page'],1)
  self.assertEqual(self.client.put(url,json=body,headers=self.reader).status_code,409)
 def test_removed_lending_endpoints_and_fresh_schema(self):
  paths=app.openapi()['paths']
  for term in ['loans','fines','waitlist','copies','reminders']:
   self.assertFalse(any(term in path for path in paths))
  with connect() as db:
   tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
   self.assertFalse({'loans','fines','waitlist','copies','reminders'} & tables)
 def test_search_filters_and_favorites(self):
  self.assertEqual(len(self.client.get('/api/v1/books?q=DUONG').json()),1)
  self.assertEqual(self.client.get('/api/v1/books?readable_only=true').json(),[])
  self.upload();self.assertEqual(len(self.client.get('/api/v1/books?readable_only=true').json()),1)
  url=f'/api/v1/favorites/{self.book}'
  for _ in range(2):self.assertEqual(self.client.put(url,headers=self.reader).status_code,200)
  self.assertEqual(len(self.client.get('/api/v1/favorites',headers=self.reader).json()),1)
  self.assertEqual(self.client.get('/api/v1/favorites',headers=self.other).json(),[])
 def test_archive_hides_book_and_pages(self):
  meta=self.upload().json();self.client.put(f'/api/v1/favorites/{self.book}',headers=self.reader)
  self.assertEqual(self.client.delete(f'/api/v1/books/{self.book}',headers=self.reader).status_code,403)
  self.assertEqual(self.client.delete(f'/api/v1/books/{self.book}',headers=self.staff).status_code,200)
  self.assertEqual(self.client.get('/api/v1/books').json(),[])
  self.assertEqual(self.client.get('/api/v1/favorites',headers=self.reader).json(),[])
  self.assertEqual(self.client.get(f'/api/v1/books/{self.book}').status_code,404)
  self.assertEqual(self.client.get(f'/api/v1/books/{self.book}/pages/1',params={'v':meta['revision']}).status_code,404)
 def test_catalog_permissions_and_auth(self):
  self.assertEqual(self.client.post('/api/v1/books',headers=self.reader,json={'title':'No'}).status_code,403)
  self.assertEqual(self.client.post('/api/v1/auth/register',json={'email':'x@test.local','password':'Testing-12345','name':'x','role':'librarian'}).status_code,422)
  self.client.post('/api/v1/auth/logout',headers=self.reader)
  self.assertEqual(self.client.get('/api/v1/auth/me',headers=self.reader).status_code,401)
 def test_migrate_legacy_preserves_books_and_history(self):
  with patch.dict(os.environ,{'DATABASE_PATH':self.temp.name+'/old.sqlite'}):
   with connect() as db:
    db.executescript(Path('backend/migrations/001_initial.sql').read_text())
    db.execute("INSERT INTO books(title) VALUES ('Legacy')")
   migrate();migrate()
   with connect() as db:
    self.assertEqual(db.execute('SELECT title FROM books').fetchone()[0],'Legacy')
    self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],4)
    self.assertEqual(db.execute('SELECT count(*) FROM loans').fetchone()[0],0)
