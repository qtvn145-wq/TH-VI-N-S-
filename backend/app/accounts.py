"""Account administration; librarian is the existing administrative role."""
import sqlite3
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import Field, field_validator
from .db import connect, get
from .schemas import Input, Registration, UserOut, OkOut
from .security import librarian, password_hash

class AccountCreate(Registration):
    role: Literal['reader', 'librarian'] = 'reader'

class AccountUpdate(Input):
    email: str = Field(min_length=3, max_length=254, pattern=r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
    name: str = Field(min_length=1, max_length=150)
    role: Literal['reader', 'librarian']
    @field_validator('email')
    @classmethod
    def normalize(cls, value): return value.lower()

class PasswordUpdate(Input):
    password: str = Field(min_length=10, max_length=128)

router = APIRouter(prefix='/api/v1/admin/users', tags=['Account administration'])

def authorize(db, actor):
    # Recheck under the write lock: an administrator may have just been demoted.
    row = db.execute('SELECT role FROM users WHERE id=?', (actor['id'],)).fetchone()
    if not row or row['role'] != 'librarian':
        raise HTTPException(403, 'LIBRARIAN_REQUIRED')

def protect_last(db, target):
    if target['role'] == 'librarian' and db.execute("SELECT count(*) FROM users WHERE role='librarian'").fetchone()[0] <= 1:
        raise HTTPException(409, 'LAST_ADMIN')

def unique_email(db, email, exclude=0):
    if db.execute('SELECT id FROM users WHERE lower(email)=? AND id<>?', (email, exclude)).fetchone():
        raise HTTPException(409, 'EMAIL_EXISTS')

@router.get('', response_model=list[UserOut])
def list_users(q: str = Query('', max_length=254), limit: int = Query(13, ge=1, le=100), offset: int = Query(0, ge=0), actor=Depends(librarian)):
    with connect() as db:
        authorize(db, actor)
        return [dict(r) for r in db.execute('SELECT id,email,name,role FROM users WHERE instr(lower(email),lower(?))>0 OR instr(lower(name),lower(?))>0 ORDER BY id LIMIT ? OFFSET ?', (q.strip(), q.strip(), limit, offset))]

@router.post('', response_model=UserOut, status_code=201)
def create_user(p: AccountCreate, actor=Depends(librarian)):
    hashed = password_hash(p.password)
    with connect(True) as db:
        authorize(db, actor); unique_email(db, p.email)
        id = db.execute('INSERT INTO users(email,name,password_hash,role) VALUES (?,?,?,?)', (p.email,p.name,hashed,p.role)).lastrowid
        return get(db, 'users', id)

@router.put('/{id}', response_model=UserOut)
def update_user(id: int, p: AccountUpdate, actor=Depends(librarian)):
    with connect(True) as db:
        authorize(db, actor); target = get(db, 'users', id)
        if p.role != target['role']: protect_last(db, target)
        unique_email(db, p.email, id)
        db.execute('UPDATE users SET email=?,name=?,role=? WHERE id=?', (p.email,p.name,p.role,id))
        if p.email != target['email'] or p.role != target['role']:
            db.execute('DELETE FROM sessions WHERE user_id=?', (id,))
        return get(db, 'users', id)

@router.put('/{id}/password', response_model=OkOut)
def reset_password(id: int, p: PasswordUpdate, actor=Depends(librarian)):
    hashed = password_hash(p.password)
    with connect(True) as db:
        authorize(db, actor); get(db, 'users', id)
        db.execute('UPDATE users SET password_hash=? WHERE id=?', (hashed,id))
        db.execute('DELETE FROM sessions WHERE user_id=?', (id,))
    return {'ok': True}

@router.delete('/{id}', response_model=OkOut)
def delete_user(id: int, actor=Depends(librarian)):
    try:
        with connect(True) as db:
            authorize(db, actor); target = get(db, 'users', id)
            protect_last(db, target)
            if id == actor['id']: raise HTTPException(409, 'CANNOT_DELETE_SELF')
            for table in ('sessions', 'favorites', 'reading_progress'):
                db.execute(f'DELETE FROM {table} WHERE user_id=?', (id,))
            db.execute('DELETE FROM users WHERE id=?', (id,))
    except sqlite3.IntegrityError:
        raise HTTPException(409, 'ACCOUNT_HAS_HISTORY') from None
    return {'ok': True}
