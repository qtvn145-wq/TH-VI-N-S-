"""Dedicated demonstration database; never resets existing data."""
import os
os.environ['DATABASE_PATH'] = os.getenv('DEMO_DATABASE_PATH','data/demo.sqlite3')
os.environ['MEDIA_DIR'] = 'data/demo-covers'
from app.db import connect, migrate
from app.security import password_hash
from datetime import datetime, timedelta, timezone

def seed():
    migrate()
    with connect(True) as db:
        if db.execute('SELECT count(*) FROM users').fetchone()[0]:
            print('Demo already initialized; existing data kept.')
            return
        for email,name,role in [('reader@demo.local','Nguyễn Minh Anh','reader'),('librarian@demo.local','Trần Thu Hà','librarian')]:
            db.execute('INSERT INTO users(email,name,password_hash,role) VALUES (?,?,?,?)',(email,name,password_hash('ThuVienDemo2026!'),role))
        for n in ['Lập trình','Cơ sở dữ liệu','Mạng & bảo mật','Trí tuệ nhân tạo']: db.execute('INSERT INTO categories(name) VALUES (?)',(n,))
        for n in ['Nguyễn Văn An','Trần Minh Đức','Lê Thu Hương','Phạm Hoàng Nam']: db.execute('INSERT INTO authors(name) VALUES (?)',(n,))
        titles=['Nhập môn lập trình Python','Cơ sở dữ liệu quan hệ','Mạng máy tính căn bản','Trí tuệ nhân tạo ứng dụng','Cấu trúc dữ liệu & giải thuật','Thiết kế hệ quản trị dữ liệu','An toàn thông tin','Học máy với Python']
        for i,title in enumerate(titles,1):
            db.execute('INSERT INTO books(title,description) VALUES (?,?)',(title,'Tài liệu minh họa cho bản chạy thử Thư viện số Khoa CNTT. Giới thiệu kiến thức nền tảng và bài tập thực hành dành cho sinh viên.'))
            db.execute('INSERT INTO book_authors VALUES (?,?)',(i,(i-1)%4+1))
            db.execute('INSERT INTO book_categories VALUES (?,?)',(i,(i-1)%4+1))
            for j in range(0 if i==8 else 3): db.execute('INSERT INTO copies(book_id,barcode) VALUES (?,?)',(i,f'CNTT-{i:03}-{j+1:03}'))
        now=datetime.now(timezone.utc)
        db.execute("INSERT INTO loans(user_id,copy_id,status,reserved_at,borrowed_at,due_date,daily_fine) VALUES (1,1,'borrowed',?,?,?,2000)",((now-timedelta(days=19)).isoformat(),(now-timedelta(days=18)).isoformat(),(now-timedelta(days=4)).date().isoformat()))
    print('Demo ready. Accounts and password: see FRONTEND_README.md')

if __name__=='__main__':
    seed()
    import uvicorn
    uvicorn.run('serve:app',host='127.0.0.1',port=8081)
