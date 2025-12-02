# ---- Base image ----
FROM python:3.11-slim

# ---- Environment setup ----
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# ---- Set work directory ----
WORKDIR /app

# ---- Install system dependencies ----
RUN apt-get update && apt-get install -y build-essential libpq-dev poppler-utils && rm -rf /var/lib/apt/lists/*
RUN apt-get update && apt-get install -y build-essential libpq-dev poppler-utils tesseract-ocr && rm -rf /var/lib/apt/lists/*

# ---- Copy requirements ----
COPY requirements.txt .

# ---- Install Python dependencies ----
RUN pip install --no-cache-dir -r requirements.txt

# ---- Copy application code ----
COPY . .

# ---- Make entrypoint executable ----
RUN chmod +x entrypoint.sh

# ---- Default command ----
CMD ["./entrypoint.sh"]