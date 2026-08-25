FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

VOLUME ["/app/bdd", "/app/upload"]

COPY . .

# Initialise la base de données SQLite au démarrage
ENV FLASK_APP=app.py
EXPOSE 5100

ARG APP_VERSION=dev
ENV APP_VERSION=${APP_VERSION}

CMD ["flask", "run", "--host=0.0.0.0", "--port=5100"]
