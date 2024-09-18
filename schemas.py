from pydantic import BaseModel, EmailStr, ConfigDict, field_validator, ValidationError
from models import User

class Token(BaseModel):
    access_token: str
    token_type: str


class UserBase(BaseModel):
    username: str
    email: EmailStr | None = None
    full_name: str | None = None

class UserOut(UserBase):
    model_config = ConfigDict(from_attributes=True)
    id: int

class NoteBase(BaseModel):
    title: str
    content: str | None = None

class NoteCreate(NoteBase):
    model_config = {"extra": "forbid"}


class NoteRead(NoteBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    author_id: int
    author_username: str