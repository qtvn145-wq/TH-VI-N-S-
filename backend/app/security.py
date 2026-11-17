import hashlib
import hmac
import secrets
from datetime import datetime, timezone
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from .db import connect

bearer = HTTPBearer()

def password_hash(password, salt=None):
    salt = salt or secrets.token_hex(16)
    value = hashlib.scrypt(password.encode(), salt=salt.encode(), n=16384, r=8, p=1).hex()
    return salt + ':' + value

def verify(password, stored):
    return hmac.compare_digest(password_hash(password, stored.split(':')[0]), stored)

def digest(token):
    return hashlib.sha256(token.encode()).hexdigest()

def now():
    return datetime.now(timezone.utc)

def current_user(auth: HTTPAuthorizationCredentials = Depends(bearer)):
    with connect() as db:
        row = db.execute('SELECT u.* FROM users u JOIN sessions s ON s.user_id=u.id WHERE s.token_hash=? AND s.expires_at>?', (digest(auth.credentials), now().isoformat())).fetchone()
        if not row:
            raise HTTPException(401, 'INVALID_SESSION')
        return dict(row)

def librarian(user=Depends(current_user)):
    if user['role'] != 'librarian':
        raise HTTPException(403, 'LIBRARIAN_REQUIRED')
    return user
