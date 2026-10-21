"""认证、令牌、节流与密码策略测试。"""
from conftest import data_of, login


def test_health_reports_service_and_database(client):
    payload = data_of(client.get('/api/health'))
    assert payload['service'] == 'achievement-api'
    assert payload['status'] == 'ok'
    assert payload['database']['user'] >= 7
    assert isinstance(payload['migrations'], list)


def test_login_success_returns_tokens_and_profile(client):
    response = login(client, 'teacher1', '123456')
    assert response.status_code == 200
    payload = data_of(response)
    assert payload['access_token'] and payload['refresh_token']
    assert payload['user']['username'] == 'teacher1'
    assert payload['user']['role'] == 'teacher'
    assert payload['user']['profile']['name'] == '张伟'
    assert payload['user']['last_login_at']


def test_login_wrong_password_is_rejected(client):
    response = login(client, 'teacher1', 'wrong-password')
    assert response.status_code == 401
    assert '用户名或密码错误' in response.get_json()['message']


def test_anonymous_requests_get_401(client):
    for url in ('/api/achievements', '/api/teachers', '/api/stats/overview',
                '/api/users', '/api/logs/'):
        assert client.get(url).status_code == 401, url


def test_login_throttle_locks_after_repeated_failures(client):
    for _ in range(5):
        login(client, 'teacher2', 'bad-password')
    response = login(client, 'teacher2', '123456')
    assert response.status_code == 429
    assert '重试' in response.get_json()['message']


def test_me_returns_student_advisors(client, student_headers):
    payload = data_of(client.get('/api/auth/me', headers=student_headers))
    assert payload['profile']['student_no']
    assert payload['advisors'], '学生应能看到自己的指导教师'


def test_change_password_rotates_token_version(client):
    headers = login_and_headers(client, 'teacher3', '123456')
    response = client.post('/api/auth/change-password', headers=headers,
                           json={'old_password': '123456', 'new_password': 'newpass123'})
    payload = data_of(response)
    assert payload['access_token']
    # 旧令牌立即失效
    assert client.get('/api/auth/me', headers=headers).status_code == 401
    # 新令牌可用
    new_headers = {'Authorization': 'Bearer %s' % payload['access_token']}
    assert client.get('/api/auth/me', headers=new_headers).status_code == 200
    # 原密码不再可用，新密码可登录
    assert login(client, 'teacher3', '123456').status_code == 401
    assert login(client, 'teacher3', 'newpass123').status_code == 200


def test_change_password_rejects_same_or_too_short(client, teacher_headers):
    response = client.post('/api/auth/change-password', headers=teacher_headers,
                           json={'old_password': '123456', 'new_password': '123456'})
    assert response.status_code == 400
    response = client.post('/api/auth/change-password', headers=teacher_headers,
                           json={'old_password': '123456', 'new_password': '123'})
    assert response.status_code == 400


def test_refresh_token_flow(client):
    response = login(client, 'teacher1', '123456')
    tokens = data_of(response)
    access = {'Authorization': 'Bearer %s' % tokens['access_token']}
    refresh = {'Authorization': 'Bearer %s' % tokens['refresh_token']}
    # 访问令牌不能用于刷新接口，刷新令牌不能用于业务接口
    assert client.post('/api/auth/refresh', headers=access).status_code in (401, 422)
    assert client.get('/api/achievements', headers=refresh).status_code == 401
    refreshed = data_of(client.post('/api/auth/refresh', headers=refresh))
    assert refreshed['access_token']
    assert client.get('/api/auth/me',
                      headers={'Authorization': 'Bearer %s' % refreshed['access_token']}).status_code == 200


def test_disabled_account_cannot_login_and_token_is_revoked(client, admin_headers,
                                                            teacher_headers):
    me = data_of(client.get('/api/auth/me', headers=teacher_headers))
    user_id = me['id']
    data_of(client.put(f'/api/users/{user_id}/status', headers=admin_headers,
                       json={'is_active': False}))
    assert client.get('/api/auth/me', headers=teacher_headers).status_code == 401
    assert login(client, 'teacher1', '123456').status_code == 403


def test_must_change_password_blocks_business_api(client, app, admin_headers):
    """开启强制改密后，未改密账号访问业务接口应被 403 拦截。"""
    app.config['FORCE_PASSWORD_CHANGE'] = True
    try:
        created = data_of(client.post('/api/users', headers=admin_headers, json={
            'username': 'needchange', 'password': '123456', 'role': 'reviewer',
            'must_change_password': True,
        }))
        assert created['must_change_password'] is True
        headers = login_and_headers(client, 'needchange', '123456')
        response = client.get('/api/achievements', headers=headers)
        assert response.status_code == 403
        assert '密码' in response.get_json()['message']
        # 改密接口本身必须放行，否则账号会被锁死
        changed = client.post('/api/auth/change-password', headers=headers,
                              json={'old_password': '123456', 'new_password': 'brandnew1'})
        assert changed.status_code == 200
    finally:
        app.config['FORCE_PASSWORD_CHANGE'] = False


def login_and_headers(client, username, password):
    response = login(client, username, password)
    assert response.status_code == 200, response.get_data(as_text=True)
    return {'Authorization': 'Bearer %s' % data_of(response)['access_token']}