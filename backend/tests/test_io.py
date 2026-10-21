"""导入导出测试：模板、批量导入语义、统计报表、缺件清单与佐证材料包。"""
import zipfile
from io import BytesIO

from openpyxl import load_workbook

from conftest import build_xlsx, data_of, upload

REPORT_SHEETS = [
    '概览', '成果明细', '成果类型分布', '年度成果趋势', '成果级别分布', '院系成果分布',
    '师生汇总', '缺件清单', '指标点覆盖', '指导教师成果',
]


def import_file(client, url, headers, headers_row, rows, filename='data.xlsx', extra=None):
    payload = {'file': (build_xlsx(headers_row, rows), filename)}
    if extra:
        payload.update(extra)
    return client.post(url, headers=headers, data=payload,
                       content_type='multipart/form-data')


def test_download_all_templates(client, admin_headers):
    for kind in ('teachers', 'students', 'achievements'):
        response = client.get(f'/api/import/templates/{kind}', headers=admin_headers)
        assert response.status_code == 200, kind
        assert response.mimetype.endswith('spreadsheetml.sheet')
        sheet = load_workbook(BytesIO(response.data)).active
        assert sheet.max_column >= 4, kind

    categories = data_of(client.get('/api/export/attachment-categories', headers=admin_headers))
    assert isinstance(categories, list) and categories, '应返回支撑材料分类清单'


def test_template_download_requires_login(client):
    assert client.get('/api/import/templates/teachers').status_code == 401


def test_teacher_import_creates_account_and_skips_duplicates(client, admin_headers):
    response = import_file(
        client, '/api/import/teachers', admin_headers,
        ['姓名', '所属院系', '职称', '邮箱', '登录名', '初始密码'],
        [
            ['导入教师甲', '信息工程学院', '副教授', 'imp1@example.com', 'imp_t1', 'abc123'],
            ['', '信息工程学院', '讲师', 'imp2@example.com', 'imp_t2', 'abc123'],
            ['导入教师乙', '信息工程学院', '讲师', 'imp3@example.com', 'admin', 'abc123'],
        ])
    result = data_of(response)
    assert result['created'] == 1
    assert result['skipped'] == 2
    assert len(result['errors']) == 2

    # 导入的账号可以直接登录
    login = client.post('/api/auth/login', json={'username': 'imp_t1', 'password': 'abc123'})
    assert login.status_code == 200

    # 字典归一：全角空格与首尾空格会被清洗
    created = data_of(client.post('/api/teachers', headers=admin_headers, json={
        'name': '规范化教师', 'department': '　计算机学院 ', 'title': '教授',
    }))
    assert created['department'] == '计算机学院'

    # 未登记的取值会被标记出来，便于统一口径
    data_of(client.post('/api/teachers', headers=admin_headers, json={
        'name': '脏数据教师', 'department': '随便写的学院', 'title': '研究员',
    }))
    usage = data_of(client.get('/api/dicts/usage', headers=admin_headers))['department']
    row = next(item for item in usage if item['name'] == '随便写的学院')
    assert row['registered'] is True, '通过接口录入的院系会自动登记进字典'
    assert row['count'] >= 1

    # 绕过接口直接写入的脏数据必须被标记为「未登记」
    from extensions import db
    from models import Teacher

    with client.application.app_context():
        db.session.add(Teacher(name='手工脏数据', department='野鸡学院', title='讲师'))
        db.session.commit()
    usage = data_of(client.get('/api/dicts/usage', headers=admin_headers))['department']
    dirty = next(item for item in usage if item['name'] == '野鸡学院')
    assert dirty['registered'] is False


def test_student_import_with_advisor(client, admin_headers):
    response = import_file(
        client, '/api/import/students', admin_headers,
        ['学号', '姓名', '年级', '专业', '班级', '指导教师', '登录名', '初始密码'],
        [
            ['IMP2025001', '导入学生甲', '2025级', '软件工程', '软工2501', '张伟', 'imp_s1', 'abc123'],
            ['IMP2025001', '重复学号', '2025级', '软件工程', '软工2501', '', '', ''],
        ])
    result = data_of(response)
    assert result['created'] == 1
    assert result['skipped'] == 1

    listed = data_of(client.get('/api/students?keyword=IMP2025001', headers=admin_headers))
    student = listed['items'][0]
    assert student['name'] == '导入学生甲'
    assert student['advisor_names'] == '张伟'
    assert student['username'] == 'imp_s1'


def test_achievement_import_semantics(client, admin_headers):
    response = import_file(
        client, '/api/import/achievements', admin_headers,
        ['所属人类型', '所属人姓名', '成果类型', '成果名称', '年份', '级别', '说明'],
        [
            ['教师', '张伟', '科研成果', '导入验证科研成果', 2025, '省部级', '正常导入'],
            ['学生', '2022002', '学科竞赛', '导入验证竞赛奖项', 2024, '国家级', '按学号匹配'],
            ['教师', '张伟', '奖学金', '类型不匹配示例', 2024, '校级', '应跳过'],
            ['教师', '查无此人', '科研成果', '人员不存在示例', 2024, '校级', '应跳过'],
            ['教师', '张伟', '科研成果', '导入验证科研成果', 2025, '省部级', '重复应跳过'],
            ['学生', '陈静', '论文', '级别非法示例', 2024, '省部级', '应跳过'],
        ])
    result = data_of(response)
    assert result['created'] == 2, result
    assert result['skipped'] == 4, result
    joined = ' '.join(result['errors'])
    assert '不匹配' in joined
    assert '已存在' in joined
    assert '级别' in joined

    listed = data_of(client.get('/api/achievements?keyword=导入验证&page=1&page_size=50',
                                headers=admin_headers))
    assert listed['total'] == 2

    # 再次导入同一文件，skip_duplicates 默认开启，全部跳过
    response = import_file(
        client, '/api/import/achievements', admin_headers,
        ['所属人类型', '所属人姓名', '成果类型', '成果名称', '年份', '级别', '说明'],
        [['教师', '张伟', '科研成果', '导入验证科研成果', 2025, '省部级', '重复']])
    assert data_of(response)['created'] == 0


def test_import_requires_admin(client, teacher_headers, reviewer_headers):
    response = import_file(client, '/api/import/teachers', teacher_headers,
                           ['姓名'], [['越权导入']])
    assert response.status_code == 403
    response = import_file(client, '/api/import/teachers', reviewer_headers,
                           ['姓名'], [['审核员导入']])
    assert response.status_code == 403


def test_import_rejects_bad_file(client, admin_headers):
    response = client.post('/api/import/teachers',
                           headers=admin_headers,
                           data={'file': (BytesIO(b'not an excel'), 'bad.xlsx')},
                           content_type='multipart/form-data')
    assert response.status_code == 400


def test_export_achievements_and_missing_evidence(client, admin_headers):
    response = client.get('/api/export/achievements', headers=admin_headers)
    assert response.status_code == 200
    sheet = load_workbook(BytesIO(response.data)).active
    assert sheet['A1'].value == '序号'
    assert sheet.max_row >= 2

    response = client.get('/api/export/missing-evidence', headers=admin_headers)
    assert response.status_code == 200
    assert load_workbook(BytesIO(response.data)).active['A1'].value == '序号'


def test_export_report_has_expected_sheets(client, admin_headers):
    response = client.get('/api/export/report', headers=admin_headers)
    assert response.status_code == 200
    workbook = load_workbook(BytesIO(response.data))
    assert workbook.sheetnames == REPORT_SHEETS
    detail = workbook['成果明细']
    assert detail['A1'].value == '序号' and detail.max_row >= 2
    overview = workbook['概览']
    assert overview.max_row >= 2


def test_export_report_requires_elevated(client, teacher_headers):
    assert client.get('/api/export/report', headers=teacher_headers).status_code == 403
    assert client.get('/api/export/package', headers=teacher_headers).status_code == 200


def test_export_package_structure(client, admin_headers):
    created = data_of(client.post('/api/achievements', headers=admin_headers, json={
        'title': '材料包验证成果', 'category': '科研成果', 'level': '省部级',
        'owner_type': 'teacher', 'owner_id': 1, 'year': 2025,
    }))
    upload(client, f"/api/achievements/{created['id']}/attachments", admin_headers,
           '材料包证据.pdf', data={'category': '获奖证书'})

    response = client.get('/api/export/package', headers=admin_headers)
    assert response.status_code == 200
    assert response.mimetype == 'application/zip'
    archive = zipfile.ZipFile(BytesIO(response.data))
    names = archive.namelist()
    assert '材料清单.xlsx' in names
    assert 'README.txt' in names
    payload = [name for name in names if name.endswith('材料包证据.pdf')]
    assert payload, names
    # 目录结构：<院系>/<所属人>/<成果>/<材料分类>/<文件名>
    parts = payload[0].split('/')
    assert len(parts) == 5, parts
    assert parts[-2] == '获奖证书'
    manifest = load_workbook(BytesIO(archive.read('材料清单.xlsx'))).active
    assert manifest['A1'].value == '序号'
    assert manifest.max_row >= 2


def test_teacher_export_only_contains_own_achievements(client, teacher_headers):
    response = client.get('/api/export/achievements', headers=teacher_headers)
    assert response.status_code == 200
    sheet = load_workbook(BytesIO(response.data)).active
    # 演示数据中张伟名下有 3 条成果
    assert sheet.max_row - 1 == 3, sheet.max_row