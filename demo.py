"""Create an isolated electronic-library demo; never resets existing data."""
import os
os.environ['DATABASE_PATH']=os.getenv('DEMO_DATABASE_PATH','data/ebook-demo.sqlite3')
os.environ['MEDIA_DIR']='data/ebook-demo-covers'
os.environ['EBOOK_DIR']='data/ebook-demo-files'
from backend.app.db import connect,migrate
from backend.app.security import password_hash
from backend.app.ebooks import root,process_pdf
from PIL import Image,ImageDraw,ImageFont
from pathlib import Path
import secrets

def seed():
 migrate()
 with connect(True) as db:
  if db.execute('SELECT count(*) FROM users').fetchone()[0]:
   print('Demo exists; data kept.');return
  for email,name,role in [('reader@demo.local','Bạn đọc demo','reader'),('librarian@demo.local','Quản trị demo','librarian')]:
   db.execute('INSERT INTO users(email,name,password_hash,role) VALUES (?,?,?,?)',(email,name,password_hash('ThuVienDemo2026!'),role))
  db.execute("INSERT INTO categories(name) VALUES ('Hướng dẫn')")
  db.execute("INSERT INTO authors(name) VALUES ('Thư viện Khoa CNTT')")
  bid=db.execute('INSERT INTO books(title,description) VALUES (?,?)',('Khám phá thư viện số','Sách mẫu tự tạo gồm 6 trang để thử chế độ lật trang, phóng to và lưu tiến độ.')).lastrowid
  db.execute('INSERT INTO book_authors VALUES (?,1)',(bid,));db.execute('INSERT INTO book_categories VALUES (?,1)',(bid,))
  pages=[]
  sections=[('THU VIEN SO','A small guide to your reading space'),('01 / DISCOVER','Search books by title, author or category.'),('02 / OPEN A BOOK','Open a digital book and choose one or two pages.'),('03 / TURN THE PAGE','Use arrow keys or swipe to turn a page.'),('04 / KEEP YOUR PLACE','Sign in to save reading progress to your account.'),('05 / READ EVERY DAY','Your next idea may be on the next page.')]
  for i,(title,body) in enumerate(sections):
   img=Image.new('RGB',(700,950),'#f7f3e8');draw=ImageDraw.Draw(img)
   draw.rectangle((0,0,700,170),fill='#214d3d');draw.text((45,65),title,fill='white',font=ImageFont.load_default(size=32))
   draw.text((45,240),body,fill='#214d3d',font=ImageFont.load_default(size=19))
   draw.rectangle((45,350,655,740),fill=['#c5d4b8','#d9e5d7','#d5dfce'][i%3]);draw.text((80,480),str(i+1).zfill(2),fill='#214d3d',font=ImageFont.load_default(size=100))
   draw.text((45,890),'KHOA CNTT / READING GUIDE',fill='#617563',font=ImageFont.load_default(size=14));pages.append(img)
  revision=secrets.token_hex(16);path=root()/(revision+'.pdf')
  pages[0].save(path,'PDF',save_all=True,append_images=pages[1:]);db.execute('INSERT INTO ebooks VALUES (?,?,?)',(bid,revision,len(pages)))
  media=Path(os.environ['MEDIA_DIR']);media.mkdir(parents=True,exist_ok=True);pages[0].save(media/'demo.jpg');db.execute('UPDATE books SET cover_url=? WHERE id=?',('/media/demo.jpg',bid))
  for image in pages:image.close()
 print('Demo ready: reader@demo.local / librarian@demo.local — ThuVienDemo2026!')
if __name__=='__main__':
 seed()
 import uvicorn
 uvicorn.run('serve:app',host='127.0.0.1',port=8081)
