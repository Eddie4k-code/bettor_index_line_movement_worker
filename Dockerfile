FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=UTC

WORKDIR /app

COPY requirements.txt .
RUN grep -v '^psycopg2==' requirements.txt > requirements-docker.txt \
    && pip install --no-cache-dir psycopg2-binary==2.9.12 \
    && pip install --no-cache-dir -r requirements-docker.txt

COPY . .

CMD ["python", "main.py"]
