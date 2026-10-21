"""账号与人员档案的关联维护。

原实现的缺陷：通过「账号权限管理」给已有教师建号时只写了 User.owner_id，
没有回写 Teacher.user_id，导致教师列表显示"未关联"而账号实际已存在。
现在所有入口都调用 `sync_user_links()`，双向引用只有一处写入口径。
"""
from constants import ROLE_ADMIN, ROLE_STUDENT, ROLE_TEACHER
from extensions import db
from models import Student, Teacher, User


def sync_user_links(user):
    """把 User 与 Teacher/Student 的关联写成双向一致（不提交事务）。"""
    Teacher.query.filter(Teacher.user_id == user.id).update(
        {'user_id': None}, synchronize_session=False)
    Student.query.filter(Student.user_id == user.id).update(
        {'user_id': None}, synchronize_session=False)
    if user.owner_type == ROLE_TEACHER and user.owner_id:
        Teacher.query.filter(Teacher.id == user.owner_id).update(
            {'user_id': user.id}, synchronize_session=False)
    elif user.owner_type == ROLE_STUDENT and user.owner_id:
        Student.query.filter(Student.id == user.owner_id).update(
            {'user_id': user.id}, synchronize_session=False)
    db.session.flush()


def detach_user(user):
    """解除账号与人员的关联。"""
    user.owner_type = None
    user.owner_id = None
    sync_user_links(user)


def set_owner(user, owner_type, owner_id):
    user.owner_type = owner_type if owner_type in (ROLE_TEACHER, ROLE_STUDENT) else None
    user.owner_id = owner_id if user.owner_type else None
    sync_user_links(user)


def create_account(username, password, role, owner_type=None, owner_id=None,
                   must_change_password=False):
    user = User(
        username=username,
        role=role,
        owner_type=owner_type if role in (ROLE_TEACHER, ROLE_STUDENT) else None,
        owner_id=owner_id if role in (ROLE_TEACHER, ROLE_STUDENT) else None,
        must_change_password=must_change_password,
    )
    user.set_password(password)
    db.session.add(user)
    db.session.flush()
    sync_user_links(user)
    return user


def unique_username(base):
    """生成不冲突的登录名：teacher → teacher2 → teacher3 …"""
    from models import User as _User
    candidate = base
    index = 1
    while _User.query.filter_by(username=candidate).first():
        index += 1
        candidate = f'{base}{index}'
    return candidate


def owner_exists(owner_type, owner_id):
    if owner_type == ROLE_TEACHER:
        return db.session.get(Teacher, owner_id) is not None
    if owner_type == ROLE_STUDENT:
        return db.session.get(Student, owner_id) is not None
    return False


def owner_label(owner_type, owner_id):
    if owner_type == ROLE_TEACHER:
        teacher = db.session.get(Teacher, owner_id)
        return teacher.name if teacher else ''
    if owner_type == ROLE_STUDENT:
        student = db.session.get(Student, owner_id)
        return student.name if student else ''
    return ''


def account_for_owner(owner_type, owner_id):
    return User.query.filter_by(owner_type=owner_type, owner_id=owner_id).first()


__all__ = [
    'sync_user_links', 'detach_user', 'set_owner', 'create_account',
    'unique_username', 'owner_exists', 'owner_label', 'account_for_owner',
    'ROLE_ADMIN',
]