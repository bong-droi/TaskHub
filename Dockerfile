# ============================================================================
# Stage 1: builder - Cài đặt dependencies từ file lock vào /install
# ============================================================================
FROM python:3.12.9-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

COPY requirements.lock .
RUN pip install --no-cache-dir --prefix=/install -r requirements.lock

# ============================================================================
# Stage 2: runtime - Image chạy production nhẹ, bảo mật với non-root user
# ============================================================================
FROM python:3.12.9-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Tạo group và non-root user để không chạy container dưới quyền root
RUN groupadd --gid 1001 appgroup && \
    useradd --uid 1001 --gid appgroup --shell /bin/sh --create-home appuser

WORKDIR /app

# Chỉ copy thư viện đã cài đặt từ stage builder
COPY --from=builder /install /usr/local

# Copy mã nguồn cần thiết (app/, migrations/, scripts/, alembic.ini) và gán quyền sở hữu
COPY --chown=appuser:appgroup app/ ./app/
COPY --chown=appuser:appgroup migrations/ ./migrations/
COPY --chown=appuser:appgroup scripts/ ./scripts/
COPY --chown=appuser:appgroup alembic.ini ./alembic.ini

USER appuser

EXPOSE 8000

# Dùng `exec` để uvicorn thay thế sh làm PID 1, nhận SIGTERM khi `docker stop` và chạy lifespan shutdown
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]
