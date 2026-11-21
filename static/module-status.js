/* Backend facts and this browser's verification are deliberately separate. */
(() => {
  'use strict';
  let facts = null;
  let busy = false;
  const put = (id, text) => { const el = document.getElementById(id); if (el) el.textContent = text; };
  function render() {
    if (document.getElementById('exchange-upbit-status')) {
      let text = '서버 상태 확인 불가';
      if (facts) {
        const t = facts.trading;
        const keyOk = typeof upbitKeyVerified !== 'undefined' && upbitKeyVerified;
        text = t.recoveryRequired ? '주문·보유 상태 대조 필요' : !t.liveEnabled ? '실거래 잠금' : keyOk ? '자산조회 인증됨 · 시작 전 주문 권한 확인' : '키 인증 필요';
      }
      put('exchange-upbit-status', text);
      put('exchange-bithumb-status', facts ? '조회·키 인증만 지원' : '서버 상태 확인 불가');
      put('exchange-binance-status', facts ? '조회·키 인증만 지원' : '서버 상태 확인 불가');
    }
    let box = document.getElementById('module-readiness');
    if (!box && !document.getElementById('exchange-upbit-status')) {
      box = document.createElement('p'); box.id = 'module-readiness'; box.setAttribute('role', 'status');
      box.style.cssText = 'padding:14px 20px;border:1px solid #475569;background:#10151e;color:#e2e8f0;white-space:pre-line;margin:12px 20px;position:relative;z-index:5';
      const nav = document.querySelector('nav'); if (nav) nav.after(box); else document.body.prepend(box);
    }
    if (box) box.textContent = !facts ? '서버 기능 상태를 확인하지 못했습니다.' : location.pathname.includes('stock') ? facts.stock.message : 'Studio: ' + facts.studio.message + '\n샘플 보기와 AI 생성 결과는 별개입니다. 현재 AI 결과는 콘셉트 이미지이며 치수 기반 3D 모델은 아닙니다.';
  }
  async function refresh() {
    if (busy || document.hidden) return;
    busy = true;
    try {
      const r = await fetch('/api/modules/status', {cache:'no-store', signal:AbortSignal.timeout(8000)});
      if (!r.ok) throw new Error('status');
      facts = await r.json();
    } catch (_) { facts = null; }
    finally { busy = false; render(); }
  }
  refresh(); setInterval(refresh, 15000);
  document.addEventListener('input', render);
  document.addEventListener('click', () => setTimeout(render, 250));
})();
