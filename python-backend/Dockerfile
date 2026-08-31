FROM python:3.10-slim
WORKDIR /app

# Настройка зеркала для pip
ENV PIP_EXTRA_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
ENV PIP_TRUSTED_HOST=pypi.tuna.tsinghua.edu.cn
ENV PIP_DEFAULT_TIMEOUT=60
ENV PIP_RETRIES=10
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip && \
  pip install --no-cache-dir -r requirements.txt

COPY . .

# При IS_PRODUCTION=True отключается access-log, иначе запускается со стандартными логами
CMD ["sh", "-c", "if [ \"$IS_PRODUCTION\" = 'True' ] || [ \"$IS_PRODUCTION\" = 'true' ]; then \
  exec uvicorn main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips '*' --no-access-log; \
  else \
  exec uvicorn main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips '*'; \
  fi"]
