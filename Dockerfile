FROM python:3.11-slim AS builder

WORKDIR /build
COPY pyproject.toml poetry.lock ./

RUN pip install --no-cache-dir poetry==2.2.1 \
    && poetry export -f requirements.txt -o requirements.txt --without dev

FROM python:3.11-slim

WORKDIR /app

RUN groupadd --gid 1001 appuser \
    && useradd --uid 1001 --gid appuser --shell /bin/bash appuser

COPY --from=builder /build/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
