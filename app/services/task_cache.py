"""Cache danh sách task theo project (GET /projects/{id}/tasks).

Chiến lược: **version counter theo project** thay vì xoá key theo pattern.
  - Mỗi project có một số phiên bản `tasks:ver:{project_id}`.
  - Key dữ liệu chứa số phiên bản hiện tại: `tasks:p{id}:v{ver}:{bộ lọc}`.
  - Task/label của project đổi -> `invalidate()` tăng phiên bản (INCR, O(1)) -> mọi key cũ tự
    "mồ côi", không ai đọc tới nữa và hết hạn theo TTL. Không cần SCAN/KEYS (chậm, chặn Redis).

Quy tắc an toàn:
  1. Kiểm tra QUYỀN trước, rồi mới đụng cache -> dữ liệu trong cache dùng chung được vì ai
     tới được đây đều đã có quyền xem project.
  2. Đọc phiên bản TRƯỚC khi query DB và ghi cache dưới đúng phiên bản đó. Nếu có ghi xen giữa,
     dữ liệu cũ nằm dưới phiên bản cũ (không ai đọc), không bao giờ đè lên dữ liệu mới.
  3. Redis lỗi/chết -> ghi cảnh báo rồi chạy tiếp bằng DB; cache chỉ là tối ưu, không được
     làm API hỏng.
"""

import logging
from dataclasses import dataclass
from typing import Literal

from app.core.cache import CacheBackend
from app.models.enums import TaskPriority, TaskStatus
from app.schemas.common import Page
from app.schemas.task import TaskRead

logger = logging.getLogger("taskhub.cache")

# Key version phải sống lâu hơn mọi key dữ liệu của nó (nếu version hết hạn rồi reset về 0 thì
# key dữ liệu cũ có thể "sống lại"). Key dữ liệu sống tối đa CACHE_TTL_SECONDS (mặc định 60s).
VERSION_TTL_SECONDS = 24 * 60 * 60

CacheStatus = Literal["HIT", "MISS", "BYPASS"]


@dataclass(frozen=True)
class TaskListParams:
    page: int
    limit: int
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    assignee_id: int | None = None
    label_id: int | None = None

    @property
    def skip(self) -> int:
        return (self.page - 1) * self.limit

    @property
    def key_part(self) -> str:
        def v(x) -> str:
            return "*" if x is None else str(getattr(x, "value", x))

        return (
            f"status={v(self.status)}&priority={v(self.priority)}&assignee={v(self.assignee_id)}"
            f"&label={v(self.label_id)}&page={self.page}&limit={self.limit}"
        )


@dataclass(frozen=True)
class TaskListResult:
    page: Page[TaskRead]
    cache: CacheStatus


class TaskListCache:
    def __init__(self, backend: CacheBackend, ttl: int) -> None:
        self.backend = backend
        self.ttl = ttl

    @property
    def enabled(self) -> bool:
        return self.backend.enabled

    @staticmethod
    def _version_key(project_id: int) -> str:
        return f"tasks:ver:{project_id}"

    @staticmethod
    def _data_key(project_id: int, version: int, params: TaskListParams) -> str:
        return f"tasks:p{project_id}:v{version}:{params.key_part}"

    async def version(self, project_id: int) -> int:
        try:
            raw = await self.backend.get(self._version_key(project_id))
            return int(raw) if raw else 0
        except Exception:
            logger.warning("Cache: đọc version lỗi, bỏ qua cache", exc_info=True)
            return 0

    async def get(
        self, project_id: int, version: int, params: TaskListParams
    ) -> Page[TaskRead] | None:
        try:
            raw = await self.backend.get(self._data_key(project_id, version, params))
            return Page[TaskRead].model_validate_json(raw) if raw else None
        except Exception:
            logger.warning("Cache: đọc lỗi, chạy bằng DB", exc_info=True)
            return None

    async def set(
        self, project_id: int, version: int, params: TaskListParams, page: Page[TaskRead]
    ) -> None:
        try:
            await self.backend.set(
                self._data_key(project_id, version, params), page.model_dump_json(), self.ttl
            )
        except Exception:
            logger.warning("Cache: ghi lỗi, bỏ qua", exc_info=True)

    async def invalidate(self, project_id: int) -> None:
        """Gọi SAU KHI đã commit thay đổi (task, label gắn trên task, tên/màu label...)."""
        try:
            await self.backend.incr(self._version_key(project_id), VERSION_TTL_SECONDS)
        except Exception:
            # Không làm hỏng thao tác ghi đã thành công; dữ liệu cũ tối đa tồn tại đến hết TTL
            logger.warning("Cache: vô hiệu hoá lỗi, dữ liệu cũ tối đa %ss", self.ttl, exc_info=True)
