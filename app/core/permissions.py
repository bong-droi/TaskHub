"""Ma trận quyền theo role trong workspace (một chỗ duy nhất, dễ đọc, dễ test).

| Hành động               | OWNER | EDITOR | VIEWER |
|-------------------------|:-----:|:------:|:------:|
| Xem workspace/project/task |  x  |   x    |   x    |
| Tạo/sửa project, task   |   x   |   x    |        |
| Archive project         |   x   |   x    |        |
| Xoá task                |  mọi task | task do mình tạo |  |
| Xoá comment             | mọi comment | comment của mình | comment của mình |
| Sửa/xoá workspace, xoá project, quản lý thành viên | x | | |

User có role toàn hệ thống ADMIN được coi như OWNER của mọi workspace.

Quy tắc đơn giản là tập role (READ/WRITE/MANAGE_ROLES). Quy tắc phụ thuộc vào resource
(ai tạo task, ai viết comment) là các hàm `can_*` bên dưới. Service KHÔNG tự viết điều kiện
phân quyền, chỉ gọi các hằng/hàm ở đây, để file này luôn là nguồn sự thật duy nhất.
"""

from typing import TYPE_CHECKING

from app.models.enums import WorkspaceRole

if TYPE_CHECKING:
    from app.models import Comment, Task, User

READ_ROLES = frozenset(WorkspaceRole)
WRITE_ROLES = frozenset({WorkspaceRole.OWNER, WorkspaceRole.EDITOR})
MANAGE_ROLES = frozenset({WorkspaceRole.OWNER})


def can_delete_task(role: WorkspaceRole, task: "Task", user: "User") -> bool:
    """OWNER xoá mọi task; EDITOR chỉ xoá task do chính mình tạo; VIEWER không xoá được.

    Task có `created_by = None` (người tạo đã bị xoá) chỉ OWNER mới xoá được."""
    if role == WorkspaceRole.OWNER:
        return True
    return role == WorkspaceRole.EDITOR and task.created_by == user.id


def can_delete_comment(role: WorkspaceRole, comment: "Comment", user: "User") -> bool:
    """OWNER xoá mọi comment; người khác chỉ xoá comment do chính mình viết."""
    return role == WorkspaceRole.OWNER or comment.author_id == user.id
