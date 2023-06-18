FROM python:latest as builder

WORKDIR /app

COPY ../app /app

COPY ../app/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

FROM nginx:latest

COPY nginx.conf /etc/nginx/nginx.conf

RUN echo "daemon off;" >> /etc/nginx/nginx.conf

FROM builder AS final

COPY . /app

RUN ls -l /app

ENTRYPOINT sh ./entrypoint.sh
