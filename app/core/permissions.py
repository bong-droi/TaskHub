"""Ma trận quyền theo role trong workspace (một chỗ duy nhất, dễ đọc, dễ test).

| Hành động               | OWNER | EDITOR | VIEWER |
|-------------------------|:-----:|:------:|:------:|
| Xem workspace/project/task |  x  |   x    |   x    |
| Tạo/sửa project, task   |   x   |   x    |        |
| Archive project         |   x   |   x    |        |
| Xoá task                |  mọi task | task do mình tạo |  |
| Sửa/xoá workspace, xoá project, quản lý thành viên | x | | |

User có role toàn hệ thống ADMIN được coi như OWNER của mọi workspace.
"""

from app.models.enums import WorkspaceRole

READ_ROLES = frozenset(WorkspaceRole)
WRITE_ROLES = frozenset({WorkspaceRole.OWNER, WorkspaceRole.EDITOR})
MANAGE_ROLES = frozenset({WorkspaceRole.OWNER})
