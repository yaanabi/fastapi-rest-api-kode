from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.orm import relationship, DeclarativeBase


class Base(DeclarativeBase):    
    pass


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True)
    password = Column(String, nullable=False)

    def __repr__(self):
        return f"{self.username}"



class Note(Base):
    __tablename__ = "notes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String)
    content = Column(String, nullable=True)
    author_id = Column(Integer, ForeignKey("users.id"))
    author = relationship("User", back_populates="notes")

User.notes = relationship("Note", back_populates="author")