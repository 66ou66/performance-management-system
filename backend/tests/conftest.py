"""pytest 公共配置：隔离的临时数据库与上传目录。

关键点：必须在导入 app/config 之前设置环境变量，因为 config.py 在导入时就
读取了 DATABASE_URL 与目录配置。
"""
import os
import shutil
import sys
import tempfile

import pytest

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

TEMP_DIR = tempfile.mkdtemp(prefix='achievement_pytest_')
os.environ['APP_ENV'] = 'testing'
os.environ['DATABASE_URL'] = 'sqlite:///' + os.path.join(TEMP_DIR, 'pytest.db')
os.environ['UPLOAD_FOLDER'] = os.path.join(TEMP_DIR, 'uploads')
os.environ['BACKUP_FOLDER'] = os.path.join(TEMP_DIR, 'backups')
os.environ['LOG_FOLDER'] = os.path.join(TEMP_DIR, 'logs')
os.environ['BACKUP_ON_START'] = '0'
os.environ['REQUIRE_REVIEW'] = '0'
os.environ['FORCE_PASSWORD_CHANGE'] = '0'
os.environ['ACCESS_LOG_ENABLED'] = '0'
os.environ.setdefault('LOGIN_MAX_ATTEMPTS', '5')

from openpyxl import Workbook  # noqa: E402
from io import BytesIO  # noqa: E402

from app import create_app  # noqa: E402
from extensions import db  # noqa: E402
from security import login_throttle  # noqa: E402
from seed import seed_if_empty  # noqa: E402


@pytest.fixture(scope='session')
def app():
    application = create_app()
    application.config.update(TESTING=True)
    yield application
    shutil.rmtree(TEMP_DIR, ignore_errors=True)


@pytest.fixture(autouse=True)
def clean_database(app):
    """每个用例都从「全新安装 + 演示种子数据」开始，避免用例间相互影响。"""
    from migrate import run_migrations

    with app.app_context():
        db.session.remove()
        db.drop_all()
        # run_migrations 内部会 create_all 并补齐字典、认证指标点等基础数据
        run_migrations(app)
        seed_if_empty()
    login_throttle.reset_all()
    yield


@pytest.fixture
def client(app):
    return app.test_client()


def login(client, username, password):
    return client.post('/api/auth/login', json={'username': username, 'password': password})


def headers_for(client, username, password):
    response = login(client, username, password)
    assert response.status_code == 200, response.get_data(as_text=True)
    token = response.get_json()['data']['access_token']
    return {'Authorization': 'Bearer %s' % token}


@pytest.fixture
def admin_headers(client):
    return headers_for(client, 'admin', 'admin123')


@pytest.fixture
def reviewer_headers(client):
    return headers_for(client, 'reviewer', '123456')


@pytest.fixture
def teacher_headers(client):
    return headers_for(client, 'teacher1', '123456')


@pytest.fixture
def student_headers(client):
    return headers_for(client, 'student1', '123456')


def data_of(response):
    """取出统一响应体中的 data，便于断言。"""
    payload = response.get_json()
    assert payload is not None, response.get_data(as_text=True)[:200]
    assert payload.get('code') == 0, payload
    return payload['data']


def build_xlsx(headers, rows):
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(list(headers))
    for row in rows:
        sheet.append(list(row))
    buffer = BytesIO()
    workbook.save(buffer)
    buffer.seek(0)
    return buffer


@pytest.fixture
def sql_counter(app):
    """统计一次调用产生的 SQL 语句数量，用于回归 N+1 查询。"""
    from sqlalchemy import event

    with app.app_context():
        engine = db.engine

    def _count(callback):
        statements = []

        def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            statements.append(statement)

        event.listen(engine, 'before_cursor_execute', before_cursor_execute)
        try:
            callback()
        finally:
            event.remove(engine, 'before_cursor_execute', before_cursor_execute)
        return statements

    return _count


def upload(client, url, headers, filename, content=b'%PDF-1.4 demo', field='file', data=None):
    payload = {'file': (BytesIO(content), filename)}
    if data:
        payload.update(data)
    return client.post(url, headers=headers, data=payload,
                       content_type='multipart/form-data')