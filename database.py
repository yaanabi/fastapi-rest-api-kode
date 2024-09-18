from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

DB_URL = os.getenv("DB_URL")
engine = create_engine(DB_URL)
SessionDB = sessionmaker(autocommit=False, autoflush=False, bind=engine)  


def get_db():
    db = SessionDB()
    try:
        yield db
    finally:
        db.close()