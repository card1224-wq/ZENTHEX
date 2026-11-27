from types import SimpleNamespace
import unittest
from unittest.mock import patch
from pathlib import Path
import shutil
import subprocess

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from database.models import TradeRecord
from trading import router as trading


class MobileReportTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
        TradeRecord.__table__.create(self.engine)
        self.db = sessionmaker(bind=self.engine)()
        self.db.add_all([
            TradeRecord(user_id=1, mode='real', ticker='KRW-MBL', pnl_krw=-98, pnl_pct=-0.0036, reason='힘 약화 방어 매도'),
            TradeRecord(user_id=2, mode='real', ticker='PRIVATE-OTHER', pnl_krw=90000, pnl_pct=0.3),
            TradeRecord(user_id=None, mode='real', ticker='ANONYMOUS', pnl_krw=70000, pnl_pct=0.2),
            TradeRecord(user_id=1, mode='practice', ticker='PRACTICE', pnl_krw=888, pnl_pct=0.1),
        ])
        self.db.commit()
        app = FastAPI()
        app.include_router(trading.router)
        app.dependency_overrides[trading.get_db] = lambda: self.db
        self.client = TestClient(app)

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_export_requires_authentication(self):
        response = self.client.get('/api/finance/analysis-report')
        self.assertEqual(response.status_code, 401)

    def test_export_contains_only_authenticated_users_real_trades(self):
        with patch.object(trading, 'get_current_user', return_value=SimpleNamespace(id=1)):
            response = self.client.get('/api/finance/analysis-report', headers={'Authorization': 'Bearer test-token'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['cache-control'], 'no-store')
        report = response.json()['performance']
        self.assertEqual(report['tradeCount'], 1)
        self.assertEqual(report['totalPnlKrw'], -98)
        for forbidden in ('PRIVATE-OTHER', 'ANONYMOUS', 'PRACTICE', 'test-token', 'secretKey', 'accessKey'):
            self.assertNotIn(forbidden, response.text)

    def test_invalid_authentication_never_falls_back_to_anonymous_history(self):
        with patch.object(trading, 'get_current_user', side_effect=HTTPException(401, 'invalid')):
            for path in ('/api/finance/analysis-report', '/api/finance/performance?mode=real'):
                response = self.client.get(path, headers={'Authorization': 'Bearer invalid'})
                self.assertEqual(response.status_code, 401)
                self.assertNotIn('ANONYMOUS', response.text)

    @unittest.skipUnless(shutil.which('node'), 'Node is required for app frontend checks')
    def test_mobile_frontend_and_private_cache_boundaries(self):
        subprocess.run(['node', str(Path(__file__).with_name('mobile_app_check.cjs'))], check=True, capture_output=True, text=True)
