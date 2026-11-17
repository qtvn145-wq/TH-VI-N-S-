import io
import os
import secrets
import sqlite3
import unicodedata
from contextlib import asynccontextmanager
from datetime import timedelta
from pathlib import Path
from typing import Literal
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
Image.MAX_IMAGE_PIXELS = 16_000_000

@asynccontextmanager
async def lifespan(app):
    if os.getenv("AUTO_MIGRATE", "true").lower() == "true":
        migrate()
    yield

app = FastAPI(title='Thư viện số Khoa CNTT', version='2.0.0', lifespan=lifespan, responses={code: {'model': ErrorOut} for code in (401,403,404,409,413,415)},
    description='Thư viện sách điện tử. Đọc PDF, yêu thích và lưu tiến độ. Bearer session 8 giờ.')
app.add_middleware(CORSMiddleware,allow_origins=os.getenv('CORS_ORIGINS','http://localhost:5173').split(','),allow_methods=['GET','POST','PUT','DELETE'],allow_headers=['Authorization','Content-Type'])
app.mount('/media',StaticFiles(directory=MEDIA),name='media')

@app.exception_handler(sqlite3.IntegrityError)
async def integrity_error(request, exc):
    return JSONResponse(status_code=409,content={'detail':'DATA_CONFLICT'})

def book_out(db,id):
    row=get(db,'books',id)
    if row['archived']: raise HTTPException(404,'NOT_FOUND')
    for kind in ('authors','categories'):
        key='author' if kind=='authors' else 'category'
        row[key+'_ids']=[r[0] for r in db.execute(f'SELECT {key}_id FROM book_{kind} WHERE book_id=? ORDER BY {key}_id',(id,))]
    ebook=db.execute('SELECT page_count,revision FROM ebooks WHERE book_id=?',(id,)).fetchone()
    row.update(page_count=ebook['page_count'] if ebook else 0,ebook_revision=ebook['revision'] if ebook else None)
    return row

def relations(db,id,p):
    for kind,ids,key in [('authors',p.author_ids,'author'),('categories',p.category_ids,'category')]:
        for rid in set(ids): get(db,kind,rid)
        db.execute(f'DELETE FROM book_{kind} WHERE book_id=?',(id,))
        db.executemany(f'INSERT INTO book_{kind} VALUES (?,?)',[(id,rid) for rid in set(ids)])

@app.get('/api/v1/health',response_model=HealthOut,tags=['System'])
def health():
    with connect() as db:
        db.execute('SELECT id FROM users LIMIT 1')
        if db.execute('PRAGMA user_version').fetchone()[0] != 4:
            raise HTTPException(503, 'SCHEMA_NOT_READY')
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
def books(q:str='',author:str='',category_id:int|None=None,limit:int=Query(20,ge=1,le=100),offset:int=Query(0,ge=0),readable_only:bool=False,sort:Literal['id','newest','title']='id'):
    with connect() as db:
        # Python casefold gives Vietnamese case-insensitive matching (SQLite LOWER is ASCII).
        rows=db.execute('SELECT id,title FROM books WHERE archived=0 ORDER BY id').fetchall()
        ids=[]
        for r in rows:
            if search_text(q) not in search_text(r['title']): continue
            names=[a[0] for a in db.execute('SELECT a.name FROM authors a JOIN book_authors ba ON ba.author_id=a.id WHERE ba.book_id=?',(r['id'],))]
            if author and not any(search_text(author) in search_text(n) for n in names): continue
            if category_id and not db.execute('SELECT 1 FROM book_categories WHERE book_id=? AND category_id=?',(r['id'],category_id)).fetchone(): continue
            ids.append(r['id'])
        results=[book_out(db,id) for id in ids]
        if readable_only:
            results=[b for b in results if b['page_count']>0]
        if sort=='newest': results.sort(key=lambda b:b['id'],reverse=True)
        if sort=='title': results.sort(key=lambda b:(search_text(b['title']),b['id']))
        return results[offset:offset+limit]

def search_text(value):
    normalized=unicodedata.normalize('NFD',value.strip().casefold().replace('đ','d'))
    return ''.join(c for c in normalized if not unicodedata.combining(c))

@app.get('/api/v1/favorites',response_model=list[BookOut],tags=['Favorites'])
def favorites(limit:int=Query(20,ge=1,le=100),offset:int=Query(0,ge=0),u=Depends(current_user)):
    with connect() as db:
        ids=db.execute('SELECT f.book_id FROM favorites f JOIN books b ON b.id=f.book_id WHERE f.user_id=? AND b.archived=0 ORDER BY f.created_at DESC,f.book_id DESC LIMIT ? OFFSET ?', (u['id'],limit,offset)).fetchall()
        return [book_out(db,r[0]) for r in ids]

@app.get('/api/v1/favorites/{book_id}',response_model=OkOut,tags=['Favorites'])
def favorite_status(book_id:int,u=Depends(current_user)):
    with connect() as db:
        book_out(db,book_id)
        return {'ok':db.execute('SELECT 1 FROM favorites WHERE user_id=? AND book_id=?',(u['id'],book_id)).fetchone() is not None}

@app.put('/api/v1/favorites/{book_id}',response_model=OkOut,tags=['Favorites'])
def save_favorite(book_id:int,u=Depends(current_user)):
    with connect(True) as db:
        book_out(db,book_id)
        db.execute('INSERT INTO favorites(user_id,book_id,created_at) VALUES (?,?,?) ON CONFLICT(user_id,book_id) DO NOTHING',(u['id'],book_id,now().isoformat()))
    return {'ok':True}

@app.delete('/api/v1/favorites/{book_id}',response_model=OkOut,tags=['Favorites'])
def remove_favorite(book_id:int,u=Depends(current_user)):
    with connect(True) as db:
        db.execute('DELETE FROM favorites WHERE user_id=? AND book_id=?',(u['id'],book_id))
    return {'ok':True}

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
        db.execute('UPDATE books SET archived=1 WHERE id=?',(id,))
        db.execute('DELETE FROM favorites WHERE book_id=?',(id,))
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


# Reader routes use the same authentication and storage helpers.
from .ebooks import router as ebook_router
app.include_router(ebook_router)

from .accounts import router as accounts_router
app.include_router(accounts_router)

from .password_reset import router as password_reset_router
app.include_router(password_reset_router)
