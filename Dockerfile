FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir redis
COPY app.py /app/