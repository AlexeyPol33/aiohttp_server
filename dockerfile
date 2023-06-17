FROM python:latest as builder

WORKDIR /app

COPY ../app /app

COPY ../app/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

FROM nginx:latest

COPY nginx.conf /etc/nginx/nginx.conf

RUN echo "daemon off;" >> /etc/nginx/nginx.conf

FROM builder AS final

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000 \
    WEB_CONCURRENCY=2 \
    DB_USER_NAME=postgres \
    DB_PASSWORD=postgres \
    DB_NAME=test \
    DB_HOST=bd \
    DB_PORT=5432


COPY . /app

RUN ls -l /app

CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:$PORT --workers $WEB_CONCURRENCY main:get_app"]
