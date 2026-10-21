from routes.achievement_routes import achievement_bp
from routes.admin_routes import admin_bp
from routes.advisor_routes import advisor_bp
from routes.auth_routes import auth_bp
from routes.dict_routes import dict_bp
from routes.import_export_routes import io_bp
from routes.indicator_routes import indicator_bp
from routes.log_routes import log_bp
from routes.meta_routes import meta_bp
from routes.stats_routes import stats_bp
from routes.student_routes import student_bp
from routes.system_routes import system_bp
from routes.teacher_routes import teacher_bp

all_blueprints = [
    auth_bp,
    teacher_bp,
    student_bp,
    achievement_bp,
    stats_bp,
    io_bp,
    admin_bp,
    meta_bp,
    dict_bp,
    indicator_bp,
    advisor_bp,
    log_bp,
    system_bp,
]