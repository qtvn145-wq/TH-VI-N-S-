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
    page_count: int
    ebook_revision: str | None

class NamedOut(Named):
    id: int

class ErrorOut(BaseModel):
    detail: str

class OkOut(BaseModel):
    ok: bool

class HealthOut(BaseModel):
    status: str

class CoverOut(BaseModel):
    cover_url: str

class ProgressInput(Input):
    page: int = Field(ge=1)
    revision: str = Field(min_length=32,max_length=32)

class ProgressOut(BaseModel):
    page: int
    revision: str

class EbookOut(BaseModel):
    book_id: int
    page_count: int
    revision: str
