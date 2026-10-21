from flask import Blueprint, current_app, request
from sqlalchemy import or_

from audit import ACTION_CREATE, ACTION_UPDATE, diff_dict, log_operation
from auth_utils import admin_required, get_current_user, role_required
from constants import ROLE_STUDENT, ROLE_TEACHER
from extensions import db
from maintenance import delete_student
from models import Achievement, AdvisorRelation, Student, Teacher, User
from security import normalize_text
from services import normalize_dict_value
from utils import error, get_page_args, paginate, parse_bool, success
from validators import validate_student

student_bp = Blueprint('student', __name__, url_prefix='/api/students')

EDITABLE_FIELDS = ('student_no', 'name', 'grade', 'major', 'department',
                   'class_name', 'email', 'phone')
ADMIN_ONLY_FIELDS = ('student_no', 'grade', 'major', 'department', 'class_name')


def set_advisors(student, advisor_ids):
    """全量设置学生的指导教师列表（第一个为主导师）。"""
    AdvisorRelation.query.filter_by(student_id=student.id).delete(synchronize_session=False)
    for index, teacher_id in enumerate(advisor_ids or []):
        db.session.add(AdvisorRelation(
            teacher_id=int(teacher_id),
            student_id=student.id,
            is_primary=(index == 0),
        ))


@student_bp.get('/', strict_slashes=False)
@role_required('admin', 'reviewer')
def list_students():
    keyword = normalize_text(request.args.get('keyword'))
    major = normalize_text(request.args.get('major'))
    grade = normalize_text(request.args.get('grade'))
    department = normalize_text(request.args.get('department'))
    advisor_id = request.args.get('advisor_id')
    has_account = request.args.get('has_account')

    query = Student.query
    if keyword:
        like = f'%{keyword}%'
        query = query.filter(or_(
            Student.name.like(like), Student.student_no.like(like),
            Student.major.like(like), Student.class_name.like(like),
        ))
    if major:
        query = query.filter(Student.major == major)
    if grade:
        query = query.filter(Student.grade == grade)
    if department:
        query = query.filter(Student.department == department)
    if advisor_id not in (None, ''):
        try:
            teacher_id = int(advisor_id)
        except (TypeError, ValueError):
            return error('指导教师参数不合法')
        student_ids = {row.student_id for row in
                       AdvisorRelation.query.filter_by(teacher_id=teacher_id).all()}
        query = query.filter(Student.id.in_(student_ids or {-1}))
    if has_account not in (None, ''):
        account_ids = {u.owner_id for u in User.query.filter_by(owner_type=ROLE_STUDENT).all()}
        if parse_bool(has_account):
            query = query.filter(Student.id.in_(account_ids or {-1}))
        else:
            query = query.filter(~Student.id.in_(account_ids or {-1}))
    query = query.order_by(Student.id.desc())
    page, page_size = get_page_args()
    return success(paginate(query, page, page_size))


@student_bp.get('/options')
@role_required('admin', 'reviewer')
def student_options():
    items = Student.query.order_by(Student.name).all()
    return success([
        {'id': s.id, 'name': s.name, 'student_no': s.student_no,
         'major': s.major, 'department': s.department,
         'label': f'{s.name}（{s.student_no}）'}
        for s in items
    ])


@student_bp.get('/<int:student_id>')
@role_required('admin', 'reviewer', 'student')
def get_student(student_id):
    user = get_current_user()
    if user.role == 'student' and user.owner_id != student_id:
        return error('无权查看他人信息', status=403, code=403)
    student = db.session.get(Student, student_id)
    if student is None:
        return error('学生不存在', status=404, code=404)
    return success(student.to_dict())


@student_bp.get('/<int:student_id>/profile')
@role_required('admin', 'reviewer', 'student')
def student_profile(student_id):
    user = get_current_user()
    if user.role == 'student' and user.owner_id != student_id:
        return error('无权查看他人信息', status=403, code=403)
    student = db.session.get(Student, student_id)
    if student is None:
        return error('学生不存在', status=404, code=404)
    achievements = (Achievement.query
                    .filter_by(owner_type=ROLE_STUDENT, owner_id=student_id, is_deleted=False)
                    .order_by(Achievement.year.desc(), Achievement.id.desc()).all())
    return success({
        'student': student.to_dict(),
        'achievements': Achievement.to_dict_list(achievements),
    })


@student_bp.post('/', strict_slashes=False)
@admin_required
def create_student():
    data = request.get_json(silent=True) or {}
    payload, message = validate_student(data)
    if message:
        return error(message)
    if Student.query.filter_by(student_no=payload['student_no']).first():
        return error('学号已存在')

    username = normalize_text(data.get('username'))
    password = data.get('password') or ''
    if username:
        if User.query.filter_by(username=username).first():
            return error('登录名已存在')
        if len(password) < current_app.config['MIN_PASSWORD_LENGTH']:
            return error(f'初始密码长度不能少于 {current_app.config["MIN_PASSWORD_LENGTH"]} 位')

    advisor_ids = payload.pop('advisor_ids', [])
    student = Student(
        student_no=payload['student_no'],
        name=payload['name'],
        grade=normalize_dict_value('grade', payload.get('grade')),
        major=normalize_dict_value('major', payload.get('major')),
        department=normalize_dict_value('department', payload.get('department')),
        class_name=payload.get('class_name', ''),
        email=payload.get('email', ''),
        phone=payload.get('phone', ''),
    )
    db.session.add(student)
    db.session.flush()
    set_advisors(student, advisor_ids)

    if username:
        from accounts import create_account
        user = create_account(
            username, password, ROLE_STUDENT,
            owner_type=ROLE_STUDENT, owner_id=student.id,
            must_change_password=parse_bool(
                data.get('must_change_password'),
                current_app.config.get('FORCE_PASSWORD_CHANGE', False),
            ),
        )
        student.user_id = user.id
    db.session.commit()
    log_operation(ACTION_CREATE, 'student', student.id,
                  f'新增学生「{student.name}」（{student.student_no}）'
                  + (f'，账号 {username}' if username else ''))
    return success(student.to_dict(), '学生新增成功')


@student_bp.put('/<int:student_id>')
@role_required('admin', 'student')
def update_student(student_id):
    user = get_current_user()
    if user.role == 'student' and user.owner_id != student_id:
        return error('无权修改他人信息', status=403, code=403)
    student = db.session.get(Student, student_id)
    if student is None:
        return error('学生不存在', status=404, code=404)

    data = request.get_json(silent=True) or {}
    if user.role != 'admin':
        blocked = [field for field in ADMIN_ONLY_FIELDS if field in data]
        if blocked:
            return error('学号、年级、专业、班级与院系请联系管理员修改', status=403, code=403)
        if 'advisor_ids' in data:
            return error('指导教师由管理员维护', status=403, code=403)

    payload, message = validate_student(data, partial=True)
    if message:
        return error(message)
    if 'student_no' in payload:
        exists = Student.query.filter(Student.student_no == payload['student_no'],
                                      Student.id != student_id).first()
        if exists:
            return error('学号已存在')

    before = student.to_dict()
    advisor_ids = payload.pop('advisor_ids', None)
    for field, value in payload.items():
        if field == 'grade':
            value = normalize_dict_value('grade', value)
        elif field == 'major':
            value = normalize_dict_value('major', value)
        elif field == 'department':
            value = normalize_dict_value('department', value)
        setattr(student, field, value)
    if advisor_ids is not None:
        set_advisors(student, advisor_ids)
    db.session.commit()

    after = student.to_dict()
    changes = diff_dict(before, after, EDITABLE_FIELDS + ('advisor_names',))
    log_operation(ACTION_UPDATE, 'student', student.id,
                  f'修改学生「{student.name}」信息',
                  detail={'changes': changes} if changes else None)
    return success(after, '学生信息已更新')


@student_bp.delete('/<int:student_id>')
@admin_required
def remove_student(student_id):
    operator = get_current_user()
    student = db.session.get(Student, student_id)
    if student is None:
        return error('学生不存在', status=404, code=404)
    result = delete_student(student, operator=operator)
    return success(result,
                   f'学生已删除，同时清理成果 {result["achievements"]} 条、'
                   f'支撑材料 {result["files_removed"]} 个')