"""系统维护：运行信息、数据备份、孤儿附件清理、迁移重跑。"""
import os

from flask import Blueprint, current_app, request, send_file

from auth_utils import admin_required, login_required
from constants import ROLE_LABELS
from extensions import db
from maintenance import backup_now, cleanup_orphans, list_backups
from migrate import orphan_files, run_migrations
from models import Achievement, CertificationIndicator, DictItem, OperationLog
from security import login_throttle
from utils import error, parse_bool, success

system_bp = Blueprint('system', __name__, url_prefix='/api/system')


@system_bp.get('/info')
@admin_required
def info():
    from migrate import REPORT, database_summary
    upload_folder = current_app.config['UPLOAD_FOLDER']
    file_count = 0
    total_size = 0
    if os.path.isdir(upload_folder):
        for root, _dirs, files in os.walk(upload_folder):
            for filename in files:
                if filename == '.gitkeep':
                    continue
                file_count += 1
                total_size += os.path.getsize(os.path.join(root, filename))
    from models import format_size
    return success({
        'app_env': current_app.config['APP_ENV'],
        'debug': bool(current_app.config['DEBUG']),
        'database': current_app.config['SQLALCHEMY_DATABASE_URI'].split('://')[0],
        'upload_folder': upload_folder,
        'backup_folder': current_app.config['BACKUP_FOLDER'],
        'require_review': bool(current_app.config.get('REQUIRE_REVIEW')),
        'force_password_change': bool(current_app.config.get('FORCE_PASSWORD_CHANGE')),
        'password_strength_check': bool(current_app.config.get('PASSWORD_STRENGTH_CHECK')),
        'cors_origins': current_app.config.get('CORS_ORIGINS'),
        'max_upload_mb': round(current_app.config['MAX_CONTENT_LENGTH'] / 1024 / 1024, 1),
        'row_counts': database_summary(current_app),
        'upload_files': file_count,
        'upload_size': format_size(total_size),
        'login_throttle': login_throttle.snapshot(),
        'migration_report': list(REPORT),
        'coverage': {
            'achievements': Achievement.query.filter(Achievement.is_deleted.is_(False)).count(),
            'trash': Achievement.query.filter(Achievement.is_deleted.is_(True)).count(),
            'indicators': CertificationIndicator.query.count(),
            'dict_items': DictItem.query.count(),
            'logs': OperationLog.query.count(),
        },
    })


@system_bp.get('/orphans')
@admin_required
def orphans():
    files = orphan_files(current_app)
    upload_folder = current_app.config['UPLOAD_FOLDER']
    items = []
    for relative in files[:500]:
        full = os.path.join(upload_folder, relative)
        items.append({
            'path': relative,
            'size': os.path.getsize(full) if os.path.exists(full) else 0,
        })
    return success({'total': len(files), 'items': items})


@system_bp.post('/cleanup-orphans')
@admin_required
def cleanup():
    removed = cleanup_orphans(current_app)
    return success({'removed': removed}, f'已清理 {removed} 个未被引用的文件')


@system_bp.post('/migrate')
@admin_required
def migrate():
    report = run_migrations(current_app)
    return success({'actions': report},
                   '结构检查完成' + (f'，执行了 {len(report)} 项变更' if report else '，无需变更'))


@system_bp.get('/backups')
@admin_required
def backups():
    return success({
        'items': list_backups(current_app),
        'keep': current_app.config['BACKUP_KEEP'],
        'folder': current_app.config['BACKUP_FOLDER'],
    })


@system_bp.post('/backup')
@admin_required
def create_backup():
    target = backup_now(current_app)
    name = os.path.basename(target)
    size = os.path.getsize(target) if os.path.exists(target) else 0
    return success({'name': name, 'size': size}, f'备份已生成：{name}')


@system_bp.get('/backup/download')
@admin_required
def download_backup():
    name = (request.args.get('name') or '').strip()
    folder = current_app.config['BACKUP_FOLDER']
    if not name or os.path.basename(name) != name or not name.endswith('.zip'):
        return error('备份文件名不合法')
    full = os.path.join(folder, name)
    if not os.path.exists(full):
        return error('备份文件不存在', status=404, code=404)
    return send_file(full, as_attachment=True, download_name=name,
                     mimetype='application/zip')


@system_bp.get('/config-hints')
@login_required
def config_hints():
    """给前端展示"当前部署处于什么模式"，避免误把开发配置当生产。"""
    config = current_app.config
    return success({
        'app_env': config['APP_ENV'],
        'debug': bool(config['DEBUG']),
        'require_review': bool(config.get('REQUIRE_REVIEW')),
        'role_labels': ROLE_LABELS,
        'max_upload_mb': round(config['MAX_CONTENT_LENGTH'] / 1024 / 1024, 1),
        'max_attachment_count': config['MAX_ATTACHMENT_COUNT'],
    })


@system_bp.post('/toggle-require-review')
@admin_required
def toggle_require_review():
    """运行期切换审核开关需要重启才生效，这里只做提示。"""
    value = parse_bool((request.get_json(silent=True) or {}).get('require_review'))
    return error(f'审核开关由环境变量 REQUIRE_REVIEW 控制，请修改 .env 后重启服务'
                 f'（当前请求值 {value}）', status=400, code=400)