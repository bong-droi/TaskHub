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
PROJECT_NOT_FOUND = "Project không tồn tại"
ASSIGNEE_NOT_FOUND = "Assignee không tồn tại"

# Auth
PASSWORD_MIN_LENGTH = 8
BCRYPT_MAX_BYTES = 72  # bcrypt chỉ xét 72 byte đầu của mật khẩu
FULL_NAME_MAX_LENGTH = 100
EMAIL_ALREADY_REGISTERED = "Email đã được đăng ký"
INVALID_CREDENTIALS = "Email hoặc mật khẩu không đúng"
ACCOUNT_DISABLED = "Tài khoản đã bị vô hiệu hoá"
ACCOUNT_UNAVAILABLE = "Tài khoản không khả dụng"
INVALID_ACCESS_TOKEN = "Token không hợp lệ hoặc đã hết hạn"
INVALID_REFRESH_TOKEN = "Refresh token không hợp lệ hoặc đã hết hạn"
REFRESH_TOKEN_REVOKED = "Refresh token đã bị thu hồi"
WRONG_CURRENT_PASSWORD = "Mật khẩu hiện tại không đúng"
