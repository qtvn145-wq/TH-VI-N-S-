"""PDF upload, rendered pages and personal reading progress."""
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import Response
from .db import connect, get
from .security import current_user, librarian
from .schemas import EbookOut, ProgressInput, ProgressOut

router=APIRouter(prefix='/api/v1',tags=['Ebooks'])
MAX_PDF_BYTES=25*1024*1024

def root():
    path=Path(os.getenv('EBOOK_DIR','data/ebooks')).resolve()
    path.mkdir(parents=True,exist_ok=True)
    return path

def active_book(db,book_id):
    book=get(db,'books',book_id)
    if book['archived']: raise HTTPException(404,'NOT_FOUND')
    return book

def ebook(db,book_id):
    active_book(db,book_id)
    row=db.execute('SELECT * FROM ebooks WHERE book_id=?',(book_id,)).fetchone()
    if row is None: raise HTTPException(404,'EBOOK_NOT_FOUND')
    return dict(row)

def process_pdf(mode,path,page=None):
    command=[sys.executable,'-m','backend.app.pdf_worker',mode,str(path)]
    if page is not None: command.append(str(page))
    try:
        result=subprocess.run(command,cwd=Path(__file__).resolve().parents[2],capture_output=True,timeout=20)
    except subprocess.TimeoutExpired:
        raise HTTPException(422,'PDF_TOO_COMPLEX')
    if result.returncode: raise HTTPException(422,'INVALID_PDF')
    return result.stdout

@router.post('/books/{book_id}/ebook',response_model=EbookOut)
def upload_ebook(book_id:int,file:UploadFile=File(...),u=Depends(librarian)):
    with connect() as db: active_book(db,book_id)
    raw=file.file.read(MAX_PDF_BYTES+1)
    if len(raw)>MAX_PDF_BYTES: raise HTTPException(413,'PDF_TOO_LARGE')
    if not raw.startswith(b'%PDF-'): raise HTTPException(415,'INVALID_PDF')
    revision=secrets.token_hex(16)
    path=root()/(revision+'.pdf')
    path.write_bytes(raw)
    try:
        info=json.loads(process_pdf('info',path))
        # Validate that at least the first page can be rendered before publication.
        preview=process_pdf('render',path,1)
        (root()/(revision+'-1.jpg')).write_bytes(preview)
        with connect(True) as db:
            active_book(db,book_id)
            db.execute('INSERT INTO ebooks VALUES (?,?,?) ON CONFLICT(book_id) DO UPDATE SET revision=excluded.revision,page_count=excluded.page_count',(book_id,revision,info['page_count']))
            db.execute('DELETE FROM reading_progress WHERE book_id=?',(book_id,))
    except Exception:
        # If publication succeeded, retain its PDF even if optional caching failed.
        with connect() as db:
            published=db.execute('SELECT 1 FROM ebooks WHERE revision=?',(revision,)).fetchone()
        if not published:
            path.unlink(missing_ok=True)
            (root()/(revision+'-1.jpg')).unlink(missing_ok=True)
        raise
    return {'book_id':book_id,'revision':revision,'page_count':info['page_count']}

@router.get('/books/{book_id}/ebook',response_model=EbookOut)
def ebook_info(book_id:int):
    with connect() as db: return ebook(db,book_id)

@router.get('/books/{book_id}/pages/{page}')
def read_page(book_id:int,page:int,v:str=Query(min_length=32,max_length=32)):
    with connect() as db: row=ebook(db,book_id)
    if v!=row['revision']: raise HTTPException(409,'EBOOK_CHANGED')
    if not 1<=page<=row['page_count']: raise HTTPException(404,'PAGE_NOT_FOUND')
    path=root()/(v+'.pdf')
    if not path.is_file(): raise HTTPException(404,'EBOOK_NOT_FOUND')
    cache=root()/f'{v}-{page}.jpg'
    if cache.is_file(): raw=cache.read_bytes()
    else:
        raw=process_pdf('render',path,page)
        temp=cache.with_suffix('.'+secrets.token_hex(8)+'.tmp')
        try:
            temp.write_bytes(raw); os.replace(temp,cache)
        finally: temp.unlink(missing_ok=True)
    return Response(raw,media_type='image/jpeg',headers={'Cache-Control':'private, max-age=0, must-revalidate','X-Content-Type-Options':'nosniff'})

@router.get('/books/{book_id}/progress',response_model=ProgressOut)
def progress(book_id:int,u=Depends(current_user)):
    with connect() as db:
        row=ebook(db,book_id)
        saved=db.execute('SELECT page FROM reading_progress WHERE user_id=? AND book_id=? AND revision=?',(u['id'],book_id,row['revision'])).fetchone()
        return {'page':saved[0] if saved else 1,'revision':row['revision']}

@router.put('/books/{book_id}/progress',response_model=ProgressOut)
def save_progress(book_id:int,p:ProgressInput,u=Depends(current_user)):
    with connect(True) as db:
        row=ebook(db,book_id)
        if p.revision!=row['revision']: raise HTTPException(409,'EBOOK_CHANGED')
        if p.page>row['page_count']: raise HTTPException(422,'PAGE_NOT_FOUND')
        db.execute('INSERT INTO reading_progress VALUES (?,?,?,?) ON CONFLICT(user_id,book_id) DO UPDATE SET revision=excluded.revision,page=excluded.page',(u['id'],book_id,p.revision,p.page))
    return p
