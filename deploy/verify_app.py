"""Exercise route dispatch, not framework-internal route container attributes."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from unittest.mock import patch
from fastapi.testclient import TestClient
import main


def verify():
    with patch('trading.router.get_current_price', return_value=0), TestClient(main.app) as client:
        for path in ['/api/health', '/api/modules/status', '/api/finance/status', '/api/stock/status',
                     '/finance.html', '/studio.html', '/stock.html', '/research.html', '/static/module-status.js']:
            response = client.get(path)
            if response.status_code != 200:
                raise RuntimeError('HTTP 검사 실패: '+path+' '+str(response.status_code))
        assert client.get('/api/health').json()['service'] == 'zenthex-saas'
        modules = client.get('/api/modules/status').json()
        assert modules['trading']['binance']['ordersEnabled'] is False
        assert modules['stock']['ordersEnabled'] is False
    print('주요 API/페이지 응답 9개 확인 완료. 외부 시세/주문/AI 호출 없음.')


if __name__ == '__main__':
    verify()
