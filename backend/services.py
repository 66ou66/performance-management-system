"""领域服务：权限范围、组合检索、字典归一化、附件存储。

把"角色数据隔离 + 多条件检索"集中在这里，路由只负责参数与响应，
避免同一套过滤逻辑在 achievement / stats / import-export 三处各写一遍。
"""
import os

from sqlalchemy import Text, and_, cast, exists, or_, select

from constants import (
    COUNTED_STATUSES,
    ELEVATED_ROLES,
    STATUS_APPROVED,
    category_owner_type,
)
from extensions import db
from models import (
    Achievement,
    AchievementIndicator,
    Attachment,
    DictItem,
    Student,
    Teacher,
)
from security import normalize_text, safe_filename

SORTABLE = {
    'year': Achievement.year,
    'title': Achievement.title,
    'level': Achievement.level,
    'category': Achievement.category,
    'status': Achievement.status,
    'updated_at': Achievement.updated_at,
    'created_at': Achievement.created_at,
    'owner_name': Achievement.owner_id,
}


def is_elevated(user):
    """管理员与审核员可以查看全部数据。"""
    return bool(user) and user.role in ELEVATED_ROLES


def is_admin(user):
    return bool(user) and user.role == 'admin'


# --------------------------------------------------------------------------- #
# 字典归一化
# --------------------------------------------------------------------------- #
def _alias_index(kind):
    mapping = {}
    for item in DictItem.query.filter_by(kind=kind).all():
        mapping[item.name] = item.name
        for alias in item.alias_list():
            mapping[normalize_text(alias)] = item.name
    return mapping


def normalize_dict_value(kind, value, auto_register=True):
    """把院系/专业/职称/年级统一到字典里的规范名称。

    未命中字典时按原名登记为新的字典项，管理员可以在"字典管理"里合并。
    """
    cleaned = normalize_text(value)
    if not cleaned:
        return ''
    mapping = _alias_index(kind)
    canonical = mapping.get(cleaned)
    if canonical:
        return canonical
    if not auto_register:
        return cleaned
    exists_item = DictItem.query.filter_by(kind=kind, name=cleaned).first()
    if exists_item is None:
        max_order = db.session.query(db.func.max(DictItem.sort_order)).filter_by(
            kind=kind).scalar()
        db.session.add(DictItem(kind=kind, name=cleaned,
                                sort_order=(max_order or 0) + 1))
        db.session.flush()
    return cleaned


def dict_names(kind, active_only=True):
    query = DictItem.query.filter_by(kind=kind)
    if active_only:
        query = query.filter(DictItem.is_active.is_(True))
    return [item.name for item in query.order_by(DictItem.sort_order, DictItem.id).all()]


# --------------------------------------------------------------------------- #
# 成果查询构建
# --------------------------------------------------------------------------- #
def _owner_id_subquery(like):
    return (
        select(Teacher.id).where(Teacher.name.like(like)),
        select(Student.id).where(Student.name.like(like)),
    )


def scope_achievements(query, user, include_deleted=False):
    """按角色做数据隔离。"""
    if not include_deleted:
        query = query.filter(Achievement.is_deleted.is_(False))
    if is_elevated(user):
        return query
    if user is None or not user.owner_type or not user.owner_id:
        # 未绑定人员的账号看不到任何他人数据
        return query.filter(Achievement.id == -1)
    return query.filter(
        Achievement.owner_type == user.owner_type,
        Achievement.owner_id == user.owner_id,
    )


def parse_statuses(raw, user=None, default_counted=False):
    if raw:
        values = [item.strip() for item in str(raw).split(',') if item.strip()]
        if values:
            return values
    if default_counted:
        return list(COUNTED_STATUSES)
    return []


def build_achievement_query(user, args, base_query=None, include_deleted=False):
    """按角色做数据隔离，并叠加多条件组合检索。"""
    query = base_query if base_query is not None else Achievement.query
    query = scope_achievements(query, user, include_deleted=include_deleted)

    keyword = normalize_text(args.get('keyword'))
    if keyword:
        like = f'%{keyword}%'
        query = query.filter(or_(
            Achievement.title.like(like),
            Achievement.description.like(like),
            Achievement.level.like(like),
            cast(Achievement.extra, Text).like(like),
        ))

    category = normalize_text(args.get('category'))
    if category:
        query = query.filter(Achievement.category == category)

    level = normalize_text(args.get('level'))
    if level:
        query = query.filter(Achievement.level == level)

    owner_type = normalize_text(args.get('owner_type'))
    if owner_type:
        query = query.filter(Achievement.owner_type == owner_type)

    year = args.get('year')
    if year not in (None, ''):
        try:
            query = query.filter(Achievement.year == int(year))
        except (TypeError, ValueError):
            pass

    academic_year = normalize_text(args.get('academic_year'))
    if academic_year:
        query = query.filter(Achievement.academic_year == academic_year)

    statuses = parse_statuses(args.get('status'))
    if statuses:
        query = query.filter(Achievement.status.in_(statuses))

    owner_name = normalize_text(args.get('owner_name'))
    if owner_name:
        teacher_ids, student_ids = _owner_id_subquery(f'%{owner_name}%')
        query = query.filter(or_(
            and_(Achievement.owner_type == 'teacher', Achievement.owner_id.in_(teacher_ids)),
            and_(Achievement.owner_type == 'student', Achievement.owner_id.in_(student_ids)),
        ))

    department = normalize_text(args.get('department'))
    if department:
        like = f'%{department}%'
        teacher_ids = select(Teacher.id).where(Teacher.department.like(like))
        student_ids = select(Student.id).where(Student.department.like(like))
        query = query.filter(or_(
            and_(Achievement.owner_type == 'teacher', Achievement.owner_id.in_(teacher_ids)),
            and_(Achievement.owner_type == 'student', Achievement.owner_id.in_(student_ids)),
        ))

    advisor_id = args.get('advisor_id')
    if advisor_id not in (None, ''):
        try:
            query = query.filter(Achievement.advisor_id == int(advisor_id))
        except (TypeError, ValueError):
            pass

    indicator_id = args.get('indicator_id')
    if indicator_id not in (None, ''):
        try:
            subquery = select(AchievementIndicator.achievement_id).where(
                AchievementIndicator.indicator_id == int(indicator_id))
            query = query.filter(Achievement.id.in_(subquery))
        except (TypeError, ValueError):
            pass

    has_attachment = args.get('has_attachment')
    if has_attachment not in (None, ''):
        attached = exists().where(Attachment.achievement_id == Achievement.id)
        if str(has_attachment) in ('0', 'false', 'False', 'no'):
            query = query.filter(~attached)
        elif str(has_attachment) in ('1', 'true', 'True', 'yes'):
            query = query.filter(attached)

    return apply_sort(query, args)


def apply_sort(query, args):
    sort = normalize_text(args.get('sort'))
    field = sort.lstrip('-')
    column = SORTABLE.get(field)
    if column is None:
        return query.order_by(Achievement.year.desc(), Achievement.id.desc())
    ordering = column.desc() if sort.startswith('-') else column.asc()
    return query.order_by(ordering, Achievement.id.desc())


# --------------------------------------------------------------------------- #
# 附件存储
# --------------------------------------------------------------------------- #
def relative_storage_dir(achievement, year=None):
    """分类存储：<学年>/<owner_type>_<owner_id>/<成果id>/"""
    if year is None:
        from datetime import datetime
        year = datetime.now().year
    academic_year = achievement.academic_year or f'{year}-{year + 1}'
    return os.path.join(academic_year, f'{achievement.owner_type}_{achievement.owner_id}',
                        str(achievement.id))


def absolute_attachment_path(app_config, stored_path):
    return os.path.join(app_config['UPLOAD_FOLDER'], stored_path)


def remove_file(app_config, stored_path):
    """删除单个附件文件，同时清掉可能变空的目录。"""
    if not stored_path:
        return False
    full = absolute_attachment_path(app_config, stored_path)
    removed = False
    if os.path.exists(full):
        try:
            os.remove(full)
            removed = True
        except OSError:
            return False
    folder = os.path.dirname(full)
    upload_root = os.path.abspath(app_config['UPLOAD_FOLDER'])
    while os.path.abspath(folder).startswith(upload_root) and os.path.abspath(folder) != upload_root:
        try:
            if os.path.isdir(folder) and not os.listdir(folder):
                os.rmdir(folder)
                folder = os.path.dirname(folder)
            else:
                break
        except OSError:
            break
    return removed


def remove_achievement_files(app_config, achievement):
    """删除一条成果的全部支撑材料文件（含兼容字段），返回删除数量。"""
    removed = 0
    for row in Attachment.query.filter_by(achievement_id=achievement.id).all():
        if remove_file(app_config, row.stored_path):
            removed += 1
    if achievement.attachment_path:
        if remove_file(app_config, achievement.attachment_path):
            removed += 1
    return removed


def remove_owner_files(app_config, owner_type, owner_ids):
    """删除某批教师/学生的全部成果附件文件（用于删除人员时的级联清理）。"""
    if not owner_ids:
        return 0
    rows = (Attachment.query
            .join(Achievement, Attachment.achievement_id == Achievement.id)
            .filter(Achievement.owner_type == owner_type,
                    Achievement.owner_id.in_(list(owner_ids)))
            .all())
    removed = 0
    for row in rows:
        if remove_file(app_config, row.stored_path):
            removed += 1
    legacy = Achievement.query.filter(
        Achievement.owner_type == owner_type,
        Achievement.owner_id.in_(list(owner_ids)),
        Achievement.attachment_path.isnot(None),
    ).all()
    for item in legacy:
        if remove_file(app_config, item.attachment_path):
            removed += 1
    return removed


def unique_stored_name(directory, filename):
    """在目标目录里生成不冲突的文件名，保留原始文件名便于人工识别。"""
    from uuid import uuid4
    base = safe_filename(filename)
    stem, dot, ext = base.rpartition('.')
    if not dot:
        stem, ext = base, ''
    candidate = f'{stem}_{uuid4().hex[:8]}'
    full = os.path.join(directory, candidate + (f'.{ext}' if ext else ''))
    guard = 0
    while os.path.exists(full) and guard < 50:  # pragma: no cover - 概率极低
        guard += 1
        candidate = f'{stem}_{uuid4().hex[:8]}'
        full = os.path.join(directory, candidate + (f'.{ext}' if ext else ''))
    return candidate + (f'.{ext}' if ext else '')


def indicator_map_for(achievement_ids):
    if not achievement_ids:
        return {}
    rows = (db.session.query(AchievementIndicator.achievement_id, AchievementIndicator.indicator_id)
            .filter(AchievementIndicator.achievement_id.in_(achievement_ids)).all())
    result = {}
    for achievement_id, indicator_id in rows:
        result.setdefault(achievement_id, []).append(indicator_id)
    return result


def apply_indicators(achievement, indicator_ids):
    """全量替换某条成果的指标点关联。"""
    AchievementIndicator.query.filter_by(achievement_id=achievement.id).delete()
    for indicator_id in indicator_ids or []:
        db.session.add(AchievementIndicator(
            achievement_id=achievement.id, indicator_id=int(indicator_id)))


def counted_status_values():
    return list(COUNTED_STATUSES)


def category_matches_owner(category, owner_type):
    expected = category_owner_type(category)
    if expected is None:
        return False
    return expected == owner_type


def default_status_for(user):
    """教师/学生提交的成果在开启审核时进入待审核。"""
    from flask import current_app
    if user is not None and user.role in ('admin', 'reviewer'):
        return STATUS_APPROVED
    if current_app.config.get('REQUIRE_REVIEW'):
        return 'pending'
    return STATUS_APPROVED