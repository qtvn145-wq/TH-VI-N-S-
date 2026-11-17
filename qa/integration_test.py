import io,json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import pypdfium2 as pdfium
from fastapi.testclient import TestClient
from serve import app
from backend.app.db import connect
from backend.app.security import password_hash

class Integration(unittest.TestCase):
 def test_upload_read_and_progress_with_frontend_assets(self):
  with tempfile.TemporaryDirectory() as temp,patch.dict(os.environ,{'DATABASE_PATH':temp+'/db','EBOOK_DIR':temp+'/ebooks','AUTO_MIGRATE':'true'}),TestClient(app) as c:
   index=c.get('/');self.assertEqual(index.status_code,200)
   for asset in ['src/app.js','src/api.js','src/reader.js','config.js','styles/style.css']:
    self.assertEqual(c.get('/ui/'+asset).status_code,200)
   for asset in ['/ui/src/app.js','/ui/styles/style.css']:
    self.assertIn(asset,index.text)
   with connect(True) as db: db.execute("INSERT INTO users(email,name,password_hash,role) VALUES (?,?,?,'librarian')",('staff@test.local','Staff',password_hash('Testing2026!')))
   headers={'Authorization':'Bearer '+c.post('/api/v1/auth/login',json={'email':'staff@test.local','password':'Testing2026!'}).json()['access_token']}
   b=c.post('/api/v1/books',headers=headers,json={'title':'Integration eBook'}).json()['id']
   with pdfium.PdfDocument.new() as pdf:
    pdf.new_page(200,300).close();pdf.new_page(200,300).close();out=io.BytesIO();pdf.save(out)
   meta=c.post(f'/api/v1/books/{b}/ebook',headers=headers,files={'file':('sample.pdf',out.getvalue(),'application/pdf')}).json()
   self.assertEqual(c.get(f'/api/v1/books/{b}/pages/2',params={'v':meta['revision']}).status_code,200)
   self.assertEqual(c.put(f'/api/v1/books/{b}/progress',headers=headers,json={'page':2,'revision':meta['revision']}).status_code,200)
   self.assertEqual(c.get(f'/api/v1/books/{b}/progress',headers=headers).json()['page'],2)
   self.assertEqual(json.loads(Path('docs/openapi.json').read_text()),app.openapi())
if __name__=='__main__':unittest.main()
