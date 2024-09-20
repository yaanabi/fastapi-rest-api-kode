You need to have docker installed
git clone this repo
To run webapp type: docker-compose up --build in cmd from project folder
To run tests:

py -m venv myvenv -> activate venv
pip install -r requirements.txt
rename .env.template to .env
pytest from root project folder while docker compose is up
Go to http://127.0.0.1:8000/docs 
hardcoded test users:
1) username: user1, password: password1
2) username: user2, password: password2
3) username: admin, password: admin123
