"""字典管理：院系 / 专业 / 职称 / 年级。

统计口径分裂的根因是这些字段以自由文本存储（"计算机学院" 与 "计算机学院 "）。
这里提供规范化字典 + 别名映射 + 合并功能，存量数据由迁移脚本自动登记。
"""
from flask import Blueprint, request
from sqlalchemy import or_

from audit import ACTION_CREATE, ACTION_DELETE, ACTION_MERGE_DICT, ACTION_UPDATE, log_operation
from auth_utils import admin_required
from constants import DICT_KINDS
from extensions import db
from models import DictItem, Student, Teacher
from security import normalize_text
from utils import error, get_page_args, paginate, parse_bool, parse_int, success

dict_bp = Blueprint('dict', __name__, url_prefix='/api/dicts')


def _validate_kind(kind):
    if kind not in DICT_KINDS:
        return None
    return kind


@dict_bp.get('/', strict_slashes=False)
@admin_required
def list_items():
    kind = normalize_text(request.args.get('kind'))
    keyword = normalize_text(request.args.get('keyword'))
    query = DictItem.query
    if kind:
        if not _validate_kind(kind):
            return error('字典类型不合法')
        query = query.filter(DictItem.kind == kind)
    if keyword:
        like = f'%{keyword}%'
        query = query.filter(or_(DictItem.name.like(like), DictItem.parent_name.like(like)))
    query = query.order_by(DictItem.kind, DictItem.sort_order, DictItem.id)
    page, page_size = get_page_args()
    return success(paginate(query, page, page_size))


@dict_bp.get('/grouped')
@admin_required
def grouped():
    """按类型分组返回，供下拉与"字典管理"页面使用。"""
    result = {}
    for kind in DICT_KINDS:
        items = (DictItem.query.filter_by(kind=kind)
                 .order_by(DictItem.sort_order, DictItem.id).all())
        result[kind] = [item.to_dict() for item in items]
    return success(result)


@dict_bp.get('/usage')
@admin_required
def usage():
    """列出实际数据中出现、但尚未登记进字典的取值（待规范化）。"""
    result = {}
    checks = {
        'department': [(Teacher, Teacher.department), (Student, Student.department)],
        'major': [(Student, Student.major)],
        'title': [(Teacher, Teacher.title)],
        'grade': [(Student, Student.grade)],
    }
    for kind, sources in checks.items():
        known = {item.name for item in DictItem.query.filter_by(kind=kind).all()}
        used = {}
        for model, column in sources:
            rows = db.session.query(column, db.func.count()).filter(
                column.isnot(None), column != '').group_by(column).all()
            for name, count in rows:
                used[name] = used.get(name, 0) + count
        result[kind] = [
            {'name': name, 'count': count, 'registered': name in known}
            for name, count in sorted(used.items(), key=lambda kv: -kv[1])
        ]
    return success(result)


@dict_bp.post('/', strict_slashes=False)
@admin_required
def create_item():
    data = request.get_json(silent=True) or {}
    kind = _validate_kind(normalize_text(data.get('kind')))
    if not kind:
        return error('字典类型不合法')
    name = normalize_text(data.get('name'))
    if not name:
        return error('请输入字典项名称')
    if DictItem.query.filter_by(kind=kind, name=name).first():
        return error('该字典项已存在')
    aliases = data.get('aliases') or []
    if isinstance(aliases, str):
        aliases = [normalize_text(item) for item in aliases.replace('，', ',').split(',')]
    aliases = [normalize_text(item) for item in aliases if normalize_text(item)]
    item = DictItem(
        kind=kind,
        name=name,
        aliases=aliases,
        parent_name=normalize_text(data.get('parent_name')) or None,
        sort_order=parse_int(data.get('sort_order'), 0) or 0,
        is_active=parse_bool(data.get('is_active'), True),
    )
    db.session.add(item)
    db.session.commit()
    log_operation(ACTION_CREATE, 'dict_item', item.id,
                  f'新增字典项 {DICT_KINDS[kind]}：{name}')
    return success(item.to_dict(), '字典项已新增')


@dict_bp.put('/<int:item_id>')
@admin_required
def update_item(item_id):
    item = db.session.get(DictItem, item_id)
    if item is None:
        return error('字典项不存在', status=404, code=404)
    data = request.get_json(silent=True) or {}
    old_name = item.name
    if 'name' in data:
        name = normalize_text(data.get('name'))
        if not name:
            return error('字典项名称不能为空')
        exists = DictItem.query.filter(DictItem.kind == item.kind, DictItem.name == name,
                                       DictItem.id != item.id).first()
        if exists:
            return error('同类型下已存在该名称')
        item.name = name
    if 'aliases' in data:
        aliases = data.get('aliases') or []
        if isinstance(aliases, str):
            aliases = [normalize_text(value) for value in aliases.replace('，', ',').split(',')]
        item.aliases = [normalize_text(value) for value in aliases if normalize_text(value)]
    if 'parent_name' in data:
        item.parent_name = normalize_text(data.get('parent_name')) or None
    if 'sort_order' in data:
        item.sort_order = parse_int(data.get('sort_order'), item.sort_order) or 0
    if 'is_active' in data:
        item.is_active = parse_bool(data.get('is_active'), True)
    if item.name != old_name:
        _rename_usage(item.kind, old_name, item.name)
    db.session.commit()
    log_operation(ACTION_UPDATE, 'dict_item', item.id,
                  f'修改字典项 {DICT_KINDS.get(item.kind, item.kind)}：'
                  f'{old_name} → {item.name}')
    return success(item.to_dict(), '字典项已更新')


@dict_bp.delete('/<int:item_id>')
@admin_required
def delete_item(item_id):
    item = db.session.get(DictItem, item_id)
    if item is None:
        return error('字典项不存在', status=404, code=404)
    kind, name = item.kind, item.name
    db.session.delete(item)
    db.session.commit()
    log_operation(ACTION_DELETE, 'dict_item', item_id,
                  f'删除字典项 {DICT_KINDS.get(kind, kind)}：{name}')
    return success(None, '字典项已删除（存量数据中的取值保持不变）')


@dict_bp.post('/merge')
@admin_required
def merge_items():
    """把 source 合并进 target：改写存量数据中的取值，并清空 source。"""
    data = request.get_json(silent=True) or {}
    source_id = parse_int(data.get('source_id'))
    target_id = parse_int(data.get('target_id'))
    source = db.session.get(DictItem, source_id) if source_id else None
    target = db.session.get(DictItem, target_id) if target_id else None
    if source is None or target is None:
        return error('请选择要合并的两个字典项')
    if source.kind != target.kind:
        return error('只能合并同一类型的字典项')
    if source.id == target.id:
        return error('源与目标不能相同')

    affected = _rename_usage(source.kind, source.name, target.name)
    aliases = set(target.alias_list()) | set(source.alias_list()) | {source.name}
    target.aliases = sorted(alias for alias in aliases if alias != target.name)
    db.session.delete(source)
    db.session.commit()
    log_operation(ACTION_MERGE_DICT, 'dict_item', target.id,
                  f'合并 {DICT_KINDS.get(source.kind, source.kind)}：'
                  f'{source.name} → {target.name}（影响 {affected} 行）')
    return success({'affected': affected}, f'已合并，更新了 {affected} 条数据')


def _rename_usage(kind, old_name, new_name):
    """把存量数据里的 old_name 改写为 new_name，返回影响行数。"""
    affected = 0
    if kind == 'department':
        affected += Teacher.query.filter(Teacher.department == old_name).update(
            {'department': new_name}, synchronize_session=False)
        affected += Student.query.filter(Student.department == old_name).update(
            {'department': new_name}, synchronize_session=False)
    elif kind == 'major':
        affected += Student.query.filter(Student.major == old_name).update(
            {'major': new_name}, synchronize_session=False)
    elif kind == 'title':
        affected += Teacher.query.filter(Teacher.title == old_name).update(
            {'title': new_name}, synchronize_session=False)
    elif kind == 'grade':
        affected += Student.query.filter(Student.grade == old_name).update(
            {'grade': new_name}, synchronize_session=False)
    return affected