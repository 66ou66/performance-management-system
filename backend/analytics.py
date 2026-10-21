"""统计聚合。

全部改成数据库侧 GROUP BY：
原实现把整表拉进内存再用 Counter 分组，1000 条数据要 1018 次 SQL、600ms 以上；
现在固定查询次数、与数据量基本无关。
"""
from collections import Counter
from datetime import datetime

from sqlalchemy import and_, func

from constants import COUNTED_STATUSES
from extensions import db
from models import (
    Achievement,
    AchievementIndicator,
    Attachment,
    CertificationIndicator,
    Student,
    Teacher,
)
from services import build_achievement_query

DIMENSIONS = ('category', 'year', 'level', 'department', 'status', 'academic_year',
              'owner_type', 'advisor')

_ACHIEVEMENT_DIMENSIONS = ('category', 'level', 'status', 'owner_type', 'academic_year')


def filtered_achievements(user, args, default_counted=True):
    """应用数据范围 + 全部筛选条件；未显式指定状态时只统计"已通过"。"""
    query = build_achievement_query(user, args)
    if not (args.get('status') or '').strip() and default_counted:
        query = query.filter(Achievement.status.in_(list(COUNTED_STATUSES)))
    return query.order_by(None)


def _id_subquery(query):
    """过滤后的成果 id 子查询——所有聚合都基于它，保证口径完全一致。"""
    return query.with_entities(Achievement.id).subquery()


def _base(sub, *entities):
    """以 achievement 为主表、JOIN 过滤后的 id 集合，构建聚合查询。"""
    return (db.session.query(*entities)
            .select_from(Achievement)
            .join(sub, sub.c.id == Achievement.id))


def grouped_counts(query, dimension):
    """单维度分组计数，返回 [{name, value}]。"""
    sub = _id_subquery(query)

    if dimension in _ACHIEVEMENT_DIMENSIONS:
        column = getattr(Achievement, dimension)
        rows = (_base(sub, column, func.count(Achievement.id))
                .group_by(column).all())
        return _shape([(value, count) for value, count in rows],
                      by_name=(dimension == 'academic_year'))

    if dimension == 'year':
        rows = (_base(sub, Achievement.year, func.count(Achievement.id))
                .group_by(Achievement.year).all())
        return _shape([(str(year) if year is not None else '', count) for year, count in rows],
                      by_name=True)

    if dimension == 'department':
        counter = Counter()
        for model, owner_type in ((Teacher, 'teacher'), (Student, 'student')):
            rows = (_base(sub, model.department, func.count(Achievement.id))
                    .join(model, and_(model.id == Achievement.owner_id,
                                      Achievement.owner_type == owner_type))
                    .group_by(model.department).all())
            for name, count in rows:
                counter[name or '未填写院系'] += count
        return _shape(list(counter.items()))

    if dimension == 'advisor':
        rows = (_base(sub, Teacher.name, func.count(Achievement.id))
                .join(Teacher, Teacher.id == Achievement.advisor_id)
                .group_by(Teacher.name).all())
        return _shape([(name or '', count) for name, count in rows])

    return []


def _shape(pairs, by_name=False):
    merged = Counter()
    for name, count in pairs:
        if name in (None, ''):
            continue
        merged[str(name)] += count
    items = list(merged.items())
    if by_name:
        items.sort(key=lambda kv: kv[0])
    else:
        items.sort(key=lambda kv: (-kv[1], kv[0]))
    return [{'name': name, 'value': value} for name, value in items]


CLASSIC_DIMENSIONS = ('category', 'year', 'level', 'department')


def all_breakdowns(query, dimensions=None):
    """概览附带的分布数据，键名保持 by_xxx 的历史约定。"""
    return {'by_%s' % dimension: grouped_counts(query, dimension)
            for dimension in (dimensions or CLASSIC_DIMENSIONS)}


def overview(user, query):
    """概览计数。counts 保持原有键名，另外补充审核与材料完整度指标。"""
    total = query.count()
    current_year = datetime.now().year
    this_year = query.filter(Achievement.year == current_year).count()
    sub = _id_subquery(query)
    with_attachment = (db.session.query(func.count(func.distinct(Attachment.achievement_id)))
                       .select_from(Attachment)
                       .join(sub, sub.c.id == Attachment.achievement_id)
                       .scalar()) or 0
    with_attachment = int(with_attachment)
    counts = {
        'achievements': total,
        'this_year': this_year,
        'attachments': with_attachment,
        'missing_evidence': max(total - with_attachment, 0),
    }
    from services import is_elevated
    if is_elevated(user):
        counts['teachers'] = Teacher.query.count()
        counts['students'] = Student.query.count()
        pending_query = Achievement.query.filter(Achievement.is_deleted.is_(False),
                                                 Achievement.status == 'pending')
        counts['pending'] = pending_query.count()
        rows = (db.session.query(Achievement.owner_type, func.count())
                .filter(Achievement.is_deleted.is_(False), Achievement.status == 'pending')
                .group_by(Achievement.owner_type).all())
        for owner_type, value in rows:
            counts[f'pending_{owner_type}'] = value
    else:
        counts['pending'] = Achievement.query.filter(
            Achievement.is_deleted.is_(False),
            Achievement.owner_type == user.owner_type,
            Achievement.owner_id == user.owner_id,
            Achievement.status == 'pending').count()
    counts['trash'] = Achievement.query.filter(
        Achievement.is_deleted.is_(True)).count() if is_elevated(user) else 0
    return counts


def rankings(query, by='teacher', limit=10, only_advisors=False):
    """个人成果排行。"""
    owner_type = 'student' if by == 'student' else 'teacher'
    model = Student if owner_type == 'student' else Teacher
    sub = _id_subquery(query)
    base = db.session.query(model.name, func.count(Achievement.id)).select_from(Achievement) \
        .join(sub, sub.c.id == Achievement.id)
    if only_advisors and owner_type == 'teacher':
        base = base.join(Teacher, Teacher.id == Achievement.advisor_id) \
            .group_by(Teacher.name).order_by(func.count(Achievement.id).desc())
        rows = base.limit(limit).all()
    else:
        base = base.join(model, and_(model.id == Achievement.owner_id,
                                     Achievement.owner_type == owner_type)) \
            .group_by(model.id, model.name) \
            .order_by(func.count(Achievement.id).desc(), model.name)
        rows = base.limit(limit).all()
    return [{'name': name or '', 'value': count, 'owner_type': owner_type}
            for name, count in rows]


def cross_tab(query, row_dimension, col_dimension):
    """二维交叉统计（例如 成果类型 × 年度）。"""
    rows_data = grouped_counts(query, row_dimension)
    cols_data = grouped_counts(query, col_dimension)
    row_column = _column_for(row_dimension)
    col_column = _column_for(col_dimension)
    cells = {}
    if row_column is not None and col_column is not None and row_dimension != col_dimension:
        sub = _id_subquery(query)
        grouped = (_base(sub, row_column, col_column, func.count(Achievement.id))
                   .group_by(row_column, col_column).all())
        for row_value, col_value, count in grouped:
            row_name = str(row_value) if row_value not in (None, '') else '未填写'
            col_name = str(col_value) if col_value not in (None, '') else '未填写'
            cells[f'{row_name}||{col_name}'] = count
    return {
        'rows': [item['name'] for item in rows_data],
        'cols': [item['name'] for item in cols_data],
        'cells': cells,
        'rows_data': rows_data,
        'cols_data': cols_data,
        'same_dimension': row_dimension == col_dimension,
    }


def _column_for(dimension):
    if dimension in _ACHIEVEMENT_DIMENSIONS:
        return getattr(Achievement, dimension)
    if dimension == 'year':
        return Achievement.year
    return None


def indicator_coverage(query):
    """认证指标点覆盖情况：每个指标点关联的成果数量。"""
    sub = _id_subquery(query)
    indicators = (CertificationIndicator.query
                  .filter_by(is_active=True)
                  .order_by(CertificationIndicator.sort_order, CertificationIndicator.id)
                  .all())
    rows = (db.session.query(AchievementIndicator.indicator_id, func.count())
            .select_from(AchievementIndicator)
            .join(sub, sub.c.id == AchievementIndicator.achievement_id)
            .group_by(AchievementIndicator.indicator_id).all())
    counter = {indicator_id: count for indicator_id, count in rows}
    total = query.count()
    covered = (db.session.query(func.count(func.distinct(AchievementIndicator.achievement_id)))
               .select_from(AchievementIndicator)
               .join(sub, sub.c.id == AchievementIndicator.achievement_id)
               .scalar()) or 0
    items = []
    for indicator in indicators:
        count = counter.get(indicator.id, 0)
        items.append({
            'id': indicator.id,
            'code': indicator.code,
            'name': indicator.name,
            'description': indicator.description,
            'value': count,
            'percent': round(count * 100.0 / total, 1) if total else 0.0,
        })
    return {
        'items': items,
        'total_achievements': total,
        'covered_achievements': int(covered),
        'coverage_percent': round(int(covered) * 100.0 / total, 1) if total else 0.0,
        'uncovered_indicators': [item['code'] for item in items if item['value'] == 0],
    }


def person_summary(query, limit=None):
    """师生汇总：每人成果数、已归档材料的成果数、缺件数、最近年份。"""
    sub = _id_subquery(query)
    # 一次性统计「每人有材料的成果数」，避免逐人查询造成 N+1
    attachment_counts = {
        (row[0], row[1]): row[2]
        for row in (db.session.query(Achievement.owner_type, Achievement.owner_id,
                                     func.count(func.distinct(Attachment.achievement_id)))
                    .select_from(Attachment)
                    .join(sub, sub.c.id == Attachment.achievement_id)
                    .join(Achievement, Achievement.id == Attachment.achievement_id)
                    .group_by(Achievement.owner_type, Achievement.owner_id)
                    .all())
    }
    result = []
    for model, owner_type in ((Teacher, 'teacher'), (Student, 'student')):
        rows = (_base(sub, model.id, model.name,
                      func.count(Achievement.id), func.max(Achievement.year))
                .join(model, and_(model.id == Achievement.owner_id,
                                  Achievement.owner_type == owner_type))
                .group_by(model.id, model.name)
                .order_by(func.count(Achievement.id).desc()).all())
        for person_id, name, count, last_year in rows:
            with_attachment = int(attachment_counts.get((owner_type, person_id), 0) or 0)
            result.append({
                'owner_type': owner_type,
                'owner_id': person_id,
                'name': name,
                'achievement_count': count,
                'value': count,
                'with_attachment': with_attachment,
                'missing_evidence': max(count - with_attachment, 0),
                'last_year': last_year,
            })
    result.sort(key=lambda item: item['achievement_count'], reverse=True)
    return result[:limit] if limit else result


def yearly_trend(query):
    """年度趋势 + 同比。"""
    items = grouped_counts(query, 'year')
    trend = []
    previous = None
    for item in items:
        current = item['value']
        change = None
        if previous not in (None, 0):
            change = round((current - previous) * 100.0 / previous, 1)
        trend.append({**item, 'change_percent': change})
        previous = current
    return trend


def missing_evidence_rows(query, limit=None):
    """缺件清单：已通过但没有支撑材料的成果。"""
    sub = _id_subquery(query)
    attached = (db.session.query(Attachment.achievement_id)
                .select_from(Attachment)
                .join(sub, sub.c.id == Attachment.achievement_id)
                .distinct().subquery())
    rows = (_base(sub, Achievement)
            .outerjoin(attached, attached.c.achievement_id == Achievement.id)
            .filter(attached.c.achievement_id.is_(None))
            .order_by(Achievement.year.desc(), Achievement.id.desc()))
    items = rows.limit(limit).all() if limit else rows.all()
    return [item for item in items]