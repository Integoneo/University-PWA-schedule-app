FROM python:3.10-slim
WORKDIR /app


ENV PIP_DEFAULT_TIMEOUT=60
ENV PIP_RETRIES=5
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]
