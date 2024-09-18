import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import os
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

from main import app, create_test_users
from database import get_db
from models import Base, User, Note

TEST_DB_URL = os.environ["TEST_DB_URL"]

engine = create_engine(TEST_DB_URL)
TestingSessionLocal = sessionmaker(autocommit=False,
                                   autoflush=False,
                                   bind=engine)


@pytest.fixture(scope="module")
def test_db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    create_test_users(db)

    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="module")
def client(test_db):

    def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


@pytest.fixture(scope="module")
def access_token(client: TestClient):
    response = client.post("/token",
                           data={
                               "username": 'user1',
                               "password": 'password1'
                           })
    assert response.status_code == 200
    return response.json()["access_token"]


def test_login_success(access_token: str):
    assert access_token is not None


def test_login_fail(client: TestClient):
    response = client.post("/token",
                           data={
                               "username": 'wrong user',
                               "password": "wrong password"
                           })

    assert response.status_code == 401
    assert response.json()['detail'] == "Incorrect username or password"


def test_get_authenticated_user_info(client: TestClient, access_token: str):
    response = client.get("/users/me",
                          headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200
    assert response.json()['username'] == "user1"


def test_get_unauthenticated_user_info(client: TestClient):
    response = client.get("/users/me")
    assert response.status_code == 401


def test_create_note_fail_non_auth(client: TestClient):
    response = client.post("/notes",
                           data={
                               "title": "Some title",
                               "content": "some content"
                           })
    assert response.status_code == 401


def test_create_note_fail_missing_title(client: TestClient, access_token: str):
    response = client.post("/notes",
                           headers={"Authorization": f"Bearer {access_token}"},
                           data={"content": "Some content"},
                           params={"dont_spellcheck": True})
    assert response.status_code == 422


def test_create_note_success_missing_content(client: TestClient,
                                             access_token: str):
    response = client.post("/notes",
                           headers={"Authorization": f"Bearer {access_token}"},
                           data={"title": "Some title"},
                           params={"dont_spellcheck": True})
    assert response.status_code == 201


def test_read_note_fail_non_auth(client: TestClient):
    response = client.get("/notes/1")
    assert response.status_code == 401


def test_read_notes_fail_non_auth(client: TestClient):
    response = client.get("/notes")
    assert response.status_code == 401


def test_create_note_success_no_spellcheck(client: TestClient,
                                           access_token: str):
    response = client.post("/notes",
                           headers={"Authorization": f"Bearer {access_token}"},
                           data={
                               "title": "название запски",
                               "content": "содержание замткеи"
                           },
                           params={"dont_spellcheck": True})
    assert response.status_code == 201
    assert response.json()['title'] == "название запски"
    assert response.json()['content'] == "содержание замткеи"
    assert response.json()['author']['username'] == "user1"


def test_create_note_fail_spellcheck(client: TestClient, access_token: str):
    response = client.post("/notes",
                           headers={"Authorization": f"Bearer {access_token}"},
                           data={
                               "title": "название запски",
                               "content": "содержание замткеи"
                           })
    assert response.status_code == 422


def test_create_note_success_spellcheck(client: TestClient, access_token: str):
    response = client.post("/notes",
                           headers={"Authorization": f"Bearer {access_token}"},
                           data={
                               "title": "название заметки",
                               "content": "содержание заметки"
                           },
                           params={"dont_spellcheck": False})
    assert response.status_code == 201
    assert response.json()['title'] == "название заметки"
    assert response.json()['content'] == "содержание заметки"
    assert response.json()['author']['username'] == "user1"


def test_read_note_fail_wrong_user(client: TestClient):
    response = client.post("/token",
                           data={
                               "username": 'admin',
                               "password": "admin123"
                           })
    access_token = response.json()["access_token"]

    response = client.get("/notes/1",
                          headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 403


def test_read_notes_empty_wrong_user(client: TestClient):
    response = client.post("/token",
                           data={
                               "username": 'admin',
                               "password": "admin123"
                           })
    access_token = response.json()["access_token"]

    response = client.get("/notes",
                          headers={"Authorization": f"Bearer {access_token}"})
    assert response.json() == []
