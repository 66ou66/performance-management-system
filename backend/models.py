"""数据模型。

设计要点：
1. 每个模型都提供 `to_dict_list(items)` 批量序列化方法，列表接口用它一次性把
   关联对象（所属人、附件、成果计数）查出来，杜绝逐行查询的 N+1 问题；
2. `Achievement` 支持类别专有字段（extra JSON）、审核流、软删除、审计与索引；
3. 支撑材料从"单附件字符串"升级为独立的一对多 `Attachment` 表；
4. 教师与学生的指导关系用 `AdvisorRelation` 单独建模，避免重复记账。
"""
from datetime import datetime

from werkzeug.security import check_password_hash, generate_password_hash

from constants import (
    COUNTED_STATUSES,
    ROLE_STUDENT,
    ROLE_TEACHER,
    STATUS_APPROVED,
    categories_for,
    extra_labels,
    levels_for,
)
from extensions import db


def _fmt(value):
    return value.strftime('%Y-%m-%d %H:%M:%S') if value else None


def _fmt_date(value):
    return value.strftime('%Y-%m-%d') if value else None


def academic_year_of(year, start_month=9):
    """由自然年推导学年字符串，例如 2024 -> '2024-2025'。"""
    if not year:
        return ''
    try:
        year = int(year)
    except (TypeError, ValueError):
        return ''
    return f'{year}-{year + 1}'


# --------------------------------------------------------------------------- #
# 账号
# --------------------------------------------------------------------------- #
class User(db.Model):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default=ROLE_STUDENT)
    owner_type = db.Column(db.String(20))
    owner_id = db.Column(db.Integer)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    # 令牌版本：修改/重置密码或调整权限时自增，使旧 JWT 立即失效
    token_version = db.Column(db.Integer, nullable=False, default=0)
    must_change_password = db.Column(db.Boolean, nullable=False, default=False)
    last_login_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def bump_token_version(self):
        self.token_version = (self.token_version or 0) + 1

    def owner_name(self, cache=None):
        if not self.owner_type or not self.owner_id:
            return ''
        key = (self.owner_type, self.owner_id)
        if cache is not None and key in cache:
            return cache[key].get('name', '')
        model = Teacher if self.owner_type == ROLE_TEACHER else Student
        person = db.session.get(model, self.owner_id)
        return person.name if person else ''

    def to_dict(self, owner_name=None):
        name = self.owner_name() if owner_name is None else owner_name
        return {
            'id': self.id,
            'username': self.username,
            'role': self.role,
            'owner_type': self.owner_type,
            'owner_id': self.owner_id,
            'owner_name': name,
            'is_active': bool(self.is_active),
            'must_change_password': bool(self.must_change_password),
            'last_login_at': _fmt(self.last_login_at),
            'created_at': _fmt(self.created_at),
            'updated_at': _fmt(self.updated_at),
        }

    @classmethod
    def to_dict_list(cls, items):
        teacher_ids = {u.owner_id for u in items if u.owner_type == ROLE_TEACHER and u.owner_id}
        student_ids = {u.owner_id for u in items if u.owner_type == ROLE_STUDENT and u.owner_id}
        names = {}
        if teacher_ids:
            for row in Teacher.query.filter(Teacher.id.in_(teacher_ids)).all():
                names[(ROLE_TEACHER, row.id)] = row.name
        if student_ids:
            for row in Student.query.filter(Student.id.in_(student_ids)).all():
                names[(ROLE_STUDENT, row.id)] = row.name
        return [u.to_dict(owner_name=names.get((u.owner_type, u.owner_id), '')) for u in items]


# --------------------------------------------------------------------------- #
# 字典（院系 / 专业 / 职称 / 年级）
# --------------------------------------------------------------------------- #
class DictItem(db.Model):
    """轻量字典表。

    存量的 department / major / title 仍然是字符串列，避免破坏导入导出与历史数据；
    但写入时会经过 `normalize_dict_value()` 归一化（去空格、别名映射），
    统计与筛选因此不会因为"计算机学院 "和"计算机学院"而分裂。
    """

    __tablename__ = 'dict_item'
    __table_args__ = (
        db.UniqueConstraint('kind', 'name', name='uq_dict_kind_name'),
        db.Index('ix_dict_kind', 'kind', 'sort_order'),
    )

    id = db.Column(db.Integer, primary_key=True)
    kind = db.Column(db.String(30), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    aliases = db.Column(db.JSON, default=list)
    parent_name = db.Column(db.String(120))
    sort_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    def alias_list(self):
        value = self.aliases
        return list(value) if isinstance(value, (list, tuple)) else []

    def to_dict(self):
        return {
            'id': self.id,
            'kind': self.kind,
            'name': self.name,
            'aliases': self.alias_list(),
            'parent_name': self.parent_name,
            'sort_order': self.sort_order,
            'is_active': bool(self.is_active),
            'created_at': _fmt(self.created_at),
        }


# --------------------------------------------------------------------------- #
# 教师 / 学生
# --------------------------------------------------------------------------- #
class Teacher(db.Model):
    __tablename__ = 'teacher'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    department = db.Column(db.String(120))
    title = db.Column(db.String(80))
    email = db.Column(db.String(120))
    phone = db.Column(db.String(40))
    research_area = db.Column(db.String(200))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    user = db.relationship('User', foreign_keys=[user_id])

    def to_dict(self, achievement_count=None, username=None):
        count = achievement_count
        if count is None:
            count = Achievement.query.filter_by(
                owner_type=ROLE_TEACHER, owner_id=self.id, is_deleted=False
            ).count()
        name = username
        if name is None:
            name = self.user.username if self.user else None
        return {
            'id': self.id,
            'name': self.name,
            'department': self.department,
            'title': self.title,
            'email': self.email,
            'phone': self.phone,
            'research_area': self.research_area,
            'user_id': self.user_id,
            'username': name,
            'achievement_count': count,
            'created_at': _fmt(self.created_at),
            'updated_at': _fmt(self.updated_at),
        }

    @classmethod
    def to_dict_list(cls, items):
        ids = [t.id for t in items]
        counts = _achievement_counts(ROLE_TEACHER, ids)
        usernames = _usernames_for(ROLE_TEACHER, ids)
        return [
            t.to_dict(achievement_count=counts.get(t.id, 0), username=usernames.get(t.id))
            for t in items
        ]


class Student(db.Model):
    __tablename__ = 'student'

    id = db.Column(db.Integer, primary_key=True)
    student_no = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(80), nullable=False)
    grade = db.Column(db.String(30))
    major = db.Column(db.String(120))
    department = db.Column(db.String(120))
    class_name = db.Column(db.String(80))
    email = db.Column(db.String(120))
    phone = db.Column(db.String(40))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    user = db.relationship('User', foreign_keys=[user_id])

    def advisors(self):
        rows = (AdvisorRelation.query
                .filter_by(student_id=self.id)
                .order_by(AdvisorRelation.is_primary.desc(), AdvisorRelation.id)
                .all())
        return rows

    def to_dict(self, achievement_count=None, username=None, advisors=None, advisor_names=None):
        count = achievement_count
        if count is None:
            count = Achievement.query.filter_by(
                owner_type=ROLE_STUDENT, owner_id=self.id, is_deleted=False
            ).count()
        name = username
        if name is None:
            name = self.user.username if self.user else None
        if advisors is None:
            advisors = self.advisors()
        if advisor_names is None:
            advisor_names = _teacher_names([a.teacher_id for a in advisors])
        advisor_list = [
            {
                'id': a.id,
                'teacher_id': a.teacher_id,
                'teacher_name': advisor_names.get(a.teacher_id, ''),
                'is_primary': bool(a.is_primary),
                'start_year': a.start_year,
                'end_year': a.end_year,
            }
            for a in advisors
        ]
        return {
            'id': self.id,
            'student_no': self.student_no,
            'name': self.name,
            'grade': self.grade,
            'major': self.major,
            'department': self.department,
            'class_name': self.class_name,
            'email': self.email,
            'phone': self.phone,
            'user_id': self.user_id,
            'username': name,
            'achievement_count': count,
            'advisors': advisor_list,
            'advisor_names': '、'.join(item['teacher_name'] for item in advisor_list if item['teacher_name']),
            'created_at': _fmt(self.created_at),
            'updated_at': _fmt(self.updated_at),
        }

    @classmethod
    def to_dict_list(cls, items):
        ids = [s.id for s in items]
        counts = _achievement_counts(ROLE_STUDENT, ids)
        usernames = _usernames_for(ROLE_STUDENT, ids)
        advisor_map = _advisors_for(ids)
        teacher_names = _teacher_names(
            {a.teacher_id for rows in advisor_map.values() for a in rows}
        )
        return [
            s.to_dict(
                achievement_count=counts.get(s.id, 0),
                username=usernames.get(s.id),
                advisors=advisor_map.get(s.id, []),
                advisor_names=teacher_names,
            )
            for s in items
        ]


class AdvisorRelation(db.Model):
    """教师指导学生关系（支持多导师与按学年变更）。"""

    __tablename__ = 'advisor_relation'
    __table_args__ = (
        db.UniqueConstraint('teacher_id', 'student_id', name='uq_advisor_pair'),
        db.Index('ix_advisor_student', 'student_id'),
        db.Index('ix_advisor_teacher', 'teacher_id'),
    )

    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teacher.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    is_primary = db.Column(db.Boolean, nullable=False, default=False)
    start_year = db.Column(db.Integer)
    end_year = db.Column(db.Integer)
    note = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.now)

    def to_dict(self, teacher_name='', student_name=''):
        return {
            'id': self.id,
            'teacher_id': self.teacher_id,
            'teacher_name': teacher_name,
            'student_id': self.student_id,
            'student_name': student_name,
            'is_primary': bool(self.is_primary),
            'start_year': self.start_year,
            'end_year': self.end_year,
            'note': self.note,
            'created_at': _fmt(self.created_at),
        }


# --------------------------------------------------------------------------- #
# 认证指标点
# --------------------------------------------------------------------------- #
class CertificationIndicator(db.Model):
    __tablename__ = 'certification_indicator'
    __table_args__ = (db.UniqueConstraint('code', name='uq_indicator_code'),)

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(40), nullable=False)
    name = db.Column(db.String(160), nullable=False)
    description = db.Column(db.Text)
    sort_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now)

    def to_dict(self, achievement_count=None):
        return {
            'id': self.id,
            'code': self.code,
            'name': self.name,
            'description': self.description,
            'sort_order': self.sort_order,
            'is_active': bool(self.is_active),
            'achievement_count': achievement_count,
        }


class AchievementIndicator(db.Model):
    __tablename__ = 'achievement_indicator'
    __table_args__ = (
        db.UniqueConstraint('achievement_id', 'indicator_id', name='uq_achievement_indicator'),
        db.Index('ix_ai_indicator', 'indicator_id'),
    )

    id = db.Column(db.Integer, primary_key=True)
    achievement_id = db.Column(db.Integer, db.ForeignKey('achievement.id'), nullable=False)
    indicator_id = db.Column(db.Integer, db.ForeignKey('certification_indicator.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)


# --------------------------------------------------------------------------- #
# 支撑材料
# --------------------------------------------------------------------------- #
class Attachment(db.Model):
    __tablename__ = 'attachment'
    __table_args__ = (
        db.Index('ix_attachment_achievement', 'achievement_id'),
    )

    id = db.Column(db.Integer, primary_key=True)
    achievement_id = db.Column(db.Integer, db.ForeignKey('achievement.id'), nullable=False)
    stored_path = db.Column(db.String(400), nullable=False)   # 相对 UPLOAD_FOLDER
    original_name = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(50), default='其他')
    size = db.Column(db.Integer, default=0)
    mime = db.Column(db.String(120))
    uploaded_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    uploaded_at = db.Column(db.DateTime, default=datetime.now)

    uploader = db.relationship('User', foreign_keys=[uploaded_by])

    def to_dict(self, uploader_name=None):
        name = uploader_name
        if name is None:
            name = self.uploader.username if self.uploader else ''
        return {
            'id': self.id,
            'achievement_id': self.achievement_id,
            'original_name': self.original_name,
            'category': self.category,
            'size': self.size or 0,
            'size_text': format_size(self.size or 0),
            'mime': self.mime,
            'uploaded_by': self.uploaded_by,
            'uploader_name': name,
            'uploaded_at': _fmt(self.uploaded_at),
        }

    @classmethod
    def to_dict_list(cls, items):
        uploader_ids = {a.uploaded_by for a in items if a.uploaded_by}
        names = {}
        if uploader_ids:
            for user in User.query.filter(User.id.in_(uploader_ids)).all():
                names[user.id] = user.username
        return [a.to_dict(uploader_name=names.get(a.uploaded_by, '')) for a in items]


def format_size(size):
    if not size:
        return '0 B'
    units = ['B', 'KB', 'MB', 'GB']
    value = float(size)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f'{value:.0f} {unit}' if unit == 'B' else f'{value:.1f} {unit}'
        value /= 1024
    return f'{size} B'


# --------------------------------------------------------------------------- #
# 业绩成果
# --------------------------------------------------------------------------- #
class Achievement(db.Model):
    __tablename__ = 'achievement'
    __table_args__ = (
        db.Index('ix_achievement_owner', 'owner_type', 'owner_id'),
        db.Index('ix_achievement_dim', 'category', 'year', 'level'),
        db.Index('ix_achievement_status', 'status', 'is_deleted'),
        db.Index('ix_achievement_advisor', 'advisor_id'),
    )

    id = db.Column(db.Integer, primary_key=True)
    owner_type = db.Column(db.String(20), nullable=False)
    owner_id = db.Column(db.Integer, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    year = db.Column(db.Integer)
    academic_year = db.Column(db.String(20))
    level = db.Column(db.String(50))
    role_rank = db.Column(db.String(50))
    description = db.Column(db.Text)
    extra = db.Column(db.JSON, default=dict)

    # 学生成果对应的指导教师（与 AdvisorRelation 互补，用于“某导师指导的学生成果”统计）
    advisor_id = db.Column(db.Integer, db.ForeignKey('teacher.id'))
    # 教师侧「指导学生成果」可引用学生侧成果，避免同一事件被计两次
    source_achievement_id = db.Column(db.Integer, db.ForeignKey('achievement.id'))

    # 审核流
    status = db.Column(db.String(20), nullable=False, default=STATUS_APPROVED)
    reviewer_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    reviewed_at = db.Column(db.DateTime)
    review_comment = db.Column(db.String(500))
    submitted_at = db.Column(db.DateTime)

    # 审计与软删除
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    updated_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    is_deleted = db.Column(db.Boolean, nullable=False, default=False)
    deleted_at = db.Column(db.DateTime)
    deleted_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    # 兼容字段：迁移时会把已有的单附件同步进 attachment 表，此处保留只读展示
    attachment_path = db.Column(db.String(255))

    reviewer = db.relationship('User', foreign_keys=[reviewer_id])
    advisor = db.relationship('Teacher', foreign_keys=[advisor_id])

    # ---------------------------------------------------------------- helpers
    def owner(self):
        if self.owner_type == ROLE_TEACHER:
            return db.session.get(Teacher, self.owner_id)
        if self.owner_type == ROLE_STUDENT:
            return db.session.get(Student, self.owner_id)
        return None

    def extra_value(self, key, default=''):
        data = self.extra
        if not isinstance(data, dict):
            return default
        value = data.get(key)
        return default if value is None else value

    def extra_display(self):
        labels = extra_labels(self.category)
        result = {}
        for key, label in labels.items():
            value = self.extra_value(key)
            if value not in ('', None):
                result[label] = value
        return result

    def to_dict(self, owner=None, attachments=None, indicators=None, advisor_name=None,
                review_comment=False):
        if owner is None:
            owner = self.owner()
        if attachments is None:
            attachments = self.attachment_rows() if self.id else []
        if indicators is None:
            indicators = self.indicator_rows() if self.id else []
        name = advisor_name
        if name is None:
            name = self.advisor.name if self.advisor else ''
        payload = {
            'id': self.id,
            'owner_type': self.owner_type,
            'owner_id': self.owner_id,
            'owner_name': owner.name if owner else '',
            'owner_department': (getattr(owner, 'department', '') or '') if owner else '',
            'category': self.category,
            'title': self.title,
            'year': self.year,
            'academic_year': self.academic_year or academic_year_of(self.year),
            'level': self.level,
            'level_options': levels_for(self.category),
            'role_rank': self.role_rank,
            'description': self.description,
            'extra': self.extra if isinstance(self.extra, dict) else {},
            'extra_display': self.extra_display(),
            'advisor_id': self.advisor_id,
            'advisor_name': name,
            'source_achievement_id': self.source_achievement_id,
            'status': self.status,
            'reviewer_id': self.reviewer_id,
            'reviewed_at': _fmt(self.reviewed_at),
            'submitted_at': _fmt(self.submitted_at),
            'attachments': [a.to_dict() for a in attachments],
            'attachment_count': len(attachments),
            'has_attachment': bool(attachments) or bool(self.attachment_path),
            'indicators': [
                {'id': i.id, 'code': i.code, 'name': i.name} for i in indicators
            ],
            'indicator_ids': [i.id for i in indicators],
            'created_by': self.created_by,
            'updated_by': self.updated_by,
            'created_at': _fmt(self.created_at),
            'updated_at': _fmt(self.updated_at),
            'is_deleted': bool(self.is_deleted),
        }
        if review_comment or self.review_comment:
            payload['review_comment'] = self.review_comment
            payload['reviewer_name'] = self.reviewer.username if self.reviewer else ''
        # 兼容旧前端字段：主附件优先取 attachment_path 指向的那一份
        primary = None
        if self.attachment_path:
            primary = next((a for a in attachments if a.stored_path == self.attachment_path),
                           None)
        if primary is None and attachments:
            primary = attachments[0]
        payload['attachment_name'] = primary.original_name if primary else ''
        payload['attachment_id'] = primary.id if primary else None
        payload['attachment_path'] = self.attachment_path or (
            primary.stored_path if primary else None)
        return payload

    def attachment_rows(self):
        return (Attachment.query.filter_by(achievement_id=self.id)
                .order_by(Attachment.id).all())

    def indicator_rows(self, limit=None):
        query = (db.session.query(CertificationIndicator)
                 .join(AchievementIndicator,
                       AchievementIndicator.indicator_id == CertificationIndicator.id)
                 .filter(AchievementIndicator.achievement_id == self.id)
                 .order_by(CertificationIndicator.sort_order, CertificationIndicator.id))
        return query.all()

    @classmethod
    def to_dict_list(cls, items, with_review_comment=False):
        """批量序列化：固定 5 条查询，与列表长度无关。"""
        if not items:
            return []
        teacher_ids = {a.owner_id for a in items if a.owner_type == ROLE_TEACHER}
        student_ids = {a.owner_id for a in items if a.owner_type == ROLE_STUDENT}
        owners = {}
        if teacher_ids:
            for row in Teacher.query.filter(Teacher.id.in_(teacher_ids)).all():
                owners[(ROLE_TEACHER, row.id)] = row
        if student_ids:
            for row in Student.query.filter(Student.id.in_(student_ids)).all():
                owners[(ROLE_STUDENT, row.id)] = row
        achievement_ids = [a.id for a in items]
        attachments = _attachments_for(achievement_ids)
        indicators = _indicators_for(achievement_ids)
        advisor_names = _teacher_names({a.advisor_id for a in items if a.advisor_id})
        return [
            a.to_dict(
                owner=owners.get((a.owner_type, a.owner_id)),
                attachments=attachments.get(a.id, []),
                indicators=indicators.get(a.id, []),
                advisor_name=advisor_names.get(a.advisor_id, ''),
                review_comment=with_review_comment,
            )
            for a in items
        ]


# --------------------------------------------------------------------------- #
# 操作日志
# --------------------------------------------------------------------------- #
class OperationLog(db.Model):
    __tablename__ = 'operation_log'
    __table_args__ = (
        db.Index('ix_log_created', 'created_at'),
        db.Index('ix_log_target', 'target_type', 'target_id'),
        db.Index('ix_log_action', 'action'),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    username = db.Column(db.String(80))
    role = db.Column(db.String(20))
    action = db.Column(db.String(60), nullable=False)
    target_type = db.Column(db.String(40))
    target_id = db.Column(db.Integer)
    summary = db.Column(db.String(500))
    detail = db.Column(db.JSON)
    ip = db.Column(db.String(60))
    created_at = db.Column(db.DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'username': self.username,
            'role': self.role,
            'action': self.action,
            'target_type': self.target_type,
            'target_id': self.target_id,
            'summary': self.summary,
            'detail': self.detail if isinstance(self.detail, dict) else {},
            'ip': self.ip,
            'created_at': _fmt(self.created_at),
        }


# --------------------------------------------------------------------------- #
# 批量查询辅助（避免 N+1）
# --------------------------------------------------------------------------- #
def _achievement_counts(owner_type, owner_ids):
    from sqlalchemy import func
    if not owner_ids:
        return {}
    rows = (db.session.query(Achievement.owner_id, func.count(Achievement.id))
            .filter(Achievement.owner_type == owner_type,
                    Achievement.owner_id.in_(owner_ids),
                    Achievement.is_deleted.is_(False))
            .group_by(Achievement.owner_id).all())
    return {owner_id: count for owner_id, count in rows}


def _usernames_for(owner_type, owner_ids):
    if not owner_ids:
        return {}
    rows = (db.session.query(User.owner_id, User.username)
            .filter(User.owner_type == owner_type, User.owner_id.in_(owner_ids)).all())
    return {owner_id: username for owner_id, username in rows}


def _teacher_names(teacher_ids):
    ids = {tid for tid in teacher_ids if tid}
    if not ids:
        return {}
    rows = db.session.query(Teacher.id, Teacher.name).filter(Teacher.id.in_(ids)).all()
    return {tid: name for tid, name in rows}


def _advisors_for(student_ids):
    if not student_ids:
        return {}
    rows = (AdvisorRelation.query
            .filter(AdvisorRelation.student_id.in_(student_ids))
            .order_by(AdvisorRelation.is_primary.desc(), AdvisorRelation.id)
            .all())
    result = {}
    for row in rows:
        result.setdefault(row.student_id, []).append(row)
    return result


def _attachments_for(achievement_ids):
    if not achievement_ids:
        return {}
    rows = (Attachment.query
            .filter(Attachment.achievement_id.in_(achievement_ids))
            .order_by(Attachment.id)
            .all())
    result = {}
    for row in rows:
        result.setdefault(row.achievement_id, []).append(row)
    return result


def _indicators_for(achievement_ids):
    if not achievement_ids:
        return {}
    rows = (db.session.query(AchievementIndicator.achievement_id, CertificationIndicator)
            .join(CertificationIndicator,
                  AchievementIndicator.indicator_id == CertificationIndicator.id)
            .filter(AchievementIndicator.achievement_id.in_(achievement_ids))
            .order_by(CertificationIndicator.sort_order, CertificationIndicator.id)
            .all())
    result = {}
    for achievement_id, indicator in rows:
        result.setdefault(achievement_id, []).append(indicator)
    return result


def counted_statuses():
    return list(COUNTED_STATUSES)


def allowed_categories(owner_type):
    return categories_for(owner_type)