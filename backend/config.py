"""应用配置。

安全相关（密钥、CORS、调试开关）一律从环境变量或本地密钥文件读取，
不再在源码里硬编码弱默认值。

优先级：
    环境变量  >  项目根目录 .env  >  backend/instance/secrets.json  >  首次自动生成

首次启动时会自动生成 64 位随机密钥并写入 backend/instance/secrets.json，
因此即使什么都不配置，也不存在“源码里的固定密钥”被利用的问题；
APP_ENV=production 时则强制要求通过环境变量显式提供密钥。
"""
import json
import os
import secrets as _secrets
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
PROJECT_DIR = os.path.abspath(os.path.join(BASE_DIR, os.pardir))
INSTANCE_DIR = os.path.join(BASE_DIR, 'instance')
SECRETS_FILE = os.path.join(INSTANCE_DIR, 'secrets.json')

VALID_ENVS = ('development', 'testing', 'production')


def _load_env_file(path):
    """极简 .env 解析（避免引入 python-dotenv 依赖）。已存在的环境变量优先。"""
    if not os.path.exists(path):
        return
    try:
        with open(path, 'r', encoding='utf-8-sig') as handle:
            for raw in handle:
                line = raw.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                key, _, value = line.partition('=')
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = value
    except OSError:
        pass


_load_env_file(os.path.join(PROJECT_DIR, '.env'))
_load_env_file(os.path.join(BASE_DIR, '.env'))

APP_ENV = (os.environ.get('APP_ENV') or 'development').strip().lower()
if APP_ENV not in VALID_ENVS:
    raise RuntimeError(f'APP_ENV 只能是 {VALID_ENVS} 之一，当前为 {APP_ENV!r}')
IS_PRODUCTION = APP_ENV == 'production'
IS_TESTING = APP_ENV == 'testing'


def _persisted_secrets():
    if not os.path.exists(SECRETS_FILE):
        return {}
    try:
        with open(SECRETS_FILE, 'r', encoding='utf-8') as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _write_secrets(data):
    os.makedirs(INSTANCE_DIR, exist_ok=True)
    with open(SECRETS_FILE, 'w', encoding='utf-8') as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)


def _resolve_secret(name):
    """解析密钥：环境变量 → 本地密钥文件 → 自动生成并持久化。"""
    value = (os.environ.get(name) or '').strip()
    if value:
        return value
    if IS_PRODUCTION:
        raise RuntimeError(
            f'生产环境（APP_ENV=production）必须显式提供环境变量 {name}，'
            f'例如在 .env 中设置 {name}=<64 位随机字符串>'
        )
    store = _persisted_secrets()
    value = (store.get(name) or '').strip()
    if value:
        return value
    value = _secrets.token_hex(32)  # 64 个字符，满足 RFC 7518 对 HMAC-SHA256 的密钥长度要求
    store[name] = value
    try:
        _write_secrets(store)
    except OSError:
        pass
    return value


def _env_bool(name, default=False):
    raw = os.environ.get(name)
    if raw is None or raw == '':
        return default
    return str(raw).strip().lower() in ('1', 'true', 'yes', 'on')


def _env_int(name, default):
    raw = os.environ.get(name)
    try:
        return int(str(raw).strip())
    except (TypeError, ValueError):
        return default


def _env_list(name, default):
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return list(default)
    return [item.strip() for item in raw.split(',') if item.strip()]


DEFAULT_CORS_ORIGINS = [
    'http://127.0.0.1:5173',
    'http://localhost:5173',
    'http://127.0.0.1:4173',
    'http://localhost:4173',
]


class Config:
    APP_ENV = APP_ENV
    IS_PRODUCTION = IS_PRODUCTION
    IS_TESTING = IS_TESTING
    DEBUG = _env_bool('FLASK_DEBUG', not IS_PRODUCTION and not IS_TESTING)
    TESTING = IS_TESTING

    SECRET_KEY = _resolve_secret('SECRET_KEY')
    JWT_SECRET_KEY = _resolve_secret('JWT_SECRET_KEY')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=_env_int('JWT_EXPIRE_HOURS', 12))
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=_env_int('JWT_REFRESH_EXPIRE_DAYS', 7))

    # 本地开发绑定回环地址；对外部署（多机访问）通过 HOST 环境变量显式放开
    HOST = os.environ.get('HOST', '0.0.0.0' if IS_PRODUCTION else '127.0.0.1')
    PORT = _env_int('PORT', 5000)

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL', 'sqlite:///' + os.path.join(BASE_DIR, 'app.db')
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {'pool_pre_ping': True}

    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or os.path.join(BASE_DIR, 'uploads')
    BACKUP_FOLDER = os.environ.get('BACKUP_FOLDER') or os.path.join(BASE_DIR, 'backups')
    LOG_FOLDER = os.environ.get('LOG_FOLDER') or os.path.join(BASE_DIR, 'logs')
    BACKUP_KEEP = _env_int('BACKUP_KEEP', 10)
    BACKUP_ON_START = _env_bool('BACKUP_ON_START', True)

    CORS_ORIGINS = _env_list('CORS_ORIGINS', DEFAULT_CORS_ORIGINS)

    MAX_CONTENT_LENGTH = _env_int('MAX_CONTENT_LENGTH', 20 * 1024 * 1024)
    MAX_ATTACHMENT_COUNT = _env_int('MAX_ATTACHMENT_COUNT', 20)

    ALLOWED_EXTENSIONS = {
        'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx',
        'jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'zip', 'rar', '7z',
    }

    # 登录失败节流：默认 5 次失败锁定 5 分钟
    LOGIN_MAX_ATTEMPTS = _env_int('LOGIN_MAX_ATTEMPTS', 5)
    LOGIN_LOCK_SECONDS = _env_int('LOGIN_LOCK_SECONDS', 300)
    LOGIN_WINDOW_SECONDS = _env_int('LOGIN_WINDOW_SECONDS', 900)

    # 开启后，教师/学生提交的成果默认进入「待审核」状态
    REQUIRE_REVIEW = _env_bool('REQUIRE_REVIEW', False)
    # 开启后，新建账号首次登录必须修改密码
    FORCE_PASSWORD_CHANGE = _env_bool('FORCE_PASSWORD_CHANGE', False)
    MIN_PASSWORD_LENGTH = _env_int('MIN_PASSWORD_LENGTH', 6)
    # 开启后拒绝常见弱口令（演示环境默认关闭，便于保留 123456 演示账号）
    PASSWORD_STRENGTH_CHECK = _env_bool('PASSWORD_STRENGTH_CHECK', False)

    # 认证学年起始月份（9 = 学年从 9 月起）
    ACADEMIC_YEAR_START_MONTH = _env_int('ACADEMIC_YEAR_START_MONTH', 9)
    ACADEMIC_YEAR_SPAN = _env_int('ACADEMIC_YEAR_SPAN', 12)

    ACCESS_LOG_ENABLED = _env_bool('ACCESS_LOG_ENABLED', True)
    PAGE_SIZE_MAX = _env_int('PAGE_SIZE_MAX', 100)