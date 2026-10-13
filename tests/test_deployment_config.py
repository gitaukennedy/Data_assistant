import importlib
import os
import sys


def load_app_with_cors(origins):
    os.environ['CORS_ORIGINS'] = origins
    sys.modules.pop('app', None)
    return importlib.import_module('app')


def test_cors_is_restricted_to_allowed_origins():
    app_module = load_app_with_cors('https://app.example.com,https://admin.example.com')
    client = app_module.app.test_client()

    allowed = client.get('/api/version', headers={'Origin': 'https://app.example.com'})
    assert allowed.headers.get('Access-Control-Allow-Origin') == 'https://app.example.com'

    blocked = client.get('/api/version', headers={'Origin': 'https://evil.example.com'})
    assert blocked.headers.get('Access-Control-Allow-Origin') is None


def test_app_has_expected_routes():
    app_module = load_app_with_cors('http://localhost:3000')
    client = app_module.app.test_client()

    version = client.get('/api/version')
    assert version.status_code == 200
    assert version.get_json()['status'] == 'active'
