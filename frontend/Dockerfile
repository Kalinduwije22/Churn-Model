# ---- Streamlit frontend image ----
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8501

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

RUN useradd -m appuser && chown -R appuser /app
USER appuser

EXPOSE 8501

# Bind to all interfaces and the Container Apps port. Headless mode + disabling
# CORS/XSRF avoids issues when running behind the Container Apps HTTPS proxy.
CMD ["sh", "-c", "streamlit run app.py --server.port=${PORT} --server.address=0.0.0.0 --server.headless=true --server.enableCORS=false --server.enableXsrfProtection=false"]
