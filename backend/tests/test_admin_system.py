"""账号权限、字典、指标点、指导关系、操作日志与系统维护测试。"""
from conftest import data_of, headers_for, login, upload


def create_user(client, admin_headers, **overrides):
    payload = {'username': 'newuser', 'password': 'abc123', 'role': 'reviewer'}
    payload.update(overrides)
    return client.post('/api/users', headers=admin_headers, json=payload)


def test_user_list_and_filters(client, admin_headers):
    payload = data_of(client.get('/api/users?page=1&page_size=50', headers=admin_headers))
    assert payload['total'] >= 7
    roles = data_of(client.get('/api/users?role=reviewer', headers=admin_headers))['items']
    assert roles and all(row['role'] == 'reviewer' for row in roles)
    linked = data_of(client.get('/api/users?linked=1', headers=admin_headers))['items']
    assert linked and all(row['owner_type'] for row in linked)
    unlinked = data_of(client.get('/api/users?linked=0', headers=admin_headers))['items']
    assert unlinked and all(not row['owner_type'] for row in unlinked)
    assert data_of(client.get('/api/users?keyword=张伟', headers=admin_headers))['total'] >= 1


def test_user_management_requires_admin(client, teacher_headers, reviewer_headers):
    for headers in (teacher_headers, reviewer_headers):
        assert client.get('/api/users', headers=headers).status_code == 403
        assert create_user(client, headers, username='x').status_code == 403


def test_create_user_role_rules_and_candidates(client, admin_headers):
    # 审核员不绑定人员档案
    reviewer = data_of(create_user(client, admin_headers, username='rev_new', role='reviewer'))
    assert reviewer['owner_type'] is None

    # 教师/学生必须绑定未占用的档案
    candidates = data_of(client.get('/api/users/candidates?role=teacher', headers=admin_headers))
    assert all(item['id'] for item in candidates)
    taken = {row['owner_id'] for row in
             data_of(client.get('/api/users?linked=1&page_size=50', headers=admin_headers))['items']
             if row['owner_type'] == 'teacher'}
    assert all(item['id'] not in taken for item in candidates)

    assert create_user(client, admin_headers, username='t_new', role='teacher',
                       owner_id=1).status_code == 400  # 张伟已有关联账号
    assert create_user(client, admin_headers, username='t_new', role='teacher',
                       owner_id=9999).status_code == 400

    # 重复登录名
    assert create_user(client, admin_headers, username='admin').status_code == 400


def test_self_role_change_and_last_admin_protection(client, admin_headers):
    me = data_of(client.get('/api/auth/me', headers=admin_headers))
    # 不能修改自己的管理员角色
    assert client.put(f"/api/users/{me['id']}", headers=admin_headers,
                      json={'role': 'reviewer'}).status_code == 400
    # 不能删除自己
    assert client.delete(f"/api/users/{me['id']}", headers=admin_headers).status_code == 400
    # 不能禁用自己
    assert client.put(f"/api/users/{me['id']}/status", headers=admin_headers,
                      json={'is_active': False}).status_code == 400


def test_reset_password_and_unbind_and_delete(client, admin_headers):
    teacher_user = next(row for row in
                        data_of(client.get('/api/users?role=teacher&page_size=50',
                                           headers=admin_headers))['items']
                        if row['owner_type'] == 'teacher')
    data_of(client.post(f"/api/users/{teacher_user['id']}/reset-password", headers=admin_headers,
                        json={'new_password': 'reset1234', 'must_change_password': True}))
    assert login(client, teacher_user['username'], '123456').status_code == 401
    assert login(client, teacher_user['username'], 'reset1234').status_code == 200

    # 解绑后档案保留，账号不再关联人员
    data_of(client.post(f"/api/users/{teacher_user['id']}/unbind", headers=admin_headers))
    after = data_of(client.get(f"/api/users?keyword={teacher_user['username']}",
                               headers=admin_headers))['items'][0]
    assert after['owner_type'] is None
    teacher = data_of(client.get('/api/teachers?page_size=50', headers=admin_headers))
    assert any(row['id'] == teacher_user['owner_id'] for row in teacher['items'])

    # 删除账号不会删除人员档案
    data_of(client.delete(f"/api/users/{teacher_user['id']}", headers=admin_headers))
    assert login(client, teacher_user['username'], 'reset1234').status_code == 401


def test_dict_crud_and_merge(client, admin_headers):
    created = data_of(client.post('/api/dicts', headers=admin_headers, json={
        'kind': 'department', 'name': '测试学院', 'aliases': '测试学院别名,测试院',
    }))
    assert created['name'] == '测试学院'
    assert created['aliases'] == ['测试学院别名', '测试院']

    # 别名归一：录入时用别名会被转换成规范名称
    teacher = data_of(client.post('/api/teachers', headers=admin_headers, json={
        'name': '别名学院教师', 'department': '测试学院别名',
    }))
    assert teacher['department'] == '测试学院'

    grouped = data_of(client.get('/api/dicts/grouped', headers=admin_headers))
    assert any(item['name'] == '测试学院' for item in grouped['department'])

    # 合并：把新增字典项并入已有项
    target = next(item for item in grouped['department'] if item['name'] == '计算机学院')
    result = data_of(client.post('/api/dicts/merge', headers=admin_headers,
                                 json={'source_id': created['id'], 'target_id': target['id']}))
    assert result['affected'] >= 1, '别名录入的教师应被改写为规范学院'
    grouped = data_of(client.get('/api/dicts/grouped', headers=admin_headers))
    assert all(item['name'] != '测试学院' for item in grouped['department'])
    teacher = data_of(client.get('/api/teachers?keyword=别名学院教师', headers=admin_headers))
    assert teacher['items'][0]['department'] == '计算机学院'


def test_dict_requires_login_and_admin(client, teacher_headers):
    assert client.get('/api/dicts').status_code == 401
    assert client.post('/api/dicts', headers=teacher_headers,
                       json={'kind': 'department', 'name': 'X'}).status_code == 403


def test_indicator_crud_and_delete_unlinks(client, admin_headers, teacher_headers):
    assert client.post('/api/indicators', headers=teacher_headers,
                       json={'code': 'X', 'name': 'Y'}).status_code == 403

    created = data_of(client.post('/api/indicators', headers=admin_headers, json={
        'code': '13', 'name': '测试指标点', 'description': 'pytest',
    }))
    assert created['code'] == '13'
    assert client.post('/api/indicators', headers=admin_headers,
                       json={'code': '13', 'name': '重复编号'}).status_code == 400

    updated = data_of(client.put(f"/api/indicators/{created['id']}", headers=admin_headers,
                                 json={'name': '改名指标点', 'is_active': False}))
    assert updated['name'] == '改名指标点'

    achievement = data_of(client.post('/api/achievements', headers=admin_headers, json={
        'title': '指标点关联成果', 'category': '科研成果', 'level': '省部级',
        'owner_type': 'teacher', 'owner_id': 1, 'year': 2025,
        'indicator_ids': [created['id']],
    }))
    assert [row['id'] for row in achievement['indicators']] == [created['id']]

    result = data_of(client.delete(f"/api/indicators/{created['id']}", headers=admin_headers))
    assert result['unlinked'] == 1
    detail = data_of(client.get(f"/api/achievements/{achievement['id']}", headers=admin_headers))
    assert detail['indicators'] == []


def test_advisor_relation_crud_and_uniqueness(client, admin_headers):
    student = data_of(client.post('/api/students', headers=admin_headers, json={
        'student_no': 'ADV-0001', 'name': '指导关系学生', 'grade': '2024级',
        'major': '软件工程', 'department': '计算机学院', 'advisor_ids': [1, 2],
    }))
    assert len(student['advisors']) == 2
    assert student['advisors'][0]['is_primary'] is True

    # 重复建立同一对关系会被拒绝
    assert client.post('/api/advisors', headers=admin_headers,
                       json={'teacher_id': 1, 'student_id': student['id']}).status_code == 400

    relations = data_of(client.get(f"/api/advisors?student_id={student['id']}",
                                   headers=admin_headers))['items']
    assert len(relations) == 2
    data_of(client.delete(f"/api/advisors/{relations[0]['id']}", headers=admin_headers))
    remaining = data_of(client.get(f"/api/advisors?student_id={student['id']}",
                                   headers=admin_headers))['items']
    assert len(remaining) == 1


def test_teacher_sees_only_own_advisor_relations(client, admin_headers, teacher_headers):
    relations = data_of(client.get('/api/advisors?page_size=50', headers=teacher_headers))['items']
    assert relations
    assert all(row['teacher_name'] == '张伟' for row in relations)


def test_operation_logs_recorded_and_scoped(client, admin_headers, teacher_headers):
    data_of(client.post('/api/achievements', headers=admin_headers, json={
        'title': '日志验证成果', 'category': '科研成果', 'level': '省部级',
        'owner_type': 'teacher', 'owner_id': 1, 'year': 2025,
    }))
    logs = data_of(client.get('/api/logs?page=1&page_size=50', headers=admin_headers))
    assert logs['total'] >= 1
    assert any('日志验证成果' in row['summary'] for row in logs['items'])

    options = data_of(client.get('/api/logs/options', headers=admin_headers))
    assert options['actions'] and options['targets']

    summary = data_of(client.get('/api/logs/summary', headers=admin_headers))
    assert 'daily' in summary and 'by_action' in summary and summary['total'] >= 1

    # 教师无权查看操作日志
    assert client.get('/api/logs', headers=teacher_headers).status_code == 403


def test_system_info_backup_and_orphans(client, admin_headers, app):
    info = data_of(client.get('/api/system/info', headers=admin_headers))
    assert info['app_env'] in ('development', 'testing', 'production')
    assert info['coverage']['achievements'] >= 14
    assert 'login_throttle' in info

    created = data_of(client.post('/api/system/backup', headers=admin_headers))
    assert created['name'].endswith('.zip')
    backups = data_of(client.get('/api/system/backups', headers=admin_headers))
    assert backups['items'] and backups['keep'] >= 1
    download = client.get(f"/api/system/backup/download?name={created['name']}",
                          headers=admin_headers)
    assert download.status_code == 200
    assert download.data[:2] == b'PK'

    # 孤儿文件：磁盘上存在但没有任何成果引用
    import os
    orphan_path = os.path.join(app.config['UPLOAD_FOLDER'], 'orphan_demo.pdf')
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    with open(orphan_path, 'wb') as handle:
        handle.write(b'%PDF-1.4 orphan')
    listed = data_of(client.get('/api/system/orphans', headers=admin_headers))
    assert any('orphan_demo.pdf' in row['path'] for row in listed['items'])
    cleaned = data_of(client.post('/api/system/cleanup-orphans', headers=admin_headers))
    assert cleaned['removed'] >= 1
    assert not os.path.exists(orphan_path)


def test_system_endpoints_require_admin(client, teacher_headers, reviewer_headers):
    for headers in (teacher_headers, reviewer_headers):
        assert client.get('/api/system/info', headers=headers).status_code == 403
        assert client.get('/api/system/backups', headers=headers).status_code == 403


def test_migration_is_idempotent(client, admin_headers, app):
    with app.app_context():
        from migrate import run_migrations
        from models import Achievement, Teacher, User
        before = (User.query.count(), Teacher.query.count(), Achievement.query.count())
        report = run_migrations(app)
        after = (User.query.count(), Teacher.query.count(), Achievement.query.count())
    assert before == after
    assert report == [], report


def test_cleanup_orphans_keeps_referenced_files(client, admin_headers, app):
    """清理孤儿文件不能误删仍然被引用的支撑材料。"""
    import os

    from extensions import db
    from models import Attachment

    created = data_of(client.post('/api/achievements', headers=admin_headers, json={
        'title': '引用文件保护验证', 'category': '科研成果', 'level': '省部级',
        'owner_type': 'teacher', 'owner_id': 1, 'year': 2025,
    }))
    upload(client, f"/api/achievements/{created['id']}/attachments", admin_headers,
           '受保护材料.pdf', data={'category': '成果正文'})
    with app.app_context():
        row = Attachment.query.filter_by(achievement_id=created['id']).one()
        stored = row.stored_path
        attachment_id = row.id
    assert os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], stored))

    data_of(client.post('/api/system/cleanup-orphans', headers=admin_headers))
    assert os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], stored))

    # 删除附件后文件应被回收
    data_of(client.delete(f"/api/achievements/{created['id']}/attachments/{attachment_id}",
                          headers=admin_headers))
    assert not os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], stored))


def test_password_reset_by_admin_then_login(client, admin_headers):
    data_of(create_user(client, admin_headers, username='pwd_user', role='reviewer'))
    user = data_of(client.get('/api/users?keyword=pwd_user', headers=admin_headers))['items'][0]

    # 弱口令被拒绝（长度不足）
    assert client.post(f"/api/users/{user['id']}/reset-password", headers=admin_headers,
                       json={'new_password': '123'}).status_code == 400
    data_of(client.post(f"/api/users/{user['id']}/reset-password", headers=admin_headers,
                        json={'new_password': 'strong-pass-1'}))
    assert login(client, 'pwd_user', 'strong-pass-1').status_code == 200


def test_role_matrix(client, admin_headers):
    """各角色核心接口权限矩阵。"""
    teacher = headers_for(client, 'teacher1', '123456')
    student = headers_for(client, 'student1', '123456')
    reviewer = headers_for(client, 'reviewer', '123456')

    assert client.get('/api/teachers/options', headers=teacher).status_code == 403
    assert client.get('/api/teachers/options', headers=reviewer).status_code == 200
    assert client.get('/api/students', headers=teacher).status_code == 403
    assert client.get('/api/export/report', headers=teacher).status_code == 403
    assert client.get('/api/users', headers=reviewer).status_code == 403
    assert client.get('/api/logs', headers=reviewer).status_code == 403
    assert client.get('/api/achievements', headers=student).status_code == 200
    assert client.get('/api/achievements/trash', headers=student).status_code == 200
    assert client.get('/api/advisors', headers=student).status_code == 403
    assert client.get('/api/stats/scope-options', headers=reviewer).status_code == 200
    assert client.get('/api/health').status_code == 200