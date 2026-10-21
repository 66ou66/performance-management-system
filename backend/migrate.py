"""零依赖的幂等数据库迁移器。

解决的问题：原项目用 `db.create_all()` 建表，一旦模型加了字段就只能删库重建
（README 里写着"想重置演示数据就删除 app.db"）。本模块在每次启动时自动把
存量 SQLite 库补齐到当前模型结构，并回填历史数据，**不丢数据**。

执行三类动作：
1. 已存在的表：对比模型与实际列，缺失的列用 ALTER TABLE ADD COLUMN 补上；
2. 缺失的表与索引：交给 db.create_all() 与 CREATE INDEX IF NOT EXISTS 创建；
3. 数据回填与字典初始化：老的单附件字段 → attachment 表、学年、审核状态、字典项等。

非 SQLite 数据库（MySQL/PostgreSQL）走 db.create_all() 分支，
后续可用 Alembic 接管（见 README 的"数据库演进"小节）。
"""
import json
import os

from sqlalchemy import inspect, text
from sqlalchemy.types import Boolean, DateTime, Integer, Numeric, SmallInteger

from constants import DEFAULT_INDICATORS, DICT_KINDS
from extensions import db

# 本次迁移的动作记录，供启动日志与 /api/health 展示
REPORT = []


def _record(message):
    REPORT.append(message)


def _sql_literal(value):
    if isinstance(value, bool):
        return '1' if value else '0'
    if isinstance(value, (int, float)):
        return str(value)
    escaped = str(value).replace("'", "''")
    return f"'{escaped}'"


def _column_default_sql(column, dialect):
    """为 NOT NULL 的新列推导一个可写入 ALTER 语句的默认值。"""
    default = column.default
    if default is not None and getattr(default, 'is_scalar', False):
        return _sql_literal(default.arg)
    if column.server_default is not None:
        return None  # 交给数据库自带的 server_default
    if isinstance(column.type, Boolean):
        return '0'
    if isinstance(column.type, (Integer, SmallInteger)):
        return '0'
    if isinstance(column.type, Numeric):
        return '0'
    if isinstance(column.type, DateTime):
        return None
    return "''"


def _add_missing_columns(engine):
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    dialect = engine.dialect
    for table in db.metadata.sorted_tables:
        if table.name not in existing_tables:
            continue
        have = {col['name'] for col in inspector.get_columns(table.name)}
        for column in table.columns:
            if column.name in have:
                continue
            type_sql = column.type.compile(dialect=dialect)
            clause = f'ALTER TABLE {table.name} ADD COLUMN {column.name} {type_sql}'
            if not column.nullable:
                literal = _column_default_sql(column, dialect)
                if literal is not None:
                    clause += f' NOT NULL DEFAULT {literal}'
            with engine.begin() as conn:
                conn.execute(text(clause))
            _record(f'新增列 {table.name}.{column.name}')


def _create_missing_indexes(engine):
    """为已存在的表补建模型里声明的索引（create_all 不会给老表加索引）。"""
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    for table in db.metadata.sorted_tables:
        if table.name not in existing_tables:
            continue
        have = {idx['name'] for idx in inspector.get_indexes(table.name)}
        for index in table.indexes:
            if index.name in have:
                continue
            columns = ', '.join(col.name for col in index.columns)
            unique = 'UNIQUE ' if index.unique else ''
            statement = (f'CREATE {unique}INDEX IF NOT EXISTS {index.name} '
                         f'ON {table.name} ({columns})')
            with engine.begin() as conn:
                conn.execute(text(statement))
            _record(f'新增索引 {index.name}')


def _backfill_achievements(engine):
    statements = [
        ("UPDATE achievement SET status = 'approved' WHERE status IS NULL OR status = ''",
         '回填成果审核状态'),
        ("UPDATE achievement SET is_deleted = 0 WHERE is_deleted IS NULL",
         '回填软删除标记'),
        ("UPDATE achievement SET extra = '{}' WHERE extra IS NULL OR extra = ''",
         '回填类别专有字段'),
        ("UPDATE user SET token_version = 0 WHERE token_version IS NULL",
         '回填令牌版本'),
        ("UPDATE user SET must_change_password = 0 WHERE must_change_password IS NULL",
         '回填首登改密标记'),
    ]
    for statement, message in statements:
        with engine.begin() as conn:
            result = conn.execute(text(statement))
        if result.rowcount:
            _record(f'{message}（{result.rowcount} 行）')
    # 学年：自然年 → 'YYYY-YYYY+1'
    with engine.begin() as conn:
        rows = conn.execute(text(
            "SELECT id, year FROM achievement "
            "WHERE (academic_year IS NULL OR academic_year = '') AND year IS NOT NULL"
        )).fetchall()
        for row_id, year in rows:
            conn.execute(
                text('UPDATE achievement SET academic_year = :ay WHERE id = :id'),
                {'ay': f'{int(year)}-{int(year) + 1}', 'id': row_id},
            )
    if rows:
        _record(f'回填学年（{len(rows)} 行）')
    # 去除存量院系/专业/职称/年级字段的首尾空白与全角空格
    for table, columns in (
        ('teacher', ['department', 'title']),
        ('student', ['department', 'major', 'grade']),
    ):
        for column in columns:
            with engine.begin() as conn:
                result = conn.execute(text(
                    f"UPDATE {table} SET {column} = TRIM(REPLACE({column}, '　', ' ')) "
                    f"WHERE {column} IS NOT NULL AND {column} != "
                    f"TRIM(REPLACE({column}, '　', ' '))"
                ))
            if result.rowcount:
                _record(f'规范化 {table}.{column}（{result.rowcount} 行）')


def _migrate_legacy_attachments(app):
    """把老的单附件字段迁移为 attachment 记录（文件保持原路径不动）。"""
    from config import Config
    from models import Achievement, Attachment

    upload_folder = app.config['UPLOAD_FOLDER']
    rows = Achievement.query.filter(
        Achievement.attachment_path.isnot(None), Achievement.attachment_path != ''
    ).all()
    moved = 0
    for item in rows:
        if Attachment.query.filter_by(achievement_id=item.id).first():
            continue
        stored = item.attachment_path
        parts = stored.split('_', 1)
        original = parts[1] if len(parts) > 1 else stored
        path = os.path.join(upload_folder, stored)
        if not os.path.exists(path):
            continue
        db.session.add(Attachment(
            achievement_id=item.id,
            stored_path=stored,
            original_name=original,
            category='其他',
            size=os.path.getsize(path),
            uploaded_by=item.created_by,
            uploaded_at=item.created_at,
        ))
        moved += 1
    if moved:
        db.session.commit()
        _record(f'历史单附件迁移为支撑材料记录（{moved} 条）')


def _seed_reference_data(app):
    """初始化认证指标点与字典项。"""
    from models import CertificationIndicator, DictItem, Student, Teacher

    if CertificationIndicator.query.count() == 0:
        for index, item in enumerate(DEFAULT_INDICATORS):
            db.session.add(CertificationIndicator(
                code=item['code'], name=item['name'],
                description=item['description'], sort_order=index,
            ))
        db.session.commit()
        _record(f'初始化认证指标点（{len(DEFAULT_INDICATORS)} 条）')

    if DictItem.query.count() == 0:
        created = 0
        department_names = set()
        major_pairs = set()
        title_names = set()
        grade_names = set()
        for teacher in Teacher.query.all():
            if teacher.department:
                department_names.add(teacher.department.strip())
            if teacher.title:
                title_names.add(teacher.title.strip())
        for student in Student.query.all():
            if student.department:
                department_names.add(student.department.strip())
            if student.major:
                major_pairs.add((student.major.strip(), (student.department or '').strip()))
            if student.grade:
                grade_names.add(student.grade.strip())
        order = 0
        for name in sorted(department_names):
            db.session.add(DictItem(kind='department', name=name, sort_order=order))
            order += 1
            created += 1
        order = 0
        for name, parent in sorted(major_pairs):
            db.session.add(DictItem(kind='major', name=name, parent_name=parent or None,
                                    sort_order=order))
            order += 1
            created += 1
        for order, name in enumerate(sorted(title_names)):
            db.session.add(DictItem(kind='title', name=name, sort_order=order))
            created += 1
        for order, name in enumerate(sorted(grade_names)):
            db.session.add(DictItem(kind='grade', name=name, sort_order=order))
            created += 1
        if created:
            db.session.commit()
            _record(f'从存量数据初始化字典项（{created} 条）')


def run_migrations(app):
    REPORT.clear()
    with app.app_context():
        engine = db.engine
        inspector = inspect(engine)
        had_tables = bool(inspector.get_table_names())
        if engine.dialect.name == 'sqlite' and had_tables:
            _add_missing_columns(engine)
        db.create_all()
        if engine.dialect.name == 'sqlite':
            _create_missing_indexes(engine)
            if had_tables:
                _backfill_achievements(engine)
        if had_tables:
            _migrate_legacy_attachments(app)
        _seed_reference_data(app)
    return list(REPORT)


def referenced_files(app):
    """返回 uploads 目录下仍被数据库引用的相对路径集合。"""
    from models import Achievement, Attachment
    referenced = set()
    with app.app_context():
        for row in Attachment.query.all():
            referenced.add(os.path.normpath(row.stored_path))
        for item in Achievement.query.filter(Achievement.attachment_path.isnot(None)).all():
            if item.attachment_path:
                referenced.add(os.path.normpath(item.attachment_path))
    return referenced


def orphan_files(app):
    """列出 uploads 目录里没有被 attachment 表引用的文件（清理用）。"""
    folder = app.config['UPLOAD_FOLDER']
    referenced = referenced_files(app)
    found = []
    if os.path.isdir(folder):
        for root, _dirs, files in os.walk(folder):
            for filename in files:
                if filename == '.gitkeep':
                    continue
                full = os.path.join(root, filename)
                relative = os.path.relpath(full, folder)
                if os.path.normpath(relative) in referenced:
                    continue
                found.append(relative)
    return found


def database_summary(app):
    """返回 {表名: 行数}，用于启动日志与健康检查。"""
    from models import (Achievement, Attachment, CertificationIndicator, DictItem,
                        OperationLog, Student, Teacher, User)
    models = {
        'user': User, 'teacher': Teacher, 'student': Student,
        'achievement': Achievement, 'attachment': Attachment,
        'dict_item': DictItem, 'certification_indicator': CertificationIndicator,
        'operation_log': OperationLog,
    }
    summary = {}
    with app.app_context():
        for name, model in models.items():
            try:
                summary[name] = model.query.count()
            except Exception:  # pragma: no cover - 表不存在时兜底
                summary[name] = None
    return summary


def dumps_report():
    return json.dumps(REPORT, ensure_ascii=False)


__all__ = ['run_migrations', 'orphan_files', 'database_summary', 'REPORT', 'DICT_KINDS']