"""教师—学生指导关系管理。

需求大纲要求"统计教师教学、科研、指导学生业绩"，原实现没有关系模型，
只能靠教师在"指导学生成果"类别里手工再记一条，导致同一事件被计两次。
"""
from flask import Blueprint, request

from audit import ACTION_CREATE, ACTION_DELETE, ACTION_UPDATE, log_operation
from auth_utils import admin_required, get_current_user, role_required
from extensions import db
from models import AdvisorRelation, Student, Teacher
from utils import error, get_page_args, paginate, parse_bool, parse_int, success
from validators import parse_id_list


advisor_bp = Blueprint('advisor', __name__, url_prefix='/api/advisors')


def _relation_dict(row, teacher_names=None, student_names=None):
    teacher_names = teacher_names or {}
    student_names = student_names or {}
    return row.to_dict(
        teacher_name=teacher_names.get(row.teacher_id, ''),
        student_name=student_names.get(row.student_id, ''),
    )


@advisor_bp.get('/', strict_slashes=False)
@role_required('admin', 'reviewer', 'teacher')
def list_relations():
    user = get_current_user()
    teacher_id = parse_int(request.args.get('teacher_id'))
    student_id = parse_int(request.args.get('student_id'))
    if user.role == 'teacher':
        teacher_id = user.owner_id

    query = AdvisorRelation.query
    if teacher_id:
        query = query.filter(AdvisorRelation.teacher_id == teacher_id)
    if student_id:
        query = query.filter(AdvisorRelation.student_id == student_id)
    query = query.order_by(AdvisorRelation.is_primary.desc(), AdvisorRelation.id)
    page, page_size = get_page_args()
    teacher_names = {t.id: t.name for t in Teacher.query.all()}
    student_names = {s.id: s.name for s in Student.query.all()}
    return success(paginate(
        query, page, page_size,
        serializer=lambda items: [_relation_dict(row, teacher_names, student_names)
                                  for row in items],
    ))


@advisor_bp.post('/', strict_slashes=False)
@admin_required
def create_relation():
    data = request.get_json(silent=True) or {}
    teacher_id = parse_int(data.get('teacher_id'))
    student_id = parse_int(data.get('student_id'))
    teacher = db.session.get(Teacher, teacher_id) if teacher_id else None
    student = db.session.get(Student, student_id) if student_id else None
    if teacher is None:
        return error('请选择指导教师')
    if student is None:
        return error('请选择学生')
    if AdvisorRelation.query.filter_by(teacher_id=teacher.id, student_id=student.id).first():
        return error('该指导关系已存在')

    is_primary = parse_bool(data.get('is_primary'), False)
    if is_primary:
        AdvisorRelation.query.filter_by(student_id=student.id).update(
            {'is_primary': False}, synchronize_session=False)
    row = AdvisorRelation(
        teacher_id=teacher.id,
        student_id=student.id,
        is_primary=is_primary,
        start_year=parse_int(data.get('start_year')),
        end_year=parse_int(data.get('end_year')),
        note=(data.get('note') or '').strip()[:200],
    )
    db.session.add(row)
    if AdvisorRelation.query.filter_by(student_id=student.id).count() == 0:
        row.is_primary = True
    db.session.commit()
    log_operation(ACTION_CREATE, 'advisor', row.id,
                  f'新增指导关系：{teacher.name} → {student.name}')
    return success(_relation_dict(row, {teacher.id: teacher.name}, {student.id: student.name}),
                   '指导关系已新增')


@advisor_bp.put('/<int:relation_id>')
@admin_required
def update_relation(relation_id):
    row = db.session.get(AdvisorRelation, relation_id)
    if row is None:
        return error('指导关系不存在', status=404, code=404)
    data = request.get_json(silent=True) or {}
    if 'is_primary' in data and parse_bool(data.get('is_primary')):
        AdvisorRelation.query.filter_by(student_id=row.student_id).update(
            {'is_primary': False}, synchronize_session=False)
        row.is_primary = True
    elif 'is_primary' in data:
        row.is_primary = False
    if 'start_year' in data:
        row.start_year = parse_int(data.get('start_year'))
    if 'end_year' in data:
        row.end_year = parse_int(data.get('end_year'))
    if 'note' in data:
        row.note = (data.get('note') or '').strip()[:200]
    db.session.commit()
    teacher = db.session.get(Teacher, row.teacher_id)
    student = db.session.get(Student, row.student_id)
    log_operation(ACTION_UPDATE, 'advisor', row.id, '修改指导关系')
    return success(_relation_dict(row,
                                  {row.teacher_id: teacher.name if teacher else ''},
                                  {row.student_id: student.name if student else ''}),
                   '指导关系已更新')


@advisor_bp.delete('/<int:relation_id>')
@admin_required
def delete_relation(relation_id):
    row = db.session.get(AdvisorRelation, relation_id)
    if row is None:
        return error('指导关系不存在', status=404, code=404)
    teacher = db.session.get(Teacher, row.teacher_id)
    student = db.session.get(Student, row.student_id)
    db.session.delete(row)
    db.session.flush()
    remaining = AdvisorRelation.query.filter_by(student_id=row.student_id).all()
    if remaining and not any(item.is_primary for item in remaining):
        remaining[0].is_primary = True
    db.session.commit()
    log_operation(ACTION_DELETE, 'advisor', relation_id,
                  f'解除指导关系：{teacher.name if teacher else ""} → '
                  f'{student.name if student else ""}')
    return success(None, '指导关系已解除')


@advisor_bp.post('/sync-student')
@admin_required
def sync_student_advisors():
    """按学生全量设置指导教师（第一个为主导师）。"""
    data = request.get_json(silent=True) or {}
    student_id = parse_int(data.get('student_id'))
    student = db.session.get(Student, student_id) if student_id else None
    if student is None:
        return error('学生不存在', status=404, code=404)
    teacher_ids = parse_id_list(data.get('teacher_ids'))
    if teacher_ids is None:
        return error('指导教师列表不合法')
    found = {t.id for t in Teacher.query.filter(Teacher.id.in_(teacher_ids)).all()} \
        if teacher_ids else set()
    if teacher_ids and len(found) != len(teacher_ids):
        return error('存在无效的指导教师')

    AdvisorRelation.query.filter_by(student_id=student.id).delete(synchronize_session=False)
    for index, teacher_id in enumerate(teacher_ids):
        db.session.add(AdvisorRelation(teacher_id=teacher_id, student_id=student.id,
                                       is_primary=(index == 0)))
    db.session.commit()
    log_operation(ACTION_UPDATE, 'advisor', student.id,
                  f'设置 {student.name} 的指导教师 {len(teacher_ids)} 人')
    return success([_relation_dict(row) for row in student.advisors()], '指导教师已更新')