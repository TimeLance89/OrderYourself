FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    DATABASE_PATH=/app/data/order_yourself.db \
    PORT=8000

RUN python - <<'PY'
import sys
assert sys.version_info[:2] == (3, 12), sys.version
print('Using Python', sys.version)
PY

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY static ./static
COPY docker-entrypoint.sh ./docker-entrypoint.sh

RUN chmod +x /app/docker-entrypoint.sh \
    && mkdir -p /app/data

EXPOSE 8000

CMD ["/app/docker-entrypoint.sh"]
