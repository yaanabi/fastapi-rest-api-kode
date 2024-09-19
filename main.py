from typing import Annotated
from pydantic import BaseModel, ValidationError

from fastapi.responses import RedirectResponse
from fastapi import FastAPI, Depends, HTTPException, status, Form
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from jose import JWTError, jwt, ExpiredSignatureError


from auth import *
from database import get_db, engine
from schemas import Token, UserOut, NoteRead, NoteCreate
from models import Base, User, Note
from spell_check_utils import spell_check

app = FastAPI()

Base.metadata.create_all(bind=engine)


def create_test_users(db):

    test_users = [
        {
            "username": "user1",
            "password": pwd_context.hash("password1")
        },
        {
            "username": "user2",
            "password": pwd_context.hash("password2")
        },
        {
            "username": "admin",
            "password": pwd_context.hash("admin123")
        },
    ]

    for user_data in test_users:
        if not db.query(User).filter(
                User.username == user_data["username"]).first():
            user = User(username=user_data["username"],
                        password=user_data["password"])
            db.add(user)
            db.commit()


create_test_users(next(get_db()))


async def spellcheck_note(note: NoteCreate):
    spelling_errors = await spell_check(note.title + " " + (note.content or ''))
    if spelling_errors:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Spelling errors found: " +
            ";".join(map(str, spelling_errors)),
        )




def get_current_user(token: str = Depends(oauth2_scheme),
                     db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    user_not_found_exception = HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="User not found",
    )
    jwt_expired_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token expired",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except ExpiredSignatureError:
        raise jwt_expired_exception
    except JWTError:
        raise credentials_exception
    user = get_user(db, username=username)
    if user is None:
        raise user_not_found_exception
    return user


@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/docs")


@app.post("/token")
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm,
                         Depends()],
    db: Session = Depends(get_db)
) -> Token:
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user.username},
                                       expires_delta=access_token_expires)
    return Token(access_token=access_token, token_type="bearer")


@app.get("/users/me", response_model=UserOut)
async def get_authenticated_user_info(
        current_user: Annotated[User, Depends(get_current_user)]):
    return current_user


@app.post("/notes/",
          response_model=NoteRead,
          status_code=status.HTTP_201_CREATED)
async def create_note(note: Annotated[NoteCreate, Form()],
                      current_user: Annotated[User,
                                              Depends(get_current_user)],
                      db: Session = Depends(get_db),
                      dont_spellcheck: bool | None = None) -> Note:
    if not dont_spellcheck:
        await spellcheck_note(note)
    note = Note(title=note.title,
                content=note.content,
                author_id=current_user.id)
    db.add(note)
    db.commit()
    db.refresh(note)
    note_to_return = NoteRead(id=note.id,
                              title=note.title,
                              content=note.content,
                              author_id=note.author_id,
                              author_username=note.author.username)
    return note_to_return


@app.get("/notes/", response_model=list[NoteRead])
async def get_notes(current_user: Annotated[User,
                                            Depends(get_current_user)],
                    db: Session = Depends(get_db)):
    return [
        NoteRead(id=note.id,
                 title=note.title,
                 content=note.content,
                 author_id=note.author_id,
                 author_username=note.author.username)
        for note in db.query(Note).filter(
            Note.author_id == current_user.id).all()
    ]


@app.get("/notes/{note_id}", response_model=NoteRead)
async def get_note(note_id: int,
                   current_user: Annotated[User,
                                           Depends(get_current_user)],
                   db: Session = Depends(get_db)):
    note = db.query(Note).filter(Note.id == note_id).first()
    if not note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Note not found")
    if note.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this note")
    note_to_return = NoteRead(id=note.id,
                              title=note.title,
                              content=note.content,
                              author_id=note.author_id,
                              author_username=note.author.username)
    return note_to_return


@app.put("/notes/{note_id}", response_model=NoteRead)
async def update_note(note_id: int,
                      note: Annotated[NoteCreate, Form()],
                      current_user: Annotated[User,
                                              Depends(get_current_user)],
                      db: Session = Depends(get_db),
                      dont_spellcheck: bool | None = None):
    note_in_db = db.query(Note).filter(Note.id == note_id).first()
    if not note_in_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Note not found")
    if note_in_db.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to update this note")
    if not dont_spellcheck:
        spelling_errors = await spell_check(note.title + " " + note.content)
        if spelling_errors:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Spelling errors found: " +
                ";".join(map(str, spelling_errors)),
            )
    note_in_db.title = note.title
    note_in_db.content = note.content
    db.commit()
    db.refresh(note_in_db)
    note_to_return = NoteRead(id=note_in_db.id,
                              title=note_in_db.title,
                              content=note_in_db.content,
                              author_id=note_in_db.author_id,
                              author_username=note_in_db.author.username)
    return note_to_return


@app.delete("/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(note_id: int,
                      current_user: Annotated[User,
                                              Depends(get_current_user)],
                      db: Session = Depends(get_db)):
    note = db.query(Note).filter(Note.id == note_id).first()
    if not note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Note not found")
    if note.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to delete this note")
    db.delete(note)
    db.commit()
