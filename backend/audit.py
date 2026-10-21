"""操作审计日志。

认证场景下"谁在什么时候改了哪条记录"必须可追溯，
因此所有写操作都通过 `log_operation()` 落一条 operation_log。
"""
from flask import has_request_context, request

from extensions import db
from models import OperationLog

# 动作常量
ACTION_LOGIN = 'login'
ACTION_LOGIN_FAILED = 'login_failed'
ACTION_LOGOUT = 'logout'
ACTION_CREATE = 'create'
ACTION_UPDATE = 'update'
ACTION_DELETE = 'delete'
ACTION_RESTORE = 'restore'
ACTION_PURGE = 'purge'
ACTION_UPLOAD = 'upload'
ACTION_DOWNLOAD = 'download'
ACTION_REVIEW = 'review'
ACTION_IMPORT = 'import'
ACTION_EXPORT = 'export'
ACTION_MERGE_DICT = 'merge_dict'
ACTION_RESET_PASSWORD = 'reset_password'
ACTION_CHANGE_PASSWORD = 'change_password'
ACTION_BACKUP = 'backup'

ACTION_LABELS = {
    ACTION_LOGIN: '登录',
    ACTION_LOGIN_FAILED: '登录失败',
    ACTION_LOGOUT: '退出登录',
    ACTION_CREATE: '新增',
    ACTION_UPDATE: '修改',
    ACTION_DELETE: '删除',
    ACTION_RESTORE: '恢复',
    ACTION_PURGE: '彻底删除',
    ACTION_UPLOAD: '上传附件',
    ACTION_DOWNLOAD: '下载附件',
    ACTION_REVIEW: '审核',
    ACTION_IMPORT: '批量导入',
    ACTION_EXPORT: '导出',
    ACTION_MERGE_DICT: '合并字典项',
    ACTION_RESET_PASSWORD: '重置密码',
    ACTION_CHANGE_PASSWORD: '修改密码',
    ACTION_BACKUP: '数据备份',
}

TARGET_LABELS = {
    'achievement': '业绩成果',
    'teacher': '教师',
    'student': '学生',
    'user': '账号',
    'attachment': '支撑材料',
    'dict_item': '字典项',
    'indicator': '认证指标点',
    'advisor': '指导关系',
    'system': '系统',
}


def _client_ip():
    if not has_request_context():
        return ''
    forwarded = request.headers.get('X-Forwarded-For', '')
    if forwarded:
        return forwarded.split(',')[0].strip()[:60]
    return (request.remote_addr or '')[:60]


def log_operation(action, target_type=None, target_id=None, summary='', detail=None,
                  user=None, commit=True):
    """写入一条操作日志；失败时不影响主流程。"""
    try:
        if user is None:
            from auth_utils import get_current_user
            try:
                user = get_current_user()
            except Exception:
                user = None
        entry = OperationLog(
            user_id=getattr(user, 'id', None),
            username=getattr(user, 'username', '') or '',
            role=getattr(user, 'role', '') or '',
            action=action,
            target_type=target_type,
            target_id=target_id,
            summary=(summary or '')[:500],
            detail=detail if isinstance(detail, dict) else None,
            ip=_client_ip(),
        )
        db.session.add(entry)
        if commit:
            db.session.commit()
        return entry
    except Exception:  # pragma: no cover - 审计失败不应阻断业务
        db.session.rollback()
        return None


def diff_dict(before, after, fields):
    """返回发生变化的字段 {字段: {'before':…, 'after':…}}，用于审计详情。"""
    changes = {}
    for field in fields:
        old = before.get(field)
        new = after.get(field)
        if old != new:
            changes[field] = {'before': old, 'after': new}
    return changes