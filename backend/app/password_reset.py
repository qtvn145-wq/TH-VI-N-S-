import logging
import os
import secrets
import smtplib
import ssl
import time
from datetime import timedelta
from email.message import EmailMessage
from urllib.parse import urlsplit
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import Field, field_validator
from .schemas import Input, OkOut
from .db import connect
from .security import digest, now, password_hash

router=APIRouter(prefix='/api/v1/auth',tags=['Auth'])

class ForgotPassword(Input):
    email: str = Field(min_length=3,max_length=254,pattern=r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
    @field_validator('email')
    @classmethod
    def normalize(cls,value): return value.lower()

class ResetPassword(Input):
    token: str = Field(min_length=43,max_length=43,pattern=r'^[A-Za-z0-9_-]+$')
    password: str = Field(min_length=10,max_length=128)

def mail_config():
    origin=os.getenv('PUBLIC_ORIGIN','http://localhost:8081').rstrip('/')
    parsed=urlsplit(origin)
    host=os.getenv('SMTP_HOST','');sender=os.getenv('SMTP_FROM','')
    mode=os.getenv('SMTP_SECURITY','starttls')
    try: port=int(os.getenv('SMTP_PORT','587'))
    except ValueError: raise HTTPException(503,'RESET_EMAIL_UNAVAILABLE') from None
    if not host or not sender or mode not in ('starttls','ssl') or not 1<=port<=65535 or not parsed.netloc or parsed.username or parsed.path or parsed.query or parsed.fragment or (parsed.scheme!='https' and not (parsed.scheme=='http' and parsed.hostname in ('localhost','127.0.0.1'))):
        raise HTTPException(503,'RESET_EMAIL_UNAVAILABLE')
    return origin,host,port,sender,mode

def deliver_reset(recipient, token, config):
    origin,host,port,sender,mode=config
    msg=EmailMessage();msg['Subject']='Đặt lại mật khẩu — Thư viện số';msg['From']=sender;msg['To']=recipient
    msg.set_content('Bạn đã yêu cầu đặt lại mật khẩu Thư viện số.\n\n'+origin+'/#reset-password?token='+token+'\n\nLiên kết có hiệu lực 15 phút và chỉ dùng một lần. Nếu không yêu cầu, bạn có thể bỏ qua email này. Không chia sẻ liên kết với người khác.')
    try:
        context=ssl.create_default_context()
        client=smtplib.SMTP_SSL(host,port,timeout=15,context=context) if mode=='ssl' else smtplib.SMTP(host,port,timeout=15)
        with client:
            if mode=='starttls': client.starttls(context=context)
            username=os.getenv('SMTP_USER','')
            if username: client.login(username,os.getenv('SMTP_PASSWORD',''))
            client.send_message(msg)
    except Exception:
        # Never log credentials, recipient, reset link or SMTP exception content.
        logging.getLogger(__name__).error('Password reset email delivery failed; check SMTP configuration.')
        with connect(True) as db: db.execute('DELETE FROM password_resets WHERE token_hash=?',(digest(token),))

@router.post('/forgot-password',response_model=OkOut,status_code=202)
def forgot_password(p:ForgotPassword,tasks:BackgroundTasks):
    config=mail_config();stamp=int(time.time())
    with connect(True) as db:
        db.execute('DELETE FROM reset_limits WHERE window_start<?',(stamp-3600,))
        db.execute('DELETE FROM password_resets WHERE expires_at<=?',(now().isoformat(),))
        keys=[('global',100),('email:'+digest(p.email),5)]
        for key,limit in keys:
            row=db.execute('SELECT * FROM reset_limits WHERE key=?',(key,)).fetchone()
            if row and (row['count']>=limit or (key!='global' and stamp-row['last_request']<60)):
                return {'ok':True}
        for key,_ in keys:
            db.execute('INSERT INTO reset_limits VALUES (?,?,1,?) ON CONFLICT(key) DO UPDATE SET count=count+1,last_request=excluded.last_request',(key,stamp,stamp))
        user=db.execute('SELECT * FROM users WHERE email=?',(p.email,)).fetchone()
        if user:
            token=secrets.token_urlsafe(32)
            db.execute('DELETE FROM password_resets WHERE user_id=?',(user['id'],))
            db.execute('INSERT INTO password_resets VALUES (?,?,?,?,?)',(digest(token),user['id'],user['email'],digest(user['password_hash']),(now()+timedelta(minutes=15)).isoformat()))
            tasks.add_task(deliver_reset,p.email,token,config)
    return {'ok':True}

@router.post('/reset-password',response_model=OkOut)
def reset_password(p:ResetPassword):
    hashed=password_hash(p.password)
    with connect(True) as db:
        reset=db.execute('SELECT r.*,u.email AS current_email,u.password_hash FROM password_resets r JOIN users u ON u.id=r.user_id WHERE r.token_hash=? AND r.expires_at>?',(digest(p.token),now().isoformat())).fetchone()
        if not reset or reset['email']!=reset['current_email'] or reset['password_version']!=digest(reset['password_hash']):
            raise HTTPException(400,'RESET_LINK_INVALID')
        db.execute('UPDATE users SET password_hash=? WHERE id=?',(hashed,reset['user_id']))
        db.execute('DELETE FROM sessions WHERE user_id=?',(reset['user_id'],))
        db.execute('DELETE FROM password_resets WHERE user_id=?',(reset['user_id'],))
    return {'ok':True}
