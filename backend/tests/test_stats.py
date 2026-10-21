"""统计口径、多维分析、交叉表、指标点覆盖与查询性能回归测试。"""
from conftest import data_of, headers_for

DIMENSIONS = ('category', 'year', 'level', 'department', 'status',
              'academic_year', 'owner_type', 'advisor')


def make_pending(client, admin_headers):
    """管理员可直接把成果建为待审核状态，用于验证统计口径。"""
    return data_of(client.post('/api/achievements', headers=admin_headers, json={
        'title': '统计口径测试（待审核）', 'category': '论文', 'level': '普通期刊',
        'owner_type': 'student', 'owner_id': 1, 'year': 2024, 'status': 'pending',
    }))


def test_overview_counts_and_extra_indicators(client, admin_headers):
    counts = data_of(client.get('/api/stats/overview', headers=admin_headers))['counts']
    assert counts['achievements'] >= 14
    assert counts['this_year'] >= 0
    assert counts['attachments'] >= 0
    assert 'missing_evidence' in counts and 'pending' in counts and 'trash' in counts
    assert counts['teachers'] >= 3 and counts['students'] >= 2


def test_overview_includes_all_breakdowns(client, admin_headers):
    payload = data_of(client.get('/api/stats/overview', headers=admin_headers))
    for key in ('by_category', 'by_year', 'by_level', 'by_department'):
        assert payload[key], key
        assert all(set(row) == {'name', 'value'} for row in payload[key])


def test_every_dimension_returns_rows(client, admin_headers):
    for dimension in DIMENSIONS:
        response = client.get(f'/api/stats/breakdown?dimension={dimension}', headers=admin_headers)
        assert response.status_code == 200, dimension
        payload = data_of(response)
        assert payload['dimension'] == dimension
        assert payload['items'], dimension
        assert all(row['value'] > 0 for row in payload['items']), dimension


def test_year_dimension_is_sorted_ascending(client, admin_headers):
    items = data_of(client.get('/api/stats/breakdown?dimension=year', headers=admin_headers))['items']
    names = [row['name'] for row in items]
    assert names == sorted(names)


def test_invalid_dimension_is_rejected(client, admin_headers):
    response = client.get('/api/stats/breakdown?dimension=not-exist', headers=admin_headers)
    assert response.status_code == 400
    assert client.get('/api/stats/cross?row=category&col=bad-dim',
                      headers=admin_headers).status_code == 400
    assert client.get('/api/stats/ranking?by=aliens', headers=admin_headers).status_code == 400


def test_only_approved_achievements_are_counted_by_default(client, admin_headers):
    before = data_of(client.get('/api/stats/overview', headers=admin_headers))['counts']
    created = make_pending(client, admin_headers)
    after = data_of(client.get('/api/stats/overview', headers=admin_headers))['counts']
    assert after['achievements'] == before['achievements'], '待审核成果不应计入默认统计口径'
    assert after['pending'] == before['pending'] + 1

    pending_view = data_of(client.get('/api/stats/overview?status=pending',
                                      headers=admin_headers))['counts']
    assert pending_view['achievements'] >= 1
    assert created['id'] in [
        row['id'] for row in data_of(client.get('/api/stats/missing-evidence?status=pending',
                                                headers=admin_headers))['items']
    ]


def test_cross_tab_shapes(client, admin_headers):
    payload = data_of(client.get('/api/stats/cross?row=category&col=year', headers=admin_headers))
    assert payload['rows'] and payload['cols'] and payload['cells']
    assert payload['row_dimension'] == 'category'
    assert all('||' in key for key in payload['cells'])


def test_ranking_respects_limit_and_scope(client, admin_headers):
    items = data_of(client.get('/api/stats/ranking?by=teacher&limit=2',
                               headers=admin_headers))['items']
    assert len(items) <= 2
    assert items[0]['value'] >= items[-1]['value']

    students = data_of(client.get('/api/stats/ranking?by=student&limit=10',
                                  headers=admin_headers))['items']
    assert students and all(row['value'] > 0 for row in students)

    advisors = data_of(client.get('/api/stats/ranking?by=teacher&limit=10&only_advisors=1',
                                  headers=admin_headers))['items']
    assert advisors, '至少有一位教师指导了学生'


def test_indicator_coverage(client, admin_headers):
    coverage = data_of(client.get('/api/stats/indicators', headers=admin_headers))
    assert len(coverage['items']) >= 12
    assert coverage['total_achievements'] >= 1
    assert 0 <= coverage['coverage_percent'] <= 100
    assert isinstance(coverage['uncovered_indicators'], list)


def test_person_summary_and_trend(client, admin_headers):
    persons = data_of(client.get('/api/stats/persons?limit=5', headers=admin_headers))['items']
    assert persons and len(persons) <= 5
    assert {'name', 'owner_type', 'value'} <= set(persons[0])

    trend = data_of(client.get('/api/stats/trend', headers=admin_headers))['items']
    assert trend
    for row in trend:
        assert 'change_percent' in row


def test_dashboard_is_single_request(client, admin_headers):
    payload = data_of(client.get('/api/stats/dashboard', headers=admin_headers))
    for key in ('counts', 'by_category', 'by_year', 'by_level', 'by_department',
                'by_academic_year', 'trend', 'teacher_ranking', 'student_ranking',
                'advisor_ranking'):
        assert key in payload, key


def test_scope_options_requires_elevated(client, admin_headers, teacher_headers):
    payload = data_of(client.get('/api/stats/scope-options', headers=admin_headers))
    assert payload['departments'] and payload['majors']
    assert client.get('/api/stats/scope-options', headers=teacher_headers).status_code == 403


def test_teacher_statistics_are_scoped_to_self(client, teacher_headers, admin_headers):
    own = data_of(client.get('/api/stats/overview', headers=teacher_headers))['counts']
    all_counts = data_of(client.get('/api/stats/overview', headers=admin_headers))['counts']
    # 演示数据中张伟（teacher1）名下有 3 条成果
    assert own['achievements'] == 3, own
    assert own['achievements'] < all_counts['achievements']
    assert 'teachers' not in own, '普通教师不应看到全校师生总数'


def test_list_endpoint_sql_statement_budget(client, admin_headers, sql_counter):
    """列表页必须批量取数：100 条数据的 SQL 语句应保持在常数级。"""
    statements = sql_counter(
        lambda: data_of(client.get('/api/achievements?page=1&page_size=100',
                                   headers=admin_headers)))
    assert len(statements) <= 15, len(statements)


def test_stats_endpoint_sql_statement_budget(client, admin_headers, sql_counter):
    statements = sql_counter(
        lambda: data_of(client.get('/api/stats/dashboard', headers=admin_headers)))
    assert len(statements) <= 25, len(statements)


def test_student_cannot_use_elevated_stats_filters(client, student_headers):
    """学生使用 department 等筛选不会越权看到他人数据。"""
    payload = data_of(client.get('/api/achievements?department=计算机学院&page=1&page_size=100',
                                 headers=student_headers))
    assert all(row['owner_type'] == 'student' for row in payload['items'])
    other = headers_for(client, 'student2', '123456')
    other_items = data_of(client.get('/api/achievements?page=1&page_size=100', headers=other))
    assert other_items['items'], 'student2 也应能看到自己的成果'