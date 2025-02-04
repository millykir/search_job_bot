FROM python:3.12.3-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

RUN pip install --upgrade pip==24.0 && pip install -r requirements.txt

COPY . .

ENV DATABASE_URL=postgresql://job_user:dsNSMm283290nc@db/job_bot

CMD ["./entrypoint.sh"]
