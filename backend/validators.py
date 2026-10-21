"""输入校验与规范化。

前端下拉选项与后端校验共用 `constants` 里的同一份字典，
从根源上消除"随便写的级别""99999 年"这类脏维度入库。
"""
import re
from datetime import datetime

from constants import (
    ALL_CATEGORIES,
    AWARD_RANKS,
    FIELD_TEMPLATES,
    ROLE_RANKS,
    STATUS_LABELS,
    categories_for,
    extra_keys,
    levels_for,
)
from extensions import db
from models import Achievement, CertificationIndicator, Student, Teacher
from security import normalize_text, validate_password

EMAIL_PATTERN = re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
DATE_PATTERN = re.compile(r'^\d{4}-\d{2}-\d{2}$')

MIN_YEAR = 1950


def _max_year():
    return datetime.now().year + 1


def normalize_email(value):
    email = normalize_text(value)
    if not email:
        return ''
    return email if EMAIL_PATTERN.match(email) else None


def normalize_date(value):
    text_value = normalize_text(value)
    if not text_value:
        return ''
    if DATE_PATTERN.match(text_value):
        try:
            datetime.strptime(text_value, '%Y-%m-%d')
            return text_value
        except ValueError:
            return None
    try:
        return datetime.fromisoformat(text_value.replace('Z', '')).strftime('%Y-%m-%d')
    except ValueError:
        return None


def normalize_extra(category, raw):
    """按类别字段模板清洗 extra，丢弃模板外的键，保证统计口径稳定。"""
    data = raw if isinstance(raw, dict) else {}
    allowed = extra_keys(category)
    templates = {field['key']: field for field in FIELD_TEMPLATES.get(category, [])}
    cleaned = {}
    for key in allowed:
        if key not in data:
            continue
        field = templates[key]
        value = data.get(key)
        field_type = field.get('type', 'text')
        if field_type == 'number':
            if value in (None, ''):
                cleaned[key] = ''
                continue
            try:
                number = float(value)
            except (TypeError, ValueError):
                return None, f'「{field["label"]}」必须是数字'
            cleaned[key] = int(number) if number.is_integer() else number
        elif field_type == 'date':
            parsed = normalize_date(value)
            if parsed is None:
                return None, f'「{field["label"]}」日期格式应为 YYYY-MM-DD'
            cleaned[key] = parsed
        elif field_type == 'select':
            text_value = normalize_text(value)
            options = field.get('options') or []
            if text_value and options and text_value not in options:
                return None, f'「{field["label"]}」取值不在允许范围内'
            cleaned[key] = text_value
        else:
            text_value = normalize_text(value)
            limit = int(field.get('maxlength') or 200)
            if len(text_value) > limit:
                return None, f'「{field["label"]}」长度不能超过 {limit} 字'
            cleaned[key] = text_value
    return cleaned, None


def parse_id_list(raw):
    """把 [1, '2'] / '1,2' 统一成 [1, 2]。"""
    if raw in (None, ''):
        return []
    if isinstance(raw, str):
        items = [item.strip() for item in raw.split(',') if item.strip()]
    elif isinstance(raw, (list, tuple, set)):
        items = list(raw)
    else:
        items = [raw]
    result = []
    for item in items:
        try:
            value = int(item)
        except (TypeError, ValueError):
            return None
        if value not in result:
            result.append(value)
    return result


def validate_achievement(data, owner_type, owner_id, existing=None, partial=False):
    """返回 (payload, error_message)。partial=True 时只校验传入的字段。"""
    payload = {}

    if not partial or 'category' in data:
        category = normalize_text(data.get('category'))
        if not category:
            return None, '请选择成果类型'
        if category not in categories_for(owner_type):
            return None, '成果类型与所属人类型不匹配'
        payload['category'] = category

    category = payload.get('category') or getattr(existing, 'category', None) \
        or normalize_text(data.get('category'))

    if not partial or 'title' in data:
        title = normalize_text(data.get('title'))
        if not title:
            return None, '请输入成果名称'
        if len(title) > 255:
            return None, '成果名称长度不能超过 255 字'
        payload['title'] = title

    if not partial or 'year' in data:
        raw_year = data.get('year')
        if raw_year in (None, ''):
            if not partial:
                payload['year'] = datetime.now().year
        else:
            try:
                year = int(raw_year)
            except (TypeError, ValueError):
                return None, '年份必须是数字'
            if year < MIN_YEAR or year > _max_year():
                return None, f'年份需在 {MIN_YEAR} 至 {_max_year()} 之间'
            payload['year'] = year

    year = payload.get('year', existing.year if existing else None)
    if not partial or 'academic_year' in data:
        academic_year = normalize_text(data.get('academic_year'))
        if academic_year:
            if not re.match(r'^\d{4}-\d{4}$', academic_year):
                return None, '学年格式应为 YYYY-YYYY'
            payload['academic_year'] = academic_year
        elif year:
            payload['academic_year'] = f'{year}-{year + 1}'

    if not partial or 'level' in data:
        level = normalize_text(data.get('level'))
        if level:
            allowed = levels_for(category)
            if level not in allowed:
                return None, f'「{category}」的级别只能是：{"、".join(allowed)}'
        payload['level'] = level

    if not partial or 'role_rank' in data:
        role_rank = normalize_text(data.get('role_rank'))
        if role_rank and role_rank not in ROLE_RANKS:
            return None, '完成人排序取值不合法'
        payload['role_rank'] = role_rank

    if not partial or 'description' in data:
        description = normalize_text(data.get('description'))
        if len(description) > 2000:
            return None, '成果描述长度不能超过 2000 字'
        payload['description'] = description

    if not partial or 'extra' in data:
        cleaned, message = normalize_extra(category, data.get('extra'))
        if message:
            return None, message
        payload['extra'] = cleaned

    if not partial or 'status' in data:
        status = normalize_text(data.get('status'))
        if status:
            if status not in STATUS_LABELS:
                return None, '审核状态不合法'
            payload['status'] = status

    if not partial or 'advisor_id' in data:
        raw_advisor = data.get('advisor_id')
        if raw_advisor in (None, ''):
            payload['advisor_id'] = None
        else:
            try:
                advisor_id = int(raw_advisor)
            except (TypeError, ValueError):
                return None, '指导教师不合法'
            if db.session.get(Teacher, advisor_id) is None:
                return None, '指导教师不存在'
            payload['advisor_id'] = advisor_id

    if not partial or 'source_achievement_id' in data:
        raw_source = data.get('source_achievement_id')
        if raw_source in (None, ''):
            payload['source_achievement_id'] = None
        else:
            try:
                source_id = int(raw_source)
            except (TypeError, ValueError):
                return None, '关联成果不合法'
            if db.session.get(Achievement, source_id) is None:
                return None, '关联的成果不存在'
            payload['source_achievement_id'] = source_id

    if 'indicator_ids' in data:
        ids = parse_id_list(data.get('indicator_ids'))
        if ids is None:
            return None, '认证指标点不合法'
        if ids:
            found = {row.id for row in CertificationIndicator.query.filter(
                CertificationIndicator.id.in_(ids)).all()}
            missing = [item for item in ids if item not in found]
            if missing:
                return None, '存在无效的认证指标点'
        payload['indicator_ids'] = ids

    return payload, None


def validate_teacher(data, partial=False):
    payload = {}
    if not partial or 'name' in data:
        name = normalize_text(data.get('name'))
        if not name:
            return None, '请输入教师姓名'
        if len(name) > 80:
            return None, '教师姓名长度不能超过 80 字'
        payload['name'] = name
    for field, limit, label in (('department', 120, '所属院系'), ('title', 80, '职称'),
                                ('research_area', 200, '研究方向'), ('phone', 40, '联系电话')):
        if not partial or field in data:
            value = normalize_text(data.get(field))
            if len(value) > limit:
                return None, f'{label}长度不能超过 {limit} 字'
            payload[field] = value
    if not partial or 'email' in data:
        email = normalize_email(data.get('email'))
        if email is None:
            return None, '邮箱格式不正确'
        payload['email'] = email
    return payload, None


def validate_student(data, partial=False):
    payload = {}
    if not partial or 'name' in data:
        name = normalize_text(data.get('name'))
        if not name:
            return None, '请输入学生姓名'
        if len(name) > 80:
            return None, '学生姓名长度不能超过 80 字'
        payload['name'] = name
    if not partial or 'student_no' in data:
        student_no = normalize_text(data.get('student_no'))
        if not student_no:
            return None, '请输入学号'
        if len(student_no) > 50:
            return None, '学号长度不能超过 50 字'
        payload['student_no'] = student_no
    for field, limit, label in (('grade', 30, '年级'), ('major', 120, '专业'),
                                ('department', 120, '所属院系'), ('class_name', 80, '班级'),
                                ('phone', 40, '联系电话')):
        if not partial or field in data:
            value = normalize_text(data.get(field))
            if len(value) > limit:
                return None, f'{label}长度不能超过 {limit} 字'
            payload[field] = value
    if not partial or 'email' in data:
        email = normalize_email(data.get('email'))
        if email is None:
            return None, '邮箱格式不正确'
        payload['email'] = email
    if 'advisor_ids' in data:
        ids = parse_id_list(data.get('advisor_ids'))
        if ids is None:
            return None, '指导教师不合法'
        if ids:
            found = {row.id for row in Teacher.query.filter(Teacher.id.in_(ids)).all()}
            if [item for item in ids if item not in found]:
                return None, '存在无效的指导教师'
        payload['advisor_ids'] = ids
    return payload, None


def validate_user(data, partial=False, min_password=6, strength_check=False):
    payload = {}
    if not partial or 'username' in data:
        username = normalize_text(data.get('username'))
        if not username:
            return None, '请输入登录名'
        if len(username) > 80:
            return None, '登录名长度不能超过 80 字'
        if not re.match(r'^[A-Za-z0-9_.@-]+$', username):
            return None, '登录名只能包含字母、数字、下划线、点、@ 与短横线'
        payload['username'] = username
    if 'password' in data:
        password = data.get('password') or ''
        ok, message = validate_password(password, min_password, strength_check)
        if not ok:
            return None, message
        payload['password'] = password
    if not partial or 'role' in data:
        role = normalize_text(data.get('role'))
        if role not in ('admin', 'reviewer', 'teacher', 'student'):
            return None, '请选择有效的角色'
        payload['role'] = role
    return payload, None


def validate_attachment_category(category, allowed):
    value = normalize_text(category)
    if value and value not in allowed:
        return None, '支撑材料分类不合法'
    return value or '其他', None


def validate_owner(owner_type, owner_id):
    if owner_type == 'teacher':
        return db.session.get(Teacher, owner_id) is not None
    if owner_type == 'student':
        return db.session.get(Student, owner_id) is not None
    return False