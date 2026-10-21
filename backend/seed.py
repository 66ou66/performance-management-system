"""演示数据。

仅在数据库里一个账号都没有时写入，覆盖新模型的全部特性：
- 教师 / 学生 / 审核员三类账号与人员档案的双向关联（accounts.sync_user_links）
- 成果的学年、审核状态、类别专有字段（extra）
- 教师—学生指导关系（AdvisorRelation）
- 支撑材料的分类归档（Attachment + 真实落盘文件）
- 认证指标点关联（AchievementIndicator）
- 字典项（院系 / 专业 / 职称 / 年级）

注意：演示账号与密码（admin/admin123、teacher1/123456、student1/123456）是给初次
启动的用户体验用的，正式部署请立即修改或删除。
"""
import os

from audit import ACTION_CREATE, log_operation
from extensions import db
from models import (
    Achievement,
    AchievementIndicator,
    AdvisorRelation,
    Attachment,
    CertificationIndicator,
    DictItem,
    Student,
    Teacher,
    User,
)
from services import relative_storage_dir

PLACEHOLDER_TEXT = """这是系统自动生成的演示佐证材料。

真实使用时请在此位置上传扫描件或电子版文件（PDF / 图片 / Office 文档均可），
并在「支撑材料」区域选择正确的材料分类，例如：获奖证书、立项/结题材料、
成果正文、检索/收录证明、申报书、现场照片等。

材料分类规范后，导出的「佐证材料包」会按
<院系>/<所属人>/<成果序号_成果名称>/<材料分类>/<文件名>
的目录结构自动整理，可直接提交给认证或评估专家查阅。
"""


def seed_if_empty():
    if User.query.count() > 0:
        return
    from flask import current_app

    admin = User(username='admin', role='admin')
    admin.set_password('admin123')
    db.session.add(admin)

    reviewer = User(username='reviewer', role='reviewer')
    reviewer.set_password('123456')
    db.session.add(reviewer)
    db.session.flush()

    teacher_rows = [
        {'name': '张伟', 'department': '计算机学院', 'title': '教授',
         'email': 'zhangwei@example.com', 'phone': '13800000001',
         'research_area': '数据治理与工程教育认证', 'username': 'teacher1'},
        {'name': '李娜', 'department': '软件学院', 'title': '副教授',
         'email': 'lina@example.com', 'phone': '13800000002',
         'research_area': '软件缺陷预测与智能测试', 'username': 'teacher2'},
        {'name': '王强', 'department': '计算机学院', 'title': '讲师',
         'email': 'wangqiang@example.com', 'phone': '13800000003',
         'research_area': '多源数据融合与智慧校园', 'username': 'teacher3'},
    ]
    teachers = []
    for row in teacher_rows:
        teacher = Teacher(
            name=row['name'], department=row['department'], title=row['title'],
            email=row['email'], phone=row['phone'], research_area=row['research_area'],
        )
        db.session.add(teacher)
        db.session.flush()
        user = User(username=row['username'], role='teacher',
                    owner_type='teacher', owner_id=teacher.id)
        user.set_password('123456')
        db.session.add(user)
        db.session.flush()
        teacher.user_id = user.id
        teachers.append(teacher)

    student_rows = [
        {'student_no': '2021001', 'name': '刘洋', 'grade': '2021级', 'major': '软件工程',
         'department': '计算机学院', 'class_name': '软工2101',
         'email': 'liuyang@example.com', 'phone': '13900000001', 'username': 'student1'},
        {'student_no': '2022002', 'name': '陈静', 'grade': '2022级',
         'major': '计算机科学与技术', 'department': '计算机学院', 'class_name': '计科2202',
         'email': 'chenjing@example.com', 'phone': '13900000002', 'username': 'student2'},
    ]
    students = []
    for row in student_rows:
        student = Student(
            student_no=row['student_no'], name=row['name'], grade=row['grade'],
            major=row['major'], department=row['department'],
            class_name=row['class_name'], email=row['email'], phone=row['phone'],
        )
        db.session.add(student)
        db.session.flush()
        user = User(username=row['username'], role='student',
                    owner_type='student', owner_id=student.id)
        user.set_password('123456')
        db.session.add(user)
        db.session.flush()
        student.user_id = user.id
        students.append(student)

    # 指导关系：刘洋 → 张伟（主导师）；陈静 → 李娜（主导师）+ 王强
    for teacher, student, is_primary in (
        (teachers[0], students[0], True),
        (teachers[1], students[1], True),
        (teachers[2], students[1], False),
    ):
        db.session.add(AdvisorRelation(
            teacher_id=teacher.id, student_id=student.id, is_primary=is_primary,
            start_year=2022, note='演示数据',
        ))

    achievement_rows = [
        # owner_type, owner, category, title, year, level, role_rank, description, extra
        ('teacher', teachers[0], '科研成果', '面向工程教育认证的智能数据治理方法研究',
         2025, '省部级', '主持人', '主持省级自然科学基金项目，围绕认证数据治理开展研究。',
         {'project_name': '面向工程教育认证的智能数据治理方法研究',
          'project_no': '2025JZ0412', 'fund_source': '省自然科学基金', 'fund_amount': 12}),
        ('teacher', teachers[0], '教学成果', '《数据结构》课程混合式教学改革与实践',
         2024, '校级', '主持人', '主持校级教改项目，建设在线课程资源。',
         {'project_name': '《数据结构》课程混合式教学改革', 'project_no': 'JG2024-018',
          'grant_unit': '教务处'}),
        ('teacher', teachers[0], '指导学生成果', '指导学生获中国大学生计算机设计大赛二等奖',
         2024, '国家级', '主要参与人', '指导学生团队参加学科竞赛并获奖。',
         {'contest_name': '中国大学生计算机设计大赛', 'award_rank': '二等奖',
          'student_names': '刘洋'}),
        ('teacher', teachers[1], '科研成果', '基于深度学习的软件缺陷预测关键技术',
         2025, '国家级', '主持人', '发表高水平学术论文并申请发明专利。',
         {'project_name': '软件缺陷预测关键技术', 'project_no': 'NSFC-62172xxx',
          'fund_source': '国家自然科学基金', 'fund_amount': 58}),
        ('teacher', teachers[1], '教学成果', '软件工程专业课程思政教学团队建设',
         2023, '省部级', '主要参与人', '参与省级课程思政示范项目建设。',
         {'project_name': '软件工程专业课程思政教学团队', 'project_no': 'SZ2023-07',
          'grant_unit': '省教育厅'}),
        ('teacher', teachers[2], '科研成果', '面向智慧校园的多源数据融合平台',
         2022, '市厅级', '主持人', '主持横向课题，完成平台原型开发。',
         {'project_name': '多源数据融合平台', 'project_no': 'HX2022-33',
          'fund_source': '企业横向课题', 'fund_amount': 20}),
        ('teacher', teachers[2], '指导学生成果', '指导学生完成大学生创新创业训练计划项目',
         2023, '校级', '主要参与人', '指导国家级大创项目顺利结题。',
         {'contest_name': '大学生创新创业训练计划', 'award_rank': '优秀奖',
          'student_names': '陈静'}),
        ('student', students[0], '学科竞赛', '中国大学生服务外包创新创业大赛三等奖',
         2024, '国家级', '第一作者', '团队参赛并获全国三等奖。',
         {'contest_name': '中国大学生服务外包创新创业大赛', 'award_rank': '三等奖',
          'team_rank': '队长', 'certificate_no': 'FW2024-3-0218',
          'organizer': '教育部高教司', 'team_members': '刘洋、陈静'}),
        ('student', students[0], '奖学金', '校级一等奖学金', 2023, '校级', '第一作者',
         '2022-2023 学年综合测评专业前十。',
         {'scholarship_name': '校级一等奖学金', 'award_rank': '一等',
          'amount': 3000, 'issuer': '学生工作处'}),
        ('student', students[0], '软件著作权', '校园业绩管理系统 V1.0', 2024, '软件著作权',
         '第一作者', '作为主要完成人获得软件著作权登记。',
         {'register_no': '2024SR0432188', 'register_date': '2024-05-16',
          'copyright_owner': '本单位', 'finish_date': '2024-03-20'}),
        ('student', students[1], '论文', '基于知识图谱的学业预警方法研究', 2025,
         '北大核心', '第一作者', '以第一作者发表学术论文一篇。',
         {'journal': '计算机工程与应用', 'index_type': '北大核心', 'volume_issue': '61(4): 88-96',
          'doi': '10.3778/j.issn.1002-8331.2405-0111', 'impact_factor': 1.8,
          'publish_date': '2025-02-20'}),
        ('student', students[1], '专利', '一种多源异构数据清洗装置', 2024, '实用新型',
         '第二发明人', '作为第二发明人申请实用新型专利。',
         {'patent_no': 'ZL2024 2 0334455.6', 'patent_type': '实用新型',
          'authorize_date': '2024-09-13', 'applicant': '本单位'}),
        ('student', students[1], '行业认证', 'HarmonyOS 应用开发者高级认证', 2025, '厂商级',
         '第一作者', '通过华为开发者能力认证。',
         {'cert_name': 'HarmonyOS 应用开发者高级认证', 'issuer': '华为技术有限公司',
          'certificate_no': 'HW-HOS-2025-88712', 'issue_date': '2025-03-11',
          'expire_date': '2028-03-10'}),
        ('student', students[1], '学科竞赛', '蓝桥杯全国软件和信息技术专业人才大赛省赛一等奖',
         2024, '省部级', '第一作者', '获得省赛一等奖。',
         {'contest_name': '蓝桥杯全国软件和信息技术专业人才大赛', 'award_rank': '一等奖',
          'team_rank': '个人赛', 'certificate_no': 'LQ2024-S-10233',
          'organizer': '工业和信息化部人才交流中心', 'team_members': '陈静'}),
        # 待审核示例：用于演示审核流程与"待审核"提醒
        ('student', students[1], '论文', '面向在线学习的注意力检测方法（待审核示例）', 2025,
         'EI', '第一作者', '等待专业负责人审核的示例数据。',
         {'journal': '待定', 'index_type': 'EI', 'publish_date': '2025-06-01'}),
    ]

    created = []
    for (owner_type, owner, category, title, year, level, role_rank,
         description, extra) in achievement_rows:
        pending = '待审核示例' in title
        academic_year = f'{year}-{year + 1}'
        achievement = Achievement(
            owner_type=owner_type,
            owner_id=owner.id,
            category=category,
            title=title,
            year=year,
            academic_year=academic_year,
            level=level,
            role_rank=role_rank,
            description=description,
            extra=extra,
            status='pending' if pending else 'approved',
            created_by=admin.id,
            updated_by=admin.id,
        )
        if owner_type == 'student' and category in (
                '学科竞赛', '专利', '论文', '软件著作权', '行业认证'):
            advisor = teachers[0] if owner is students[0] else teachers[1]
            achievement.advisor_id = advisor.id
        db.session.add(achievement)
        created.append(achievement)
    db.session.flush()

    _seed_attachments(created, admin, current_app)
    _seed_indicator_links(created)
    _seed_dict_items(teachers, students)

    db.session.commit()
    log_operation(ACTION_CREATE, 'system', None, '初始化演示数据', user=admin)


def _seed_attachments(achievements, admin, app):
    """给部分成果写入真实落盘的演示佐证材料。"""
    upload_folder = app.config['UPLOAD_FOLDER']
    targets = {
        0: ['立项/结题材料', '申报书'],
        1: ['立项/结题材料'],
        3: ['申报书', '成果正文'],
        7: ['获奖证书'],
        10: ['检索/收录证明', '成果正文'],
    }
    for index, categories in targets.items():
        if index >= len(achievements):
            continue
        achievement = achievements[index]
        for order, category in enumerate(categories, start=1):
            relative_dir = relative_storage_dir(achievement)
            folder = os.path.join(upload_folder, relative_dir)
            os.makedirs(folder, exist_ok=True)
            filename = f'{achievement.id}_{order}_演示材料说明.txt'
            full = os.path.join(folder, filename)
            with open(full, 'w', encoding='utf-8-sig') as handle:
                handle.write(PLACEHOLDER_TEXT)
            db.session.add(Attachment(
                achievement_id=achievement.id,
                stored_path=os.path.join(relative_dir, filename).replace('\\', '/'),
                original_name=f'{category}-演示材料说明.txt',
                category=category,
                size=os.path.getsize(full),
                mime='text/plain',
                uploaded_by=admin.id,
            ))


def _seed_indicator_links(achievements):
    by_code = {item.code: item for item in CertificationIndicator.query.all()}
    links = {
        0: ['4', '5', '12'],
        1: ['3', '5'],
        2: ['3', '9', '10'],
        3: ['4', '5'],
        4: ['8', '9'],
        7: ['9', '10', '11'],
        10: ['4', '5'],
        12: ['6', '7'],
    }
    for index, codes in links.items():
        if index >= len(achievements):
            continue
        for code in codes:
            indicator = by_code.get(code)
            if indicator is None:
                continue
            db.session.add(AchievementIndicator(
                achievement_id=achievements[index].id, indicator_id=indicator.id))


def _seed_dict_items(teachers, students):
    existing = {(item.kind, item.name) for item in DictItem.query.all()}
    rows = []
    for teacher in teachers:
        rows.append(('department', teacher.department, ['计算机系'] if teacher.department == '计算机学院' else []))
        rows.append(('title', teacher.title, []))
    for student in students:
        rows.append(('department', student.department, []))
        rows.append(('major', student.major, ['软件工程专业'] if student.major == '软件工程' else []))
        rows.append(('grade', student.grade, []))
    for kind, name, aliases in rows:
        if not name or (kind, name) in existing:
            continue
        existing.add((kind, name))
        db.session.add(DictItem(kind=kind, name=name, aliases=aliases, sort_order=0))