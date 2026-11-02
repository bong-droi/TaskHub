from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health", summary="Kiểm tra trạng thái service")
def health() -> dict[str, str]:
    return {"status": "ok"}
