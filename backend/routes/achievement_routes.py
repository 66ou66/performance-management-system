import os
from datetime import datetime

from flask import Blueprint, current_app, request, send_from_directory

from audit import (
    ACTION_CREATE,
    ACTION_DELETE,
    ACTION_DOWNLOAD,
    ACTION_PURGE,
    ACTION_RESTORE,
    ACTION_REVIEW,
    ACTION_UPDATE,
    ACTION_UPLOAD,
    diff_dict,
    log_operation,
)
from auth_utils import get_current_user, login_required, review_required
from constants import (
    ATTACHMENT_CATEGORIES,
    ROLE_ADMIN,
    ROLE_REVIEWER,
    STATUS_APPROVED,
    STATUS_PENDING,
    STATUS_REJECTED,
    STATUS_DRAFT,
)
from extensions import db
from models import Achievement, Attachment, Student, Teacher
from services import (
    apply_indicators,
    build_achievement_query,
    default_status_for,
    is_admin,
    is_elevated,
    remove_achievement_files,
    remove_file,
    relative_storage_dir,
    unique_stored_name,
)
from security import (
    allowed_file,
    guess_attachment_category,
    guess_mime,
    mime_allowed,
    safe_filename,
)
from utils import error, get_page_args, paginate, parse_bool, parse_int, success
from validators import parse_id_list, validate_achievement, validate_attachment_category

achievement_bp = Blueprint('achievement', __name__, url_prefix='/api/achievements')

EDITABLE_FIELDS = ('title', 'year', 'academic_year', 'level', 'role_rank',
                   'description', 'category', 'status', 'advisor_id')


# --------------------------------------------------------------------------- #
# 权限与取数
# --------------------------------------------------------------------------- #
def _can_view(user, achievement):
    if is_elevated(user):
        return True
    return (achievement.owner_type == user.owner_type
            and achievement.owner_id == user.owner_id)


def _can_edit(user, achievement):
    if is_admin(user):
        return True
    return (achievement.owner_type == user.owner_type
            and achievement.owner_id == user.owner_id)


def _fetch(achievement_id, include_deleted=True):
    item = db.session.get(Achievement, achievement_id)
    if item is None:
        return None
    if not include_deleted and item.is_deleted:
        return None
    return item


def _achievement_payload(item, with_review_comment=False):
    return item.to_dict(
        attachments=item.attachment_rows(),
        indicators=item.indicator_rows(),
        review_comment=with_review_comment,
    )


# --------------------------------------------------------------------------- #
# 列表 / 详情
# --------------------------------------------------------------------------- #
@achievement_bp.get('/', strict_slashes=False)
@login_required
def list_achievements():
    user = get_current_user()
    query = build_achievement_query(user, request.args)
    page, page_size = get_page_args()
    return success(paginate(query, page, page_size))


@achievement_bp.get('/trash')
@login_required
def list_trash():
    """回收站：软删除的成果。"""
    user = get_current_user()
    query = build_achievement_query(user, request.args, include_deleted=True)
    query = query.filter(Achievement.is_deleted.is_(True))
    page, page_size = get_page_args()
    return success(paginate(query, page, page_size, with_review_comment=True))


@achievement_bp.get('/missing-evidence')
@login_required
def missing_evidence():
    """缺件清单：已通过的成果中没有支撑材料的记录。"""
    user = get_current_user()
    args = dict(request.args)
    args.setdefault('has_attachment', '0')
    args.setdefault('status', STATUS_APPROVED)
    query = build_achievement_query(user, args)
    page, page_size = get_page_args()
    return success(paginate(query, page, page_size),
                   '以下成果缺少支撑材料，请及时补充')


@achievement_bp.get('/<int:achievement_id>')
@login_required
def get_achievement(achievement_id):
    user = get_current_user()
    item = _fetch(achievement_id)
    if item is None:
        return error('成果不存在', status=404, code=404)
    if not _can_view(user, item):
        return error('无权查看该成果', status=403, code=403)
    return success(_achievement_payload(item, with_review_comment=True))


# --------------------------------------------------------------------------- #
# 新增 / 修改 / 删除
# --------------------------------------------------------------------------- #
@achievement_bp.post('/', strict_slashes=False)
@login_required
def create_achievement():
    user = get_current_user()
    data = request.get_json(silent=True) or {}
    if user.role == ROLE_REVIEWER:
        return error('审核员账号仅用于审核，不能录入成果', status=403, code=403)

    if is_admin(user):
        owner_type = (data.get('owner_type') or '').strip()
        owner_id = parse_int(data.get('owner_id'))
    else:
        owner_type = user.owner_type
        owner_id = user.owner_id
    if owner_type not in ('teacher', 'student') or not owner_id:
        return error('请选择有效的所属人')
    if not _owner_exists(owner_type, owner_id):
        return error('请选择有效的所属人')

    payload, message = validate_achievement(data, owner_type, owner_id)
    if message:
        return error(message)

    status = payload.pop('status', None)
    if status in (STATUS_APPROVED, STATUS_REJECTED) and not is_elevated(user):
        return error('只有管理员或审核员可以直接确定审核结果', status=403, code=403)
    status = status or default_status_for(user)
    indicator_ids = payload.pop('indicator_ids', [])

    item = Achievement(
        owner_type=owner_type,
        owner_id=owner_id,
        created_by=user.id,
        updated_by=user.id,
        status=status,
        **payload,
    )
    if status == STATUS_PENDING:
        item.submitted_at = datetime.now()
    db.session.add(item)
    db.session.flush()
    apply_indicators(item, indicator_ids)
    db.session.commit()
    log_operation(ACTION_CREATE, 'achievement', item.id,
                  f'新增成果「{item.title}」（{item.category}）')
    return success(_achievement_payload(item), '成果新增成功')


@achievement_bp.put('/<int:achievement_id>')
@login_required
def update_achievement(achievement_id):
    user = get_current_user()
    item = _fetch(achievement_id)
    if item is None:
        return error('成果不存在', status=404, code=404)
    if item.is_deleted:
        return error('该成果在回收站中，请先恢复后再修改', status=400, code=400)
    if not _can_edit(user, item):
        return error('无权修改该成果', status=403, code=403)

    data = request.get_json(silent=True) or {}
    if is_admin(user) and ('owner_type' in data or 'owner_id' in data):
        owner_type = (data.get('owner_type') or item.owner_type).strip()
        owner_id = parse_int(data.get('owner_id'), item.owner_id)
        if not _owner_exists(owner_type, owner_id):
            return error('请选择有效的所属人')
        item.owner_type = owner_type
        item.owner_id = owner_id

    before = _achievement_payload(item)
    payload, message = validate_achievement(data, item.owner_type, item.owner_id,
                                            existing=item, partial=True)
    if message:
        return error(message)

    indicator_ids = payload.pop('indicator_ids', None)
    status_change = payload.get('status')
    if status_change in (STATUS_APPROVED, STATUS_REJECTED) and not is_elevated(user):
        return error('只有管理员或审核员可以确定审核结果', status=403, code=403)
    for field, value in payload.items():
        setattr(item, field, value)
    if indicator_ids is not None:
        apply_indicators(item, indicator_ids)
    if status_change == STATUS_PENDING and not item.submitted_at:
        item.submitted_at = datetime.now()
    item.updated_by = user.id
    db.session.commit()

    after = _achievement_payload(item)
    changes = diff_dict(before, after, EDITABLE_FIELDS)
    log_operation(ACTION_UPDATE, 'achievement', item.id,
                  f'修改成果「{item.title}」', detail={'changes': changes} if changes else None)
    return success(after, '成果已更新')


@achievement_bp.delete('/<int:achievement_id>')
@login_required
def delete_achievement(achievement_id):
    """默认软删除（进回收站）；?hard=1 且管理员时彻底删除。"""
    user = get_current_user()
    item = _fetch(achievement_id)
    if item is None:
        return error('成果不存在', status=404, code=404)
    if not _can_edit(user, item):
        return error('无权删除该成果', status=403, code=403)

    hard = parse_bool(request.args.get('hard'))
    if hard:
        return _purge(user, item)
    if item.is_deleted:
        return error('该成果已在回收站中', status=400, code=400)
    item.is_deleted = True
    item.deleted_at = datetime.now()
    item.deleted_by = user.id
    db.session.commit()
    log_operation(ACTION_DELETE, 'achievement', item.id,
                  f'删除成果「{item.title}」（可在回收站恢复）',
                  detail={'soft': True})
    return success({'id': item.id, 'is_deleted': True},
                   '成果已移入回收站，可在回收站恢复或彻底删除')


def _purge(user, item):
    removed = remove_achievement_files(current_app.config, item)
    from models import AchievementIndicator
    Attachment.query.filter_by(achievement_id=item.id).delete(synchronize_session=False)
    AchievementIndicator.query.filter_by(achievement_id=item.id).delete(
        synchronize_session=False)
    title = item.title
    item_id = item.id
    db.session.delete(item)
    db.session.commit()
    log_operation(ACTION_PURGE, 'achievement', item_id,
                  f'彻底删除成果「{title}」', detail={'files_removed': removed})
    return success(None, '成果及其支撑材料已彻底删除')


@achievement_bp.post('/<int:achievement_id>/restore')
@login_required
def restore_achievement(achievement_id):
    user = get_current_user()
    item = _fetch(achievement_id)
    if item is None:
        return error('成果不存在', status=404, code=404)
    if not _can_edit(user, item):
        return error('无权恢复该成果', status=403, code=403)
    if not item.is_deleted:
        return error('该成果未被删除', status=400, code=400)
    item.is_deleted = False
    item.deleted_at = None
    item.deleted_by = None
    db.session.commit()
    log_operation(ACTION_RESTORE, 'achievement', item.id, f'从回收站恢复成果「{item.title}」')
    return success(_achievement_payload(item), '成果已恢复')


# --------------------------------------------------------------------------- #
# 审核流
# --------------------------------------------------------------------------- #
@achievement_bp.post('/<int:achievement_id>/submit')
@login_required
def submit_for_review(achievement_id):
    user = get_current_user()
    item = _fetch(achievement_id)
    if item is None:
        return error('成果不存在', status=404, code=404)
    if not _can_edit(user, item):
        return error('无权提交该成果', status=403, code=403)
    if item.is_deleted:
        return error('回收站中的成果不能提交审核', status=400, code=400)
    if item.status == STATUS_APPROVED:
        return error('该成果已通过审核', status=400, code=400)
    item.status = STATUS_PENDING
    item.submitted_at = datetime.now()
    item.review_comment = None
    item.reviewer_id = None
    item.reviewed_at = None
    item.updated_by = user.id
    db.session.commit()
    log_operation(ACTION_UPDATE, 'achievement', item.id, f'提交成果「{item.title}」送审')
    return success(_achievement_payload(item), '已提交审核')


@achievement_bp.post('/<int:achievement_id>/review')
@review_required
def review_achievement(achievement_id):
    user = get_current_user()
    item = _fetch(achievement_id)
    if item is None:
        return error('成果不存在', status=404, code=404)
    if item.is_deleted:
        return error('回收站中的成果不能审核', status=400, code=400)
    data = request.get_json(silent=True) or {}
    action = (data.get('action') or '').strip().lower()
    comment = (data.get('comment') or '').strip()[:500]
    if action not in ('approve', 'reject', 'withdraw'):
        return error('审核动作不合法')
    if action == 'approve':
        item.status = STATUS_APPROVED
    elif action == 'reject':
        if not comment:
            return error('驳回时必须填写审核意见')
        item.status = STATUS_REJECTED
    else:
        item.status = STATUS_DRAFT
    item.reviewer_id = user.id
    item.reviewed_at = datetime.now()
    item.review_comment = comment
    db.session.commit()
    label = {'approve': '通过', 'reject': '驳回', 'withdraw': '撤回为草稿'}[action]
    log_operation(ACTION_REVIEW, 'achievement', item.id,
                  f'{label}成果「{item.title}」', detail={'comment': comment})
    return success(_achievement_payload(item, with_review_comment=True), f'已{label}')


# --------------------------------------------------------------------------- #
# 批量操作
# --------------------------------------------------------------------------- #
BATCH_ACTIONS = ('delete', 'restore', 'purge', 'set_level', 'set_status',
                 'add_indicators', 'remove_indicators')


@achievement_bp.post('/batch')
@login_required
def batch_operation():
    user = get_current_user()
    data = request.get_json(silent=True) or {}
    ids = parse_id_list(data.get('ids'))
    action = (data.get('action') or '').strip()
    if not ids:
        return error('请选择要操作的成果')
    if action not in BATCH_ACTIONS:
        return error('批量操作类型不合法')

    items = Achievement.query.filter(Achievement.id.in_(ids)).all()
    allowed = [item for item in items if _can_edit(user, item)]
    if not allowed:
        return error('没有可操作的成果（可能无权修改）', status=403, code=403)
    skipped = len(items) - len(allowed)
    affected = 0

    if action == 'delete':
        for item in allowed:
            if not item.is_deleted:
                item.is_deleted = True
                item.deleted_at = datetime.now()
                item.deleted_by = user.id
                affected += 1
    elif action == 'restore':
        for item in allowed:
            if item.is_deleted:
                item.is_deleted = False
                item.deleted_at = None
                item.deleted_by = None
                affected += 1
    elif action == 'purge':
        from models import AchievementIndicator
        for item in list(allowed):
            remove_achievement_files(current_app.config, item)
            Attachment.query.filter_by(achievement_id=item.id).delete(
                synchronize_session=False)
            AchievementIndicator.query.filter_by(achievement_id=item.id).delete(
                synchronize_session=False)
            db.session.delete(item)
            affected += 1
    elif action == 'set_level':
        from validators import validate_achievement as _validate
        for item in allowed:
            payload, message = _validate({'level': data.get('level')},
                                         item.owner_type, item.owner_id,
                                         existing=item, partial=True)
            if message:
                continue
            item.level = payload.get('level', '')
            item.updated_by = user.id
            affected += 1
    elif action == 'set_status':
        status = (data.get('status') or '').strip()
        if status not in (STATUS_DRAFT, STATUS_PENDING, STATUS_APPROVED, STATUS_REJECTED):
            return error('审核状态不合法')
        if status in (STATUS_APPROVED, STATUS_REJECTED) and user.role not in (ROLE_ADMIN, ROLE_REVIEWER):
            return error('只有管理员或审核员可以批量改变审核状态', status=403, code=403)
        for item in allowed:
            item.status = status
            if status in (STATUS_APPROVED, STATUS_REJECTED):
                item.reviewer_id = user.id
                item.reviewed_at = datetime.now()
            item.updated_by = user.id
            affected += 1
    elif action == 'add_indicators':
        indicator_ids = parse_id_list(data.get('indicator_ids'))
        if not indicator_ids:
            return error('请选择认证指标点')
        for item in allowed:
            existing = {row.id for row in item.indicator_rows()}
            for indicator_id in indicator_ids:
                if indicator_id not in existing:
                    from models import AchievementIndicator
                    db.session.add(AchievementIndicator(
                        achievement_id=item.id, indicator_id=indicator_id))
            affected += 1
    elif action == 'remove_indicators':
        from models import AchievementIndicator
        for item in allowed:
            AchievementIndicator.query.filter_by(achievement_id=item.id).delete()
            affected += 1

    db.session.commit()
    log_operation(ACTION_UPDATE, 'achievement', None,
                  f'批量{action}：影响 {affected} 条',
                  detail={'action': action, 'ids': ids, 'affected': affected})
    message = f'已处理 {affected} 条'
    if skipped:
        message += f'，跳过 {skipped} 条（无权限）'
    return success({'affected': affected, 'skipped': skipped}, message)


# --------------------------------------------------------------------------- #
# 支撑材料
# --------------------------------------------------------------------------- #
def _store_uploaded_file(item, file, category):
    config = current_app.config
    if not allowed_file(file.filename, config['ALLOWED_EXTENSIONS']):
        return None, '不支持的文件类型'
    if not mime_allowed(file.filename, file.mimetype):
        return None, '文件类型与内容不匹配，已拒绝上传'
    relative_dir = relative_storage_dir(item)
    target_dir = os.path.join(config['UPLOAD_FOLDER'], relative_dir)
    os.makedirs(target_dir, exist_ok=True)
    stored_name = unique_stored_name(target_dir, safe_filename(file.filename))
    full_path = os.path.join(target_dir, stored_name)
    file.save(full_path)
    size = os.path.getsize(full_path)
    row = Attachment(
        achievement_id=item.id,
        stored_path=os.path.join(relative_dir, stored_name).replace('\\', '/'),
        original_name=safe_filename(file.filename),
        category=category,
        size=size,
        mime=file.mimetype or guess_mime(file.filename),
        uploaded_by=get_current_user().id,
    )
    db.session.add(row)
    return row, None


@achievement_bp.get('/<int:achievement_id>/attachments')
@login_required
def list_attachments(achievement_id):
    user = get_current_user()
    item = _fetch(achievement_id)
    if item is None:
        return error('成果不存在', status=404, code=404)
    if not _can_view(user, item):
        return error('无权查看该成果', status=403, code=403)
    return success(Attachment.to_dict_list(item.attachment_rows()))


@achievement_bp.post('/<int:achievement_id>/attachments')
@login_required
def upload_attachments(achievement_id):
    user = get_current_user()
    item = _fetch(achievement_id)
    if item is None:
        return error('成果不存在', status=404, code=404)
    if not _can_edit(user, item):
        return error('无权上传该成果的支撑材料', status=403, code=403)
    files = request.files.getlist('file') or request.files.getlist('files')
    files = [f for f in files if f and f.filename]
    if not files:
        return error('请选择要上传的文件')
    limit = current_app.config['MAX_ATTACHMENT_COUNT']
    current_count = Attachment.query.filter_by(achievement_id=item.id).count()
    if current_count + len(files) > limit:
        return error(f'单条成果最多上传 {limit} 份支撑材料')
    category, message = validate_attachment_category(
        request.form.get('category'), ATTACHMENT_CATEGORIES)
    if message:
        return error(message)
    created = []
    for file in files:
        row_category = category
        if row_category == '其他':
            row_category = guess_attachment_category(file.filename)
        row, message = _store_uploaded_file(item, file, row_category)
        if message:
            for done in created:
                remove_file(current_app.config, done.stored_path)
            db.session.rollback()
            return error(message)
        created.append(row)
    if item.attachment_path is None and created:
        item.attachment_path = created[0].stored_path
    db.session.commit()
    log_operation(ACTION_UPLOAD, 'achievement', item.id,
                  f'上传 {len(created)} 份支撑材料：'
                  + '、'.join(row.original_name for row in created))
    return success(Attachment.to_dict_list(item.attachment_rows()),
                   f'已上传 {len(created)} 份支撑材料')


@achievement_bp.delete('/<int:achievement_id>/attachments/<int:attachment_id>')
@login_required
def delete_attachment(achievement_id, attachment_id):
    user = get_current_user()
    item = _fetch(achievement_id)
    if item is None:
        return error('成果不存在', status=404, code=404)
    if not _can_edit(user, item):
        return error('无权删除该支撑材料', status=403, code=403)
    row = db.session.get(Attachment, attachment_id)
    if row is None or row.achievement_id != item.id:
        return error('支撑材料不存在', status=404, code=404)
    name = row.original_name
    remove_file(current_app.config, row.stored_path)
    db.session.delete(row)
    db.session.flush()
    if item.attachment_path == row.stored_path:
        remaining = item.attachment_rows()
        item.attachment_path = remaining[0].stored_path if remaining else None
    db.session.commit()
    log_operation(ACTION_DELETE, 'attachment', attachment_id,
                  f'删除支撑材料「{name}」（所属成果 {item.id}）')
    return success(Attachment.to_dict_list(item.attachment_rows()), '支撑材料已删除')


@achievement_bp.get('/<int:achievement_id>/attachments/<int:attachment_id>/download')
@login_required
def download_attachment(achievement_id, attachment_id):
    user = get_current_user()
    item = _fetch(achievement_id)
    if item is None:
        return error('成果不存在', status=404, code=404)
    if not _can_view(user, item):
        return error('无权下载该附件', status=403, code=403)
    row = db.session.get(Attachment, attachment_id)
    if row is None or row.achievement_id != item.id:
        return error('支撑材料不存在', status=404, code=404)
    return _send_attachment(row)


def _send_attachment(row):
    folder = current_app.config['UPLOAD_FOLDER']
    full = os.path.join(folder, row.stored_path)
    if not os.path.exists(full):
        return error('附件文件已丢失，请重新上传', status=404, code=404)
    preview = request.args.get('preview') in ('1', 'true', 'yes')
    if not preview:
        log_operation(ACTION_DOWNLOAD, 'attachment', row.id,
                      f'下载支撑材料「{row.original_name}」', commit=True)
    return send_from_directory(
        folder,
        row.stored_path,
        as_attachment=not preview,
        download_name=row.original_name,
    )


# --------------------------------------------------------------------------- #
# 兼容旧接口：单附件上传 / 下载（原前端与校验脚本仍在使用）
# --------------------------------------------------------------------------- #
@achievement_bp.post('/<int:achievement_id>/attachment')
@login_required
def upload_attachment_legacy(achievement_id):
    user = get_current_user()
    item = _fetch(achievement_id)
    if item is None:
        return error('成果不存在', status=404, code=404)
    if not _can_edit(user, item):
        return error('无权上传该成果的附件', status=403, code=403)
    file = request.files.get('file')
    if file is None or not file.filename:
        return error('请选择要上传的文件')
    category, message = validate_attachment_category(
        request.form.get('category') or guess_attachment_category(file.filename),
        ATTACHMENT_CATEGORIES)
    if message:
        return error(message)
    row, message = _store_uploaded_file(item, file, category)
    if message:
        db.session.rollback()
        return error(message)
    # 兼容字段：旧前端只认 attachment_name / attachment_path，
    # 旧接口语义是"替换主附件"，因此这里始终指向刚上传的这一份
    item.attachment_path = row.stored_path
    db.session.commit()
    log_operation(ACTION_UPLOAD, 'achievement', item.id,
                  f'上传附件「{row.original_name}」')
    return success(_achievement_payload(item), '附件上传成功')


@achievement_bp.get('/<int:achievement_id>/attachment')
@login_required
def download_attachment_legacy(achievement_id):
    user = get_current_user()
    item = _fetch(achievement_id)
    if item is None:
        return error('成果不存在', status=404, code=404)
    if not _can_view(user, item):
        return error('无权下载该附件', status=403, code=403)
    rows = item.attachment_rows()
    preview = request.args.get('preview') in ('1', 'true', 'yes')
    # 旧接口语义：下载"主附件"（attachment_path 指向的那一份）
    if item.attachment_path:
        full = os.path.join(current_app.config['UPLOAD_FOLDER'], item.attachment_path)
        if os.path.exists(full):
            name = next((a.original_name for a in rows
                         if a.stored_path == item.attachment_path), None)
            if name is None:
                name = item.attachment_path.split('_', 1)[1] \
                    if '_' in item.attachment_path else os.path.basename(item.attachment_path)
            if not preview:
                log_operation(ACTION_DOWNLOAD, 'attachment', None,
                              f'下载支撑材料「{name}」', commit=True)
            return send_from_directory(
                current_app.config['UPLOAD_FOLDER'], item.attachment_path,
                as_attachment=not preview, download_name=name)
    if not rows:
        return error('该成果暂无附件', status=404, code=404)
    return _send_attachment(rows[0])


def _owner_exists(owner_type, owner_id):
    model = Teacher if owner_type == 'teacher' else Student
    if owner_type not in ('teacher', 'student') or not owner_id:
        return False
    return db.session.get(model, owner_id) is not None