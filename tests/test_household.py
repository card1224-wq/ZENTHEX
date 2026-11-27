from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
import shutil
import subprocess
import unittest
from unittest.mock import patch

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from database.models import HouseholdEntry, HouseholdSettings, TradeRecord
from household import router as household


class HouseholdTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
        for model in (HouseholdEntry, HouseholdSettings, TradeRecord):
            model.__table__.create(self.engine)
        self.db = sessionmaker(bind=self.engine)()
        app = FastAPI()
        app.include_router(household.router)
        app.dependency_overrides[household.get_db] = lambda: self.db
        self.client = TestClient(app)
        self.auth = patch.object(household, 'get_current_user', side_effect=self.user)
        self.auth.start()
        self.headers = {'Authorization': 'Bearer user-one'}

    def tearDown(self):
        self.auth.stop()
        self.db.close()
        self.engine.dispose()

    @staticmethod
    def user(token, db):
        if token not in ('user-one', 'user-two', 'disabled'):
            raise HTTPException(401, 'invalid')
        return SimpleNamespace(id=2 if token == 'user-two' else 1,
                               is_active=token != 'disabled', approval_status='approved')

    def entry(self, **updates):
        data = dict(date='2026-11-27', activity='household', kind='expense', category='대출 원리금',
                    description='기업은행 납입', method='계좌', amount_krw=2500000, status='planned', confirmed=True)
        data.update(updates)
        response = self.client.post('/api/household/entries', json=data, headers=self.headers)
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def setting(self, **updates):
        data = dict(as_of='2026-11-26', cash_krw=700000, reserve_krw=0)
        data.update(updates)
        response = self.client.put('/api/household/settings', json=data, headers=self.headers)
        self.assertEqual(response.status_code, 200, response.text)

    def summary(self, month='2026-11'):
        response = self.client.get('/api/household/summary?month=' + month, headers=self.headers)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.headers['cache-control'], 'no-store')
        return response.json()

    def test_authentication_and_account_status_required(self):
        for path in ('summary', 'entries?month=2026-11', 'export'):
            self.assertEqual(self.client.get('/api/household/' + path).status_code, 401)
            self.assertEqual(self.client.get('/api/household/' + path, headers={'Authorization': 'Bearer bad'}).status_code, 401)
            self.assertEqual(self.client.get('/api/household/' + path, headers={'Authorization': 'Bearer disabled'}).status_code, 403)

    def test_no_financial_data_is_preseeded(self):
        result = self.summary()
        self.assertIsNone(result['settings'])
        self.assertEqual(result['actual']['count'], 0)
        self.assertIsNone(result['forecast']['additional_needed_krw'])

    def test_owner_isolation_for_read_edit_delete_settings_and_export(self):
        row = self.entry()
        self.setting()
        self.headers = {'Authorization': 'Bearer user-two'}
        self.assertEqual(self.summary()['actual']['count'], 0)
        self.assertIsNone(self.summary()['settings'])
        report = self.client.get('/api/household/export', headers=self.headers).json()
        self.assertEqual(report['entries'], [])
        self.assertEqual(self.client.delete('/api/household/entries/' + str(row['id']), headers=self.headers).status_code, 404)
        data = {k: v for k, v in row.items() if k != 'id'}
        self.assertEqual(self.client.put('/api/household/entries/' + str(row['id']), headers=self.headers, json=data).status_code, 404)

    def test_shortfall_and_unknown_salary_are_distinct_from_zero(self):
        self.setting()
        self.entry()
        salary = self.entry(date='2026-12-10', kind='income', amount_krw=None, description='급여')
        result = self.summary()['forecast']
        self.assertEqual(result['additional_needed_krw'], 1800000)
        self.assertEqual(result['unknown_amounts'], 1)
        self.assertIsNone(result['days'][14]['balance_krw'])
        data = {k: v for k, v in salary.items() if k != 'id'}
        data['amount_krw'] = 0
        self.client.put('/api/household/entries/' + str(salary['id']), headers=self.headers, json=data)
        self.assertEqual(self.summary()['forecast']['days'][14]['balance_krw'], -1800000)
        data['amount_krw'] = 3000000
        self.client.put('/api/household/entries/' + str(salary['id']), headers=self.headers, json=data)
        self.assertEqual(self.summary()['forecast']['days'][14]['balance_krw'], 1200000)

    def test_reserve_increases_needed_amount(self):
        self.setting(reserve_krw=100000)
        self.entry()
        self.assertEqual(self.summary()['forecast']['additional_needed_krw'], 1900000)

    def test_card_purchase_and_payment_are_not_double_counted(self):
        self.entry(kind='income', status='done', amount_krw=300000)
        self.entry(kind='card_purchase', status='done', amount_krw=100000)
        self.entry(kind='card_payment', status='done', amount_krw=50000)
        self.entry(kind='transfer', status='done', amount_krw=900000)
        result = self.summary()['actual']
        self.assertEqual(result['income_krw'], 300000)
        self.assertEqual(result['outflow_krw'], 50000)
        self.assertEqual(result['net_krw'], 250000)
        self.assertEqual(result['card_purchases_krw'], 100000)

    def test_expected_and_separate_activity_income_never_funds_household(self):
        self.setting()
        self.entry()
        self.entry(kind='income', amount_krw=10000000, confirmed=False)
        self.entry(kind='income', amount_krw=10000000, activity='betman')
        self.assertEqual(self.summary()['forecast']['additional_needed_krw'], 1800000)

    def test_betman_refunds_are_net_of_stakes_and_do_not_change_cash_income(self):
        self.entry(activity='betman', kind='expense', status='done', amount_krw=10000)
        self.entry(activity='betman', kind='income', status='done', amount_krw=3000)
        result = self.summary()
        self.assertEqual(result['side_activities']['betman']['net_krw'], -7000)
        self.assertEqual(result['actual']['income_krw'], 0)

    def test_overdue_expense_is_included_but_overdue_income_is_not_assumed_paid(self):
        self.setting(as_of='2026-11-28')
        self.entry(date='2026-11-27')
        self.entry(date='2026-11-27', kind='income', amount_krw=5000000)
        forecast = self.summary()['forecast']
        self.assertEqual(forecast['overdue_expenses'], 1)
        self.assertEqual(forecast['days'][0]['balance_krw'], -1800000)

    def test_real_trade_summary_is_owned_and_uses_korean_month_boundary(self):
        self.db.add_all([
            TradeRecord(user_id=1, mode='real', pnl_krw=-98, created_at=datetime(2026,11,26,15)),
            TradeRecord(user_id=1, mode='real', pnl_krw=5000, created_at=datetime(2026,11,30,15,30)),
            TradeRecord(user_id=1, mode='practice', pnl_krw=90000, created_at=datetime(2026,11,26,15)),
            TradeRecord(user_id=2, mode='real', pnl_krw=90000, created_at=datetime(2026,11,26,15)),
        ])
        self.db.commit()
        result = self.summary()
        self.assertEqual(result['trading']['realized_pnl_krw'], -98)
        self.assertEqual(result['actual']['income_krw'], 0)
        self.assertEqual(self.summary('2026-12')['trading']['realized_pnl_krw'], 5000)

    def test_delete_is_excluded_and_preserves_existing_trade_records(self):
        self.setting()
        row = self.entry()
        self.assertEqual(self.client.delete('/api/household/entries/'+str(row['id']), headers=self.headers).status_code, 200)
        self.assertEqual(self.summary()['forecast']['additional_needed_krw'], 0)
        self.db.expire_all()
        self.assertTrue(self.db.get(HouseholdEntry, row['id']).deleted)

    def test_invalid_money_and_identity_injection_are_rejected(self):
        data = dict(date='2026-11-27', kind='expense', category='기타', description='입력', status='done')
        for value in (None, -1, 1.5, '1000', True, 10**12+1):
            response = self.client.post('/api/household/entries', headers=self.headers, json={**data, 'amount_krw':value})
            self.assertEqual(response.status_code, 422)
        response = self.client.post('/api/household/entries', headers=self.headers, json={**data, 'amount_krw':100, 'user_id':2})
        self.assertEqual(response.status_code, 422)

    def test_invalid_month_rejected_and_unknown_projection_requires_settings(self):
        self.assertEqual(self.client.get('/api/household/summary?month=2026-13', headers=self.headers).status_code, 422)
        self.assertEqual(self.summary()['forecast']['days'], [])

    def test_list_pagination_and_export_cover_all_owned_rows(self):
        for i in range(102):
            self.db.add(HouseholdEntry(user_id=1, date=datetime(2026,11,27).date(), kind='expense', category='기타', description=str(i), amount_krw=1, status='done'))
        self.db.commit()
        page = self.client.get('/api/household/entries?month=2026-11', headers=self.headers).json()
        self.assertEqual(page['total'], 102)
        self.assertEqual(page['next_offset'], 100)
        page2 = self.client.get('/api/household/entries?month=2026-11&offset=100', headers=self.headers).json()
        self.assertEqual(len(page2['entries']), 2)
        report = self.client.get('/api/household/export', headers=self.headers)
        self.assertEqual(report.headers['cache-control'], 'no-store')
        self.assertEqual(len(report.json()['entries']), 102)
        self.assertNotIn('user-one', report.text)

    @unittest.skipUnless(shutil.which('node'), 'Node frontend checks required')
    def test_household_mobile_frontend(self):
        subprocess.run(['node', str(Path(__file__).with_name('household_app_check.cjs'))], check=True, capture_output=True, text=True)
