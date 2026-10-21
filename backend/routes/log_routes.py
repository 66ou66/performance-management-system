"""操作日志查询（认证追溯：谁在什么时候改了什么）。"""
from datetime import datetime, timedelta

from flask import Blueprint, request
from sqlalchemy import or_

from audit import ACTION_LABELS, TARGET_LABELS
from auth_utils import admin_required
from extensions import db
from models import OperationLog
from security import normalize_text
from utils import error, get_page_args, paginate, parse_int, success

log_bp = Blueprint('log', __name__, url_prefix='/api/logs')


@log_bp.get('/', strict_slashes=False)
@admin_required
def list_logs():
    action = normalize_text(request.args.get('action'))
    target_type = normalize_text(request.args.get('target_type'))
    username = normalize_text(request.args.get('username'))
    keyword = normalize_text(request.args.get('keyword'))
    start = normalize_text(request.args.get('start_date'))
    end = normalize_text(request.args.get('end_date'))
    days = parse_int(request.args.get('days'))

    query = OperationLog.query
    if action:
        query = query.filter(OperationLog.action == action)
    if target_type:
        query = query.filter(OperationLog.target_type == target_type)
    if username:
        query = query.filter(OperationLog.username.like(f'%{username}%'))
    if keyword:
        like = f'%{keyword}%'
        query = query.filter(or_(OperationLog.summary.like(like),
                                 OperationLog.username.like(like)))
    if days:
        query = query.filter(OperationLog.created_at >= datetime.now() - timedelta(days=days))
    if start:
        try:
            query = query.filter(OperationLog.created_at >= datetime.strptime(start, '%Y-%m-%d'))
        except ValueError:
            return error('开始日期格式应为 YYYY-MM-DD')
    if end:
        try:
            query = query.filter(OperationLog.created_at <
                                 datetime.strptime(end, '%Y-%m-%d') + timedelta(days=1))
        except ValueError:
            return error('结束日期格式应为 YYYY-MM-DD')

    query = query.order_by(OperationLog.id.desc())
    page, page_size = get_page_args()
    return success(paginate(query, page, page_size))


@log_bp.get('/options')
@admin_required
def log_options():
    rows = db.session.query(OperationLog.action).distinct().all()
    actions = sorted({row[0] for row in rows if row[0]})
    return success({
        'actions': [{'value': value, 'label': ACTION_LABELS.get(value, value)}
                    for value in actions],
        'targets': [{'value': key, 'label': label} for key, label in TARGET_LABELS.items()],
    })


@log_bp.get('/summary')
@admin_required
def log_summary():
    """近 14 天的操作分布，用于审计页面的趋势图。"""
    since = datetime.now() - timedelta(days=14)
    rows = (db.session.query(db.func.date(OperationLog.created_at), db.func.count())
            .filter(OperationLog.created_at >= since)
            .group_by(db.func.date(OperationLog.created_at)).all())
    by_action = (db.session.query(OperationLog.action, db.func.count())
                 .filter(OperationLog.created_at >= since)
                 .group_by(OperationLog.action).all())
    return success({
        'daily': [{'name': str(day), 'value': count} for day, count in rows],
        'by_action': [{'name': ACTION_LABELS.get(action, action), 'value': count}
                      for action, count in by_action],
        'total': OperationLog.query.count(),
    })