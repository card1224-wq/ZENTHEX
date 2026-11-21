import asyncio
import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, Mock

from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image
from studio import router as studio
from modules_status import router as modules_router
from trading import router as trading


class ModuleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.old = Path.cwd()
        os.chdir(self.temp.name)
        Path('static/models').mkdir(parents=True)
        self.app = FastAPI()
        self.app.include_router(studio.router)
        self.app.include_router(modules_router)
        self.app.dependency_overrides[studio.get_db] = lambda: Mock()
        studio.TRIAL_USAGE_BY_IP.clear()
        studio.GENERATION_LOCK = asyncio.Lock()
        self.client = TestClient(self.app)

    def tearDown(self):
        os.chdir(self.old)
        self.temp.cleanup()

    def test_missing_ai_key_is_not_reported_as_success_or_charged(self):
        with patch.dict(os.environ, {'GEMINI_API_KEY':'', 'GOOGLE_API_KEY':''}):
            response = self.client.post('/api/studio/generate', data={'prompt':'32평 아파트'})
        self.assertEqual(response.status_code, 503)
        self.assertEqual(studio.TRIAL_USAGE_BY_IP, {})

    def test_provider_error_does_not_consume_free_trial(self):
        with patch.object(studio, 'google_ai_studio_is_configured', return_value=True), patch.object(studio, 'build_google_ai_studio_result', return_value={'status':'error','message':'생성 실패'}):
            response = self.client.post('/api/studio/generate', data={'prompt':'32평 아파트'})
        self.assertEqual(response.status_code, 502)
        self.assertEqual(studio.TRIAL_USAGE_BY_IP, {})

    def test_result_must_exist_and_success_consumes_one_trial_only(self):
        def generate(*args):
            Image.new('RGB',(8,8)).save('static/models/generated.png')
            return {'status':'success','provider':'mock','image_url':'/static/models/generated.png'}
        with patch.object(studio, 'google_ai_studio_is_configured', return_value=True), patch.object(studio, 'build_google_ai_studio_result', side_effect=generate) as provider:
            first = self.client.post('/api/studio/generate', data={'prompt':'32평 아파트'})
            second = self.client.post('/api/studio/generate', data={'prompt':'32평 아파트'})
        self.assertEqual(first.status_code, 200)
        self.assertIsNone(first.json()['model_url'])
        self.assertFalse(first.json()['dimension_accurate'])
        self.assertEqual(second.status_code,403)
        self.assertEqual(provider.call_count,1)

    def test_nonexistent_generated_file_is_failure(self):
        with patch.object(studio, 'google_ai_studio_is_configured', return_value=True), patch.object(studio, 'build_google_ai_studio_result', return_value={'status':'success','image_url':'/static/models/absent.png'}):
            response = self.client.post('/api/studio/generate', data={'prompt':'사무실'})
        self.assertEqual(response.status_code,502)
        self.assertEqual(studio.TRIAL_USAGE_BY_IP,{})

    def test_invalid_upload_does_not_call_provider_or_consume_quota(self):
        with patch.object(studio, 'build_google_ai_studio_result') as provider:
            response = self.client.post('/api/studio/upload', files={'file':('plan.png',b'not an image','image/png')})
        self.assertEqual(response.status_code,400)
        provider.assert_not_called()
        self.assertEqual(studio.TRIAL_USAGE_BY_IP,{})

    def test_uploaded_image_is_passed_then_removed(self):
        stream=io.BytesIO(); Image.new('RGB',(10,10)).save(stream,format='PNG')
        def generate(prompt, reference):
            self.assertTrue(Path(reference).is_file())
            Image.new('RGB',(10,10)).save('static/models/generated.png')
            return {'status':'success','image_url':'/static/models/generated.png'}
        with patch.object(studio, 'google_ai_studio_is_configured', return_value=True), patch.object(studio, 'build_google_ai_studio_result', side_effect=generate):
            response=self.client.post('/api/studio/upload',files={'file':('plan.png',stream.getvalue(),'image/png')})
        self.assertEqual(response.status_code,200)
        self.assertEqual(list(Path('uploads').iterdir()),[])

    def test_capabilities_never_claim_bithumb_or_binance_orders(self):
        with patch.dict(os.environ, {'ZENTHEX_ENABLE_LIVE_TRADING':'true','GEMINI_API_KEY':'secret-not-for-response'}):
            response=self.client.get('/api/modules/status')
        self.assertEqual(response.status_code,200)
        self.assertFalse(response.json()['trading']['binance']['ordersEnabled'])
        self.assertFalse(response.json()['trading']['bithumb']['ordersEnabled'])
        self.assertFalse(response.json()['stock']['ordersEnabled'])
        self.assertNotIn('secret-not-for-response',response.text)


class MarketOutageTests(unittest.IsolatedAsyncioTestCase):
    async def test_price_outage_does_not_create_a_fake_btc_price(self):
        old=trading.bot_state.held_btc
        trading.bot_state.held_btc=0
        try:
            with patch.object(trading,'get_current_price',return_value=0), patch.object(trading,'require_real_status_permission'):
                result=await trading.status(None,Mock())
            self.assertEqual(result['currentPrice'],0)
            self.assertFalse(result['priceAvailable'])
        finally:
            trading.bot_state.held_btc=old
