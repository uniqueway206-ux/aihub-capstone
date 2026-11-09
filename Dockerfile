FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app/src
WORKDIR /app
RUN useradd -m appuser
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src ./src
COPY scripts ./scripts
RUN mkdir -p data && python scripts/seed_demo_db.py && chown -R appuser:appuser /app
USER appuser
EXPOSE 8000 8501
HEALTHCHECK CMD python -c "import urllib.request as u; u.urlopen('http://localhost:8000/health')" || exit 1
CMD ["gunicorn", "-w", "2", "--threads", "4", "-t", "120", "-b", "0.0.0.0:8000", "aihub.api.app:app_factory()"]
