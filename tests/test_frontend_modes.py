from pathlib import Path
import re
import shutil
import subprocess
import unittest


@unittest.skipUnless(shutil.which('node'), 'Node frontend checks run in CI/local verification')
class FrontendModesTests(unittest.TestCase):
    def test_practice_selection_is_preserved_and_saved_preference_consumed_once(self):
        source=(Path(__file__).resolve().parents[1]/'static/finance.html').read_text()
        function=re.search(r'^function setupTradingModes\(\).*$',source,re.M).group(0)
        code='''
const assert=require('node:assert/strict');
const elements={};
function element(){return {dataset:{},value:'practice',classList:{add(){},remove(){},toggle(){}},querySelector(){return this;},insertAdjacentHTML(){},set innerHTML(x){this.value='practice'},set onclick(x){}}}
const document={getElementById(id){return elements[id]||=(element())}};
const tradingModeEl=element(); let token='token',user={role:'owner'},selectedExchange='upbit';
function userCanSeeRealTrade(){return true} function toggleTradingMode(){}
'''+function+'''
tradingModeEl.dataset.preferred='real';setupTradingModes();assert.equal(tradingModeEl.value,'real');
tradingModeEl.value='practice';setupTradingModes();assert.equal(tradingModeEl.value,'practice');
setupTradingModes();assert.equal(tradingModeEl.value,'practice');
tradingModeEl.value='real';setupTradingModes();assert.equal(tradingModeEl.value,'real');
'''
        subprocess.run(['node','-e',code],check=True,capture_output=True,text=True)

    def test_no_fixed_claim_or_automatic_restart_by_default(self):
        source=(Path(__file__).resolve().parents[1]/'static/finance.html').read_text()
        for text in ['현재 자동매매 가능','계정 생성 후 바로 연결 검증','키 인증 후 실거래 시작','Binance 자동주문은 다음 패치']:
            self.assertNotIn(text,source)
        tag=re.search(r'<input[^>]*id="auto-restart-profit"[^>]*>',source).group(0)
        self.assertNotIn('checked',tag)
