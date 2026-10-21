"""认证指标点管理（工程教育认证毕业要求 1-12 及子指标点）。"""
from flask import Blueprint, request
from sqlalchemy import func

from audit import ACTION_CREATE, ACTION_DELETE, ACTION_UPDATE, log_operation
from auth_utils import admin_required, login_required
from extensions import db
from models import Achievement, AchievementIndicator, CertificationIndicator
from security import normalize_text
from utils import error, get_page_args, paginate, parse_bool, parse_int, success

indicator_bp = Blueprint('indicator', __name__, url_prefix='/api/indicators')


def _counts():
    rows = (db.session.query(AchievementIndicator.indicator_id, func.count())
            .group_by(AchievementIndicator.indicator_id).all())
    return {indicator_id: count for indicator_id, count in rows}


@indicator_bp.get('/', strict_slashes=False)
@login_required
def list_indicators():
    include_inactive = str(request.args.get('include_inactive', '')) in ('1', 'true')
    query = CertificationIndicator.query
    if not include_inactive:
        query = query.filter(CertificationIndicator.is_active.is_(True))
    query = query.order_by(CertificationIndicator.sort_order, CertificationIndicator.id)
    page, page_size = get_page_args()
    counts = _counts()
    return success(paginate(
        query, page, page_size,
        serializer=lambda items: [item.to_dict(achievement_count=counts.get(item.id, 0))
                                  for item in items],
    ))


@indicator_bp.post('/', strict_slashes=False)
@admin_required
def create_indicator():
    data = request.get_json(silent=True) or {}
    code = normalize_text(data.get('code'))
    name = normalize_text(data.get('name'))
    if not code:
        return error('请输入指标点编号')
    if not name:
        return error('请输入指标点名称')
    if CertificationIndicator.query.filter_by(code=code).first():
        return error('该指标点编号已存在')
    max_order = db.session.query(func.max(CertificationIndicator.sort_order)).scalar()
    item = CertificationIndicator(
        code=code,
        name=name,
        description=normalize_text(data.get('description')),
        sort_order=parse_int(data.get('sort_order'), (max_order or 0) + 1) or 0,
        is_active=parse_bool(data.get('is_active'), True),
    )
    db.session.add(item)
    db.session.commit()
    log_operation(ACTION_CREATE, 'indicator', item.id, f'新增认证指标点 {code} {name}')
    return success(item.to_dict(achievement_count=0), '指标点已新增')


@indicator_bp.put('/<int:indicator_id>')
@admin_required
def update_indicator(indicator_id):
    item = db.session.get(CertificationIndicator, indicator_id)
    if item is None:
        return error('指标点不存在', status=404, code=404)
    data = request.get_json(silent=True) or {}
    if 'code' in data:
        code = normalize_text(data.get('code'))
        if not code:
            return error('指标点编号不能为空')
        exists = CertificationIndicator.query.filter(
            CertificationIndicator.code == code,
            CertificationIndicator.id != item.id).first()
        if exists:
            return error('该指标点编号已存在')
        item.code = code
    if 'name' in data:
        name = normalize_text(data.get('name'))
        if not name:
            return error('指标点名称不能为空')
        item.name = name
    if 'description' in data:
        item.description = normalize_text(data.get('description'))
    if 'sort_order' in data:
        item.sort_order = parse_int(data.get('sort_order'), item.sort_order) or 0
    if 'is_active' in data:
        item.is_active = parse_bool(data.get('is_active'), True)
    db.session.commit()
    log_operation(ACTION_UPDATE, 'indicator', item.id, f'修改认证指标点 {item.code} {item.name}')
    return success(item.to_dict(), '指标点已更新')


@indicator_bp.delete('/<int:indicator_id>')
@admin_required
def delete_indicator(indicator_id):
    item = db.session.get(CertificationIndicator, indicator_id)
    if item is None:
        return error('指标点不存在', status=404, code=404)
    linked = AchievementIndicator.query.filter_by(indicator_id=indicator_id).count()
    AchievementIndicator.query.filter_by(indicator_id=indicator_id).delete(
        synchronize_session=False)
    code, name = item.code, item.name
    db.session.delete(item)
    db.session.commit()
    log_operation(ACTION_DELETE, 'indicator', indicator_id,
                  f'删除认证指标点 {code} {name}（解除 {linked} 条关联）')
    return success({'unlinked': linked}, f'指标点已删除，解除 {linked} 条成果关联')


@indicator_bp.get('/<int:indicator_id>/achievements')
@login_required
def indicator_achievements(indicator_id):
    item = db.session.get(CertificationIndicator, indicator_id)
    if item is None:
        return error('指标点不存在', status=404, code=404)
    from auth_utils import get_current_user
    from services import scope_achievements
    user = get_current_user()
    query = (Achievement.query
             .join(AchievementIndicator,
                   AchievementIndicator.achievement_id == Achievement.id)
             .filter(AchievementIndicator.indicator_id == indicator_id))
    query = scope_achievements(query, user).order_by(Achievement.year.desc(),
                                                    Achievement.id.desc())
    page, page_size = get_page_args()
    return success(paginate(query, page, page_size),
                   f'指标点 {item.code} {item.name} 关联的成果')