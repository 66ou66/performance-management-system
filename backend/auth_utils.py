"""认证与授权工具。

在原实现基础上增加了**令牌版本校验**：修改密码、重置密码或调整角色后
`User.token_version` 自增，旧 JWT 立即失效，
解决了原 README 里"修改密码后旧令牌仍能访问"的问题。
"""
from functools import wraps

from flask import current_app, jsonify, request
from flask_jwt_extended import get_jwt, get_jwt_identity, verify_jwt_in_request

from constants import ELEVATED_ROLES, ROLE_ADMIN, ROLE_STUDENT, ROLE_TEACHER
from extensions import db
from models import User

ALL_ROLES = (ROLE_ADMIN, 'reviewer', ROLE_TEACHER, ROLE_STUDENT)

# 首登强制改密时仍然允许访问的接口
PASSWORD_EXEMPT_PATHS = (
    '/api/auth/me',
    '/api/auth/change-password',
    '/api/auth/logout',
)


def decode_identity(identity):
    if identity is None:
        return None
    try:
        return int(identity)
    except (TypeError, ValueError):
        return None


def get_current_user():
    identity = get_jwt_identity()
    user_id = decode_identity(identity)
    if user_id is None:
        return None
    return db.session.get(User, user_id)


def token_version_ok(user):
    """校验 JWT 里的 ver 声明与账号当前令牌版本是否一致。"""
    try:
        claims = get_jwt()
    except RuntimeError:  # pragma: no cover - 无 JWT 上下文
        return True
    if not isinstance(claims, dict):
        return True
    version = claims.get('ver')
    if version is None:
        # 兼容改造前签发的老令牌
        return True
    return int(version) == int(user.token_version or 0)


def _unauthorized(message):
    return jsonify({'code': 401, 'message': message, 'data': None}), 401


def _forbidden(message):
    return jsonify({'code': 403, 'message': message, 'data': None}), 403


def _needs_password_change(user):
    if not user.must_change_password:
        return False
    if not current_app.config.get('FORCE_PASSWORD_CHANGE'):
        return False
    path = request.path or ''
    if path.startswith('/api/auth/login'):
        return False
    return not path.startswith(PASSWORD_EXEMPT_PATHS)


def role_required(*roles):
    """校验 JWT、账号状态、令牌版本与角色，未通过时统一返回 JSON。"""

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            user = get_current_user()
            if user is None or not user.is_active:
                return _unauthorized('登录已失效，请重新登录')
            if not token_version_ok(user):
                return _unauthorized('登录状态已失效（密码或权限已变更），请重新登录')
            if roles and user.role not in roles:
                return _forbidden('没有权限执行该操作')
            if _needs_password_change(user):
                return jsonify({
                    'code': 403,
                    'message': '首次登录请先修改密码',
                    'data': {'must_change_password': True},
                }), 403
            return fn(*args, **kwargs)

        return wrapper

    return decorator


def login_required(fn):
    return role_required(*ALL_ROLES)(fn)


def elevated_required(fn):
    """管理员或审核员：可查看全部数据。"""
    return role_required(*ELEVATED_ROLES)(fn)


def admin_required(fn):
    return role_required(ROLE_ADMIN)(fn)


def review_required(fn):
    """可执行审核动作的角色。"""
    return role_required(ROLE_ADMIN, 'reviewer')(fn)