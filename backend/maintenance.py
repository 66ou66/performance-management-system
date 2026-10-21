"""维护性任务：级联删除、孤儿附件清理、数据备份。

原实现删除教师/学生时用 bulk delete 删成果行，却不删 uploads 里的实际文件，
留下永久残留。这里把级联清理集中到一处，任何入口都调用它。
"""
import os
import shutil
import zipfile
from datetime import datetime

from audit import ACTION_BACKUP, ACTION_DELETE, log_operation
from extensions import db
from models import (
    Achievement,
    AchievementIndicator,
    AdvisorRelation,
    Attachment,
    Student,
    Teacher,
    User,
)


def purge_achievements_of_owner(owner_type, owner_ids):
    """删除某批人员的全部成果（含指标点关联、附件记录与文件）。"""
    from services import remove_owner_files

    ids = list(owner_ids)
    if not ids:
        return 0, 0
    achievement_ids = [
        row.id for row in Achievement.query.filter(
            Achievement.owner_type == owner_type,
            Achievement.owner_id.in_(ids),
        ).all()
    ]
    files_removed = remove_owner_files(_app_config(), owner_type, ids)
    if achievement_ids:
        AchievementIndicator.query.filter(
            AchievementIndicator.achievement_id.in_(achievement_ids)).delete(
            synchronize_session=False)
        Attachment.query.filter(
            Attachment.achievement_id.in_(achievement_ids)).delete(
            synchronize_session=False)
        Achievement.query.filter(Achievement.id.in_(achievement_ids)).delete(
            synchronize_session=False)
    return len(achievement_ids), files_removed


def _app_config():
    from flask import current_app
    return current_app.config


def delete_teacher(teacher, operator=None):
    """删除教师并级联清理：成果、附件文件、指导关系、账号。"""
    username = ''
    user = User.query.filter_by(owner_type='teacher', owner_id=teacher.id).first()
    if user is None and teacher.user_id:
        user = db.session.get(User, teacher.user_id)
    if user is not None:
        username = user.username

    achievements, files_removed = purge_achievements_of_owner('teacher', [teacher.id])
    AdvisorRelation.query.filter_by(teacher_id=teacher.id).delete(synchronize_session=False)
    Achievement.query.filter(Achievement.advisor_id == teacher.id).update(
        {'advisor_id': None}, synchronize_session=False)
    if user is not None:
        db.session.delete(user)
    name = teacher.name
    db.session.delete(teacher)
    db.session.commit()
    log_operation(ACTION_DELETE, 'teacher', None,
                  f'删除教师「{name}」（账号 {username or "无"}，'
                  f'成果 {achievements} 条，清理附件 {files_removed} 个）',
                  user=operator)
    return {'achievements': achievements, 'files_removed': files_removed,
            'username': username}


def delete_student(student, operator=None):
    username = ''
    user = User.query.filter_by(owner_type='student', owner_id=student.id).first()
    if user is None and student.user_id:
        user = db.session.get(User, student.user_id)
    if user is not None:
        username = user.username

    achievements, files_removed = purge_achievements_of_owner('student', [student.id])
    AdvisorRelation.query.filter_by(student_id=student.id).delete(synchronize_session=False)
    if user is not None:
        db.session.delete(user)
    name = student.name
    student_no = student.student_no
    db.session.delete(student)
    db.session.commit()
    log_operation(ACTION_DELETE, 'student', None,
                  f'删除学生「{name}」（学号 {student_no}，账号 {username or "无"}，'
                  f'成果 {achievements} 条，清理附件 {files_removed} 个）',
                  user=operator)
    return {'achievements': achievements, 'files_removed': files_removed,
            'username': username}


def cleanup_orphans(app):
    """删除 uploads 目录里没有被数据库引用的文件。"""
    from migrate import orphan_files
    folder = app.config['UPLOAD_FOLDER']
    removed = 0
    for relative in orphan_files(app):
        full = os.path.join(folder, relative)
        try:
            os.remove(full)
            removed += 1
        except OSError:
            continue
    # 清理空目录
    if os.path.isdir(folder):
        for root, dirs, files in os.walk(folder, topdown=False):
            if os.path.abspath(root) == os.path.abspath(folder):
                continue
            if not dirs and not files:
                try:
                    os.rmdir(root)
                except OSError:
                    pass
    log_operation(ACTION_DELETE, 'system', None,
                  f'清理孤儿附件文件 {removed} 个', commit=True)
    return removed


def _database_file(app):
    uri = app.config['SQLALCHEMY_DATABASE_URI']
    if not uri.startswith('sqlite:'):
        return None
    path = uri.split('sqlite:///', 1)[-1]
    return path if os.path.exists(path) else None


def backup_now(app, keep=None):
    """把数据库与 uploads 打包成 zip 备份，返回备份文件路径。"""
    backup_dir = app.config['BACKUP_FOLDER']
    keep = keep or app.config.get('BACKUP_KEEP', 10)
    os.makedirs(backup_dir, exist_ok=True)
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    target = os.path.join(backup_dir, f'backup_{stamp}.zip')
    database = _database_file(app)
    upload_folder = app.config['UPLOAD_FOLDER']

    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as archive:
        if database:
            archive.write(database, 'app.db')
        manifest = []
        if os.path.isdir(upload_folder):
            for root, _dirs, files in os.walk(upload_folder):
                for filename in files:
                    if filename == '.gitkeep':
                        continue
                    full = os.path.join(root, filename)
                    relative = os.path.relpath(full, upload_folder)
                    archive.write(full, os.path.join('uploads', relative))
                    manifest.append(relative)
        import json
        archive.writestr('manifest.json', json.dumps({
            'created_at': datetime.now().isoformat(timespec='seconds'),
            'database': os.path.basename(database) if database else None,
            'upload_files': manifest,
            'count': len(manifest),
        }, ensure_ascii=False, indent=2))

    _rotate_backups(backup_dir, keep)
    log_operation(ACTION_BACKUP, 'system', None,
                  f'生成数据备份 {os.path.basename(target)}', commit=True)
    return target


def _rotate_backups(backup_dir, keep):
    if keep <= 0:
        return
    entries = []
    for name in os.listdir(backup_dir):
        if not name.startswith('backup_') or not name.endswith('.zip'):
            continue
        full = os.path.join(backup_dir, name)
        entries.append((os.path.getmtime(full), full))
    entries.sort(reverse=True)
    for _mtime, full in entries[keep:]:
        try:
            os.remove(full)
        except OSError:
            continue


def list_backups(app):
    backup_dir = app.config['BACKUP_FOLDER']
    if not os.path.isdir(backup_dir):
        return []
    entries = []
    for name in sorted(os.listdir(backup_dir), reverse=True):
        if not name.startswith('backup_') or not name.endswith('.zip'):
            continue
        full = os.path.join(backup_dir, name)
        stat = os.stat(full)
        entries.append({
            'name': name,
            'size': stat.st_size,
            'size_text': _size_text(stat.st_size),
            'created_at': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
        })
    return entries


def _size_text(size):
    value = float(size)
    for unit in ('B', 'KB', 'MB', 'GB'):
        if value < 1024 or unit == 'GB':
            return f'{value:.1f} {unit}'
        value /= 1024
    return f'{size} B'


def copy_upload(src, dst):  # pragma: no cover - 预留工具
    shutil.copy2(src, dst)
    return dst