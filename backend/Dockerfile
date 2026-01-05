FROM python:3.12-slim

WORKDIR /app
ENV PYTHONPATH=/app

# 依存関係
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリ
COPY app ./app
COPY alembic.ini ./alembic.ini
COPY alembic ./alembic
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
COPY tests ./tests
COPY pytest.ini ./pytest.ini

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
