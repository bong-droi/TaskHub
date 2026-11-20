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

# Workspace / Project
NAME_MIN_LENGTH = 1
WORKSPACE_NAME_MAX_LENGTH = 100
PROJECT_NAME_MAX_LENGTH = 100
PROJECT_DESCRIPTION_MAX_LENGTH = 2000
WORKSPACE_NOT_FOUND = "Workspace không tồn tại"
PROJECT_ARCHIVED = "Project đã được archive, không thể thay đổi"
USER_NOT_FOUND = "Người dùng không tồn tại"
MEMBER_NOT_FOUND = "Thành viên không tồn tại trong workspace"
ALREADY_MEMBER = "Người dùng đã là thành viên của workspace"
CANNOT_REMOVE_OWNER = "Không thể xoá owner khỏi workspace"
CANNOT_INVITE_OWNER_ROLE = "Không thể mời thành viên với role OWNER"
ASSIGNEE_NOT_IN_WORKSPACE = "Assignee không phải thành viên của workspace"

# Phân quyền
INSUFFICIENT_PERMISSION = "Bạn không có quyền thực hiện thao tác này"

# Label / Comment
LABEL_NAME_MAX_LENGTH = 50
DEFAULT_LABEL_COLOR = "#808080"
LABEL_COLOR_PATTERN = r"^#[0-9A-Fa-f]{6}$"
COMMENT_MAX_LENGTH = 2000
LABEL_NOT_FOUND = "Label không tồn tại"
LABEL_NAME_EXISTS = "Tên label đã tồn tại trong project"
LABEL_NOT_IN_PROJECT = "Label không thuộc project của task"
COMMENT_NOT_FOUND = "Comment không tồn tại"

# Lỗi hệ thống
INTERNAL_ERROR = "Lỗi hệ thống, vui lòng thử lại sau"
DATA_CONFLICT = "Dữ liệu xung đột với dữ liệu hiện có"
