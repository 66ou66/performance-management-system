from flask import Blueprint, request

import analytics
from auth_utils import get_current_user, login_required, review_required
from constants import STATUS_APPROVED
from utils import error, parse_int, success

stats_bp = Blueprint('stats', __name__, url_prefix='/api/stats')

VALID_DIMENSIONS = analytics.DIMENSIONS


def _filter_args():
    """统计接口支持列表页的全部筛选条件 + 自定义状态范围。"""
    args = dict(request.args)
    if not (args.get('status') or '').strip():
        args['status'] = STATUS_APPROVED
    return args


def _filtered():
    user = get_current_user()
    return user, analytics.filtered_achievements(user, _filter_args())


@stats_bp.get('/overview')
@login_required
def overview():
    user, query = _filtered()
    payload = {
        'counts': analytics.overview(user, query),
        'role': user.role,
        'filters': {key: value for key, value in request.args.items()},
    }
    payload.update(analytics.all_breakdowns(query))
    return success(payload)


@stats_bp.get('/breakdown')
@login_required
def breakdown():
    _user, query = _filtered()
    dimension = (request.args.get('dimension') or 'category').strip()
    if dimension not in VALID_DIMENSIONS:
        return error('统计维度不合法：' + '、'.join(VALID_DIMENSIONS))
    return success({
        'dimension': dimension,
        'total': query.count(),
        'items': analytics.grouped_counts(query, dimension),
    })


@stats_bp.get('/ranking')
@login_required
def ranking():
    _user, query = _filtered()
    by = (request.args.get('by') or 'teacher').strip()
    if by not in ('teacher', 'student'):
        return error('排行类型只能是 teacher 或 student')
    limit = parse_int(request.args.get('limit'), 10) or 10
    limit = min(max(limit, 1), 50)
    only_advisors = str(request.args.get('only_advisors', '')) in ('1', 'true', 'True')
    return success({
        'by': by,
        'items': analytics.rankings(query, by=by, limit=limit, only_advisors=only_advisors),
    })


@stats_bp.get('/cross')
@login_required
def cross():
    _user, query = _filtered()
    row = (request.args.get('row') or 'category').strip()
    col = (request.args.get('col') or 'year').strip()
    if row not in VALID_DIMENSIONS or col not in VALID_DIMENSIONS:
        return error('交叉统计维度不合法')
    payload = analytics.cross_tab(query, row, col)
    payload.update({'row_dimension': row, 'col_dimension': col})
    return success(payload)


@stats_bp.get('/trend')
@login_required
def trend():
    _user, query = _filtered()
    return success({'items': analytics.yearly_trend(query)})


@stats_bp.get('/persons')
@login_required
def persons():
    """师生汇总（管理员/审核员用于认证材料汇总表）。"""
    _user, query = _filtered()
    limit = parse_int(request.args.get('limit'))
    return success({'items': analytics.person_summary(query, limit=limit)})


@stats_bp.get('/indicators')
@login_required
def indicators():
    """认证指标点覆盖情况。"""
    _user, query = _filtered()
    return success(analytics.indicator_coverage(query))


@stats_bp.get('/missing-evidence')
@login_required
def missing_evidence():
    """缺件清单（统计口径）。"""
    _user, query = _filtered()
    rows = analytics.missing_evidence_rows(query)
    from models import Achievement
    return success({
        'total': len(rows),
        'items': Achievement.to_dict_list(rows),
    })


@stats_bp.get('/dashboard')
@login_required
def dashboard():
    """看板一次性取数，避免前端并发 6 个请求。"""
    user, query = _filtered()
    return success({
        'counts': analytics.overview(user, query),
        'role': user.role,
        'by_category': analytics.grouped_counts(query, 'category'),
        'by_year': analytics.grouped_counts(query, 'year'),
        'by_level': analytics.grouped_counts(query, 'level'),
        'by_department': analytics.grouped_counts(query, 'department'),
        'by_academic_year': analytics.grouped_counts(query, 'academic_year'),
        'trend': analytics.yearly_trend(query),
        'teacher_ranking': analytics.rankings(query, by='teacher', limit=10),
        'student_ranking': analytics.rankings(query, by='student', limit=10),
        'advisor_ranking': analytics.rankings(query, by='teacher', limit=10, only_advisors=True),
    })


@stats_bp.get('/scope-options')
@review_required
def scope_options():
    """给审核员/管理员看的可选筛选范围（院系、学年）。"""
    from services import dict_names
    return success({
        'departments': dict_names('department'),
        'majors': dict_names('major'),
        'grades': dict_names('grade'),
    })