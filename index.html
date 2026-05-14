<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Zenthex SaaS Platform</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&display=swap');
    :root {
      --bg:#06070a;
      --panel:#0f1117;
      --line:rgba(255,255,255,.12);
      --muted:#a1a1aa;
      --text:#f8fafc;
      --mint:#00e6c3;
      --steel:#91a7ff;
      --gold:#f6c66a;
    }
    * { box-sizing:border-box; }
    body { margin:0; min-height:100vh; background:var(--bg); color:var(--text); font-family:Inter,system-ui,sans-serif; }
    body::before {
      content:""; position:fixed; inset:0; pointer-events:none;
      background:
        linear-gradient(180deg, rgba(255,255,255,.035), transparent 260px),
        radial-gradient(circle at 50% -10%, rgba(145,167,255,.20), transparent 32%),
        radial-gradient(circle at 82% 18%, rgba(0,230,195,.10), transparent 22%);
    }
    body::after {
      content:"Z"; position:fixed; left:50%; top:50%; transform:translate(-50%,-50%);
      z-index:0; pointer-events:none; color:rgba(255,255,255,.028); font-size:min(58vw, 720px); font-weight:900; line-height:.8;
      text-shadow:0 0 120px rgba(0,230,195,.10);
    }
    .nav { position:sticky; top:0; z-index:20; height:74px; padding:0 32px; display:flex; align-items:center; justify-content:space-between; border-bottom:1px solid var(--line); background:rgba(6,7,10,.86); backdrop-filter:blur(18px); }
    .brand { display:flex; align-items:center; gap:12px; font-weight:900; letter-spacing:3px; }
    .mark-small { width:34px; height:34px; }
    .nav-actions { display:flex; gap:10px; align-items:center; }
    .nav a { color:white; text-decoration:none; border:1px solid var(--line); background:rgba(255,255,255,.04); padding:10px 14px; border-radius:8px; font-size:13px; font-weight:800; }
    .owner-pill { display:none; color:#ffe1a1 !important; border-color:rgba(246,198,106,.45) !important; }
    .shell { position:relative; z-index:1; width:min(1180px, calc(100% - 40px)); margin:0 auto; padding:46px 0 36px; }
    .hero { position:relative; min-height:calc(100vh - 210px); display:flex; align-items:center; justify-content:center; text-align:center; overflow:hidden; border:1px solid rgba(255,255,255,.08); border-radius:18px; background:linear-gradient(180deg, rgba(255,255,255,.04), rgba(255,255,255,.018)); }
    .hero-mark { position:absolute; inset:0; display:grid; place-items:center; opacity:.30; pointer-events:none; }
    .hero-mark img { width:min(72vw, 760px); height:auto; filter:drop-shadow(0 40px 90px rgba(0,230,195,.10)); }
    .hero-content { position:relative; z-index:2; width:min(820px, calc(100% - 32px)); padding:74px 0; }
    .eyebrow { display:inline-flex; gap:8px; align-items:center; color:#d7defe; border:1px solid rgba(145,167,255,.28); background:rgba(145,167,255,.08); padding:8px 11px; border-radius:999px; font-size:11px; font-weight:900; letter-spacing:1.4px; text-transform:uppercase; }
    h1 { margin:22px 0 18px; font-size:72px; line-height:.92; letter-spacing:-1px; }
    .lead { color:#d4d4d8; line-height:1.75; font-size:18px; margin:0 auto 26px; max-width:690px; }
    .actions { display:flex; gap:12px; flex-wrap:wrap; margin-bottom:28px; justify-content:center; }
    .cta { min-height:46px; display:inline-flex; align-items:center; justify-content:center; padding:0 18px; border-radius:8px; text-decoration:none; font-size:14px; font-weight:900; border:0; cursor:pointer; }
    .cta.main { background:white; color:#050507; }
    .cta.trade { background:var(--mint); color:#03100d; }
    .cta.sub { color:white; background:rgba(255,255,255,.04); border:1px solid var(--line); }
    .trust { display:grid; grid-template-columns:repeat(3, minmax(0,1fr)); gap:10px; max-width:760px; margin:0 auto; text-align:left; }
    .trust div { border:1px solid var(--line); background:rgba(255,255,255,.035); border-radius:8px; padding:13px; }
    .trust strong { display:block; font-size:13px; margin-bottom:5px; }
    .trust span { color:var(--muted); font-size:12px; line-height:1.5; }
    .products { display:grid; grid-template-columns:1fr 1fr; gap:14px; margin-top:28px; }
    .product { border:1px solid var(--line); background:rgba(255,255,255,.035); border-radius:10px; padding:20px; }
    .product .kicker { color:#cbd5e1; font-size:11px; font-weight:900; letter-spacing:1.4px; text-transform:uppercase; }
    .product h3 { margin:10px 0 8px; font-size:24px; }
    .product p { margin:0 0 16px; color:#b8bcc7; line-height:1.65; font-size:14px; }
    .chips { display:flex; flex-wrap:wrap; gap:7px; margin-bottom:16px; }
    .chips span { color:#e5e7eb; border:1px solid rgba(255,255,255,.10); background:rgba(255,255,255,.04); padding:7px 9px; border-radius:7px; font-size:12px; font-weight:800; }
    .policy { margin-top:20px; color:#8f96a3; font-size:12px; line-height:1.65; }
    .modal { display:none; position:fixed; inset:0; z-index:50; background:rgba(0,0,0,.72); align-items:center; justify-content:center; padding:24px; }
    .modal.open { display:flex; }
    .modal-card { width:min(760px,100%); background:#101014; border:1px solid var(--line); border-radius:10px; padding:28px; box-shadow:0 30px 80px rgba(0,0,0,.45); }
    .modal-head { display:flex; justify-content:space-between; gap:16px; align-items:start; margin-bottom:16px; }
    .modal h2 { margin:0; font-size:28px; }
    .close { width:36px; height:36px; border:1px solid var(--line); background:#17171d; color:white; border-radius:8px; cursor:pointer; font-weight:900; }
    .modal p, .modal li { color:#d4d4d8; line-height:1.8; }
    @media (max-width:900px) {
      .nav { padding:0 18px; }
      .brand span { display:none; }
      .shell { width:min(100% - 28px, 1180px); padding-top:34px; }
      .hero { min-height:auto; }
      .hero-content { padding:52px 0; }
      h1 { font-size:46px; }
      .trust, .products { grid-template-columns:1fr; }
      .hero-mark img { width:120vw; }
    }
  </style>
</head>
<body>
  <nav class="nav">
    <div class="brand">
      <svg class="mark-small" viewBox="0 0 120 120" aria-hidden="true">
        <path d="M60 8 104 33v54L60 112 16 87V33L60 8Z" fill="#10141d" stroke="#dbeafe" stroke-width="5"/>
        <path d="M31 38h44L45 82h44" fill="none" stroke="#00e6c3" stroke-width="9" stroke-linecap="round" stroke-linejoin="round"/>
        <path d="M60 8v32M16 33l31 18M104 33 73 51" stroke="#91a7ff" stroke-width="4" opacity=".85"/>
      </svg>
      <span>ZENTHEX</span>
    </div>
    <div class="nav-actions">
      <a id="owner-link" class="owner-pill" href="admin.html">CEO Dashboard</a>
      <a id="account-link" style="display:none" href="account.html">마이페이지</a>
      <a href="login.html" id="nav-auth-btn">로그인</a>
    </div>
  </nav>

  <main class="shell">
    <section class="hero">
      <div class="hero-mark"><img src="static/zenthex-mark.svg" alt="" /></div>
      <div class="hero-content">
        <span class="eyebrow">AI Studio + Signal Guard SaaS</span>
        <h1>Zenthex</h1>
        <p class="lead">AI 3D 제작과 자동매매 전략 검증을 하나의 계정, 하나의 구독, 하나의 운영 시스템으로 제공하는 SaaS 플랫폼입니다.</p>
        <div class="actions">
          <a class="cta main" href="studio.html?trial=1">Studio 1회 체험</a>
          <a class="cta trade" href="finance.html?trial=1">Trading 구조 보기</a>
          <button class="cta sub" onclick="openModal('platform-modal')">플랫폼 설명</button>
        </div>
        <div class="trust">
          <div><strong>체험 보호</strong><span>Studio는 하루 1회 보기 전용 체험 후 구독 전환</span></div>
          <div><strong>실거래 잠금</strong><span>Trading API 키는 로그인과 구독 권한 뒤에서만 표시</span></div>
          <div><strong>운영 통제</strong><span>대표 대시보드, 사용량, 결제내역, 긴급 정지 구조</span></div>
        </div>
      </div>
    </section>

    <section class="products">
      <article class="product">
        <span class="kicker">Zenthex Studio</span>
        <h3>프롬프트와 도면을 3D로</h3>
        <p>문장 또는 2D 도면을 기반으로 3D 공간을 미리보고, 구독 후 GLB 다운로드와 저장 기능을 제공합니다.</p>
        <div class="chips"><span>프롬프트 → 3D</span><span>2D 도면 분석</span><span>보기 전용 체험</span></div>
        <a class="cta main" href="studio.html?trial=1">Studio 체험</a>
      </article>
      <article class="product">
        <span class="kicker">Zenthex Trading</span>
        <h3>단타 신호 구조를 확인</h3>
        <p>24시간 강한 후보를 거르고 1분·3분·5분 단타 신호를 점수화합니다. 실거래는 구독 권한 후에만 열립니다.</p>
        <div class="chips"><span>Signal Guard</span><span>API 키 보호</span><span>Upbit 우선</span><span>Binance 확장</span></div>
        <a class="cta trade" href="finance.html?trial=1">Trading 구조 보기</a>
      </article>
    </section>
    <p class="policy">Zenthex Trading은 자동매매 보조 도구이며 투자 자문 또는 수익 보장 서비스가 아닙니다. 모든 투자 판단과 손익 책임은 사용자 본인에게 있습니다.</p>
  </main>

  <div class="modal" id="platform-modal">
    <div class="modal-card">
      <div class="modal-head"><h2>Zenthex 플랫폼</h2><button class="close" onclick="closeModal('platform-modal')">X</button></div>
      <p>Zenthex는 Studio와 Trading을 분리된 제품처럼 보여주기보다, 하나의 SaaS 계정 안에서 체험, 구독, 사용량, 결제, 운영을 관리하는 플랫폼입니다.</p>
      <ul>
        <li>Studio 체험은 보기 전용이며 다운로드는 구독 후 제공됩니다.</li>
        <li>Trading 체험판에는 API 키 입력이 노출되지 않습니다.</li>
        <li>실거래는 로그인, 구독 권한, 위험 동의 뒤에서만 실행됩니다.</li>
      </ul>
    </div>
  </div>

  <script>
    function openModal(id){ document.getElementById(id).classList.add('open'); }
    function closeModal(id){ document.getElementById(id).classList.remove('open'); }
    const token = localStorage.getItem('zx_token');
    const user = JSON.parse(localStorage.getItem('zx_user') || 'null');
    const authBtn = document.getElementById('nav-auth-btn');
    const ownerLink = document.getElementById('owner-link');
    const accountLink = document.getElementById('account-link');
    if(token){
      accountLink.style.display='inline-flex';
      authBtn.innerText='로그아웃';
      authBtn.href='#';
      authBtn.onclick=()=>{ localStorage.removeItem('zx_token'); localStorage.removeItem('zx_user'); location.reload(); };
      if(user && ['owner','admin'].includes(user.role)) ownerLink.style.display='inline-flex';
    }
  </script>
</body>
</html>
