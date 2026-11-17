import argparse
import getpass
from .db import connect,migrate
from .security import password_hash
from .schemas import Registration

def main():
    p=argparse.ArgumentParser()
    p.add_argument('command',choices=['init','librarian'])
    args=p.parse_args()
    migrate()
    if args.command=='librarian':
        user=Registration(email=input('Email: '),name=input('Tên: '),password=getpass.getpass('Mật khẩu (>=10 ký tự): '))
        with connect(True) as db:
            db.execute("INSERT INTO users(email,name,password_hash,role) VALUES (?,?,?,'librarian')",(user.email,user.name,password_hash(user.password)))
        print('Đã tạo thủ thư.')
    else: print('Migration hoàn tất.')

if __name__=='__main__': main()
