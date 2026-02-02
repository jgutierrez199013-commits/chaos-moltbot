install:
	python -m pip install -r requirements.txt

test:
	pytest -q

run:
	python moltbot.py

build:
	docker build -t moltbot:latest .
