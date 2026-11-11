"""Run: python -m app.cli init | librarian | reminders [--send]."""
import argparse
import getpass
import json
import os
import smtplib
import ssl
from datetime import timedelta
from email.message import EmailMessage
from .db import connect, migrate
from .security import password_hash, now
from .schemas import Registration
from .main import today

def reminders(send=False):
    # One worker only. Transaction prevents overlapping workers from sending concurrently.
    # SMTP acceptance followed by a crash before commit can still cause a duplicate on retry.
    count=0
    with connect(True) as db:
        rows=db.execute("SELECT l.id,l.due_date,u.email,u.name,b.title FROM loans l JOIN users u ON u.id=l.user_id JOIN copies c ON c.id=l.copy_id JOIN books b ON b.id=c.book_id WHERE l.status='borrowed' AND l.due_date<=? AND NOT EXISTS(SELECT 1 FROM reminders r WHERE r.loan_id=l.id AND r.day=?)",((today()+timedelta(days=1)).isoformat(),today().isoformat())).fetchall()
        for r in rows:
            if send:
                msg=EmailMessage()
                msg['From']=os.environ['SMTP_FROM']
                msg['To']=r['email']
                msg['Subject']='Nhắc hạn trả sách Thư viện Khoa CNTT'
                msg.set_content(f"Chào {r['name']}, sách {r['title']} có hạn trả {r['due_date']}. Vui lòng liên hệ thủ thư để trả sách.")
                with smtplib.SMTP(os.environ['SMTP_HOST'],int(os.getenv('SMTP_PORT','587')),timeout=20) as smtp:
                    smtp.starttls(context=ssl.create_default_context())
                    if os.getenv('SMTP_USER'): smtp.login(os.environ['SMTP_USER'],os.environ['SMTP_PASSWORD'])
                    smtp.send_message(msg)
                db.execute('INSERT INTO reminders VALUES (?,?,?)',(r['id'],today().isoformat(),now().isoformat()))
            count+=1
    return {'eligible':count,'sent':count if send else 0,'dry_run':not send}

def main():
    p=argparse.ArgumentParser()
    p.add_argument('command',choices=['init','librarian','reminders'])
    p.add_argument('--send',action='store_true')
    args=p.parse_args()
    migrate()
    if args.command=='librarian':
        user=Registration(email=input('Email: '),name=input('Tên: '),password=getpass.getpass('Mật khẩu (>=10 ký tự): '))
        with connect(True) as db:
            db.execute("INSERT INTO users(email,name,password_hash,role) VALUES (?,?,?,'librarian')",(user.email,user.name,password_hash(user.password)))
        print('Đã tạo thủ thư.')
    elif args.command=='reminders': print(json.dumps(reminders(args.send)))
    else: print('Migration hoàn tất.')

if __name__=='__main__': main()
