# ============================================================================
# Stage 1: builder - Cài đặt dependencies vào thư mục tách biệt /install
# ============================================================================
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ============================================================================
# Stage 2: runtime - Image chạy production nhẹ, bảo mật với non-root user
# ============================================================================
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Tạo group appgroup và user appuser (UID 1001) để không chạy container dưới quyền root
RUN groupadd --gid 1001 appgroup && \
    useradd --uid 1001 --gid appgroup --shell /bin/sh --create-home appuser

WORKDIR /app

# Chỉ copy thư viện đã cài đặt từ stage builder
COPY --from=builder /install /usr/local

# Copy mã nguồn cần thiết (app/, migrations/ - alembic/, alembic.ini) và gán quyền sở hữu
COPY --chown=appuser:appgroup app/ ./app/
COPY --chown=appuser:appgroup migrations/ ./migrations/
COPY --chown=appuser:appgroup scripts/ ./scripts/
COPY --chown=appuser:appgroup alembic.ini ./alembic.ini

USER appuser

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
