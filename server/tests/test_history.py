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
