from typing import Literal
from pydantic import BaseModel, Field, ConfigDict, field_validator

class Input(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)

class Credentials(Input):
    email: str = Field(min_length=3,max_length=254,pattern=r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
    password: str = Field(min_length=10,max_length=128)
    @field_validator('email')
    @classmethod
    def normalize(cls,v): return v.lower()

class Registration(Credentials):
    name: str = Field(min_length=1,max_length=150)

class Named(Input):
    name: str = Field(min_length=1,max_length=150)

class BookInput(Input):
    title: str = Field(min_length=1,max_length=300)
    description: str = Field(default='',max_length=5000)
    author_ids: list[int] = Field(default_factory=list,max_length=30)
    category_ids: list[int] = Field(default_factory=list,max_length=30)

class CopyInput(Input):
    barcode: str = Field(min_length=1,max_length=100)

class CopyUpdate(CopyInput):
    retired: bool = False

class Reservation(Input):
    book_id: int = Field(gt=0)

class Token(BaseModel):
    access_token: str
    token_type: str = 'bearer'
    expires_in: int

class UserOut(BaseModel):
    id: int
    email: str
    name: str
    role: Literal['reader','librarian']

class BookOut(BaseModel):
    id: int
    title: str
    description: str
    cover_url: str | None
    author_ids: list[int]
    category_ids: list[int]
    available_copies: int

class LoanOut(BaseModel):
    id: int
    user_id: int
    copy_id: int
    status: Literal['reserved','borrowed','returned','cancelled']
    reserved_at: str
    borrowed_at: str | None
    due_date: str | None
    returned_at: str | None
    daily_fine: int
    overdue_days: int
    estimated_fine: int

class NamedOut(Named):
    id: int

class ErrorOut(BaseModel):
    detail: str

class OkOut(BaseModel):
    ok: bool

class HealthOut(BaseModel):
    status: str

class CopyOut(BaseModel):
    id: int
    book_id: int
    barcode: str
    retired: bool
    loan_status: str | None = None

class CoverOut(BaseModel):
    cover_url: str

class FineOut(BaseModel):
    id: int
    loan_id: int
    amount: int
    paid_at: str | None

class QueueOut(BaseModel):
    id: int
    user_id: int
    book_id: int
    created_at: str
    position: int | None = None

class StatsOut(BaseModel):
    books: int
    borrowed: int
    overdue: int
    unpaid_fines: int
