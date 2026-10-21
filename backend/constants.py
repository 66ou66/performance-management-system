"""业务字典与元数据（唯一事实来源）。

前端通过 /api/meta/options 获取同一份定义来渲染表单与筛选器，
后端在写入时同样用它做校验，避免“前端能选、后端不认”或脏值入库。
"""

# --------------------------------------------------------------------------- #
# 角色
# --------------------------------------------------------------------------- #
ROLE_ADMIN = 'admin'
ROLE_REVIEWER = 'reviewer'   # 审核员 / 专业负责人：可查看全部并审核，不管理档案与账号
ROLE_TEACHER = 'teacher'
ROLE_STUDENT = 'student'

ROLE_LABELS = {
    ROLE_ADMIN: '管理员',
    ROLE_REVIEWER: '审核员',
    ROLE_TEACHER: '教师',
    ROLE_STUDENT: '学生',
}
ROLES = [
    {'value': ROLE_ADMIN, 'label': ROLE_LABELS[ROLE_ADMIN]},
    {'value': ROLE_REVIEWER, 'label': ROLE_LABELS[ROLE_REVIEWER]},
    {'value': ROLE_TEACHER, 'label': ROLE_LABELS[ROLE_TEACHER]},
    {'value': ROLE_STUDENT, 'label': ROLE_LABELS[ROLE_STUDENT]},
]
# 拥有全局只读范围的角色（不受“仅本人数据”限制）
ELEVATED_ROLES = (ROLE_ADMIN, ROLE_REVIEWER)

# --------------------------------------------------------------------------- #
# 成果类别
# --------------------------------------------------------------------------- #
TEACHER_CATEGORIES = ['教学成果', '科研成果', '指导学生成果']
STUDENT_CATEGORIES = ['学科竞赛', '奖学金', '专利', '论文', '软件著作权', '行业认证']
ALL_CATEGORIES = TEACHER_CATEGORIES + STUDENT_CATEGORIES

# 需要关联“指导教师”的学生类别（用于指导关系闭环）
CATEGORIES_WITH_ADVISOR = ['学科竞赛', '专利', '论文', '软件著作权', '行业认证']

# --------------------------------------------------------------------------- #
# 成果级别：按类别区分口径
#   教学/科研成果使用行政级别；论文使用收录级别；专利使用专利类型等
# --------------------------------------------------------------------------- #
ADMIN_LEVELS = ['国家级', '省部级', '市厅级', '校级', '院级', '其他']
LEVELS_BY_CATEGORY = {
    '教学成果': ADMIN_LEVELS,
    '科研成果': ADMIN_LEVELS,
    '指导学生成果': ADMIN_LEVELS,
    '学科竞赛': ['国际级', '国家级', '省部级', '市厅级', '校级', '其他'],
    '奖学金': ['国家级', '省级', '校级', '院级', '社会捐赠', '其他'],
    '专利': ['国际专利', '发明专利', '实用新型', '外观设计'],
    '论文': ['SCI', 'EI', 'CSSCI', '北大核心', '科技核心', '普通期刊', '会议论文', '其他'],
    '软件著作权': ['软件著作权'],
    '行业认证': ['国际认证', '国家级', '行业级', '厂商级'],
}
# 兼容旧数据与旧筛选器：全部可选级别的并集（保序去重）
LEVELS = []
for _category in ALL_CATEGORIES:
    for _level in LEVELS_BY_CATEGORY.get(_category, ADMIN_LEVELS):
        if _level not in LEVELS:
            LEVELS.append(_level)

AWARD_RANKS = ['特等奖', '一等奖', '二等奖', '三等奖', '优秀奖', '入围奖', '金奖', '银奖', '铜奖', '其他']
PAPER_INDEX_TYPES = ['SCI', 'SCIE', 'EI', 'CSSCI', '北大核心', '科技核心', 'ISTP', '其他']
ROLE_RANKS = ['第一作者', '第二作者', '第三作者', '通讯作者', '其他作者',
              '第一发明人', '第二发明人', '第三发明人', '其他发明人',
              '主持人', '主要参与人', '一般参与人']

# --------------------------------------------------------------------------- #
# 类别专有字段模板（存入 Achievement.extra JSON）
#   type: text / textarea / number / date / select
# --------------------------------------------------------------------------- #
FIELD_TEMPLATES = {
    '教学成果': [
        {'key': 'project_name', 'label': '项目/课程名称', 'type': 'text', 'maxlength': 160},
        {'key': 'project_no', 'label': '立项编号', 'type': 'text', 'maxlength': 80},
        {'key': 'grant_unit', 'label': '立项/认定单位', 'type': 'text', 'maxlength': 120},
    ],
    '科研成果': [
        {'key': 'project_name', 'label': '项目名称', 'type': 'text', 'maxlength': 160},
        {'key': 'project_no', 'label': '项目编号', 'type': 'text', 'maxlength': 80},
        {'key': 'fund_source', 'label': '经费来源', 'type': 'text', 'maxlength': 120},
        {'key': 'fund_amount', 'label': '经费金额（万元）', 'type': 'number'},
    ],
    '指导学生成果': [
        {'key': 'contest_name', 'label': '竞赛/项目名称', 'type': 'text', 'maxlength': 160},
        {'key': 'award_rank', 'label': '获奖等级', 'type': 'select', 'options': AWARD_RANKS},
        {'key': 'student_names', 'label': '指导学生姓名', 'type': 'text', 'maxlength': 200},
    ],
    '学科竞赛': [
        {'key': 'contest_name', 'label': '竞赛名称', 'type': 'text', 'maxlength': 160},
        {'key': 'award_rank', 'label': '获奖等级', 'type': 'select', 'options': AWARD_RANKS},
        {'key': 'team_rank', 'label': '团队排名', 'type': 'text', 'maxlength': 40},
        {'key': 'certificate_no', 'label': '证书编号', 'type': 'text', 'maxlength': 80},
        {'key': 'organizer', 'label': '主办单位', 'type': 'text', 'maxlength': 120},
        {'key': 'team_members', 'label': '团队成员', 'type': 'text', 'maxlength': 200},
    ],
    '奖学金': [
        {'key': 'scholarship_name', 'label': '奖学金名称', 'type': 'text', 'maxlength': 120},
        {'key': 'award_rank', 'label': '获奖等级', 'type': 'select', 'options': ['一等', '二等', '三等', '单项', '其他']},
        {'key': 'amount', 'label': '金额（元）', 'type': 'number'},
        {'key': 'issuer', 'label': '评定单位', 'type': 'text', 'maxlength': 120},
    ],
    '专利': [
        {'key': 'patent_no', 'label': '专利号', 'type': 'text', 'maxlength': 80},
        {'key': 'patent_type', 'label': '专利类型', 'type': 'select',
         'options': ['发明专利', '实用新型', '外观设计', '国际专利']},
        {'key': 'authorize_date', 'label': '授权日期', 'type': 'date'},
        {'key': 'applicant', 'label': '专利权人', 'type': 'text', 'maxlength': 120},
    ],
    '论文': [
        {'key': 'journal', 'label': '期刊/会议名称', 'type': 'text', 'maxlength': 160},
        {'key': 'index_type', 'label': '收录类型', 'type': 'select', 'options': PAPER_INDEX_TYPES},
        {'key': 'volume_issue', 'label': '卷期页码', 'type': 'text', 'maxlength': 80},
        {'key': 'doi', 'label': 'DOI', 'type': 'text', 'maxlength': 100},
        {'key': 'impact_factor', 'label': '影响因子', 'type': 'number'},
        {'key': 'publish_date', 'label': '发表时间', 'type': 'date'},
    ],
    '软件著作权': [
        {'key': 'register_no', 'label': '登记号', 'type': 'text', 'maxlength': 80},
        {'key': 'register_date', 'label': '登记日期', 'type': 'date'},
        {'key': 'copyright_owner', 'label': '著作权人', 'type': 'text', 'maxlength': 120},
        {'key': 'finish_date', 'label': '开发完成日期', 'type': 'date'},
    ],
    '行业认证': [
        {'key': 'cert_name', 'label': '认证名称', 'type': 'text', 'maxlength': 160},
        {'key': 'issuer', 'label': '认证机构', 'type': 'text', 'maxlength': 120},
        {'key': 'certificate_no', 'label': '证书编号', 'type': 'text', 'maxlength': 80},
        {'key': 'issue_date', 'label': '取得日期', 'type': 'date'},
        {'key': 'expire_date', 'label': '有效期至', 'type': 'date'},
    ],
}

# 导出 Excel 时把这些专有字段展开成列（顺序即列顺序）
EXTRA_EXPORT_KEYS = {
    '教学成果': ['project_name', 'project_no', 'grant_unit'],
    '科研成果': ['project_name', 'project_no', 'fund_source', 'fund_amount'],
    '指导学生成果': ['contest_name', 'award_rank', 'student_names'],
    '学科竞赛': ['contest_name', 'award_rank', 'team_rank', 'certificate_no', 'organizer', 'team_members'],
    '奖学金': ['scholarship_name', 'award_rank', 'amount', 'issuer'],
    '专利': ['patent_no', 'patent_type', 'authorize_date', 'applicant'],
    '论文': ['journal', 'index_type', 'volume_issue', 'doi', 'impact_factor', 'publish_date'],
    '软件著作权': ['register_no', 'register_date', 'copyright_owner', 'finish_date'],
    '行业认证': ['cert_name', 'issuer', 'certificate_no', 'issue_date', 'expire_date'],
}


def extra_labels(category):
    """返回 {字段key: 中文标签}，供导出与详情展示使用。"""
    return {field['key']: field['label'] for field in FIELD_TEMPLATES.get(category, [])}


def extra_keys(category):
    return [field['key'] for field in FIELD_TEMPLATES.get(category, [])]


# --------------------------------------------------------------------------- #
# 审核状态
# --------------------------------------------------------------------------- #
STATUS_DRAFT = 'draft'
STATUS_PENDING = 'pending'
STATUS_APPROVED = 'approved'
STATUS_REJECTED = 'rejected'

STATUS_LABELS = {
    STATUS_DRAFT: '草稿',
    STATUS_PENDING: '待审核',
    STATUS_APPROVED: '已通过',
    STATUS_REJECTED: '已驳回',
}
STATUSES = [{'value': key, 'label': label} for key, label in STATUS_LABELS.items()]
# 计入统计与导出的默认状态
COUNTED_STATUSES = (STATUS_APPROVED,)

# --------------------------------------------------------------------------- #
# 支撑材料分类
# --------------------------------------------------------------------------- #
ATTACHMENT_CATEGORIES = [
    '获奖证书', '立项/结题材料', '成果正文', '检索/收录证明',
    '申报书', '现场照片', '其他',
]

# 字典类型（DictItem.kind）
DICT_KINDS = {
    'department': '院系',
    'major': '专业',
    'title': '职称',
    'grade': '年级',
}

# 认证指标点默认模板（工程教育认证毕业要求，可被数据库中的自定义指标覆盖）
DEFAULT_INDICATORS = [
    {'code': '1', 'name': '工程知识', 'description': '能够将数学、自然科学、工程基础和专业知识用于解决复杂工程问题。'},
    {'code': '2', 'name': '问题分析', 'description': '能够应用数学、自然科学和工程科学的基本原理，识别、表达并通过文献研究分析复杂工程问题。'},
    {'code': '3', 'name': '设计/开发解决方案', 'description': '能够设计针对复杂工程问题的解决方案，并能够在设计环节中体现创新意识。'},
    {'code': '4', 'name': '研究', 'description': '能够基于科学原理并采用科学方法对复杂工程问题进行研究。'},
    {'code': '5', 'name': '使用现代工具', 'description': '能够针对复杂工程问题，开发、选择与使用恰当的技术、资源、现代工程工具和信息技术工具。'},
    {'code': '6', 'name': '工程与社会', 'description': '能够基于工程相关背景知识进行合理分析，评价专业工程实践和复杂工程问题解决方案对社会的影响。'},
    {'code': '7', 'name': '环境和可持续发展', 'description': '能够理解和评价针对复杂工程问题的专业工程实践对环境、社会可持续发展的影响。'},
    {'code': '8', 'name': '职业规范', 'description': '具有人文社会科学素养、社会责任感，能够在工程实践中理解并遵守工程职业道德和规范。'},
    {'code': '9', 'name': '个人和团队', 'description': '能够在多学科背景下的团队中承担个体、团队成员以及负责人的角色。'},
    {'code': '10', 'name': '沟通', 'description': '能够就复杂工程问题与业界同行及社会公众进行有效沟通和交流。'},
    {'code': '11', 'name': '项目管理', 'description': '理解并掌握工程管理原理与经济决策方法，并能在多学科环境中应用。'},
    {'code': '12', 'name': '终身学习', 'description': '具有自主学习和终身学习的意识，有不断学习和适应发展的能力。'},
]


def categories_for(owner_type):
    if owner_type == ROLE_TEACHER:
        return list(TEACHER_CATEGORIES)
    if owner_type == ROLE_STUDENT:
        return list(STUDENT_CATEGORIES)
    return list(ALL_CATEGORIES)


def levels_for(category):
    if category in LEVELS_BY_CATEGORY:
        return list(LEVELS_BY_CATEGORY[category])
    return list(ADMIN_LEVELS)


def category_owner_type(category):
    """由类别反推归属人类型。"""
    if category in TEACHER_CATEGORIES:
        return ROLE_TEACHER
    if category in STUDENT_CATEGORIES:
        return ROLE_STUDENT
    return None