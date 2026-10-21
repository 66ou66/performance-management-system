from datetime import datetime

from flask import Blueprint, current_app, request
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    get_jwt_identity,
    jwt_required,
)

from audit import (
    ACTION_CHANGE_PASSWORD,
    ACTION_LOGIN,
    ACTION_LOGIN_FAILED,
    ACTION_LOGOUT,
    log_operation,
)
from auth_utils import get_current_user, login_required
from constants import ROLE_LABELS
from extensions import db
from models import Student, Teacher, User
from security import login_throttle, normalize_text, validate_password
from utils import error, success

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')


def build_user_payload(user):
    payload = user.to_dict()
    profile = None
    advisors = []
    if user.owner_type == 'teacher':
        teacher = db.session.get(Teacher, user.owner_id)
        profile = teacher.to_dict() if teacher else None
    elif user.owner_type == 'student':
        student = db.session.get(Student, user.owner_id)
        profile = student.to_dict() if student else None
        if profile:
            advisors = profile.get('advisors', [])
    payload['profile'] = profile
    payload['advisors'] = advisors
    payload['role_label'] = ROLE_LABELS.get(user.role, user.role)
    return payload


def _issue_tokens(user):
    claims = {'ver': int(user.token_version or 0), 'role': user.role}
    access_token = create_access_token(identity=str(user.id), additional_claims=claims)
    refresh_token = create_refresh_token(identity=str(user.id), additional_claims=claims)
    return access_token, refresh_token


@auth_bp.post('/login')
def login():
    data = request.get_json(silent=True) or {}
    username = normalize_text(data.get('username'))
    password = data.get('password') or ''
    if not username or not password:
        return error('请输入用户名和密码')

    config = current_app.config
    max_attempts = config['LOGIN_MAX_ATTEMPTS']
    window = config['LOGIN_WINDOW_SECONDS']
    lock_seconds = config['LOGIN_LOCK_SECONDS']
    throttle_key = username.lower()

    allowed, remaining = login_throttle.check(throttle_key, max_attempts, window)
    if not allowed:
        log_operation(ACTION_LOGIN_FAILED, 'user', None,
                      f'账号 {username} 因多次失败被锁定', user=None)
        if remaining:
            return error(f'登录失败次数过多，请在 {remaining} 秒后重试',
                         status=429, code=429)
        return error('登录失败次数过多，请稍后重试', status=429, code=429)

    user = User.query.filter_by(username=username).first()
    if user is None or not user.check_password(password):
        locked_for = login_throttle.record_failure(throttle_key, max_attempts,
                                                   window, lock_seconds)
        log_operation(ACTION_LOGIN_FAILED, 'user', getattr(user, 'id', None),
                      f'登录名 {username} 校验失败', user=None)
        if locked_for:
            return error(f'登录失败次数过多，账号已锁定 {locked_for} 秒',
                         status=429, code=429)
        return error('用户名或密码错误', status=401, code=401)
    if not user.is_active:
        log_operation(ACTION_LOGIN_FAILED, 'user', user.id,
                      f'已禁用账号 {username} 尝试登录', user=None)
        return error('账号已被禁用，请联系管理员', status=403, code=403)

    login_throttle.reset(throttle_key)
    user.last_login_at = datetime.now()
    db.session.commit()
    access_token, refresh_token = _issue_tokens(user)
    log_operation(ACTION_LOGIN, 'user', user.id, f'{username} 登录成功', user=user)
    return success({
        'access_token': access_token,
        'refresh_token': refresh_token,
        'expires_in': int(current_app.config['JWT_ACCESS_TOKEN_EXPIRES'].total_seconds()),
        'user': build_user_payload(user),
    }, '登录成功')


@auth_bp.post('/refresh')
@jwt_required(refresh=True)
def refresh():
    user = get_current_user()
    if user is None or not user.is_active:
        return error('登录已失效，请重新登录', status=401, code=401)
    identity = get_jwt_identity()
    claims = {'ver': int(user.token_version or 0), 'role': user.role}
    access_token = create_access_token(identity=identity, additional_claims=claims)
    return success({
        'access_token': access_token,
        'user': build_user_payload(user),
    }, '令牌已刷新')


@auth_bp.get('/me')
@login_required
def me():
    return success(build_user_payload(get_current_user()))


@auth_bp.post('/logout')
@login_required
def logout():
    user = get_current_user()
    log_operation(ACTION_LOGOUT, 'user', user.id, f'{user.username} 退出登录', user=user)
    return success(None, '已退出登录')


@auth_bp.post('/change-password')
@login_required
def change_password():
    user = get_current_user()
    data = request.get_json(silent=True) or {}
    old_password = data.get('old_password') or ''
    new_password = data.get('new_password') or ''
    if not user.check_password(old_password):
        return error('原密码不正确')
    if user.check_password(new_password):
        return error('新密码不能与原密码相同')
    ok, message = validate_password(
        new_password,
        current_app.config['MIN_PASSWORD_LENGTH'],
        current_app.config.get('PASSWORD_STRENGTH_CHECK', False),
    )
    if not ok:
        return error(message)
    user.set_password(new_password)
    user.must_change_password = False
    # 令牌版本自增：该账号此前签发的所有 JWT 立即失效
    user.bump_token_version()
    db.session.commit()
    access_token, refresh_token = _issue_tokens(user)
    log_operation(ACTION_CHANGE_PASSWORD, 'user', user.id, '修改登录密码', user=user)
    return success({
        'access_token': access_token,
        'refresh_token': refresh_token,
        'user': build_user_payload(user),
    }, '密码修改成功，其他设备上的登录已失效')