from flask import Blueprint, current_app, request

from audit import ACTION_CREATE, ACTION_UPDATE, diff_dict, log_operation
from auth_utils import admin_required, get_current_user, role_required
from constants import ROLE_TEACHER
from extensions import db
from maintenance import delete_teacher
from models import Achievement, AdvisorRelation, Student, Teacher, User
from security import normalize_text
from services import normalize_dict_value
from utils import error, get_page_args, paginate, parse_bool, success
from validators import validate_teacher

teacher_bp = Blueprint('teacher', __name__, url_prefix='/api/teachers')

EDITABLE_FIELDS = ('name', 'department', 'title', 'email', 'phone', 'research_area')
ADMIN_ONLY_FIELDS = ('department', 'title')


@teacher_bp.get('/', strict_slashes=False)
@admin_required
def list_teachers():
    keyword = normalize_text(request.args.get('keyword'))
    department = normalize_text(request.args.get('department'))
    title = normalize_text(request.args.get('title'))
    has_account = request.args.get('has_account')
    advisor_of = request.args.get('advisor_of')

    query = Teacher.query
    if keyword:
        like = f'%{keyword}%'
        from sqlalchemy import or_
        query = query.filter(or_(
            Teacher.name.like(like),
            Teacher.email.like(like),
            Teacher.title.like(like),
            Teacher.research_area.like(like),
            Teacher.department.like(like),
        ))
    if department:
        query = query.filter(Teacher.department == department)
    if title:
        query = query.filter(Teacher.title == title)
    if has_account not in (None, ''):
        account_ids = {u.owner_id for u in User.query.filter_by(owner_type=ROLE_TEACHER).all()}
        if parse_bool(has_account):
            query = query.filter(Teacher.id.in_(account_ids or {-1}))
        else:
            query = query.filter(~Teacher.id.in_(account_ids or {-1}))
    if advisor_of not in (None, ''):
        try:
            student_id = int(advisor_of)
        except (TypeError, ValueError):
            return error('学生参数不合法')
        teacher_ids = {row.teacher_id for row in
                       AdvisorRelation.query.filter_by(student_id=student_id).all()}
        query = query.filter(Teacher.id.in_(teacher_ids or {-1}))
    query = query.order_by(Teacher.id.desc())
    page, page_size = get_page_args()
    return success(paginate(query, page, page_size))


@teacher_bp.get('/options')
@role_required('admin', 'reviewer')
def teacher_options():
    items = Teacher.query.order_by(Teacher.name).all()
    return success([
        {'id': t.id, 'name': t.name, 'department': t.department,
         'title': t.title, 'label': f'{t.name}（{t.department or "未设院系"}）'}
        for t in items
    ])


@teacher_bp.get('/<int:teacher_id>')
@role_required('admin', 'reviewer', 'teacher')
def get_teacher(teacher_id):
    user = get_current_user()
    if user.role == 'teacher' and user.owner_id != teacher_id:
        return error('无权查看他人信息', status=403, code=403)
    teacher = db.session.get(Teacher, teacher_id)
    if teacher is None:
        return error('教师不存在', status=404, code=404)
    return success(teacher.to_dict())


@teacher_bp.get('/<int:teacher_id>/profile')
@role_required('admin', 'reviewer', 'teacher')
def teacher_profile(teacher_id):
    """教师详情页：基本信息 + 本人成果 + 指导学生。"""
    user = get_current_user()
    if user.role == 'teacher' and user.owner_id != teacher_id:
        return error('无权查看他人信息', status=403, code=403)
    teacher = db.session.get(Teacher, teacher_id)
    if teacher is None:
        return error('教师不存在', status=404, code=404)

    own = (Achievement.query
           .filter_by(owner_type=ROLE_TEACHER, owner_id=teacher_id, is_deleted=False)
           .order_by(Achievement.year.desc(), Achievement.id.desc()).all())
    advised = (Achievement.query
               .filter(Achievement.advisor_id == teacher_id, Achievement.is_deleted.is_(False))
               .order_by(Achievement.year.desc(), Achievement.id.desc()).all())
    relations = AdvisorRelation.query.filter_by(teacher_id=teacher_id).all()
    students = [db.session.get(Student, row.student_id) for row in relations]
    students = [item for item in students if item is not None]
    return success({
        'teacher': teacher.to_dict(),
        'own_achievements': Achievement.to_dict_list(own),
        'advised_achievements': Achievement.to_dict_list(advised),
        'students': Student.to_dict_list(students),
    })


@teacher_bp.post('/', strict_slashes=False)
@admin_required
def create_teacher():
    data = request.get_json(silent=True) or {}
    payload, message = validate_teacher(data)
    if message:
        return error(message)

    username = normalize_text(data.get('username'))
    password = data.get('password') or ''
    if username:
        if User.query.filter_by(username=username).first():
            return error('登录名已存在')
        if len(password) < current_app.config['MIN_PASSWORD_LENGTH']:
            return error(f'初始密码长度不能少于 {current_app.config["MIN_PASSWORD_LENGTH"]} 位')

    teacher = Teacher(
        name=payload['name'],
        department=normalize_dict_value('department', payload.get('department')),
        title=normalize_dict_value('title', payload.get('title')),
        email=payload.get('email', ''),
        phone=payload.get('phone', ''),
        research_area=payload.get('research_area', ''),
    )
    db.session.add(teacher)
    db.session.flush()

    if username:
        from accounts import create_account
        user = create_account(
            username, password, ROLE_TEACHER,
            owner_type=ROLE_TEACHER, owner_id=teacher.id,
            must_change_password=parse_bool(
                data.get('must_change_password'),
                current_app.config.get('FORCE_PASSWORD_CHANGE', False),
            ),
        )
        teacher.user_id = user.id
    db.session.commit()
    log_operation(ACTION_CREATE, 'teacher', teacher.id,
                  f'新增教师「{teacher.name}」' + (f'（账号 {username}）' if username else ''))
    return success(teacher.to_dict(), '教师新增成功')


@teacher_bp.put('/<int:teacher_id>')
@role_required('admin', 'teacher')
def update_teacher(teacher_id):
    user = get_current_user()
    if user.role == 'teacher' and user.owner_id != teacher_id:
        return error('无权修改他人信息', status=403, code=403)
    teacher = db.session.get(Teacher, teacher_id)
    if teacher is None:
        return error('教师不存在', status=404, code=404)

    data = request.get_json(silent=True) or {}
    if user.role != 'admin':
        # 教师只能维护自己的联系方式与研究方向，院系/职称由管理员维护
        blocked = [field for field in ADMIN_ONLY_FIELDS if field in data]
        if blocked:
            return error('院系与职称信息请联系管理员修改', status=403, code=403)

    payload, message = validate_teacher(data, partial=True)
    if message:
        return error(message)

    before = teacher.to_dict()
    for field, value in payload.items():
        if field == 'department':
            value = normalize_dict_value('department', value)
        elif field == 'title':
            value = normalize_dict_value('title', value)
        setattr(teacher, field, value)
    db.session.commit()

    after = teacher.to_dict()
    changes = diff_dict(before, after, EDITABLE_FIELDS)
    log_operation(ACTION_UPDATE, 'teacher', teacher.id,
                  f'修改教师「{teacher.name}」信息',
                  detail={'changes': changes} if changes else None)
    return success(after, '教师信息已更新')


@teacher_bp.delete('/<int:teacher_id>')
@admin_required
def remove_teacher(teacher_id):
    operator = get_current_user()
    teacher = db.session.get(Teacher, teacher_id)
    if teacher is None:
        return error('教师不存在', status=404, code=404)
    if operator.owner_type == ROLE_TEACHER and operator.owner_id == teacher_id:
        return error('不能删除当前登录账号关联的教师档案')
    result = delete_teacher(teacher, operator=operator)
    return success(result,
                   f'教师已删除，同时清理成果 {result["achievements"]} 条、'
                   f'支撑材料 {result["files_removed"]} 个')