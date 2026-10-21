from datetime import datetime

from flask import Blueprint

from auth_utils import login_required
from constants import (
    ALL_CATEGORIES,
    ATTACHMENT_CATEGORIES,
    AWARD_RANKS,
    CATEGORIES_WITH_ADVISOR,
    DICT_KINDS,
    FIELD_TEMPLATES,
    LEVELS,
    LEVELS_BY_CATEGORY,
    ROLE_RANKS,
    ROLES,
    STATUSES,
    STUDENT_CATEGORIES,
    TEACHER_CATEGORIES,
)
from models import CertificationIndicator, Teacher
from services import category_matches_owner, dict_names
from utils import success

meta_bp = Blueprint('meta', __name__, url_prefix='/api/meta')


@meta_bp.get('/options')
@login_required
def options():
    current_year = datetime.now().year
    span = 12
    years = list(range(current_year, current_year - span, -1))
    academic_years = [f'{year}-{year + 1}' for year in years]
    indicators = CertificationIndicator.query.filter_by(is_active=True).order_by(
        CertificationIndicator.sort_order, CertificationIndicator.id).all()
    return success({
        'teacher_categories': TEACHER_CATEGORIES,
        'student_categories': STUDENT_CATEGORIES,
        'all_categories': ALL_CATEGORIES,
        'categories_with_advisor': CATEGORIES_WITH_ADVISOR,
        'field_templates': FIELD_TEMPLATES,
        'levels': LEVELS,
        'levels_by_category': LEVELS_BY_CATEGORY,
        'award_ranks': AWARD_RANKS,
        'role_ranks': ROLE_RANKS,
        'statuses': STATUSES,
        'roles': ROLES,
        'attachment_categories': ATTACHMENT_CATEGORIES,
        'years': years,
        'academic_years': academic_years,
        'departments': dict_names('department'),
        'majors': dict_names('major'),
        'titles': dict_names('title'),
        'grades': dict_names('grade'),
        'dict_kinds': [{'value': key, 'label': label} for key, label in DICT_KINDS.items()],
        'indicators': [item.to_dict() for item in indicators],
    })


@meta_bp.get('/dict-options')
@login_required
def dict_options():
    return success({kind: dict_names(kind) for kind in DICT_KINDS})


@meta_bp.get('/advisor-options')
@login_required
def advisor_options():
    """可作为指导教师的教师下拉。"""
    items = Teacher.query.order_by(Teacher.name).all()
    return success([
        {
            'id': item.id,
            'name': item.name,
            'label': f'{item.name}（{item.department or "未设院系"}）',
            'department': item.department,
        }
        for item in items
    ])


@meta_bp.get('/categories')
@login_required
def categories():
    """返回类别 → 归属人类型 → 级别选项的映射，供前端级联选择。"""
    return success([
        {
            'value': name,
            'owner_type': 'teacher' if category_matches_owner(name, 'teacher') else 'student',
            'levels': LEVELS_BY_CATEGORY.get(name, []),
            'fields': FIELD_TEMPLATES.get(name, []),
        }
        for name in ALL_CATEGORIES
    ])