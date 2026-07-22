FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /app/packages/data-python

RUN pip install --no-cache-dir \
    psycopg2-binary==2.9.12 \
    python-dotenv==1.2.2

COPY packages/data-python/config.py packages/data-python/runtime_mode.py ./
COPY packages/data-python/scripts/seed_sample_data.py scripts/seed_sample_data.py
COPY sample-data /app/sample-data

ENTRYPOINT ["python", "scripts/seed_sample_data.py", "--fixture-dir", "/app/sample-data/v1"]
