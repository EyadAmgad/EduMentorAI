FROM python:3.12-slim-bullseye

# Environment variables
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1 
ENV PYTHONPATH=/app/src
ENV ENVIRONMENT=production
ENV DEBUG=False
ENV TRANSFORMERS_CACHE=/tmp/transformers_cache
ENV HF_HOME=/tmp/huggingface_cache
ENV SENTENCE_TRANSFORMERS_HOME=/tmp/sentence_transformers_cache

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY ./src/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directories with proper permissions for Hugging Face Spaces
RUN mkdir -p /tmp/media/uploads /tmp/media/generated_slides && \
    chmod -R 777 /tmp/media && \
    mkdir -p /tmp/transformers_cache /tmp/huggingface_cache /tmp/sentence_transformers_cache && \
    chmod -R 777 /tmp/transformers_cache /tmp/huggingface_cache /tmp/sentence_transformers_cache

# Run Django setup commands
WORKDIR /app/src
RUN python manage.py collectstatic --noinput --clear

# Create a non-root user for security
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app /tmp/media /tmp/transformers_cache /tmp/huggingface_cache /tmp/sentence_transformers_cache

USER appuser

WORKDIR /app/src
EXPOSE 7860

# Use Gunicorn for production
CMD ["gunicorn", "rag_django.wsgi:application", "--bind", "0.0.0.0:7860", "--workers", "1", "--threads", "1", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-", "--log-level", "info"]

