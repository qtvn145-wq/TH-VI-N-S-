import unittest
from unittest.mock import patch
import test_ebooks
from backend.app.db import connect,migrate
from backend.app.security import digest

class PasswordResetTests(unittest.TestCase):
 setUp=test_ebooks.EbookTests.setUp
 tearDown=test_ebooks.EbookTests.tearDown
 account=test_ebooks.EbookTests.account
 def request_link(self,email='reader@test.local'):
  with patch('backend.app.password_reset.mail_config',return_value=('http://localhost:8081','smtp',587,'sender@test.local','starttls')),patch('backend.app.password_reset.deliver_reset') as send:
   response=self.client.post('/api/v1/auth/forgot-password',json={'email':email})
   return response,send.call_args.args[1] if send.called else None
 def reset(self,token,password='Replacement-123'):
  return self.client.post('/api/v1/auth/reset-password',json={'token':token,'password':password})
 def test_generic_response_cooldown_and_no_token_leak(self):
  response,token=self.request_link();unknown,_=self.request_link('unknown@test.local')
  self.assertEqual(response.status_code,202);self.assertEqual(response.json(),unknown.json())
  self.assertNotIn(token,response.text)
  with connect() as db:self.assertEqual(db.execute('SELECT token_hash FROM password_resets').fetchone()[0],digest(token))
  self.assertIsNone(self.request_link()[1])
 def test_reset_single_use_and_logout(self):
  _,token=self.request_link()
  self.assertEqual(self.reset(token).status_code,200)
  self.assertEqual(self.reset(token).status_code,400)
  self.assertEqual(self.client.get('/api/v1/auth/me',headers=self.reader).status_code,401)
  for password,status in [('Testing-12345',401),('Replacement-123',200)]:
   self.assertEqual(self.client.post('/api/v1/auth/login',json={'email':'reader@test.local','password':password}).status_code,status)
 def test_expiry_tamper_and_validation(self):
  _,token=self.request_link()
  self.assertEqual(self.reset('x'*43).status_code,400)
  self.assertEqual(self.reset(token,'short').status_code,422)
  with connect(True) as db:db.execute("UPDATE password_resets SET expires_at='2000-01-01'")
  self.assertEqual(self.reset(token).status_code,400)
 def test_admin_change_invalidates_reset_and_delete_cascades(self):
  _,token=self.request_link()
  with connect() as db:uid=db.execute("SELECT id FROM users WHERE email='reader@test.local'").fetchone()[0]
  self.client.put(f'/api/v1/admin/users/{uid}/password',headers=self.staff,json={'password':'Admin-password-123'})
  self.assertEqual(self.reset(token).status_code,400)
  self.assertEqual(self.client.delete(f'/api/v1/admin/users/{uid}',headers=self.staff).status_code,200)
  with connect() as db:self.assertEqual(db.execute('SELECT count(*) FROM password_resets').fetchone()[0],0)
 def test_unconfigured_and_migration_idempotency(self):
  with patch.dict('os.environ',{'SMTP_HOST':'','SMTP_FROM':''}):
   self.assertEqual(self.client.post('/api/v1/auth/forgot-password',json={'email':'reader@test.local'}).status_code,503)
  migrate();migrate()
  with connect() as db:self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],4)
 def test_failed_email_removes_token(self):
  from backend.app.password_reset import deliver_reset
  _,token=self.request_link()
  with patch('smtplib.SMTP',side_effect=OSError('failed')),self.assertLogs('backend.app.password_reset',level='ERROR'):
   deliver_reset('reader@test.local',token,('http://localhost:8081','smtp',587,'sender@test.local','starttls'))
  self.assertEqual(self.reset(token).status_code,400)
