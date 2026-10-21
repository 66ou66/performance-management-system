"""后端接口冒烟测试脚本：python smoke_test.py"""
from app import app
from models import Achievement, Student, Teacher, User


def main():
    with app.app_context():
        print(
            'seed counts: users=%d teachers=%d students=%d achievements=%d'
            % (
                User.query.count(),
                Teacher.query.count(),
                Student.query.count(),
                Achievement.query.count(),
            )
        )
        teacher_id = Teacher.query.first().id if Teacher.query.count() else 1

    client = app.test_client()

    resp = client.post('/api/auth/login', json={'username': 'admin', 'password': 'admin123'})
    print('admin login:', resp.status_code)
    assert resp.status_code == 200, resp.get_data(as_text=True)
    token = resp.get_json()['data']['access_token']
    headers = {'Authorization': 'Bearer %s' % token}

    get_urls = [
        '/api/health',
        '/api/auth/me',
        '/api/meta/options',
        '/api/achievements/?page=1&page_size=5',
        '/api/achievements/?keyword=论文&category=科研成果&year=2025',
        '/api/achievements/?sort=-year&sort=-id&status=approved',
        '/api/achievements/trash',
        '/api/achievements/missing-evidence',
        '/api/stats/overview',
        '/api/stats/dashboard',
        '/api/stats/breakdown?dimension=category',
        '/api/stats/breakdown?dimension=year',
        '/api/stats/breakdown?dimension=level',
        '/api/stats/breakdown?dimension=department',
        '/api/stats/breakdown?dimension=status',
        '/api/stats/breakdown?dimension=academic_year',
        '/api/stats/ranking?by=teacher&limit=5',
        '/api/stats/ranking?by=student&limit=5',
        '/api/stats/cross?row=category&col=year',
        '/api/stats/trend',
        '/api/stats/persons',
        '/api/stats/indicators',
        '/api/teachers/?page=1&page_size=5',
        '/api/teachers/options',
        '/api/students/?page=1&page_size=5',
        '/api/students/options',
        '/api/users?page=1&page_size=5',
        '/api/users/candidates?role=teacher',
        '/api/dicts/grouped',
        '/api/dicts/usage',
        '/api/indicators/',
        '/api/advisors/',
        '/api/logs/?page=1&page_size=5',
        '/api/logs/summary',
        '/api/system/info',
        '/api/system/orphans',
        '/api/system/backups',
        '/api/export/achievements',
        '/api/export/report',
        '/api/export/missing-evidence',
        '/api/export/package',
        '/api/import/templates/teachers',
        '/api/import/templates/students',
        '/api/import/templates/achievements',
    ]
    for url in get_urls:
        resp = client.get(url, headers=headers)
        print('GET %-52s -> %s (%d bytes)' % (url, resp.status_code, len(resp.data)))
        assert resp.status_code == 200, resp.get_data(as_text=True)[:500]

    payload = {
        'owner_type': 'teacher',
        'owner_id': teacher_id,
        'category': '科研成果',
        'title': '冒烟测试成果',
        'year': 2025,
        'level': '校级',
        'description': '自动化冒烟测试创建',
    }
    resp = client.post('/api/achievements/', json=payload, headers=headers)
    print('create achievement:', resp.status_code, resp.get_json()['message'])
    assert resp.status_code in (200, 201), resp.get_data(as_text=True)
    achievement_id = resp.get_json()['data']['id']

    resp = client.put(
        '/api/achievements/%d' % achievement_id,
        json={'title': '冒烟测试成果-已更新', 'level': '省部级'},
        headers=headers,
    )
    print('update achievement:', resp.status_code, resp.get_json()['message'])

    resp = client.get('/api/achievements/%d' % achievement_id, headers=headers)
    print('detail title:', resp.get_json()['data']['title'])
    print('detail status:', resp.get_json()['data']['status'])

    # 软删除 → 回收站 → 彻底删除（避免污染演示库）
    resp = client.delete('/api/achievements/%d' % achievement_id, headers=headers)
    print('soft delete achievement:', resp.status_code, resp.get_json()['message'])
    resp = client.get('/api/achievements/?keyword=冒烟测试成果', headers=headers)
    print('trash excluded from list:', resp.get_json()['data']['total'] == 0)
    resp = client.post('/api/achievements/%d/restore' % achievement_id, headers=headers)
    print('restore achievement:', resp.status_code)
    resp = client.delete('/api/achievements/%d?hard=1' % achievement_id, headers=headers)
    print('hard delete achievement:', resp.status_code, resp.get_json()['message'])

    # 教师账号越权检查
    resp = client.post('/api/auth/login', json={'username': 'teacher1', 'password': '123456'})
    print('teacher login:', resp.status_code)
    assert resp.status_code == 200, resp.get_data(as_text=True)
    teacher_headers = {'Authorization': 'Bearer %s' % resp.get_json()['data']['access_token']}

    resp = client.get('/api/achievements/?page=1&page_size=100', headers=teacher_headers)
    print('teacher own achievements total:', resp.get_json()['data']['total'])

    resp = client.get('/api/teachers/options', headers=teacher_headers)
    print('teacher -> /teachers/options status:', resp.status_code)

    resp = client.get('/api/export/report', headers=teacher_headers)
    print('teacher -> /export/report status:', resp.status_code)

    resp = client.get('/api/achievements/', headers={})
    print('anonymous -> achievements status:', resp.status_code)

    print('SMOKE_TEST_DONE')


if __name__ == '__main__':
    main()