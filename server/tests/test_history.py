import pytest


def test_devices_and_history_empty(client):
    assert client.get('/api/devices').json() == {'devices': []}
    body = client.get('/api/devices/unknown/history').json()
    assert body['readings'] == []
    assert body['total'] == 0


def test_history_filtered_newest_first_and_paginated(client):
    for device, value in [('b', 10), ('a', 99), ('b', 20), ('b', 30)]:
        client.post('/api/telemetry', json={'device_id': device, 'value': value})
    assert client.get('/api/devices').json() == {'devices': ['a', 'b']}
    body = client.get('/api/devices/b/history?limit=2').json()
    assert body['total'] == 3
    assert [r['value'] for r in body['readings']] == [30, 20]
    assert all('timestamp' in r and 'id' in r for r in body['readings'])
    page = client.get('/api/devices/b/history?limit=2&offset=2').json()
    assert [r['value'] for r in page['readings']] == [10]
    assert client.get('/api/devices/b/history?offset=100').json()['readings'] == []


@pytest.mark.parametrize('query', ['limit=0', 'limit=501', 'offset=-1', 'limit=abc'])
def test_invalid_history_pagination(client, query):
    assert client.get('/api/devices/b/history?' + query).status_code == 422


def test_plot_period_boundaries_order_and_device(client):
    from app import main
    with main.get_conn() as conn:
        conn.executemany(
            'INSERT INTO telemetry (device_id, value, timestamp) VALUES (?, ?, ?)', [
                ('sensor', 3, '2026-10-21T12:00:02'),
                ('sensor', 1, '2026-10-21T12:00:00'),
                ('sensor', 2, '2026-10-21T12:00:01'),
                ('other', 99, '2026-10-21T12:00:01'),
            ])
    response = client.get('/api/devices/sensor/history/plot', params={
        'from': '2026-10-21T12:00:00', 'to': '2026-10-21T12:00:01'})
    assert response.status_code == 200
    assert [r['value'] for r in response.json()['readings']] == [1, 2]
    assert client.get('/api/devices/unknown/history/plot', params={
        'from': '2026-10-21T12:00:00', 'to': '2026-10-21T12:00:01'}).json()['readings'] == []


@pytest.mark.parametrize('start,end', [
    ('2026-10-22', '2026-10-21'), ('invalid', '2026-10-21T12:00:00'),
    ('2026-10-21T12:00:00+03:00', '2026-10-21T13:00:00+03:00'),
])
def test_plot_invalid_period(client, start, end):
    assert client.get('/api/devices/sensor/history/plot', params={
        'from': start, 'to': end}).status_code == 422


def test_plot_requires_period(client):
    assert client.get('/api/devices/sensor/history/plot').status_code == 422


def test_plot_does_not_silently_truncate(client):
    from app import main
    with main.get_conn() as conn:
        conn.executemany(
            'INSERT INTO telemetry (device_id, value, timestamp) VALUES (?, ?, ?)',
            [('sensor', i, '2026-10-21T12:00:00') for i in range(50001)])
    assert client.get('/api/devices/sensor/history/plot', params={
        'from': '2026-10-21T00:00:00', 'to': '2026-10-21T23:59:59'}).status_code == 413
