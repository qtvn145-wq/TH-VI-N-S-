import io
import os
import secrets
import sqlite3
from contextlib import asynccontextmanager
from datetime import date, timedelta
from pathlib import Path
from typing import Literal
from zoneinfo import ZoneInfo
from fastapi import FastAPI, Depends, HTTPException, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image, UnidentifiedImageError
from .db import connect, get, migrate
from .security import current_user, librarian, password_hash, verify, digest, now, bearer
from .schemas import *

MEDIA = Path(os.getenv('MEDIA_DIR','data/covers'))
MEDIA.mkdir(parents=True,exist_ok=True)
LOAN_DAYS = int(os.getenv('LOAN_DAYS','14'))
DAILY_FINE = int(os.getenv('DAILY_FINE','2000'))
assert LOAN_DAYS > 0 and DAILY_FINE >= 0
Image.MAX_IMAGE_PIXELS = 16_000_000

@asynccontextmanager
async def lifespan(app):
    migrate()
    yield

app = FastAPI(title='Thư viện số Khoa CNTT', version='1.0.0', lifespan=lifespan, responses={code: {'model': ErrorOut} for code in (401,403,404,409,413,415)},
    description='REST API v1. Bearer session 8 giờ. Tiền: VND nguyên. Ngày nghiệp vụ: Asia/Ho_Chi_Minh.')
app.add_middleware(CORSMiddleware,allow_origins=os.getenv('CORS_ORIGINS','http://localhost:5173').split(','),allow_methods=['GET','POST','PUT','DELETE'],allow_headers=['Authorization','Content-Type'])
app.mount('/media',StaticFiles(directory=MEDIA),name='media')

@app.exception_handler(sqlite3.IntegrityError)
async def integrity_error(request, exc):
    return JSONResponse(status_code=409,content={'detail':'DATA_CONFLICT'})

def today(): return now().astimezone(ZoneInfo('Asia/Ho_Chi_Minh')).date()

def loan_out(row):
    row = dict(row)
    end = date.fromisoformat(row['returned_at'][:10]) if row['returned_at'] else today()
    days = max(0,(end-date.fromisoformat(row['due_date'])).days) if row['due_date'] else 0
    row.update(overdue_days=days,estimated_fine=days*row['daily_fine'])
    return row

def book_out(db,id):
    row=get(db,'books',id)
    for kind in ('authors','categories'):
        key='author' if kind=='authors' else 'category'
        row[key+'_ids']=[r[0] for r in db.execute(f'SELECT {key}_id FROM book_{kind} WHERE book_id=? ORDER BY {key}_id',(id,))]
    row['available_copies']=db.execute("SELECT count(*) FROM copies c WHERE book_id=? AND retired=0 AND NOT EXISTS(SELECT 1 FROM loans l WHERE l.copy_id=c.id AND l.status IN ('reserved','borrowed'))",(id,)).fetchone()[0]
    return row

def relations(db,id,p):
    for kind,ids,key in [('authors',p.author_ids,'author'),('categories',p.category_ids,'category')]:
        for rid in set(ids): get(db,kind,rid)
        db.execute(f'DELETE FROM book_{kind} WHERE book_id=?',(id,))
        db.executemany(f'INSERT INTO book_{kind} VALUES (?,?)',[(id,rid) for rid in set(ids)])

@app.get('/api/v1/health',response_model=HealthOut,tags=['System'])
def health():
    with connect() as db: db.execute('SELECT 1')
    return {'status':'ok'}

@app.post('/api/v1/auth/register',response_model=UserOut,status_code=201,tags=['Auth'])
def register(p:Registration):
    with connect(True) as db:
        id=db.execute("INSERT INTO users(email,name,password_hash,role) VALUES (?,?,?,'reader')",(p.email,p.name,password_hash(p.password))).lastrowid
        return get(db,'users',id)

@app.post('/api/v1/auth/login',response_model=Token,tags=['Auth'])
def login(p:Credentials):
    with connect(True) as db:
        u=db.execute('SELECT * FROM users WHERE email=?',(p.email,)).fetchone()
        if not u or not verify(p.password,u['password_hash']): raise HTTPException(401,'INVALID_CREDENTIALS')
        token=secrets.token_urlsafe(32)
        db.execute('INSERT INTO sessions VALUES (?,?,?)',(digest(token),u['id'],(now()+timedelta(hours=8)).isoformat()))
        return Token(access_token=token,expires_in=28800)

@app.get('/api/v1/auth/me',response_model=UserOut,tags=['Auth'])
def me(u=Depends(current_user)): return u

@app.post('/api/v1/auth/logout',response_model=OkOut,tags=['Auth'])
def logout(auth=Depends(bearer),u=Depends(current_user)):
    with connect(True) as db: db.execute('DELETE FROM sessions WHERE token_hash=?',(digest(auth.credentials),))
    return {'ok':True}

@app.get('/api/v1/books',response_model=list[BookOut],tags=['Catalog'])
def books(q:str='',author:str='',category_id:int|None=None,limit:int=Query(20,ge=1,le=100),offset:int=Query(0,ge=0)):
    with connect() as db:
        # Python casefold gives Vietnamese case-insensitive matching (SQLite LOWER is ASCII).
        rows=db.execute('SELECT id,title FROM books ORDER BY id').fetchall()
        ids=[]
        for r in rows:
            if q.casefold() not in r['title'].casefold(): continue
            names=[a[0] for a in db.execute('SELECT a.name FROM authors a JOIN book_authors ba ON ba.author_id=a.id WHERE ba.book_id=?',(r['id'],))]
            if author and not any(author.casefold() in n.casefold() for n in names): continue
            if category_id and not db.execute('SELECT 1 FROM book_categories WHERE book_id=? AND category_id=?',(r['id'],category_id)).fetchone(): continue
            ids.append(r['id'])
        return [book_out(db,id) for id in ids[offset:offset+limit]]

@app.get('/api/v1/books/{id}',response_model=BookOut,tags=['Catalog'])
def book(id:int):
    with connect() as db: return book_out(db,id)

@app.post('/api/v1/books',response_model=BookOut,status_code=201,tags=['Librarian'])
def create_book(p:BookInput,u=Depends(librarian)):
    with connect(True) as db:
        id=db.execute('INSERT INTO books(title,description) VALUES (?,?)',(p.title,p.description)).lastrowid
        relations(db,id,p)
        return book_out(db,id)

@app.put('/api/v1/books/{id}',response_model=BookOut,tags=['Librarian'])
def update_book(id:int,p:BookInput,u=Depends(librarian)):
    with connect(True) as db:
        get(db,'books',id)
        db.execute('UPDATE books SET title=?,description=? WHERE id=?',(p.title,p.description,id))
        relations(db,id,p)
        return book_out(db,id)

@app.delete('/api/v1/books/{id}',response_model=OkOut,tags=['Librarian'])
def delete_book(id:int,u=Depends(librarian)):
    with connect(True) as db:
        get(db,'books',id)
        db.execute('DELETE FROM books WHERE id=?',(id,))
    return {'ok':True}

@app.get('/api/v1/catalog/{kind}',response_model=list[NamedOut],tags=['Catalog'])
def names(kind:Literal['authors','categories']):
    with connect() as db: return [dict(r) for r in db.execute(f'SELECT * FROM {kind} ORDER BY id')]

@app.post('/api/v1/catalog/{kind}',response_model=NamedOut,status_code=201,tags=['Librarian'])
def add_name(kind:Literal['authors','categories'],p:Named,u=Depends(librarian)):
    with connect(True) as db:
        id=db.execute(f'INSERT INTO {kind}(name) VALUES (?)',(p.name,)).lastrowid
        return get(db,kind,id)

@app.put('/api/v1/catalog/{kind}/{id}',response_model=NamedOut,tags=['Librarian'])
def update_name(kind:Literal['authors','categories'],id:int,p:Named,u=Depends(librarian)):
    with connect(True) as db:
        get(db,kind,id)
        db.execute(f'UPDATE {kind} SET name=? WHERE id=?',(p.name,id))
        return get(db,kind,id)

@app.delete('/api/v1/catalog/{kind}/{id}',response_model=OkOut,tags=['Librarian'])
def delete_name(kind:Literal['authors','categories'],id:int,u=Depends(librarian)):
    with connect(True) as db:
        get(db,kind,id)
        db.execute(f'DELETE FROM {kind} WHERE id=?',(id,))
    return {'ok':True}

@app.get('/api/v1/books/{id}/copies',response_model=list[CopyOut],tags=['Librarian'])
def copies(id:int,u=Depends(librarian)):
    with connect() as db:
        get(db,'books',id)
        return [dict(r) for r in db.execute("SELECT c.*, (SELECT status FROM loans l WHERE l.copy_id=c.id AND status IN ('reserved','borrowed')) AS loan_status FROM copies c WHERE book_id=?",(id,))]

@app.post('/api/v1/books/{id}/copies',response_model=CopyOut,status_code=201,tags=['Librarian'])
def add_copy(id:int,p:CopyInput,u=Depends(librarian)):
    with connect(True) as db:
        get(db,'books',id)
        cid=db.execute('INSERT INTO copies(book_id,barcode) VALUES (?,?)',(id,p.barcode)).lastrowid
        return get(db,'copies',cid)

@app.put('/api/v1/copies/{id}',response_model=CopyOut,tags=['Librarian'])
def update_copy(id:int,p:CopyUpdate,u=Depends(librarian)):
    with connect(True) as db:
        get(db,'copies',id)
        if p.retired and db.execute("SELECT 1 FROM loans WHERE copy_id=? AND status IN ('reserved','borrowed')",(id,)).fetchone(): raise HTTPException(409,'COPY_IN_USE')
        db.execute('UPDATE copies SET barcode=?,retired=? WHERE id=?',(p.barcode,p.retired,id))
        return get(db,'copies',id)

@app.post('/api/v1/books/{id}/cover',response_model=CoverOut,tags=['Librarian'])
async def cover(id:int,file:UploadFile=File(...),u=Depends(librarian)):
    raw=await file.read(5*1024*1024+1)
    if len(raw)>5*1024*1024: raise HTTPException(413,'FILE_TOO_LARGE')
    try:
        with Image.open(io.BytesIO(raw)) as img:
            if img.format not in ('JPEG','PNG','WEBP'): raise ValueError()
            img.load()
            img.thumbnail((1600,1600))
            output=io.BytesIO()
            img.convert('RGB').save(output,'JPEG',quality=85)
    except (UnidentifiedImageError,ValueError,OSError,Image.DecompressionBombError):
        raise HTTPException(415,'INVALID_IMAGE')
    name=secrets.token_hex(16)+'.jpg'
    with connect(True) as db:
        get(db,'books',id)
        (MEDIA/name).write_bytes(output.getvalue())
        db.execute('UPDATE books SET cover_url=? WHERE id=?',('/media/'+name,id))
    return {'cover_url':'/media/'+name}

@app.post('/api/v1/loans',response_model=LoanOut,status_code=201,tags=['Loans'])
def reserve(p:Reservation,u=Depends(current_user)):
    with connect(True) as db:
        get(db,'books',p.book_id)
        count=db.execute("SELECT count(*) FROM loans WHERE user_id=? AND status IN ('reserved','borrowed')",(u['id'],)).fetchone()[0]
        if count>=3: raise HTTPException(409,'LOAN_LIMIT_REACHED')
        first=db.execute('SELECT user_id FROM waitlist WHERE book_id=? ORDER BY id LIMIT 1',(p.book_id,)).fetchone()
        if first and first[0]!=u['id']: raise HTTPException(409,'QUEUE_PRIORITY')
        copy=db.execute("SELECT id FROM copies c WHERE book_id=? AND retired=0 AND NOT EXISTS(SELECT 1 FROM loans l WHERE l.copy_id=c.id AND status IN ('reserved','borrowed')) ORDER BY id LIMIT 1",(p.book_id,)).fetchone()
        if not copy: raise HTTPException(409,'NO_COPY_AVAILABLE')
        id=db.execute("INSERT INTO loans(user_id,copy_id,status,reserved_at,daily_fine) VALUES (?,?,'reserved',?,?)",(u['id'],copy[0],now().isoformat(),DAILY_FINE)).lastrowid
        db.execute('DELETE FROM waitlist WHERE user_id=? AND book_id=?',(u['id'],p.book_id))
        return loan_out(get(db,'loans',id))

@app.get('/api/v1/loans',response_model=list[LoanOut],tags=['Loans'])
def loans(status:Literal['reserved','borrowed','returned','cancelled']|None=None,limit:int=Query(20,ge=1,le=100),offset:int=Query(0,ge=0),u=Depends(current_user)):
    with connect() as db:
        return [loan_out(r) for r in db.execute('SELECT * FROM loans WHERE (?=1 OR user_id=?) AND (? IS NULL OR status=?) ORDER BY id DESC LIMIT ? OFFSET ?',(u['role']=='librarian',u['id'],status,status,limit,offset))]

@app.post('/api/v1/loans/{id}/cancel',response_model=LoanOut,tags=['Loans'])
def cancel(id:int,u=Depends(current_user)):
    with connect(True) as db:
        row=get(db,'loans',id)
        if row['user_id']!=u['id'] and u['role']!='librarian': raise HTTPException(403,'FORBIDDEN')
        if row['status']!='reserved': raise HTTPException(409,'INVALID_LOAN_STATE')
        db.execute("UPDATE loans SET status='cancelled' WHERE id=?",(id,))
        return loan_out(get(db,'loans',id))

@app.post('/api/v1/loans/{id}/handover',response_model=LoanOut,tags=['Librarian'])
def handover(id:int,u=Depends(librarian)):
    with connect(True) as db:
        if get(db,'loans',id)['status']!='reserved': raise HTTPException(409,'INVALID_LOAN_STATE')
        db.execute("UPDATE loans SET status='borrowed',borrowed_at=?,due_date=? WHERE id=?",(now().isoformat(),(today()+timedelta(days=LOAN_DAYS)).isoformat(),id))
        return loan_out(get(db,'loans',id))

@app.post('/api/v1/loans/{id}/return',response_model=LoanOut,tags=['Librarian'])
def return_book(id:int,u=Depends(librarian)):
    with connect(True) as db:
        row=get(db,'loans',id)
        if row['status']!='borrowed': raise HTTPException(409,'INVALID_LOAN_STATE')
        amount=loan_out(row)['estimated_fine']
        db.execute("UPDATE loans SET status='returned',returned_at=? WHERE id=?",(now().astimezone(ZoneInfo('Asia/Ho_Chi_Minh')).isoformat(),id))
        if amount: db.execute('INSERT INTO fines(loan_id,amount) VALUES (?,?)',(id,amount))
        return loan_out(get(db,'loans',id))

@app.get('/api/v1/fines',response_model=list[FineOut],tags=['Loans'])
def fines(u=Depends(current_user)):
    with connect() as db:
        return [dict(r) for r in db.execute('SELECT f.* FROM fines f JOIN loans l ON l.id=f.loan_id WHERE ?=1 OR l.user_id=?',(u['role']=='librarian',u['id']))]

@app.post('/api/v1/fines/{id}/pay',response_model=FineOut,tags=['Librarian'])
def pay(id:int,u=Depends(librarian)):
    with connect(True) as db:
        row=get(db,'fines',id)
        if row['paid_at']: raise HTTPException(409,'ALREADY_PAID')
        db.execute('UPDATE fines SET paid_at=? WHERE id=?',(now().isoformat(),id))
        return get(db,'fines',id)

@app.post('/api/v1/waitlist',response_model=QueueOut,status_code=201,tags=['Waitlist'])
def join_queue(p:Reservation,u=Depends(current_user)):
    with connect(True) as db:
        if book_out(db,p.book_id)['available_copies']>0: raise HTTPException(409,'COPY_AVAILABLE')
        id=db.execute('INSERT INTO waitlist(user_id,book_id,created_at) VALUES (?,?,?)',(u['id'],p.book_id,now().isoformat())).lastrowid
        return get(db,'waitlist',id)

@app.get('/api/v1/waitlist',response_model=list[QueueOut],tags=['Waitlist'])
def queue(u=Depends(current_user)):
    with connect() as db:
        return [dict(r) for r in db.execute('SELECT w.*, (SELECT count(*) FROM waitlist q WHERE q.book_id=w.book_id AND q.id<=w.id) AS position FROM waitlist w WHERE ?=1 OR user_id=? ORDER BY id',(u['role']=='librarian',u['id']))]

@app.delete('/api/v1/waitlist/{id}',response_model=OkOut,tags=['Waitlist'])
def leave_queue(id:int,u=Depends(current_user)):
    with connect(True) as db:
        row=get(db,'waitlist',id)
        if row['user_id']!=u['id'] and u['role']!='librarian': raise HTTPException(403,'FORBIDDEN')
        db.execute('DELETE FROM waitlist WHERE id=?',(id,))
    return {'ok':True}

@app.get('/api/v1/stats',response_model=StatsOut,tags=['Librarian'])
def stats(u=Depends(librarian)):
    with connect() as db:
        return {'books':db.execute('SELECT count(*) FROM books').fetchone()[0],
                'borrowed':db.execute("SELECT count(*) FROM loans WHERE status='borrowed'").fetchone()[0],
                'overdue':db.execute("SELECT count(*) FROM loans WHERE status='borrowed' AND due_date<?",(today().isoformat(),)).fetchone()[0],
                'unpaid_fines':db.execute('SELECT coalesce(sum(amount),0) FROM fines WHERE paid_at IS NULL').fetchone()[0]}
