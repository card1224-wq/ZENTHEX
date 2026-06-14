<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Zenthex Stock</title>
  <style>
    :root{--bg:#06070a;--panel:#0d1016;--line:rgba(255,255,255,.12);--text:#f8fafc;--muted:#a1a1aa;--mint:#00e6c3;--gold:#f6c66a;--red:#f87171}
    *{box-sizing:border-box}
    body{margin:0;min-height:100vh;background:var(--bg);color:var(--text);font-family:Inter,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
    body:before{content:"";position:fixed;inset:0;pointer-events:none;background:linear-gradient(180deg,rgba(255,255,255,.04),transparent 280px),radial-gradient(circle at 20% 0%,rgba(0,230,195,.12),transparent 30%),radial-gradient(circle at 80% 16%,rgba(246,198,106,.12),transparent 28%)}
    a{color:inherit;text-decoration:none}
    .nav{position:sticky;top:0;z-index:10;display:flex;justify-content:space-between;align-items:center;gap:14px;padding:14px 28px;border-bottom:1px solid var(--line);background:rgba(6,7,10,.86);backdrop-filter:blur(18px)}
    .brand{display:flex;align-items:center;gap:10px;font-weight:900;letter-spacing:2px}
    .brand img{width:34px;height:34px}
    .nav-actions{display:flex;gap:8px;flex-wrap:wrap}
    .nav a,.nav button{border:1px solid var(--line);background:rgba(255,255,255,.04);color:white;border-radius:8px;padding:10px 12px;font-weight:800;cursor:pointer}
    .shell{position:relative;z-index:1;width:min(1180px,calc(100% - 32px));margin:0 auto;padding:28px 0 42px}
    .hero{display:grid;grid-template-columns:1.05fr .95fr;gap:18px;align-items:stretch}
    .panel{border:1px solid var(--line);background:rgba(255,255,255,.035);border-radius:10px;padding:22px}
    .eyebrow{display:inline-block;border:1px solid rgba(0,230,195,.28);background:rgba(0,230,195,.07);color:#bffef4;border-radius:999px;padding:8px 11px;font-size:11px;font-weight:900;letter-spacing:1px;text-transform:uppercase}
    h1{margin:18px 0 12px;font-size:54px;line-height:.95;letter-spacing:0}
    h2{margin:0 0 12px;font-size:18px}
    p{color:#cbd5e1;line-height:1.65;word-break:keep-all}
    .actions{display:flex;gap:10px;flex-wrap:wrap;margin-top:20px}
    .btn{display:inline-flex;align-items:center;justify-content:center;min-height:44px;padding:0 16px;border-radius:8px;border:1px solid var(--line);background:rgba(255,255,255,.05);font-weight:900}
    .btn.primary{background:var(--mint);color:#03100d;border:0}
    .grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin-top:18px}
    .metric strong{display:block;font-size:24px;margin-top:8px}
    .metric span{color:var(--muted);font-size:12px;font-weight:800}
    .market{display:grid;gap:8px}
    .row{display:grid;grid-template-columns:1fr auto auto;gap:10px;align-items:center;padding:12px;border:1px solid rgba(255,255,255,.09);border-radius:8px;background:rgba(0,0,0,.22)}
    .row b{font-size:14px}
    .pos{color:var(--mint);font-weight:900}
    .neg{color:var(--red);font-weight:900}
    .roadmap{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin-top:18px}
    .check{display:flex;gap:10px;align-items:flex-start;padding:13px;border:1px solid rgba(255,255,255,.09);border-radius:8px;background:rgba(0,0,0,.18)}
    .dot{width:10px;height:10px;margin-top:5px;border-radius:50%;background:var(--gold);box-shadow:0 0 20px rgba(246,198,106,.35)}
    .warn{margin-top:18px;border-color:rgba(248,113,113,.32);background:rgba(248,113,113,.06)}
    @media(max-width:900px){.hero,.grid,.roadmap{grid-template-columns:1fr}.nav{padding:12px 16px}.brand span{display:none}h1{font-size:42px}}
  </style>
</head>
<body>
  <nav class="nav">
    <div class="brand"><img src="/static/zenthex-mark.svg" alt="" /><span>ZENTHEX STOCK</span></div>
    <div class="nav-actions">
      <a href="index.html">홈</a>
      <a href="finance.html">Crypto Trading</a>
      <a href="account.html">마이페이지</a>
    </div>
  </nav>
  <main class="shell">
    <section class="hero">
      <div class="panel">
        <span class="eyebrow">Stock Auto-Trading Line</span>
        <h1>Zenthex Stock</h1>
        <p>국내주식과 향후 해외주식을 위한 별도 자동매매 서비스 라인입니다. 코인 엔진과 섞지 않고, 장 시간, 증권사 API, 손절/익절, 일일 손실 제한을 별도 리스크 매니저로 다룹니다.</p>
        <div class="actions">
          <a class="btn primary" href="#roadmap">구축 로드맵 보기</a>
          <button class="btn" type="button" onclick="loadStockStatus()">시스템 상태 확인</button>
        </div>
      </div>
      <div class="panel">
        <h2>시장 스캐너 미리보기</h2>
        <div class="market">
          <div class="row"><b>KOSPI 후보 A</b><span>거래량 2.4x</span><span class="pos">+1.18%</span></div>
          <div class="row"><b>KOSDAQ 후보 B</b><span>돌파 감시</span><span class="pos">+0.76%</span></div>
          <div class="row"><b>보유 종목 C</b><span>손절선 감시</span><span class="neg">-0.42%</span></div>
          <div class="row"><b>현금</b><span>장중 대기</span><span>분할 진입</span></div>
        </div>
      </div>
    </section>

    <section class="grid">
      <div class="panel metric"><span>1차 증권사</span><strong>한국투자</strong><p>REST/WebSocket 기반으로 SaaS 서버 구조에 가장 먼저 검토합니다.</p></div>
      <div class="panel metric"><span>실거래 전 단계</span><strong>Paper</strong><p>주식은 모의투자와 장중 로그 검증 후 실주문으로 넘어갑니다.</p></div>
      <div class="panel metric"><span>권한 구조</span><strong>Stock Pro</strong><p>대표는 전체 검토, 구독자는 본인 계좌와 본인 엔진만 사용합니다.</p></div>
    </section>

    <section id="roadmap" class="roadmap">
      <div class="check"><span class="dot"></span><div><strong>1. 설계도 확정</strong><p>Studio, Crypto Trading, Stock 3개 서비스 라인을 마스터 플랜에 반영합니다.</p></div></div>
      <div class="check"><span class="dot"></span><div><strong>2. 증권사 API 선택</strong><p>한국투자증권 Open API를 1순위로 검토하고 키/토큰 구조를 정리합니다.</p></div></div>
      <div class="check"><span class="dot"></span><div><strong>3. 모의투자 엔진</strong><p>장중 후보 탐색, 가상 매수, 목표익절, 손절, 장마감 정책을 먼저 검증합니다.</p></div></div>
      <div class="check"><span class="dot"></span><div><strong>4. 실거래 게이트</strong><p>구독, 위험동의, API 키 인증, 주문 권한, 대표 긴급정지를 통과해야 실주문을 허용합니다.</p></div></div>
    </section>

    <section class="panel warn">
      <h2>투자위험 고지</h2>
      <p>Zenthex Stock은 자동매매 도구이며 투자 자문 또는 수익 보장 서비스가 아닙니다. 모든 투자 판단과 손익 책임은 사용자 본인에게 있습니다. 이 빌드는 설계도와 화면 뼈대 단계이며 실제 주식 주문은 비활성화되어 있습니다.</p>
      <p id="stock-status">상태 확인 버튼을 누르면 현재 Stock 모듈 준비 상태를 불러옵니다.</p>
    </section>
  </main>
  <script>
    async function loadStockStatus(){
      const box=document.getElementById('stock-status');
      box.innerText='Zenthex Stock 상태를 확인하는 중입니다.';
      try{
        const res=await fetch('/api/stock/status');
        const data=await res.json();
        box.innerText=`${data.service}: ${data.phase}. ${data.message}`;
      }catch(e){
        box.innerText='Stock API에 연결하지 못했습니다. FastAPI 서버 실행 상태를 확인하세요.';
      }
    }
  </script>
</body>
</html>
