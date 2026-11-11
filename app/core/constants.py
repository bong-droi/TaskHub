"""Hằng số dùng chung: không viết số/chuỗi cứng rải rác trong schema, service, router."""

# Validation
TITLE_MIN_LENGTH = 1
TITLE_MAX_LENGTH = 200
DESCRIPTION_MAX_LENGTH = 2000

# Pagination
DEFAULT_PAGE_LIMIT = 20
MAX_PAGE_LIMIT = 100

# Thông báo lỗi
TASK_NOT_FOUND = "Task không tồn tại"
