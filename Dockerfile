FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies
COPY requirements.txt .
RUN python -m pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

ENV PYTHONUNBUFFERED=1

CMD ["python", "moltbot.py"]
