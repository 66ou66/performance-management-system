"""成果 CRUD、附件、审核、回收站、批量操作与权限矩阵测试。"""
from conftest import data_of, headers_for, upload

TEACHER_ID = 1
STUDENT_ID = 1


def new_achievement(client, headers, **overrides):
    payload = {
        'title': '测试用科研成果',
        'category': '科研成果',
        'level': '省部级',
        'owner_type': 'teacher',
        'owner_id': TEACHER_ID,
        'year': 2025,
        'description': 'pytest 自动创建',
    }
    payload.update(overrides)
    response = client.post('/api/achievements', headers=headers, json=payload)
    assert response.status_code == 200, response.get_data(as_text=True)
    return data_of(response)


def test_list_returns_pagination_envelope(client, admin_headers):
    payload = data_of(client.get('/api/achievements?page=1&page_size=5', headers=admin_headers))
    assert payload['total'] >= 14
    assert len(payload['items']) == 5
    assert payload['page'] == 1
    first = payload['items'][0]
    for field in ('id', 'title', 'owner_name', 'owner_type', 'category', 'status',
                  'attachment_count', 'has_attachment'):
        assert field in first, field


def test_create_update_delete_restore_and_purge(client, admin_headers):
    created = new_achievement(client, admin_headers)
    item_id = created['id']
    assert created['status'] == 'approved'
    assert created['academic_year']

    updated = data_of(client.put(f'/api/achievements/{item_id}', headers=admin_headers,
                                 json={'title': '改名后的成果', 'year': 2024}))
    assert updated['title'] == '改名后的成果'
    assert updated['year'] == 2024

    # 软删除后进入回收站，普通列表不再出现
    data_of(client.delete(f'/api/achievements/{item_id}', headers=admin_headers))
    listed = data_of(client.get('/api/achievements?page=1&page_size=100', headers=admin_headers))
    assert item_id not in [row['id'] for row in listed['items']]
    trash = data_of(client.get('/api/achievements/trash?page=1&page_size=100', headers=admin_headers))
    assert item_id in [row['id'] for row in trash['items']]

    # 回收站中的成果不允许直接修改
    blocked = client.put(f'/api/achievements/{item_id}', headers=admin_headers,
                         json={'title': '不应生效'})
    assert blocked.status_code == 400

    data_of(client.post(f'/api/achievements/{item_id}/restore', headers=admin_headers))
    listed = data_of(client.get('/api/achievements?page=1&page_size=100', headers=admin_headers))
    assert item_id in [row['id'] for row in listed['items']]

    # 彻底删除：先软删再 ?hard=1
    data_of(client.delete(f'/api/achievements/{item_id}', headers=admin_headers))
    data_of(client.delete(f'/api/achievements/{item_id}?hard=1', headers=admin_headers))
    trash = data_of(client.get('/api/achievements/trash?page=1&page_size=100', headers=admin_headers))
    assert item_id not in [row['id'] for row in trash['items']]
    assert client.get(f'/api/achievements/{item_id}', headers=admin_headers).status_code == 404


def test_create_rejects_category_owner_mismatch(client, admin_headers):
    response = client.post('/api/achievements', headers=admin_headers, json={
        'title': '类型与人员不匹配', 'category': '学科竞赛', 'level': '国家级',
        'owner_type': 'teacher', 'owner_id': TEACHER_ID, 'year': 2025,
    })
    assert response.status_code == 400
    assert '不匹配' in response.get_json()['message']


def test_create_rejects_unknown_owner_and_level(client, admin_headers):
    response = client.post('/api/achievements', headers=admin_headers, json={
        'title': '无效所属人', 'category': '科研成果', 'level': '省部级',
        'owner_type': 'teacher', 'owner_id': 9999, 'year': 2025,
    })
    assert response.status_code == 400
    response = client.post('/api/achievements', headers=admin_headers, json={
        'title': '无效级别', 'category': '科研成果', 'level': '宇宙级',
        'owner_type': 'teacher', 'owner_id': TEACHER_ID, 'year': 2025,
    })
    assert response.status_code == 400


def test_student_scope_and_owner_binding(client, student_headers):
    """学生只能看到本人成果，录入时所属人由后端强制绑定本人。"""
    listed = data_of(client.get('/api/achievements?page=1&page_size=100', headers=student_headers))
    assert listed['items'], '学生应能看到自己的成果'
    assert {row['owner_type'] for row in listed['items']} == {'student'}
    assert {row['owner_id'] for row in listed['items']} == {STUDENT_ID}

    created = new_achievement(client, student_headers, title='学生竞赛获奖',
                              category='学科竞赛', level='省部级',
                              owner_type='student', owner_id=9999)
    assert created['owner_id'] == STUDENT_ID
    assert created['owner_type'] == 'student'


def test_review_workflow(client, student_headers, reviewer_headers, teacher_headers, app):
    app.config['REQUIRE_REVIEW'] = True
    try:
        # 开启送审后，学生新建成果直接进入待审核状态
        created = new_achievement(client, student_headers, title='待审核论文',
                                  category='论文', level='北大核心')
        assert created['status'] == 'pending', created['status']
        assert created['submitted_at']
        item_id = created['id']

        # 教师无权审核
        assert client.post(f'/api/achievements/{item_id}/review', headers=teacher_headers,
                           json={'action': 'approve', 'comment': 'ok'}).status_code == 403

        # 驳回必须填写意见
        assert client.post(f'/api/achievements/{item_id}/review', headers=reviewer_headers,
                           json={'action': 'reject', 'comment': ''}).status_code == 400
        rejected = data_of(client.post(f'/api/achievements/{item_id}/review',
                                       headers=reviewer_headers,
                                       json={'action': 'reject', 'comment': '材料不全'}))
        assert rejected['status'] == 'rejected'
        assert rejected['review_comment'] == '材料不全'

        # 学生补充材料后重新提交，再审核通过
        resubmitted = data_of(client.post(f'/api/achievements/{item_id}/submit',
                                          headers=student_headers))
        assert resubmitted['status'] == 'pending'
        approved = data_of(client.post(f'/api/achievements/{item_id}/review',
                                       headers=reviewer_headers,
                                       json={'action': 'approve', 'comment': '材料齐全'}))
        assert approved['status'] == 'approved'
    finally:
        app.config['REQUIRE_REVIEW'] = False


def test_non_elevated_cannot_set_status_directly(client, student_headers, admin_headers):
    response = client.post('/api/achievements', headers=student_headers, json={
        'title': '越权指定状态', 'category': '学科竞赛', 'level': '省部级',
        'year': 2025, 'status': 'approved',
    })
    assert response.status_code == 403
    created = new_achievement(client, admin_headers, title='管理员直接通过')
    assert created['status'] == 'approved'


def test_reviewer_cannot_create_achievement(client, reviewer_headers):
    response = client.post('/api/achievements', headers=reviewer_headers, json={
        'title': '审核员录入', 'category': '科研成果', 'level': '省部级',
        'owner_type': 'teacher', 'owner_id': TEACHER_ID, 'year': 2025,
    })
    assert response.status_code == 403


def test_multi_attachment_upload_download_delete(client, admin_headers):
    created = new_achievement(client, admin_headers, title='带多份材料的成果')
    item_id = created['id']

    for name in ('立项书.pdf', '结题报告.docx'):
        response = upload(client, f'/api/achievements/{item_id}/attachments', admin_headers,
                          name, data={'category': '立项/结题材料'})
        assert response.status_code == 200, response.get_data(as_text=True)

    payload = data_of(client.get(f'/api/achievements/{item_id}/attachments', headers=admin_headers))
    assert len(payload) == 2
    attachment_id = payload[0]['id']

    download = client.get(f'/api/achievements/{item_id}/attachments/{attachment_id}/download',
                          headers=admin_headers)
    assert download.status_code == 200
    assert download.data.startswith(b'%PDF')

    detail = data_of(client.get(f'/api/achievements/{item_id}', headers=admin_headers))
    assert detail['attachment_count'] == 2
    assert detail['has_attachment'] is True

    data_of(client.delete(f'/api/achievements/{item_id}/attachments/{attachment_id}',
                          headers=admin_headers))
    payload = data_of(client.get(f'/api/achievements/{item_id}/attachments', headers=admin_headers))
    assert len(payload) == 1


def test_attachment_rejects_bad_extension(client, admin_headers):
    created = new_achievement(client, admin_headers, title='非法扩展名')
    response = upload(client, f"/api/achievements/{created['id']}/attachments", admin_headers,
                      'evil.exe', data={'category': '成果正文'})
    assert response.status_code == 400


def test_legacy_attachment_endpoints_contract(client, admin_headers):
    """兼容旧版单附件接口：上传后 attachment_name 必须是本次上传的文件名。"""
    created = new_achievement(client, admin_headers, title='旧接口成果')
    item_id = created['id']
    response = upload(client, f'/api/achievements/{item_id}/attachment', admin_headers, 'verify.pdf')
    assert response.status_code == 200, response.get_data(as_text=True)
    payload = data_of(response)
    assert payload['attachment_name'] == 'verify.pdf'

    download = client.get(f'/api/achievements/{item_id}/attachment', headers=admin_headers)
    assert download.status_code == 200
    assert download.data.startswith(b'%PDF')

    # 再次上传应替换主附件
    upload(client, f'/api/achievements/{item_id}/attachment', admin_headers, 'verify2.pdf')
    detail = data_of(client.get(f'/api/achievements/{item_id}', headers=admin_headers))
    assert detail['attachment_name'] == 'verify2.pdf'


def test_missing_evidence_endpoint(client, admin_headers):
    created = new_achievement(client, admin_headers, title='没有任何材料的成果')
    payload = data_of(client.get('/api/achievements/missing-evidence?page=1&page_size=100',
                                 headers=admin_headers))
    ids = [row['id'] for row in payload['items']]
    assert created['id'] in ids
    assert all(row['attachment_count'] == 0 for row in payload['items'])


def test_indicator_link_and_filter(client, admin_headers):
    indicators = data_of(client.get('/api/indicators?page=1&page_size=5', headers=admin_headers))
    indicator_id = indicators['items'][0]['id']
    created = new_achievement(client, admin_headers, title='关联指标点成果',
                              indicator_ids=[indicator_id])
    assert [row['id'] for row in created['indicators']] == [indicator_id]

    filtered = data_of(client.get(
        f'/api/achievements?indicator_id={indicator_id}&page=1&page_size=100',
        headers=admin_headers))
    assert created['id'] in [row['id'] for row in filtered['items']]

    data_of(client.post('/api/achievements/batch', headers=admin_headers,
                        json={'action': 'remove_indicators', 'ids': [created['id']]}))
    detail = data_of(client.get(f"/api/achievements/{created['id']}", headers=admin_headers))
    assert detail['indicators'] == []


def test_batch_operations(client, admin_headers):
    first = new_achievement(client, admin_headers, title='批量操作 A')
    second = new_achievement(client, admin_headers, title='批量操作 B')
    ids = [first['id'], second['id']]

    result = data_of(client.post('/api/achievements/batch', headers=admin_headers,
                                 json={'action': 'set_level', 'ids': ids, 'level': '其他'}))
    assert result['affected'] == 2

    result = data_of(client.post('/api/achievements/batch', headers=admin_headers,
                                 json={'action': 'delete', 'ids': ids}))
    assert result['affected'] == 2
    result = data_of(client.post('/api/achievements/batch', headers=admin_headers,
                                 json={'action': 'restore', 'ids': ids}))
    assert result['affected'] == 2
    result = data_of(client.post('/api/achievements/batch', headers=admin_headers,
                                 json={'action': 'purge', 'ids': ids}))
    assert result['affected'] == 2
    for item_id in ids:
        assert client.get(f'/api/achievements/{item_id}', headers=admin_headers).status_code == 404

    assert client.post('/api/achievements/batch', headers=admin_headers,
                       json={'action': 'unknown-action', 'ids': ids}).status_code == 400


def test_teacher_cannot_edit_student_owned_achievement(client, teacher_headers, admin_headers):
    """数据归属原则：学生成果由学生本人维护，指导教师也不能直接改写。

    （教师自己的「指导学生成果」是教师名下的独立记录，因此不受此限制。）
    """
    student_items = data_of(client.get('/api/achievements?owner_type=student&page=1&page_size=100',
                                       headers=admin_headers))
    advised = [row for row in student_items['items'] if row['owner_id'] == STUDENT_ID]
    assert advised
    target = advised[0]
    response = client.put(f"/api/achievements/{target['id']}", headers=teacher_headers,
                          json={'description': '不应成功'})
    assert response.status_code == 403
    assert client.get(f"/api/achievements/{target['id']}", headers=teacher_headers).status_code == 403

    # 教师名下的「指导学生成果」记录可以正常维护
    own = new_achievement(client, teacher_headers, title='指导学生获省级奖项',
                          category='指导学生成果', level='省部级')
    assert own['owner_type'] == 'teacher'
    updated = data_of(client.put(f"/api/achievements/{own['id']}", headers=teacher_headers,
                                 json={'description': '教师补充说明'}))
    assert updated['description'] == '教师补充说明'


def test_unrelated_teacher_cannot_edit(client, admin_headers):
    """未被指定为指导教师的老师不能修改该学生的成果。"""
    other = headers_for(client, 'teacher3', '123456')
    student = data_of(client.post('/api/students', headers=admin_headers, json={
        'student_no': 'PYTEST-0001', 'name': '无导师学生', 'grade': '2023级',
        'major': '软件工程', 'department': '计算机学院',
    }))
    created = data_of(client.post('/api/achievements', headers=admin_headers, json={
        'title': '无导师学生的竞赛获奖', 'category': '学科竞赛', 'level': '省部级',
        'owner_type': 'student', 'owner_id': student['id'], 'year': 2025,
    }))
    response = client.put(f"/api/achievements/{created['id']}", headers=other,
                          json={'description': '不应成功'})
    assert response.status_code == 403


def test_purge_removes_attachment_rows_and_files(client, admin_headers, app):
    """彻底删除成果时必须连带删除附件记录与磁盘文件，不留孤儿。"""
    import os

    from models import Attachment, Achievement
    from extensions import db

    created = new_achievement(client, admin_headers, title='带材料待彻底删除')
    item_id = created['id']
    upload(client, f'/api/achievements/{item_id}/attachments', admin_headers,
           '证据.pdf', data={'category': '成果正文'})

    with app.app_context():
        rows = Attachment.query.filter_by(achievement_id=item_id).all()
        assert len(rows) == 1
        stored = os.path.join(app.config['UPLOAD_FOLDER'], rows[0].stored_path)
        assert os.path.exists(stored)

    data_of(client.delete(f'/api/achievements/{item_id}', headers=admin_headers))
    data_of(client.delete(f'/api/achievements/{item_id}?hard=1', headers=admin_headers))

    with app.app_context():
        assert db.session.get(Achievement, item_id) is None
        assert Attachment.query.filter_by(achievement_id=item_id).count() == 0
        assert not os.path.exists(stored)