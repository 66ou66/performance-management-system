"""通用工具：统一响应信封、分页、类型解析。"""
from flask import jsonify, request


def success(data=None, message='操作成功', **extra):
    payload = {'code': 0, 'message': message, 'data': data}
    payload.update(extra)
    return jsonify(payload)


def error(message='操作失败', status=400, code=1):
    return jsonify({'code': code, 'message': message, 'data': None}), status


def get_page_args(default_size=10):
    max_size = 100
    try:
        from flask import current_app
        max_size = int(current_app.config.get('PAGE_SIZE_MAX', 100))
    except Exception:  # pragma: no cover - 无应用上下文时兜底
        max_size = 100
    try:
        page = int(request.args.get('page', 1))
    except (TypeError, ValueError):
        page = 1
    try:
        page_size = int(request.args.get('page_size', default_size))
    except (TypeError, ValueError):
        page_size = default_size
    return max(page, 1), min(max(page_size, 1), max_size)


def _default_serializer(items, **kwargs):
    if not items:
        return []
    bulk = getattr(type(items[0]), 'to_dict_list', None)
    if callable(bulk):
        return bulk(items, **kwargs)
    return [item.to_dict() for item in items]


def paginate(query, page, page_size, serializer=None, **serializer_kwargs):
    """分页并批量序列化。

    serializer 接收整个 items 列表，因此实现里可以做批量预取，
    避免旧版 `[item.to_dict() for item in items]` 造成的 N+1 查询。
    """
    pagination = query.paginate(page=page, per_page=page_size, error_out=False)
    items = pagination.items
    if not items:
        data = []
    elif serializer is None:
        data = _default_serializer(items, **serializer_kwargs)
    else:
        data = serializer(items, **serializer_kwargs)
    return {
        'items': data,
        'total': pagination.total,
        'page': page,
        'page_size': page_size,
        'pages': pagination.pages,
    }


def parse_int(value, default=None):
    if value is None or value == '':
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def parse_bool(value, default=False):
    if value is None or value == '':
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ('1', 'true', 'yes', 'on', 'y')


def paginated_ids(pagination_items, key='id'):
    return [getattr(item, key, item) for item in pagination_items]