FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install Python dependencies.
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copy FastAPI application.
COPY main.py .
COPY backend/ ./backend/

# Use a non-root user.
RUN useradd --create-home --uid 10001 appuser

USER appuser

EXPOSE 8080

# Cloud Run supplies PORT at runtime.
CMD ["sh", "-c", "exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080} --workers 1"]