FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    DATABASE_PATH=/app/data/order_yourself.db \
    PORT=8000

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY static ./static
COPY start.sh ./start.sh

RUN chmod +x /app/start.sh \
    && mkdir -p /app/data

EXPOSE 8000

CMD ["/app/start.sh"]
