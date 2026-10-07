FROM python:3.12-slim

# Create a non-root user with UID 1000 required by Hugging Face Spaces
RUN useradd -m -u 1000 user

WORKDIR /home/user/app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY --chown=user:user requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files with appropriate ownership
COPY --chown=user:user . .

# Ensure storage directories exist and are writable by UID 1000
RUN mkdir -p /home/user/app/database /home/user/app/exports /home/user/app/data && \
    chown -R user:user /home/user/app

USER user

ENV PORT=7860 \
    PYTHONUNBUFFERED=1

EXPOSE 7860

CMD ["python3", "app.py", "7860"]
