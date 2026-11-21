"""Owner-only, server-configured read-only Toss connector. Never submits orders."""
import json
import os
import threading
import time
import urllib.parse
import urllib.request

BASE = 'https://openapi.tossinvest.com'
_lock = threading.Lock()
_cached = None

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def configured():
    return bool(os.getenv('ZENTHEX_TOSS_CLIENT_ID') and os.getenv('ZENTHEX_TOSS_CLIENT_SECRET'))


def _request(path, headers=None, data=None):
    request = urllib.request.Request(BASE+path, data=data, headers=headers or {})
    with urllib.request.build_opener(NoRedirect).open(request, timeout=10) as response:
        return json.loads(response.read(2_000_000))


def _token():
    global _cached
    client = os.getenv('ZENTHEX_TOSS_CLIENT_ID', '')
    secret = os.getenv('ZENTHEX_TOSS_CLIENT_SECRET', '')
    if not client or not secret:
        raise ValueError('서버에 토스증권 API 설정이 없습니다.')
    with _lock:
        if _cached and _cached[0] == (client, secret) and _cached[2] > time.monotonic():
            return _cached[1]
        data = urllib.parse.urlencode({'grant_type':'client_credentials', 'client_id':client, 'client_secret':secret}).encode()
        result = _request('/oauth2/token', {'Content-Type':'application/x-www-form-urlencoded'}, data)
        token = result['access_token']
        _cached = ((client, secret), token, time.monotonic()+max(0, int(result['expires_in'])-60))
        return token


def account_summary():
    headers = {'Authorization':'Bearer '+_token()}
    accounts = _request('/api/v1/accounts', headers)['result']
    safe = [{'accountSeq':a['accountSeq'], 'accountNoMasked':'****'+str(a['accountNo'])[-4:], 'accountType':a.get('accountType')} for a in accounts]
    seq = os.getenv('ZENTHEX_TOSS_ACCOUNT_SEQ', '')
    if not seq:
        return {'accounts':safe, 'holdings':None, 'message':'조회할 accountSeq를 서버에 설정하세요. 계좌를 자동 선택하지 않습니다.', 'ordersEnabled':False}
    if seq not in [str(a['accountSeq']) for a in accounts]:
        raise ValueError('설정된 토스 계좌가 본인 계좌 목록과 일치하지 않습니다.')
    result = _request('/api/v1/holdings', {**headers, 'X-Tossinvest-Account':seq})['result']
    return {'accounts':safe, 'holdings':result, 'ordersEnabled':False, 'message':'본인 계좌 조회 완료. 토스 자동주문은 구현되지 않았습니다.'}
