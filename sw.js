<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Zenthex SaaS Platform</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&display=swap');
    :root { --bg:#06070a; --panel:#0b0d12; --line:rgba(255,255,255,.12); --muted:#a1a1aa; --text:#f8fafc; --mint:#00e6c3; --steel:#91a7ff; --gold:#f6c66a; }
    * { box-sizing:border-box; }
    body { margin:0; min-height:100vh; background:var(--bg); color:var(--text); font-family:Inter,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }
    body::before { content:""; position:fixed; inset:0; pointer-events:none; background:linear-gradient(180deg, rgba(255,255,255,.035), transparent 260px), radial-gradient(circle at 50% -12%, rgba(145,167,255,.18), transparent 34%), radial-gradient(circle at 82% 18%, rgba(0,230,195,.10), transparent 24%); }
    body::after { content:"Z"; position:fixed; left:50%; top:50%; transform:translate(-50%,-50%); z-index:0; pointer-events:none; color:rgba(255,255,255,.026); font-size:min(58vw,720px); font-weight:900; line-height:.8; text-shadow:0 0 120px rgba(0,230,195,.10); }
    a { color:inherit; }
    .nav { position:sticky; top:0; z-index:20; min-height:74px; padding:12px 32px; display:flex; align-items:center; justify-content:space-between; gap:18px; border-bottom:1px solid var(--line); background:rgba(6,7,10,.86); backdrop-filter:blur(18px); }
    .brand { display:flex; align-items:center; gap:12px; font-weight:900; letter-spacing:3px; }
    .mark-small { width:34px; height:34px; flex:0 0 auto; }
    .nav-actions { display:flex; gap:10px; align-items:center; flex-wrap:wrap; justify-content:flex-end; }
    .nav a, .nav button { color:white; text-decoration:none; border:1px solid var(--line); background:rgba(255,255,255,.04); padding:10px 14px; border-radius:8px; font-size:13px; font-weight:800; cursor:pointer; font-family:inherit; }
    .nav a:hover, .nav button:hover { border-color:rgba(0,230,195,.42); }
    .owner-pill { color:#ffe1a1 !important; border-color:rgba(246,198,106,.45) !important; }
    .shell { position:relative; z-index:1; width:min(1180px, calc(100% - 40px)); margin:0 auto; padding:28px 0 38px; }
    .hero { position:relative; min-height:58vh; display:flex; align-items:center; justify-content:center; text-align:center; overflow:hidden; border:1px solid rgba(255,255,255,.08); border-radius:18px; background:linear-gradient(180deg, rgba(255,255,255,.04), rgba(255,255,255,.018)); }
    .hero-mark { position:absolute; inset:0; display:grid; place-items:center; opacity:.30; pointer-events:none; }
    .hero-mark img { width:min(72vw,760px); height:auto; filter:drop-shadow(0 40px 90px rgba(0,230,195,.10)); }
    .hero-content { position:relative; z-index:2; width:min(850px, calc(100% - 32px)); padding:52px 0; }
    .eyebrow { display:inline-flex; color:#d7defe; border:1px solid rgba(145,167,255,.28); background:rgba(145,167,255,.08); padding:8px 11px; border-radius:999px; font-size:11px; font-weight:900; letter-spacing:1.4px; text-transform:uppercase; }
    h1 { margin:18px 0 14px; font-size:64px; line-height:.92; letter-spacing:0; }
    .lead { color:#d4d4d8; line-height:1.68; font-size:17px; margin:0 auto 20px; max-width:720px; word-break:keep-all; }
    .actions { display:flex; gap:12px; flex-wrap:wrap; margin-bottom:28px; justify-content:center; }
    .cta { min-height:46px; display:inline-flex; align-items:center; justify-content:center; padding:0 18px; border-radius:8px; text-decoration:none; font-size:14px; font-weight:900; border:0; cursor:pointer; font-family:inherit; }
    .cta.main { background:white; color:#050507; }
    .cta.trade { background:var(--mint); color:#03100d; }
    .cta.sub { color:white; background:rgba(255,255,255,.04); border:1px solid var(--line); }
    .trust, .pricing { display:grid; grid-template-columns:repeat(3, minmax(0,1fr)); gap:10px; max-width:880px; margin:0 auto; text-align:left; }
    .trust div, .price-card { border:1px solid var(--line); background:rgba(255,255,255,.035); border-radius:8px; padding:13px; }
    .trust strong, .price-card strong { display:block; font-size:13px; margin-bottom:5px; }
    .trust span, .price-card p { color:var(--muted); font-size:12px; line-height:1.5; margin:0; }
    .price-card .price { color:var(--mint); font-size:17px; font-weight:900; margin:7px 0; }
    .preview-band { margin-top:14px; display:grid; grid-template-columns:1fr 1fr; gap:14px; }
    .visual-panel { min-height:220px; border:1px solid var(--line); border-radius:10px; padding:16px; background:#090b10; position:relative; overflow:hidden; }
    .floor { position:absolute; inset:58px 24px 24px; border:2px solid rgba(0,230,195,.65); transform:perspective(720px) rotateX(58deg) rotateZ(-8deg); transform-origin:center; }
    .floor span { position:absolute; border:1px solid rgba(145,167,255,.45); background:rgba(255,255,255,.04); }
    .floor span:nth-child(1){ left:8%; top:8%; width:42%; height:38%; }
    .floor span:nth-child(2){ left:54%; top:8%; width:36%; height:28%; }
    .floor span:nth-child(3){ left:8%; top:52%; width:32%; height:34%; }
    .floor span:nth-child(4){ left:45%; top:44%; width:45%; height:42%; }
    .signal-list { position:absolute; left:18px; right:18px; bottom:18px; display:grid; gap:8px; }
    .signal-row { display:grid; grid-template-columns:1fr auto; gap:12px; padding:10px; border-radius:8px; background:rgba(255,255,255,.045); border:1px solid rgba(255,255,255,.08); font-size:13px; }
    .signal-row b { color:#99f6e4; }
    .visual-panel h3 { margin:0; position:relative; z-index:2; }
    .visual-panel p { color:#a1a1aa; position:relative; z-index:2; font-size:13px; line-height:1.55; max-width:420px; word-break:keep-all; }
    .products { display:grid; grid-template-columns:1fr 1fr; gap:14px; margin-top:28px; }
    .product { border:1px solid var(--line); background:rgba(255,255,255,.035); border-radius:10px; padding:20px; }
    .product .kicker { color:#cbd5e1; font-size:11px; font-weight:900; letter-spacing:1.4px; text-transform:uppercase; }
    .product h3 { margin:10px 0 8px; font-size:24px; letter-spacing:0; }
    .product p { margin:0 0 16px; color:#b8bcc7; line-height:1.65; font-size:14px; word-break:keep-all; }
    .chips { display:flex; flex-wrap:wrap; gap:7px; margin-bottom:16px; }
    .chips span { color:#e5e7eb; border:1px solid rgba(255,255,255,.10); background:rgba(255,255,255,.04); padding:7px 9px; border-radius:7px; font-size:12px; font-weight:800; }
    .section-title { margin:30px 0 12px; font-size:18px; font-weight:900; }
    .policy { margin:20px 0; color:#8f96a3; font-size:12px; line-height:1.65; word-break:keep-all; }
    .modal { display:none; position:fixed; inset:0; z-index:50; background:rgba(0,0,0,.72); align-items:center; justify-content:center; padding:24px; }
    .modal.open { display:flex; }
    .modal-card { width:min(760px,100%); background:#101014; border:1px solid var(--line); border-radius:10px; padding:28px; box-shadow:0 30px 80px rgba(0,0,0,.45); }
    .modal-head { display:flex; justify-content:space-between; gap:16px; align-items:start; margin-bottom:16px; }
    .modal h2 { margin:0; font-size:28px; }
    .close { width:36px; height:36px; border:1px solid var(--line); background:#17171d; color:white; border-radius:8px; cursor:pointer; font-weight:900; }
    .modal p, .modal li { color:#d4d4d8; line-height:1.8; word-break:keep-all; }
    @media (max-width:900px) {
      .nav { padding:12px 18px; }
      .brand span { display:none; }
      .shell { width:min(100% - 28px,1180px); padding-top:34px; }
      .hero { min-height:auto; }
      .hero-content { padding:52px 0; }
      h1 { font-size:46px; }
      .trust, .products, .pricing, .preview-band { grid-template-columns:1fr; }
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
    <div class="nav-actions" id="nav-actions">
      <a href="customer.html">고객센터</a>
      <a href="login.html">로그인</a>
    </div>
  </nav>

  <main class="shell">
    <section class="hero">
      <div class="hero-mark"><img src="/static/zenthex-mark.svg" alt="" /></div>
      <div class="hero-content">
        <span class="eyebrow">AI Studio + Signal Guard SaaS</span>
        <h1>Zenthex</h1>
        <p class="lead">Zenthex는 프롬프트와 2D 도면을 3D 공간으로 변환하는 AI 스튜디오와, 사용자 설정 기반 자동매매 엔진을 제공하는 구독형 SaaS 플랫폼입니다.</p>
        <div class="actions">
          <a class="cta main" href="studio.html">Studio 열기</a>
          <a class="cta trade" href="finance.html">Trading 열기</a>
          <a class="cta sub" href="#pricing">구독 가격</a>
          <button class="cta sub" type="button" onclick="openModal('platform-modal')">Zenthex란?</button>
        </div>
        <div class="trust">
          <div><strong>Studio 체험</strong><span>비로그인도 하루 1회 보기 전용 체험 후 구독을 선택할 수 있습니다.</span></div>
          <div><strong>Trading 보호</strong><span>체험 화면에서는 API 키를 받지 않고, 실거래는 구독 권한 뒤에만 열립니다.</span></div>
          <div><strong>SaaS 운영</strong><span>계정, 구독, 결제내역, 영수증과 고객 지원을 한 흐름으로 관리합니다.</span></div>
        </div>
      </div>
    </section>

    <section class="preview-band">
      <article class="visual-panel">
        <h3>Zenthex Studio Preview</h3>
        <p>프롬프트와 도면을 3D 공간으로 바꾸는 흐름을 첫 화면에서 바로 이해할 수 있게 보여줍니다.</p>
        <div class="floor" aria-hidden="true"><span></span><span></span><span></span><span></span></div>
      </article>
      <article class="visual-panel">
        <h3>Zenthex Trading Signals</h3>
        <p>실거래는 로그인, 구독, 키 인증 후 열리고 후보 코인은 서버에서 점수화합니다.</p>
        <div class="signal-list" aria-hidden="true">
          <div class="signal-row"><span>KRW-BTC</span><b>+0.42%</b></div>
          <div class="signal-row"><span>KRW-ETH</span><b>+0.36%</b></div>
          <div class="signal-row"><span>KRW-SOL</span><b>+0.31%</b></div>
        </div>
      </article>
    </section>

    <section class="products">
      <article class="product">
        <span class="kicker">Zenthex Studio</span>
        <h3>프롬프트와 도면을 3D로</h3>
        <p>문장 또는 2D 도면을 기반으로 3D 공간을 미리보고, Studio Pro 또는 Ultimate 구독 후 JPG 저장, GLB 다운로드와 작업 보관을 사용할 수 있습니다.</p>
        <div class="chips"><span>Prompt to 3D</span><span>2D 도면 분석</span><span>JPG 저장</span><span>GLB 3D 모델</span></div>
        <a class="cta main" href="studio.html">Studio 열기</a>
      </article>
      <article class="product">
        <span class="kicker">Zenthex Trading</span>
        <h3>자동매매 구조와 실거래 권한</h3>
        <p>업비트 KRW 마켓의 강한 후보를 필터링하고 단기 신호를 점수화합니다. 실제 주문은 Trading Pro 또는 Ultimate 권한과 위험 동의 후에만 실행합니다.</p>
        <div class="chips"><span>Signal Guard</span><span>Upbit 우선</span><span>API 키 보호</span><span>Binance 확장 예정</span></div>
        <a class="cta trade" href="finance.html">Trading 열기</a>
      </article>
    </section>

    <h2 class="section-title" id="pricing">구독 가격</h2>
    <section class="pricing">
      <article class="price-card"><strong>Studio Pro</strong><div class="price">월 49,000원</div><p>Studio 생성, JPG 저장, GLB 다운로드, 작업 히스토리</p></article>
      <article class="price-card"><strong>Trading Pro</strong><div class="price">월 99,000원</div><p>Trading 실거래 권한, Signal Guard, 목표 수익률 자동 종료</p></article>
      <article class="price-card"><strong>Zenthex Ultimate</strong><div class="price">월 149,000원</div><p>Studio + Trading 통합 권한, 우선 처리, 모바일 알림</p></article>
    </section>

    <p class="policy">Zenthex Trading은 자동매매 도구이며 투자 자문 또는 수익 보장 서비스가 아닙니다. 모든 투자 판단과 손익 책임은 사용자 본인에게 있습니다.</p>
  </main>

  <div class="modal" id="platform-modal">
    <div class="modal-card">
      <div class="modal-head"><h2>Zenthex란?</h2><button class="close" onclick="closeModal('platform-modal')">X</button></div>
      <p>Zenthex는 AI 3D 제작과 자동매매 실행 구조를 하나의 계정, 구독, 모바일 제어 흐름으로 제공하는 SaaS 플랫폼입니다.</p>
      <ul>
        <li>Studio 체험은 보기 전용이며 다운로드는 구독 후 제공합니다.</li>
        <li>Trading 체험은 구조 확인용이며 API 키 입력을 요구하지 않습니다.</li>
        <li>실거래는 로그인, 구독 권한, 위험 동의, API 키 확인 후에만 실행됩니다.</li>
      </ul>
    </div>
  </div>

  <script>
    function openModal(id){ document.getElementById(id).classList.add('open'); }
    function closeModal(id){ document.getElementById(id).classList.remove('open'); }

    let token = localStorage.getItem('zx_token');
    let user = JSON.parse(localStorage.getItem('zx_user') || 'null');
    const navActions = document.getElementById('nav-actions');

    function isOwner(u){ return u && u.role === 'owner'; }

    function clearSession(){
      localStorage.removeItem('zx_token');
      localStorage.removeItem('zx_user');
      localStorage.removeItem('zx_expires_at');
      token=null;
      user=null;
    }

    function renderNav(u){
      if(!u){
        navActions.innerHTML='<a href="customer.html">고객센터</a><a href="login.html">로그인</a>';
        return;
      }
      const ownerLink=isOwner(u)?'<a class="owner-pill" href="admin.html">CEO Dashboard</a>':'';
      navActions.innerHTML=`${ownerLink}<a href="account.html">마이페이지</a><a href="customer.html">고객센터</a><button type="button" onclick="logout()">로그아웃</button>`;
    }

    function logout(){
      clearSession();
      renderNav(null);
    }

    async function refreshUser(){
      const expiresAt=Number(localStorage.getItem('zx_expires_at')||0);
      if(token&&expiresAt&&Date.now()>expiresAt){ clearSession(); renderNav(null); return; }
      if(!token){ renderNav(null); return; }
      if(user){ renderNav(user); }
      try{
        const res=await fetch('/api/auth/me',{headers:{'Authorization':`Bearer ${token}`}});
        if(res.ok){
          user=await res.json();
          localStorage.setItem('zx_user',JSON.stringify(user));
          renderNav(user);
          return;
        }
        if(res.status===401){ clearSession(); }
      }catch(e){ console.error(e); }
      renderNav(user);
    }

    refreshUser();
  </script>
</body>
</html>
