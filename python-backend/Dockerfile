FROM python:3.10-slim
WORKDIR /app

ENV PYTHONUNBUFFERED=1

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# При IS_PRODUCTION=True отключается access-log, иначе запускается со стандартными логами
CMD ["sh", "-c", "if [ \"$IS_PRODUCTION\" = 'True' ] || [ \"$IS_PRODUCTION\" = 'true' ]; then \
  exec uvicorn main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips '*' --no-access-log; \
  else \
  exec uvicorn main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips '*'; \
  fi"]
