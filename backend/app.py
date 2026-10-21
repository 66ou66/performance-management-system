import logging
import os
import sys
from logging.handlers import RotatingFileHandler

from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException

from config import Config
from extensions import cors, db, jwt
from routes import all_blueprints


def _setup_logging(app):
    log_dir = app.config['LOG_FOLDER']
    os.makedirs(log_dir, exist_ok=True)
    handler = RotatingFileHandler(
        os.path.join(log_dir, 'server.log'),
        maxBytes=2 * 1024 * 1024, backupCount=5, encoding='utf-8',
    )
    handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s [%(module)s:%(lineno)d] %(message)s'))
    handler.setLevel(logging.INFO)
    # 幂等：同一个进程里多次调用 create_app 时不重复挂载文件处理器（否则日志会翻倍）
    for existing in list(app.logger.handlers):
        if isinstance(existing, RotatingFileHandler):
            app.logger.removeHandler(existing)
            existing.close()
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO if not app.config['DEBUG'] else logging.DEBUG)
    if not app.config['DEBUG']:
        # 生产模式不要向终端输出堆栈，避免泄露内部结构
        app.logger.propagate = False


def _register_access_log(app):
    """访问日志：记录方法、路径、状态码、耗时与登录账号，便于事后追溯。"""
    import time

    @app.before_request
    def _start_timer():
        request._dsh_started_at = time.perf_counter()

    @app.after_request
    def _write_access_log(response):
        if not request.path.startswith('/api/'):
            return response
        started = getattr(request, '_dsh_started_at', None)
        cost_ms = int((time.perf_counter() - started) * 1000) if started else -1
        username = '-'
        try:
            from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
            verify_jwt_in_request(optional=True)
            identity = get_jwt_identity()
            if identity:
                from models import User
                user = db.session.get(User, int(identity))
                username = user.username if user else str(identity)
        except Exception:  # pragma: no cover - 未登录请求或解析失败时不影响响应
            username = '-'
        app.logger.info(
            '%s %s -> %s %sms user=%s ip=%s',
            request.method, request.full_path.rstrip('?'), response.status_code,
            cost_ms, username, request.remote_addr,
        )
        return response


def create_app(config_object=Config):
    app = Flask(__name__)
    app.config.from_object(config_object)
    app.json.ensure_ascii = False

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['BACKUP_FOLDER'], exist_ok=True)
    _setup_logging(app)

    db.init_app(app)
    jwt.init_app(app)
    origins = app.config['CORS_ORIGINS']
    cors.init_app(
        app,
        resources={r'/api/*': {'origins': origins}},
        allow_headers=['Content-Type', 'Authorization'],
        expose_headers=['Content-Disposition'],
        methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
        supports_credentials=False,
        max_age=600,
    )

    for blueprint in all_blueprints:
        app.register_blueprint(blueprint)

    if app.config.get('ACCESS_LOG_ENABLED', True):
        _register_access_log(app)

    _register_jwt_handlers(app)
    _register_error_handlers(app)

    @app.get('/api/health')
    def health():
        from migrate import REPORT, database_summary
        payload = {
            'service': 'achievement-api',
            'app_env': app.config['APP_ENV'],
            'status': 'ok',
        }
        try:
            payload['database'] = database_summary(app)
            payload['migrations'] = list(REPORT)
        except Exception:  # pragma: no cover - 健康检查不应因统计失败而 500
            payload['database'] = None
        return jsonify({'code': 0, 'message': 'ok', 'data': payload})

    with app.app_context():
        from migrate import run_migrations
        run_migrations(app)
        from seed import seed_if_empty
        seed_if_empty()
        if app.config.get('BACKUP_ON_START') and app.config['IS_PRODUCTION']:
            try:
                from maintenance import backup_now
                backup_now(app)
            except Exception:
                app.logger.exception('启动备份失败，已跳过')

    app.logger.info('应用初始化完成：env=%s debug=%s db=%s',
                    app.config['APP_ENV'], app.config['DEBUG'],
                    app.config['SQLALCHEMY_DATABASE_URI'])
    return app


def _register_jwt_handlers(app):
    @jwt.unauthorized_loader
    def missing_token(reason):
        return jsonify({'code': 401, 'message': '请先登录后再访问', 'data': None}), 401

    @jwt.invalid_token_loader
    def invalid_token(reason):
        return jsonify({'code': 401, 'message': '登录凭证无效，请重新登录', 'data': None}), 401

    @jwt.expired_token_loader
    def expired_token(header, payload):
        token_type = payload.get('type') if isinstance(payload, dict) else None
        message = '登录已过期，请重新登录' if token_type != 'refresh' else '刷新凭证已过期，请重新登录'
        return jsonify({'code': 401, 'message': message, 'data': None}), 401

    @jwt.revoked_token_loader
    def revoked_token(header, payload):
        return jsonify({'code': 401, 'message': '登录凭证已失效，请重新登录', 'data': None}), 401

    @jwt.token_verification_failed_loader
    def verification_failed(header, payload):
        return jsonify({'code': 401, 'message': '登录凭证校验失败，请重新登录', 'data': None}), 401


def _register_error_handlers(app):
    @app.errorhandler(413)
    def handle_too_large(error):
        limit = round(app.config['MAX_CONTENT_LENGTH'] / 1024 / 1024, 1)
        return jsonify({'code': 413, 'message': f'上传内容过大，单次最大支持 {limit}MB',
                        'data': None}), 413

    @app.errorhandler(404)
    def handle_not_found(error):
        return jsonify({'code': 404, 'message': '请求的资源不存在', 'data': None}), 404

    @app.errorhandler(405)
    def handle_method(error):
        return jsonify({'code': 405, 'message': '请求方法不被允许', 'data': None}), 405

    @app.errorhandler(HTTPException)
    def handle_http(error):
        return jsonify({'code': error.code, 'message': error.description, 'data': None}), error.code

    @app.errorhandler(Exception)
    def handle_exception(error):
        app.logger.exception('未捕获异常：%s %s', request.method, request.path)
        return jsonify({'code': 500, 'message': '服务器内部错误', 'data': None}), 500


_cached_app = None


def __getattr__(name):
    """按需创建模块级 app（`from app import app` 时才会真正建应用）。

    这样导入 `create_app` 做测试的脚本不会再顺带创建一个多余的应用实例
    （否则会重复执行迁移、种子数据与日志处理器注册）。
    """
    global _cached_app
    if name == 'app':
        if _cached_app is None:
            _cached_app = create_app()
        return _cached_app
    raise AttributeError(f'module {__name__!r} has no attribute {name!r}')


if __name__ == '__main__':
    from waitress import serve
    app = create_app()
    if app.config['IS_PRODUCTION']:
        app.logger.info('以 waitress 生产模式启动：%s:%s',
                        app.config['HOST'], app.config['PORT'])
        serve(app, host=app.config['HOST'], port=app.config['PORT'], threads=8)
    else:
        app.run(host=app.config['HOST'], port=app.config['PORT'],
                debug=app.config['DEBUG'], use_reloader=False)