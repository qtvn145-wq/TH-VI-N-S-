import io
import os
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from fastapi.testclient import TestClient
from PIL import Image
from app.main import app,today
from app.db import connect
from app.cli import reminders

class LibraryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        os.environ['DATABASE_PATH']=self.tmp.name+'/test.db'
        self.c=TestClient(app)
        self.c.__enter__()
        self.reader=self.account('reader')
        self.other=self.account('other')
        self.staff=self.account('staff')
        with connect(True) as db: db.execute("UPDATE users SET role='librarian' WHERE email='staff@example.com'")
    def tearDown(self):
        self.c.__exit__(None,None,None)
        self.tmp.cleanup()
    def account(self,name):
        p={'email':name+'@example.com','name':name,'password':'safe-password-123'}
        self.assertEqual(self.c.post('/api/v1/auth/register',json=p).status_code,201)
        del p['name']
        r=self.c.post('/api/v1/auth/login',json=p)
        return {'Authorization':'Bearer '+r.json()['access_token']}
    def book(self,n=1):
        r=self.c.post('/api/v1/books',json={'title':'Cơ sở Dữ liệu'},headers=self.staff)
        self.assertEqual(r.status_code,201,r.text)
        id=r.json()['id']
        for i in range(n):
            self.assertEqual(self.c.post(f'/api/v1/books/{id}/copies',json={'barcode':f'{id}-{i}'},headers=self.staff).status_code,201)
        return id
    def reserve(self,id,who=None):
        return self.c.post('/api/v1/loans',json={'book_id':id},headers=who or self.reader)
    def test_limit_and_cancel_release(self):
        b=self.book(4)
        ids=[self.reserve(b).json()['id'] for _ in range(3)]
        self.assertEqual(self.reserve(b).json()['detail'],'LOAN_LIMIT_REACHED')
        self.assertEqual(self.c.get(f'/api/v1/books/{b}').json()['available_copies'],1)
        self.c.post(f'/api/v1/loans/{ids[0]}/cancel',headers=self.reader)
        self.assertEqual(self.reserve(b).status_code,201)
    def test_concurrent_last_copy(self):
        b=self.book()
        with ThreadPoolExecutor(2) as pool:
            results=list(pool.map(lambda h:self.reserve(b,h).status_code,[self.reader,self.other]))
        self.assertEqual(sorted(results),[201,409])
    def test_concurrent_user_limit(self):
        b=self.book(8)
        with ThreadPoolExecutor(6) as pool:
            results=list(pool.map(lambda _:self.reserve(b).status_code,range(6)))
        self.assertEqual(results.count(201),3)
        self.assertEqual(results.count(409),3)
    def test_return_fine_and_duplicate(self):
        id=self.reserve(self.book()).json()['id']
        self.assertEqual(self.c.post(f'/api/v1/loans/{id}/return',headers=self.staff).status_code,409)
        self.c.post(f'/api/v1/loans/{id}/handover',headers=self.staff)
        with connect(True) as db: db.execute('UPDATE loans SET due_date=? WHERE id=?',((today()-timedelta(days=2)).isoformat(),id))
        r=self.c.post(f'/api/v1/loans/{id}/return',headers=self.staff)
        self.assertEqual(r.json()['estimated_fine'],4000)
        self.assertEqual(self.c.post(f'/api/v1/loans/{id}/return',headers=self.staff).status_code,409)
        fine=self.c.get('/api/v1/fines',headers=self.reader).json()[0]
        self.assertEqual(fine['amount'],4000)
        self.assertEqual(self.c.post(f"/api/v1/fines/{fine['id']}/pay",headers=self.reader).status_code,403)
        self.assertEqual(self.c.post(f"/api/v1/fines/{fine['id']}/pay",headers=self.staff).status_code,200)
    def test_due_today_no_fine(self):
        id=self.reserve(self.book()).json()['id']
        self.c.post(f'/api/v1/loans/{id}/handover',headers=self.staff)
        with connect(True) as db: db.execute('UPDATE loans SET due_date=? WHERE id=?',(today().isoformat(),id))
        self.assertEqual(self.c.post(f'/api/v1/loans/{id}/return',headers=self.staff).json()['estimated_fine'],0)
        self.assertEqual(self.c.get('/api/v1/fines',headers=self.reader).json(),[])
    def test_access_and_history(self):
        id=self.reserve(self.book()).json()['id']
        self.assertEqual(self.c.get('/api/v1/loans',headers=self.other).json(),[])
        self.assertEqual(self.c.post(f'/api/v1/loans/{id}/cancel',headers=self.other).status_code,403)
        self.assertEqual(self.c.post(f'/api/v1/loans/{id}/handover',headers=self.reader).status_code,403)
        self.assertEqual(self.c.post('/api/v1/books',json={'title':'Bad'},headers=self.reader).status_code,403)
        self.assertEqual(self.c.get('/api/v1/stats',headers=self.reader).status_code,403)
    def test_queue_priority(self):
        b=self.book()
        loan=self.reserve(b).json()['id']
        q=self.c.post('/api/v1/waitlist',json={'book_id':b},headers=self.other)
        self.assertEqual(q.status_code,201)
        self.assertEqual(self.c.post('/api/v1/waitlist',json={'book_id':b},headers=self.other).status_code,409)
        self.c.post(f'/api/v1/loans/{loan}/cancel',headers=self.reader)
        self.assertEqual(self.reserve(b).json()['detail'],'QUEUE_PRIORITY')
        self.assertEqual(self.reserve(b,self.other).status_code,201)
        self.assertEqual(self.c.get('/api/v1/waitlist',headers=self.other).json(),[])
    def test_search_and_relations_rollback(self):
        a=self.c.post('/api/v1/catalog/authors',json={'name':'Nguyễn An'},headers=self.staff).json()['id']
        k=self.c.post('/api/v1/catalog/categories',json={'name':'CNTT'},headers=self.staff).json()['id']
        b=self.c.post('/api/v1/books',json={'title':'Cơ Sở Dữ Liệu','author_ids':[a],'category_ids':[k]},headers=self.staff).json()['id']
        results=self.c.get('/api/v1/books',params={'q':'cơ sở','author':'NGUYỄN','category_id':k}).json()
        self.assertEqual([r['id'] for r in results],[b])
        self.assertEqual(self.c.post('/api/v1/books',json={'title':'rollback','author_ids':[999]},headers=self.staff).status_code,404)
        self.assertEqual(self.c.get('/api/v1/books',params={'q':'rollback'}).json(),[])
    def test_auth_validation_logout(self):
        self.assertEqual(self.c.post('/api/v1/auth/register',json={'email':'h@a.com','name':'h','password':'password-123','role':'librarian'}).status_code,422)
        self.assertEqual(self.c.post('/api/v1/auth/login',json={'email':'reader@example.com','password':'bad-password'}).status_code,401)
        self.assertNotIn('password_hash',self.c.get('/api/v1/auth/me',headers=self.reader).json())
        self.c.post('/api/v1/auth/logout',headers=self.reader)
        self.assertEqual(self.c.get('/api/v1/auth/me',headers=self.reader).status_code,401)
    def test_cover_validation(self):
        b=self.book()
        self.assertEqual(self.c.post(f'/api/v1/books/{b}/cover',files={'file':('a.jpg',b'bad','image/jpeg')},headers=self.staff).status_code,415)
        out=io.BytesIO(); Image.new('RGB',(10,10)).save(out,'PNG')
        r=self.c.post(f'/api/v1/books/{b}/cover',files={'file':('a.png',out.getvalue(),'image/png')},headers=self.staff)
        self.assertEqual(r.status_code,200)
        self.assertEqual(self.c.get(r.json()['cover_url']).status_code,200)
    def test_retire_barcode_and_preserve_history(self):
        b=self.book(); id=self.reserve(b).json()['copy_id']
        self.assertEqual(self.c.put(f'/api/v1/copies/{id}',json={'barcode':'new','retired':True},headers=self.staff).status_code,409)
        self.assertEqual(self.c.post(f'/api/v1/books/{b}/copies',json={'barcode':f'{b}-0'},headers=self.staff).status_code,409)
        self.assertEqual(self.c.delete(f'/api/v1/books/{b}',headers=self.staff).status_code,409)
    def test_reminders_dry_run(self):
        id=self.reserve(self.book()).json()['id']
        self.c.post(f'/api/v1/loans/{id}/handover',headers=self.staff)
        with connect(True) as db: db.execute('UPDATE loans SET due_date=? WHERE id=?',(today().isoformat(),id))
        self.assertEqual(reminders(),{'eligible':1,'sent':0,'dry_run':True})
        with connect() as db: self.assertEqual(db.execute('SELECT count(*) FROM reminders').fetchone()[0],0)

if __name__=='__main__': unittest.main()
