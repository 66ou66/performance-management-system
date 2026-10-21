"""端到端业务流程校验：导入、导出、附件、审核、回收站、统计、权限、性能。

使用独立的临时数据库与临时上传目录，不会影响 backend/app.db 的演示数据。
运行： ..\\.venv\\Scripts\\python.exe -u verify_flows.py
"""
import gc
import os
import sys
import tempfile
import zipfile
from io import BytesIO

TEMP_DIR = tempfile.mkdtemp(prefix='achievement_verify_')
os.environ['DATABASE_URL'] = 'sqlite:///' + os.path.join(TEMP_DIR, 'verify.db')
os.environ['UPLOAD_FOLDER'] = os.path.join(TEMP_DIR, 'uploads')
os.environ['BACKUP_FOLDER'] = os.path.join(TEMP_DIR, 'backups')
os.environ['LOG_FOLDER'] = os.path.join(TEMP_DIR, 'logs')

from openpyxl import Workbook, load_workbook  # noqa: E402
from sqlalchemy import event  # noqa: E402

from app import create_app  # noqa: E402
from extensions import db  # noqa: E402
from models import Achievement, Attachment, Teacher, User  # noqa: E402

FAILURES = []
REPORT_SHEETS = [
    '概览', '成果明细', '成果类型分布', '年度成果趋势', '成果级别分布', '院系成果分布',
    '师生汇总', '缺件清单', '指标点覆盖', '指导教师成果',
]


def check(label, condition, detail=''):
    if condition:
        print('PASS  %s' % label)
    else:
        message = '%s %s' % (label, detail)
        print('FAIL  %s' % message)
        FAILURES.append(message)


def login(client, username, password):
    return client.post('/api/auth/login', json={'username': username, 'password': password})


def build_xlsx(headers, rows):
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(headers)
    for row in rows:
        sheet.append(row)
    buffer = BytesIO()
    workbook.save(buffer)
    buffer.seek(0)
    return buffer


def auth_header(resp):
    return {'Authorization': 'Bearer %s' % resp.get_json()['data']['access_token']}


def count_sql(engine, callback):
    """统计一次请求产生的 SQL 语句数量（用于回归 N+1）。"""
    statements = []

    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    event.listen(engine, 'before_cursor_execute', before_cursor_execute)
    try:
        callback()
    finally:
        event.remove(engine, 'before_cursor_execute', before_cursor_execute)
    return statements


def main():
    app = create_app()
    app.config['TESTING'] = True
    client = app.test_client()

    resp = login(client, 'admin', 'admin123')
    check('管理员登录', resp.status_code == 200, resp.get_data(as_text=True)[:120])
    admin = auth_header(resp)

    # ------------------------------------------------------------------ 统计
    resp = client.get('/api/stats/overview', headers=admin)
    overview = resp.get_json()['data']
    check('统计概览', resp.status_code == 200 and overview['counts']['achievements'] >= 14,
          'achievements=%s' % overview['counts'].get('achievements'))
    check('概览包含缺件与待审核指标',
          'missing_evidence' in overview['counts'] and 'pending' in overview['counts'],
          str(sorted(overview['counts'])))
    for dimension in ('category', 'year', 'level', 'department', 'status', 'academic_year'):
        resp = client.get('/api/stats/breakdown?dimension=' + dimension, headers=admin)
        items = resp.get_json()['data']['items']
        check('统计维度 %s' % dimension, resp.status_code == 200 and len(items) > 0)
    resp = client.get('/api/stats/breakdown?dimension=year', headers=admin)
    years = [row['name'] for row in resp.get_json()['data']['items']]
    check('年度维度按名称排序', years == sorted(years), str(years))
    resp = client.get('/api/stats/breakdown?dimension=not-exist', headers=admin)
    check('非法统计维度被拒绝', resp.status_code == 400, str(resp.status_code))

    resp = client.get('/api/stats/cross?row=category&col=year', headers=admin)
    cross = resp.get_json()['data']
    check('交叉统计', resp.status_code == 200 and len(cross['rows']) > 0
          and len(cross['cols']) > 0 and len(cross['cells']) > 0, str(resp.status_code))

    resp = client.get('/api/stats/ranking?by=teacher&limit=3', headers=admin)
    ranking = resp.get_json()['data']['items']
    check('个人排行', resp.status_code == 200 and len(ranking) <= 3 and ranking[0]['value'] > 0,
          str(ranking))

    resp = client.get('/api/stats/indicators', headers=admin)
    coverage = resp.get_json()['data']
    check('认证指标点覆盖统计',
          resp.status_code == 200 and len(coverage['items']) >= 12
          and coverage['covered_achievements'] > 0, str(coverage.get('coverage_percent')))

    # -------------------------------------------------------------- 导入模板
    for kind in ('teachers', 'achievements', 'students'):
        resp = client.get('/api/import/templates/' + kind, headers=admin)
        ok = resp.status_code == 200 and resp.mimetype.endswith('spreadsheetml.sheet')
        if ok:
            ok = len(load_workbook(BytesIO(resp.data)).active[1]) >= 4
        check('下载 %s 导入模板' % kind, ok)

    # -------------------------------------------------------------- 教师导入
    teacher_file = build_xlsx(
        ['姓名', '所属院系', '职称', '邮箱', '登录名', '初始密码'],
        [
            ['导入教师甲', '信息工程学院', '副教授', 'imp1@example.com', 'import_t1', 'abc123'],
            ['', '信息工程学院', '讲师', 'imp2@example.com', 'import_t2', 'abc123'],
            ['导入教师乙', '信息工程学院', '讲师', 'imp3@example.com', 'teacher1', 'abc123'],
        ],
    )
    resp = client.post('/api/import/teachers', data={'file': (teacher_file, 'teachers.xlsx')},
                       content_type='multipart/form-data', headers=admin)
    payload = resp.get_json()
    result = payload.get('data') or {}
    check('教师导入成功 1 条并跳过 2 条',
          resp.status_code == 200 and result.get('created') == 1 and result.get('skipped') == 2,
          str(payload))
    check('教师导入返回逐行错误说明', len(result.get('errors') or []) == 2, str(result.get('errors')))

    resp = login(client, 'import_t1', 'abc123')
    check('导入教师账号可登录', resp.status_code == 200, resp.get_data(as_text=True)[:120])
    imported_teacher_token = auth_header(resp)

    # 账号与人员档案双向关联
    with app.app_context():
        imported_teacher = Teacher.query.filter_by(name='导入教师甲').first()
        linked_user = User.query.filter_by(username='import_t1').first()
        check('导入教师账号与档案双向关联',
              imported_teacher is not None and linked_user is not None
              and imported_teacher.user_id == linked_user.id
              and linked_user.owner_type == 'teacher'
              and linked_user.owner_id == imported_teacher.id,
              'teacher.user_id=%s user.owner_id=%s' % (
                  getattr(imported_teacher, 'user_id', None),
                  getattr(linked_user, 'owner_id', None)))

    # 字典规范化：全角空格与别名归一
    resp = client.post('/api/teachers/', headers=admin, json={
        'name': '规范化教师', 'department': '　计算机学院 ', 'title': '教授',
        'email': 'normalize@example.com',
    })
    check('新增教师时清洗全角空格', resp.status_code == 200
          and resp.get_json()['data']['department'] == '计算机学院',
          str(resp.get_json().get('data', {}).get('department')))

    resp = client.post('/api/teachers/', headers=admin, json={
        'name': '脏数据教师', 'department': '随便写的学院', 'title': '研究员'})
    check('新增教师接受新院系并自动登记字典', resp.status_code == 200, str(resp.get_json()))
    resp = client.get('/api/dicts/usage', headers=admin)
    usage = resp.get_json()['data']['department']
    check('字典用量接口标记未登记取值',
          any(item['name'] == '随便写的学院' for item in usage), str(usage[:3]))

    # -------------------------------------------------------------- 成果导入
    achievement_file = build_xlsx(
        ['所属人类型', '所属人姓名', '成果类型', '成果名称', '年份', '级别', '说明'],
        [
            ['教师', '张伟', '科研成果', '导入验证科研成果', 2025, '省部级', '导入用例'],
            ['学生', '2022002', '学科竞赛', '导入验证竞赛奖项', 2024, '国家级', '按学号匹配'],
            ['教师', '张伟', '奖学金', '不匹配类型示例', 2024, '校级', '应被跳过'],
            ['教师', '查无此人', '科研成果', '不存在人员示例', 2024, '校级', '应被跳过'],
            ['教师', '张伟', '科研成果', '导入验证科研成果', 2025, '省部级', '重复数据应被跳过'],
            ['学生', '陈静', '论文', '级别非法示例', 2024, '省部级', '应被跳过'],
        ],
    )
    resp = client.post('/api/import/achievements',
                       data={'file': (achievement_file, 'achievements.xlsx')},
                       content_type='multipart/form-data', headers=admin)
    result = resp.get_json().get('data') or {}
    check('成果导入成功 2 条并跳过 4 条',
          resp.status_code == 200 and result.get('created') == 2 and result.get('skipped') == 4,
          str(resp.get_json()))
    check('成果导入错误提示包含类型不匹配',
          any('不匹配' in item for item in (result.get('errors') or [])), str(result.get('errors')))
    check('成果导入自动跳过重复成果',
          any('已存在' in item for item in (result.get('errors') or [])), str(result.get('errors')))
    check('成果导入校验级别取值',
          any('级别' in item for item in (result.get('errors') or [])), str(result.get('errors')))

    resp = client.get('/api/achievements/?keyword=导入验证', headers=admin)
    items = resp.get_json()['data']['items']
    check('导入成果可在列表中检索', len(items) == 2, 'total=%s' % len(items))

    # ------------------------------------------------------------ 成果导出
    resp = client.get('/api/export/achievements', headers=admin)
    export_ok = resp.status_code == 200 and resp.mimetype.endswith('spreadsheetml.sheet')
    if export_ok:
        sheet = load_workbook(BytesIO(resp.data)).active
        export_ok = sheet.max_row >= 2 and sheet['A1'].value == '序号'
    check('成果导出 Excel', export_ok, str(resp.status_code))

    resp = client.get('/api/export/report', headers=admin)
    report_ok = resp.status_code == 200
    if report_ok:
        workbook = load_workbook(BytesIO(resp.data))
        report_ok = workbook.sheetnames == REPORT_SHEETS
        if report_ok:
            detail = workbook['成果明细']
            report_ok = detail['A1'].value == '序号' and detail.max_row >= 2
    check('统计报表导出 %d 个工作表' % len(REPORT_SHEETS), report_ok,
          str(resp.status_code))

    # 缺件清单
    resp = client.get('/api/export/missing-evidence', headers=admin)
    check('导出缺件清单', resp.status_code == 200
          and load_workbook(BytesIO(resp.data)).active['A1'].value == '序号',
          str(resp.status_code))

    # ------------------------------------------------- 成果 + 附件生命周期
    resp = client.post('/api/achievements/', headers=admin, json={
        'owner_type': 'teacher', 'owner_id': 1, 'category': '科研成果',
        'title': '附件校验成果', 'year': 2025, 'level': '校级', 'description': '附件用例',
    })
    check('新建成果（用于附件校验）', resp.status_code in (200, 201), str(resp.get_json()))
    achievement_id = resp.get_json()['data']['id']
    check('新建成果默认已通过（未开启审核开关）',
          resp.get_json()['data']['status'] == 'approved',
          str(resp.get_json()['data'].get('status')))

    # 非法级别被拒绝
    resp = client.post('/api/achievements/', headers=admin, json={
        'owner_type': 'teacher', 'owner_id': 1, 'category': '科研成果',
        'title': '非法级别', 'year': 99999, 'level': '随便写的级别',
    })
    check('非法年份与级别被拒绝', resp.status_code == 400, str(resp.get_json()))

    # 多附件上传
    resp = client.post('/api/achievements/%d/attachments' % achievement_id,
                       data={'category': '获奖证书',
                             'file': [(BytesIO(b'%PDF-1.4 verify'), 'verify.pdf'),
                                      (BytesIO(b'\x89PNG\r\n\x1a\nverify'), 'verify.png')]},
                       content_type='multipart/form-data', headers=admin)
    attachments = resp.get_json().get('data') or []
    check('多附件上传成功', resp.status_code == 200 and len(attachments) == 2
          and attachments[0]['category'] == '获奖证书', str(resp.get_json())[:200])
    attachment_id = attachments[0]['id'] if attachments else 0
    with app.app_context():
        rows = Attachment.query.filter_by(achievement_id=achievement_id).order_by(
            Attachment.id).all()
        stored_path = os.path.join(app.config['UPLOAD_FOLDER'],
                                   rows[0].stored_path if rows else '')

    resp = client.get('/api/achievements/%d/attachments/%d/download'
                      % (achievement_id, attachment_id), headers=admin)
    check('下载指定附件', resp.status_code == 200
          and resp.data.startswith(b'%PDF'), str(resp.status_code))
    resp.close()
    resp = client.get('/api/achievements/%d/attachments/%d/download?preview=1'
                      % (achievement_id, attachment_id), headers=admin)
    check('预览附件使用 inline',
          resp.status_code == 200
          and 'inline' in resp.headers.get('Content-Disposition', ''),
          resp.headers.get('Content-Disposition', ''))
    resp.close()

    resp = client.delete('/api/achievements/%d/attachments/%d'
                         % (achievement_id, attachment_id), headers=admin)
    check('删除单个附件', resp.status_code == 200 and len(resp.get_json()['data']) == 1,
          str(resp.get_json())[:200])
    check('删除单个附件同时清理文件', not os.path.exists(stored_path), stored_path)

    # 旧接口兼容（原前端与脚本仍在使用）
    resp = client.post('/api/achievements/%d/attachment' % achievement_id,
                       data={'file': (BytesIO(b'%PDF-1.4 verify'), 'verify.pdf')},
                       content_type='multipart/form-data', headers=admin)
    attachment = resp.get_json().get('data') or {}
    check('上传附件（旧接口）',
          resp.status_code == 200 and attachment.get('attachment_name') == 'verify.pdf',
          str(resp.get_json())[:200])
    legacy_path = os.path.join(app.config['UPLOAD_FOLDER'],
                               attachment.get('attachment_path') or '')

    resp = client.get('/api/achievements/%d/attachment' % achievement_id, headers=admin)
    check('下载附件（旧接口）', resp.status_code == 200
          and resp.data.startswith(b'%PDF'), str(resp.status_code))
    resp.close()
    resp = client.get('/api/achievements/%d/attachment?preview=1' % achievement_id, headers=admin)
    disposition = resp.headers.get('Content-Disposition', '')
    check('预览附件使用 inline（旧接口）',
          resp.status_code == 200 and 'inline' in disposition, disposition)
    resp.close()
    gc.collect()

    # 软删除 → 回收站 → 恢复 → 彻底删除
    resp = client.delete('/api/achievements/%d' % achievement_id, headers=admin)
    check('删除成果进入回收站', resp.status_code == 200
          and resp.get_json()['data']['is_deleted'] is True, str(resp.get_json()))
    with app.app_context():
        remained = Achievement.query.filter_by(title='附件校验成果').count()
        soft = Achievement.query.filter_by(title='附件校验成果').first()
        check('软删除保留数据行（可恢复）',
              remained == 1 and soft is not None and soft.is_deleted is True,
              'remained=%s' % remained)
    check('软删除保留支撑材料文件（可恢复）', os.path.exists(legacy_path), legacy_path)
    resp = client.get('/api/achievements/?keyword=附件校验成果', headers=admin)
    check('回收站中的成果不出现在列表', resp.get_json()['data']['total'] == 0,
          str(resp.get_json()['data']['total']))
    resp = client.get('/api/achievements/trash?keyword=附件校验成果', headers=admin)
    check('回收站可查询到已删除成果', resp.get_json()['data']['total'] == 1,
          str(resp.get_json()['data']['total']))

    resp = client.post('/api/achievements/%d/restore' % achievement_id, headers=admin)
    check('从回收站恢复成果', resp.status_code == 200, str(resp.get_json()))
    resp = client.get('/api/achievements/?keyword=附件校验成果', headers=admin)
    check('恢复后重新出现在列表', resp.get_json()['data']['total'] == 1,
          str(resp.get_json()['data']['total']))

    resp = client.delete('/api/achievements/%d?hard=1' % achievement_id, headers=admin)
    check('彻底删除成果', resp.status_code == 200, str(resp.get_json()))
    with app.app_context():
        remained = Achievement.query.filter_by(title='附件校验成果').count()
        attachment_rows = Attachment.query.join(
            Achievement, Achievement.id == Attachment.achievement_id,
            isouter=True).filter(Achievement.id.is_(None)).count()
    check('彻底删除后数据库无残留', remained == 0, 'remained=%s' % remained)
    check('彻底删除清理附件文件',
          not os.path.exists(legacy_path) and not os.path.exists(stored_path), legacy_path)
    check('删除成果不留下孤儿附件记录', attachment_rows == 0, 'orphans=%s' % attachment_rows)

    # ------------------------------------------------------------------ 审核流
    resp = login(client, 'student1', '123456')
    check('学生登录', resp.status_code == 200)
    student = auth_header(resp)

    resp = client.post('/api/achievements/', headers=student, json={
        'category': '学科竞赛', 'title': '审核流测试成果', 'year': 2025, 'level': '校级',
        'extra': {'award_rank': '一等奖', 'contest_name': '审核流测试竞赛'},
    })
    check('学生录入本人成果', resp.status_code in (200, 201), str(resp.get_json())[:200])
    review_id = resp.get_json()['data']['id']
    check('类别专有字段被保存',
          resp.get_json()['data']['extra'].get('award_rank') == '一等奖',
          str(resp.get_json()['data'].get('extra')))

    resp = client.put('/api/achievements/%d' % review_id, headers=student,
                      json={'level': '国家级', 'extra': {'award_rank': '特等奖'}})
    check('学生可修改本人成果', resp.status_code == 200, str(resp.get_json())[:200])

    resp = client.put('/api/achievements/%d' % review_id, headers=student,
                      json={'status': 'approved'})
    check('学生不能自行把成果置为已通过', resp.status_code == 403, str(resp.status_code))

    resp = client.put('/api/achievements/%d' % review_id, headers=student,
                      json={'status': 'draft'})
    check('学生可将成果存为草稿', resp.status_code == 200, str(resp.get_json())[:200])
    resp = client.post('/api/achievements/%d/submit' % review_id, headers=student)
    check('提交审核后状态为待审核',
          resp.status_code == 200 and resp.get_json()['data']['status'] == 'pending',
          str(resp.get_json())[:200])

    resp = client.post('/api/achievements/%d/review' % review_id, headers=student,
                       json={'action': 'approve'})
    check('学生不能审核成果', resp.status_code == 403, str(resp.status_code))

    resp = client.post('/api/achievements/%d/review' % review_id, headers=admin,
                       json={'action': 'reject'})
    check('驳回时必须填写审核意见', resp.status_code == 400, str(resp.get_json()))

    resp = login(client, 'reviewer', '123456')
    check('审核员登录', resp.status_code == 200)
    reviewer = auth_header(resp)

    resp = client.post('/api/achievements/%d/review' % review_id, headers=reviewer,
                       json={'action': 'approve', 'comment': '材料齐全'})
    check('审核员通过成果',
          resp.status_code == 200 and resp.get_json()['data']['status'] == 'approved',
          str(resp.get_json())[:200])
    check('审核意见被记录',
          resp.get_json()['data'].get('review_comment') == '材料齐全',
          str(resp.get_json()['data'].get('review_comment')))

    resp = client.post('/api/achievements/', headers=reviewer, json={
        'owner_type': 'student', 'owner_id': 1, 'category': '学科竞赛', 'title': '审核员录数据'})
    check('审核员不能录入成果', resp.status_code == 403, str(resp.status_code))

    resp = client.get('/api/users', headers=reviewer)
    check('审核员不能管理账号', resp.status_code == 403, str(resp.status_code))

    # -------------------------------------------------------------- 批量操作
    resp = client.post('/api/achievements/batch', headers=admin,
                       json={'ids': [review_id], 'action': 'add_indicators',
                             'indicator_ids': [1, 2]})
    check('批量关联认证指标点', resp.status_code == 200
          and resp.get_json()['data']['affected'] == 1, str(resp.get_json()))
    resp = client.get('/api/achievements/%d' % review_id, headers=admin)
    check('指标点关联可读回',
          len(resp.get_json()['data']['indicators']) == 2,
          str(resp.get_json()['data'].get('indicators')))

    resp = client.post('/api/achievements/batch', headers=admin,
                       json={'ids': [review_id], 'action': 'set_level', 'level': '省部级'})
    check('批量修改级别', resp.status_code == 200
          and resp.get_json()['data']['affected'] == 1, str(resp.get_json()))
    resp = client.post('/api/achievements/batch', headers=admin,
                       json={'ids': [review_id], 'action': 'set_level', 'level': '不存在的级别'})
    check('批量修改级别时过滤非法取值',
          resp.status_code == 200 and resp.get_json()['data']['affected'] == 0,
          str(resp.get_json()))

    resp = client.post('/api/achievements/batch', headers=admin,
                       json={'ids': [review_id], 'action': 'set_status', 'status': 'pending'})
    check('批量改变审核状态', resp.status_code == 200, str(resp.get_json()))
    resp = client.post('/api/achievements/batch', headers=student,
                       json={'ids': [review_id], 'action': 'set_status', 'status': 'approved'})
    check('普通用户不能批量通过审核', resp.status_code == 403, str(resp.status_code))

    resp = client.post('/api/achievements/batch', headers=admin,
                       json={'ids': [review_id], 'action': 'delete'})
    check('批量移入回收站', resp.status_code == 200, str(resp.get_json()))
    resp = client.post('/api/achievements/batch', headers=admin,
                       json={'ids': [review_id], 'action': 'purge'})
    check('批量彻底删除', resp.status_code == 200, str(resp.get_json()))

    # ------------------------------------------------------ 佐证材料包导出
    resp = client.get('/api/export/package', headers=admin)
    package_ok = resp.status_code == 200 and resp.data[:2] == b'PK'
    if package_ok:
        with zipfile.ZipFile(BytesIO(resp.data)) as archive:
            names = archive.namelist()
            package_ok = '材料清单.xlsx' in names and any(
                name.startswith('计算机学院/') for name in names)
    check('导出佐证材料包（含分类目录与清单）', package_ok, str(resp.status_code))

    # ---------------------------------------------------------- 系统与运维
    resp = client.get('/api/system/info', headers=admin)
    info = resp.get_json()['data']
    check('系统信息接口', resp.status_code == 200 and 'migration_report' in info,
          str(resp.status_code))
    check('报告已登记的附件文件', info.get('upload_files', 0) >= 1, str(info.get('upload_files')))

    resp = client.post('/api/system/backup', headers=admin)
    backup = resp.get_json().get('data') or {}
    check('生成数据备份', resp.status_code == 200
          and os.path.exists(os.path.join(app.config['BACKUP_FOLDER'], backup.get('name', ''))),
          str(resp.get_json()))
    resp = client.get('/api/system/backups', headers=admin)
    check('查询备份列表', resp.status_code == 200
          and len(resp.get_json()['data']['items']) == 1, str(resp.get_json())[:200])

    resp = client.post('/api/system/cleanup-orphans', headers=admin)
    check('清理孤儿附件', resp.status_code == 200, str(resp.get_json()))

    with app.app_context():
        from migrate import run_migrations
        before = (User.query.count(), Teacher.query.count(), Achievement.query.count())
        report = run_migrations(app)
        after = (User.query.count(), Teacher.query.count(), Achievement.query.count())
    check('迁移脚本可重复执行且不丢数据',
          before == after and report == [], 'before=%s after=%s report=%s'
          % (before, after, report))

    # ------------------------------------------------------------ 权限隔离
    resp = login(client, 'teacher1', '123456')
    check('教师登录', resp.status_code == 200)
    teacher = auth_header(resp)

    resp = client.post('/api/import/teachers',
                       data={'file': (build_xlsx(['姓名'], [['越权导入']]), 'x.xlsx')},
                       content_type='multipart/form-data', headers=teacher)
    check('教师不能导入教师数据', resp.status_code == 403, str(resp.status_code))

    resp = client.get('/api/export/report', headers=teacher)
    check('教师不能导出统计报表', resp.status_code == 403, str(resp.status_code))

    resp = client.get('/api/users', headers=teacher)
    check('教师不能访问账号管理', resp.status_code == 403, str(resp.status_code))

    resp = client.get('/api/logs/', headers=teacher)
    check('教师不能查看操作日志', resp.status_code == 403, str(resp.status_code))

    resp = client.get('/api/export/achievements', headers=teacher)
    export_ok = resp.status_code == 200
    if export_ok:
        export_ok = load_workbook(BytesIO(resp.data)).active.max_row - 1 == 4
    check('教师导出仅含本人成果（3 条种子 + 1 条导入）', export_ok, str(resp.status_code))

    resp = client.get('/api/stats/overview', headers=teacher)
    counts = resp.get_json()['data']['counts']
    check('教师统计仅本人数据', resp.status_code == 200 and counts['achievements'] == 4, str(counts))

    resp = client.get('/api/achievements/?page=1&page_size=100', headers=teacher)
    total = resp.get_json()['data']['total']
    check('教师成果列表仅本人数据', total == 4, 'total=%s' % total)

    resp = client.get('/api/achievements/?keyword=导入验证科研成果', headers=teacher)
    check('教师可检索本人导入成果', resp.get_json()['data']['total'] == 1)

    resp = client.get('/api/teachers/', headers=teacher)
    check('教师不能查看教师名册', resp.status_code == 403, str(resp.status_code))

    resp = client.get('/api/students/', headers=teacher)
    check('教师不能查看学生名册', resp.status_code == 403, str(resp.status_code))

    # 教师不能修改他人的成果（跨人越权）
    with app.app_context():
        other = Achievement.query.filter(Achievement.owner_type == 'student',
                                         Achievement.is_deleted.is_(False)).first()
        other_id = other.id if other else 0
    resp = client.put('/api/achievements/%d' % other_id, headers=teacher, json={'title': '越权改'})
    check('教师不能修改他人成果', resp.status_code == 403, str(resp.status_code))

    resp = client.get('/api/achievements/%d' % other_id, headers=teacher)
    check('教师不能查看他人成果详情', resp.status_code == 403, str(resp.status_code))

    # ------------------------------------------------------------ 账号管理
    resp = client.get('/api/users', headers=admin)
    users = resp.get_json()['data']
    check('管理员可访问账号管理', resp.status_code == 200 and users['total'] >= 6,
          'total=%s' % users.get('total'))

    resp = client.get('/api/users?keyword=import_t1', headers=admin)
    imported_user = resp.get_json()['data']['items'][0]
    check('账号列表显示关联人员', bool(imported_user.get('owner_name')),
          str(imported_user))

    # 令牌失效：改密后旧令牌不可用
    resp = client.post('/api/auth/change-password', headers=imported_teacher_token,
                       json={'old_password': 'abc123', 'new_password': 'abc1234'})
    check('修改密码返回新令牌', resp.status_code == 200, str(resp.get_json())[:200])
    resp = client.get('/api/auth/me', headers=imported_teacher_token)
    check('改密后旧令牌立即失效', resp.status_code == 401, str(resp.status_code))
    resp = login(client, 'import_t1', 'abc1234')
    check('新密码可登录', resp.status_code == 200, str(resp.get_data(as_text=True))[:120])
    login_data = resp.get_json()['data']
    new_token = auth_header(resp)
    resp = client.get('/api/auth/me', headers=new_token)
    check('新令牌可用', resp.status_code == 200, str(resp.status_code))
    resp = client.post('/api/auth/refresh', headers={
        'Authorization': 'Bearer %s' % login_data['refresh_token']})
    check('刷新令牌接口可用', resp.status_code == 200, str(resp.get_json())[:200])

    # 禁用账号后无法登录且旧令牌失效
    resp = client.put('/api/users/%d/status' % imported_user['id'], headers=admin,
                      json={'is_active': False})
    check('禁用账号', resp.status_code == 200, str(resp.get_json()))
    resp = login(client, 'import_t1', 'abc1234')
    check('禁用账号无法登录', resp.status_code == 403, str(resp.status_code))
    resp = client.get('/api/auth/me', headers=new_token)
    check('禁用账号的旧令牌失效', resp.status_code == 401, str(resp.status_code))

    # 不能删除/禁用自己，也不能删除最后一个管理员
    resp = client.put('/api/users/%d/status' % 1, headers=admin, json={'is_active': False})
    check('管理员不能禁用自己', resp.status_code == 400, str(resp.status_code))
    resp = client.put('/api/users/%d' % 1, headers=admin, json={'role': 'teacher',
                                                                'owner_id': 1})
    check('不能把当前账号改为非管理员', resp.status_code == 400, str(resp.get_json()))

    # ------------------------------------------------------------ 登录节流
    for _ in range(5):
        client.post('/api/auth/login', json={'username': 'nosuchuser', 'password': 'wrong'})
    resp = client.post('/api/auth/login', json={'username': 'nosuchuser', 'password': 'wrong'})
    check('连续失败登录触发节流 429', resp.status_code == 429, str(resp.status_code))

    # ---------------------------------------------------------------- 性能
    with app.app_context():
        engine = db.engine
        list_statements = count_sql(engine, lambda: client.get(
            '/api/achievements/?page=1&page_size=100', headers=admin))
        stats_statements = count_sql(engine, lambda: client.get(
            '/api/stats/overview', headers=admin))
    check('成果列表 SQL 次数与数据量无关（<= 15）', len(list_statements) <= 15,
          'statements=%d' % len(list_statements))
    check('统计概览 SQL 次数与数据量无关（<= 20）', len(stats_statements) <= 20,
          'statements=%d' % len(stats_statements))

    # ------------------------------------------------------------ 匿名访问
    resp = client.get('/api/achievements/')
    check('匿名访问成果列表返回 401', resp.status_code == 401, str(resp.status_code))
    resp = client.get('/api/system/info')
    check('匿名访问系统信息返回 401', resp.status_code == 401, str(resp.status_code))
    resp = client.get('/api/health')
    check('健康检查可匿名访问', resp.status_code == 200, str(resp.status_code))

    print('')
    if FAILURES:
        print('VERIFY_FAILED %d 项未通过' % len(FAILURES))
        for item in FAILURES:
            print(' -', item)
        return 1
    print('VERIFY_FLOWS_DONE 全部校验通过')
    return 0


if __name__ == '__main__':
    sys.exit(main())