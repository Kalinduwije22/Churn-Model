# ---- Serving image for the churn API ----
# Uses the lean serving requirements so the image stays small, which means
# faster cold starts when Container Apps scales the app up from zero.
FROM python:3.11-slim

# Avoid .pyc files and force unbuffered logs (so logs show up in Azure live).
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app

# Install serving deps first (better layer caching — deps change rarely).
COPY requirements-serve.txt .
RUN pip install --no-cache-dir -r requirements-serve.txt

# Copy only what serving needs: the feature module, the app, the model.
COPY src/ ./src/
COPY app/ ./app/
COPY models/ ./models/

# Run as a non-root user (good practice; some platforms require it).
RUN useradd -m appuser && chown -R appuser /app
USER appuser

EXPOSE 8000

# Container Apps injects $PORT; bind to it. Single worker is plenty for a demo
# and keeps memory low enough for the free tier.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
