from flask import Blueprint, current_app, request
from sqlalchemy import or_

from accounts import create_account, detach_user, set_owner, sync_user_links
from audit import (
    ACTION_CREATE,
    ACTION_DELETE,
    ACTION_RESET_PASSWORD,
    ACTION_UPDATE,
    diff_dict,
    log_operation,
)
from auth_utils import admin_required, get_current_user
from constants import ROLE_ADMIN, ROLE_REVIEWER, ROLE_STUDENT, ROLE_TEACHER, ROLE_LABELS
from extensions import db
from models import Student, Teacher, User
from security import normalize_text, validate_password
from utils import error, get_page_args, paginate, parse_bool, parse_int, success
from validators import validate_user

admin_bp = Blueprint('admin', __name__, url_prefix='/api')

EDITABLE_FIELDS = ('username', 'role', 'owner_type', 'owner_id', 'is_active',
                   'must_change_password')


def _linked_owner_ids(owner_type):
    return {u.owner_id for u in User.query.filter_by(owner_type=owner_type).all() if u.owner_id}


@admin_bp.get('/users', strict_slashes=False)
@admin_required
def list_users():
    keyword = normalize_text(request.args.get('keyword'))
    role = normalize_text(request.args.get('role'))
    status = request.args.get('status')
    linked = request.args.get('linked')

    query = User.query
    if keyword:
        like = f'%{keyword}%'
        owner_teacher_ids = [row.id for row in Teacher.query.filter(Teacher.name.like(like)).all()]
        owner_student_ids = [row.id for row in Student.query.filter(Student.name.like(like)).all()]
        query = query.filter(or_(
            User.username.like(like),
            User.owner_id.in_(owner_teacher_ids or [-1]),
            User.owner_id.in_(owner_student_ids or [-1]),
        ))
    if role:
        query = query.filter(User.role == role)
    if status in ('0', '1'):
        query = query.filter(User.is_active == (status == '1'))
    if linked in ('0', '1'):
        has_owner = User.owner_type.isnot(None)
        query = query.filter(has_owner if linked == '1' else ~has_owner)
    query = query.order_by(User.id.desc())
    page, page_size = get_page_args()
    return success(paginate(query, page, page_size))


@admin_bp.get('/users/candidates')
@admin_required
def candidates():
    role = normalize_text(request.args.get('role'))
    items = []
    if role == ROLE_TEACHER:
        linked = _linked_owner_ids(ROLE_TEACHER)
        for teacher in Teacher.query.order_by(Teacher.id).all():
            if teacher.id not in linked:
                items.append({
                    'id': teacher.id, 'name': teacher.name,
                    'label': f'{teacher.name}（{teacher.department or "未设院系"}）',
                })
    elif role == ROLE_STUDENT:
        linked = _linked_owner_ids(ROLE_STUDENT)
        for student in Student.query.order_by(Student.id).all():
            if student.id not in linked:
                items.append({
                    'id': student.id, 'name': student.name,
                    'label': f'{student.name}（{student.student_no}）',
                })
    return success(items)


@admin_bp.post('/users', strict_slashes=False)
@admin_required
def create_user():
    data = request.get_json(silent=True) or {}
    payload, message = validate_user(
        data,
        min_password=current_app.config['MIN_PASSWORD_LENGTH'],
        strength_check=current_app.config.get('PASSWORD_STRENGTH_CHECK', False),
    )
    if message:
        return error(message)
    username = payload['username']
    role = payload['role']
    if User.query.filter_by(username=username).first():
        return error('登录名已存在')

    owner_type = None
    owner_id = None
    if role in (ROLE_TEACHER, ROLE_STUDENT):
        owner_type = role
        owner_id = parse_int(data.get('owner_id'))
        person = db.session.get(Teacher if role == ROLE_TEACHER else Student, owner_id) \
            if owner_id else None
        if person is None:
            return error('请选择关联人员')
        if User.query.filter_by(owner_type=owner_type, owner_id=owner_id).first():
            return error('该人员已关联账号')

    user = create_account(
        username, payload['password'], role,
        owner_type=owner_type, owner_id=owner_id,
        must_change_password=parse_bool(
            data.get('must_change_password'),
            current_app.config.get('FORCE_PASSWORD_CHANGE', False),
        ),
    )
    db.session.commit()
    log_operation(ACTION_CREATE, 'user', user.id,
                  f'新增账号 {username}（{ROLE_LABELS.get(role, role)}）')
    return success(user.to_dict(), '账号创建成功')


@admin_bp.put('/users/<int:user_id>')
@admin_required
def update_user(user_id):
    current = get_current_user()
    user = db.session.get(User, user_id)
    if user is None:
        return error('账号不存在', status=404, code=404)
    data = request.get_json(silent=True) or {}

    role = normalize_text(data.get('role')) or user.role
    if role not in (ROLE_ADMIN, ROLE_REVIEWER, ROLE_TEACHER, ROLE_STUDENT):
        return error('角色不合法')
    if user.id == current.id and role != ROLE_ADMIN:
        return error('不能修改当前登录账号的管理员角色')
    if user.role == ROLE_ADMIN and role != ROLE_ADMIN:
        remaining = User.query.filter(User.role == ROLE_ADMIN, User.id != user.id).count()
        if remaining == 0:
            return error('系统必须保留至少一个管理员账号')

    before = user.to_dict()
    user.role = role
    if role in (ROLE_TEACHER, ROLE_STUDENT):
        default_owner = user.owner_id if user.owner_type == role else None
        owner_id = parse_int(data.get('owner_id'), default_owner)
        person = db.session.get(Teacher if role == ROLE_TEACHER else Student, owner_id) \
            if owner_id else None
        if person is None:
            return error('请选择关联人员')
        exists = User.query.filter_by(owner_type=role, owner_id=owner_id) \
            .filter(User.id != user.id).first()
        if exists:
            return error('该人员已关联其他账号')
        set_owner(user, role, owner_id)
    else:
        detach_user(user)

    db.session.commit()
    after = user.to_dict()
    changes = diff_dict(before, after, EDITABLE_FIELDS)
    log_operation(ACTION_UPDATE, 'user', user.id,
                  f'修改账号 {user.username}',
                  detail={'changes': changes} if changes else None)
    return success(after, '账号信息已更新')


@admin_bp.put('/users/<int:user_id>/status')
@admin_required
def update_user_status(user_id):
    current = get_current_user()
    user = db.session.get(User, user_id)
    if user is None:
        return error('账号不存在', status=404, code=404)
    if user.id == current.id:
        return error('不能禁用当前登录账号')
    data = request.get_json(silent=True) or {}
    value = parse_bool(data.get('is_active', True), True)
    user.is_active = value
    if not value:
        # 禁用即让该账号已签发的令牌全部失效
        user.bump_token_version()
    db.session.commit()
    log_operation(ACTION_UPDATE, 'user', user.id,
                  f'{"启用" if value else "禁用"}账号 {user.username}')
    return success(user.to_dict(), '账号状态已更新')


@admin_bp.post('/users/<int:user_id>/reset-password')
@admin_required
def reset_password(user_id):
    user = db.session.get(User, user_id)
    if user is None:
        return error('账号不存在', status=404, code=404)
    data = request.get_json(silent=True) or {}
    new_password = data.get('new_password') or ''
    ok, message = validate_password(
        new_password,
        current_app.config['MIN_PASSWORD_LENGTH'],
        current_app.config.get('PASSWORD_STRENGTH_CHECK', False),
    )
    if not ok:
        return error(message)
    user.set_password(new_password)
    user.must_change_password = parse_bool(data.get('must_change_password')) \
        or current_app.config.get('FORCE_PASSWORD_CHANGE', False)
    user.bump_token_version()
    db.session.commit()
    log_operation(ACTION_RESET_PASSWORD, 'user', user.id,
                  f'重置账号 {user.username} 的密码')
    return success(None, '密码重置成功，该账号其他登录已失效')


@admin_bp.delete('/users/<int:user_id>')
@admin_required
def remove_user(user_id):
    current = get_current_user()
    user = db.session.get(User, user_id)
    if user is None:
        return error('账号不存在', status=404, code=404)
    if user.id == current.id:
        return error('不能删除当前登录账号')
    if user.role == ROLE_ADMIN:
        remaining = User.query.filter(User.role == ROLE_ADMIN, User.id != user.id).count()
        if remaining == 0:
            return error('系统必须保留至少一个管理员账号')
    username = user.username
    detach_user(user)
    db.session.delete(user)
    db.session.commit()
    log_operation(ACTION_DELETE, 'user', user_id, f'删除账号 {username}')
    return success(None, f'账号 {username} 已删除（人员档案保留）')


@admin_bp.post('/users/<int:user_id>/unbind')
@admin_required
def unbind_user(user_id):
    """解除账号与人员档案的绑定，保留双方数据。"""
    user = db.session.get(User, user_id)
    if user is None:
        return error('账号不存在', status=404, code=404)
    if not user.owner_type:
        return error('该账号未关联人员')
    detach_user(user)
    db.session.commit()
    log_operation(ACTION_UPDATE, 'user', user.id, f'解除账号 {user.username} 的人员绑定')
    return success(user.to_dict(), '已解除人员关联')