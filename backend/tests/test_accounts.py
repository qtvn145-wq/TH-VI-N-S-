import unittest
import test_ebooks
from backend.app.db import connect

class AccountTests(unittest.TestCase):
 setUp = test_ebooks.EbookTests.setUp
 tearDown = test_ebooks.EbookTests.tearDown
 account = test_ebooks.EbookTests.account
 base = '/api/v1/admin/users'
 def create(self, **changes):
  return self.client.post(self.base,headers=self.staff,json={'email':'new@test.local','name':'New','password':'New-password-123','role':'reader',**changes})
 def target(self, email='reader@test.local'):
  with connect() as db: return dict(db.execute('SELECT * FROM users WHERE email=?',(email,)).fetchone())
 def update(self,target,**changes):
  return self.client.put(self.base+'/'+str(target['id']),headers=self.staff,json={k:changes.get(k,target[k]) for k in ('email','name','role')})
 def test_permissions_and_no_password_disclosure(self):
  for headers in ({},self.reader):
   self.assertIn(self.client.get(self.base,headers=headers).status_code,(401,403))
   self.assertIn(self.client.post(self.base,headers=headers,json={'email':'a@b.co','name':'x','password':'Password-123'}).status_code,(401,403))
   for method,path,body in [('PUT','/1',{'name':'x','email':'a@b.co','role':'librarian'}),('PUT','/1/password',{'password':'Password-123'}),('DELETE','/1',None)]:
    self.assertIn(self.client.request(method,self.base+path,headers=headers,json=body).status_code,(401,403))
  result=self.client.get(self.base,headers=self.staff)
  self.assertEqual(result.status_code,200)
  for row in result.json():self.assertEqual(set(row),{'id','email','name','role'})
 def test_create_search_validation_and_unique_email(self):
  result=self.create(email='NEW@test.local');self.assertEqual(result.status_code,201)
  self.assertEqual(result.json()['email'],'new@test.local');self.assertNotIn('password_hash',result.json())
  self.assertEqual(self.create().json()['detail'],'EMAIL_EXISTS')
  self.assertEqual(self.create(email='a@test.local',password='short').status_code,422)
  self.assertEqual(self.create(email='a@test.local',role='admin').status_code,422)
  rows=self.client.get(self.base+'?q=new%40&limit=1',headers=self.staff).json()
  self.assertEqual([r['id'] for r in rows],[result.json()['id']])
  self.assertEqual(self.client.get(self.base+'?q=new%40&offset=1',headers=self.staff).json(),[])
 def test_update_revoke_sessions_and_conflict_rollback(self):
  target=self.target()
  self.assertEqual(self.update(target,email='other@test.local',name='Changed').status_code,409)
  self.assertEqual(self.target()['name'],'reader')
  result=self.update(target,email='renamed@test.local',role='librarian')
  self.assertEqual(result.status_code,200)
  self.assertEqual(self.client.get('/api/v1/auth/me',headers=self.reader).status_code,401)
  token=self.client.post('/api/v1/auth/login',json={'email':'renamed@test.local','password':'Testing-12345'}).json()['access_token']
  self.assertEqual(self.client.get(self.base,headers={'Authorization':'Bearer '+token}).status_code,200)
 def test_last_admin_and_self_delete(self):
  admin=self.target('staff@test.local')
  self.assertEqual(self.update(admin,role='reader').json()['detail'],'LAST_ADMIN')
  self.assertEqual(self.client.delete(self.base+'/'+str(admin['id']),headers=self.staff).json()['detail'],'LAST_ADMIN')
  self.assertEqual(self.create(role='librarian').status_code,201)
  self.assertEqual(self.client.delete(self.base+'/'+str(admin['id']),headers=self.staff).json()['detail'],'CANNOT_DELETE_SELF')
  self.assertEqual(self.update(admin,role='reader').status_code,200)
  self.assertEqual(self.client.get(self.base,headers=self.staff).status_code,401)
 def test_password_reset_invalidates_old_login_and_sessions(self):
  target=self.target();url=self.base+'/'+str(target['id'])+'/password'
  self.assertEqual(self.client.put(url,headers=self.staff,json={'password':'short'}).status_code,422)
  self.assertEqual(self.client.put(url,headers=self.staff,json={'password':'Replacement-123'}).status_code,200)
  self.assertEqual(self.client.get('/api/v1/auth/me',headers=self.reader).status_code,401)
  self.assertEqual(self.client.post('/api/v1/auth/login',json={'email':target['email'],'password':'Testing-12345'}).status_code,401)
  self.assertEqual(self.client.post('/api/v1/auth/login',json={'email':target['email'],'password':'Replacement-123'}).status_code,200)
 def test_delete_cleans_private_data_and_revokes_login(self):
  target=self.target();uid=target['id']
  with connect(True) as db:
   db.execute('INSERT INTO favorites(user_id,book_id,created_at) VALUES (?,?,?)',(uid,self.book,'now'))
   db.execute('INSERT INTO reading_progress VALUES (?,?,?,?)',(uid,self.book,'r'*32,1))
  self.assertEqual(self.client.delete(self.base+'/'+str(uid),headers=self.staff).status_code,200)
  self.assertEqual(self.client.get('/api/v1/auth/me',headers=self.reader).status_code,401)
  with connect() as db:
   for table in ('sessions','favorites','reading_progress'):
    self.assertEqual(db.execute(f'SELECT count(*) FROM {table} WHERE user_id=?',(uid,)).fetchone()[0],0)
  self.assertEqual(self.client.delete(self.base+'/'+str(uid),headers=self.staff).status_code,404)
 def test_legacy_history_delete_rolls_back(self):
  uid=self.target()['id']
  with connect(True) as db:
   db.execute('CREATE TABLE legacy_history(user_id INTEGER REFERENCES users(id))')
   db.execute('INSERT INTO legacy_history VALUES (?)',(uid,))
  response=self.client.delete(self.base+'/'+str(uid),headers=self.staff)
  self.assertEqual(response.json()['detail'],'ACCOUNT_HAS_HISTORY')
  self.assertEqual(self.client.get('/api/v1/auth/me',headers=self.reader).status_code,200)
