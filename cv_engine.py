<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Zenthex SaaS Platform</title>
  <style>
    :root{--bg:#06070a;--panel:#0b0d12;--line:rgba(255,255,255,.12);--muted:#a1a1aa;--text:#f8fafc;--mint:#00e6c3;--blue:#91a7ff;--gold:#f6c66a;--red:#f87171}
    *{box-sizing:border-box}
    body{margin:0;min-height:100vh;background:var(--bg);color:var(--text);font-family:Inter,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
    body:before{content:"";position:fixed;inset:0;pointer-events:none;background:linear-gradient(180deg,rgba(255,255,255,.04),transparent 280px),radial-gradient(circle at 45% -12%,rgba(145,167,255,.18),transparent 34%),radial-gradient(circle at 86% 18%,rgba(0,230,195,.10),transparent 24%)}
    body:after{content:"Z";position:fixed;left:50%;top:50%;transform:translate(-50%,-50%);z-index:0;pointer-events:none;color:rgba(255,255,255,.026);font-size:min(58vw,720px);font-weight:900;line-height:.8}
    a{color:inherit;text-decoration:none}
    .nav{position:sticky;top:0;z-index:20;min-height:74px;padding:12px 32px;display:flex;align-items:center;justify-content:space-between;gap:18px;border-bottom:1px solid var(--line);background:rgba(6,7,10,.86);backdrop-filter:blur(18px)}
    .brand{display:flex;align-items:center;gap:12px;font-weight:900;letter-spacing:3px}
    .brand img{width:34px;height:34px}
    .nav-actions{display:flex;gap:10px;align-items:center;flex-wrap:wrap;justify-content:flex-end}
    .nav a,.nav button{color:white;border:1px solid var(--line);background:rgba(255,255,255,.04);padding:10px 14px;border-radius:8px;font-size:13px;font-weight:800;cursor:pointer;font-family:inherit}
    .nav a:hover,.nav button:hover{border-color:rgba(0,230,195,.42)}
    .owner-pill{color:#ffe1a1!important;border-color:rgba(246,198,106,.45)!important}
    .shell{position:relative;z-index:1;width:min(1180px,calc(100% - 40px));margin:0 auto;padding:28px 0 42px}
    .hero{position:relative;min-height:56vh;display:flex;align-items:center;justify-content:center;text-align:center;overflow:hidden;border:1px solid rgba(255,255,255,.08);border-radius:18px;background:linear-gradient(180deg,rgba(255,255,255,.045),rgba(255,255,255,.018))}
    .hero-mark{position:absolute;inset:0;display:grid;place-items:center;opacity:.28;pointer-events:none}
    .hero-mark img{width:min(72vw,760px);height:auto;filter:drop-shadow(0 40px 90px rgba(0,230,195,.10))}
    .hero-content{position:relative;z-index:2;width:min(900px,calc(100% - 32px));padding:52px 0}
    .eyebrow{display:inline-flex;color:#d7defe;border:1px solid rgba(145,167,255,.28);background:rgba(145,167,255,.08);padding:8px 11px;border-radius:999px;font-size:11px;font-weight:900;letter-spacing:1.4px;text-transform:uppercase}
    h1{margin:18px 0 14px;font-size:64px;line-height:.92;letter-spacing:0}
    .lead{color:#d4d4d8;line-height:1.68;font-size:17px;margin:0 auto 22px;max-width:760px;word-break:keep-all}
    .actions{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:28px;justify-content:center}
    .cta{min-height:46px;display:inline-flex;align-items:center;justify-content:center;padding:0 18px;border-radius:8px;font-size:14px;font-weight:900;border:0;cursor:pointer;font-family:inherit}
    .cta.main{background:white;color:#050507}
    .cta.trade{background:var(--mint);color:#03100d}
    .cta.stock{background:var(--gold);color:#11100a}
    .cta.sub{color:white;background:rgba(255,255,255,.04);border:1px solid var(--line)}
    .trust,.pricing{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;max-width:920px;margin:0 auto;text-align:left}
    .trust div,.price-card{border:1px solid var(--line);background:rgba(255,255,255,.035);border-radius:8px;padding:13px}
    .trust strong,.price-card strong{display:block;font-size:13px;margin-bottom:5px}
    .trust span,.price-card p{color:var(--muted);font-size:12px;line-height:1.5;margin:0;word-break:keep-all}
    .price-card .price{color:var(--mint);font-size:17px;font-weight:900;margin:7px 0}
    .preview-band{margin-top:14px;display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}
    .visual-panel{min-height:230px;border:1px solid var(--line);border-radius:10px;padding:16px;background:#090b10;position:relative;overflow:hidden}
    .visual-panel h3{margin:0;position:relative;z-index:2}
    .visual-panel p{color:#a1a1aa;position:relative;z-index:2;font-size:13px;line-height:1.55;word-break:keep-all}
    .floor{position:absolute;inset:64px 24px 24px;border:2px solid rgba(0,230,195,.65);transform:perspective(720px) rotateX(58deg) rotateZ(-8deg);transform-origin:center}
    .floor span{position:absolute;border:1px solid rgba(145,167,255,.45);background:rgba(255,255,255,.04)}
    .floor span:nth-child(1){left:8%;top:8%;width:42%;height:38%}
    .floor span:nth-child(2){left:54%;top:8%;width:36%;height:28%}
    .floor span:nth-child(3){left:8%;top:52%;width:32%;height:34%}
    .floor span:nth-child(4){left:45%;top:44%;width:45%;height:42%}
    .signal-list{position:absolute;left:18px;right:18px;bottom:18px;display:grid;gap:8px}
    .signal-row{display:grid;grid-template-columns:1fr auto;gap:12px;padding:10px;border-radius:8px;background:rgba(255,255,255,.045);border:1px solid rgba(255,255,255,.08);font-size:13px}
    .signal-row b{color:#99f6e4}
    .stock-bars{position:absolute;left:18px;right:18px;bottom:18px;display:grid;gap:9px}
    .stock-row{display:grid;grid-template-columns:1fr auto;gap:10px;align-items:center;padding:10px;border-radius:8px;background:rgba(246,198,106,.07);border:1px solid rgba(246,198,106,.18);font-size:13px}
    .stock-row b{color:#ffe1a1}
    .products{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px;margin-top:28px}
    .product{border:1px solid var(--line);background:rgba(255,255,255,.035);border-radius:10px;padding:20px}
    .product .kicker{color:#cbd5e1;font-size:11px;font-weight:900;letter-spacing:1.4px;text-transform:uppercase}
    .product h3{margin:10px 0 8px;font-size:24px;letter-spacing:0}
    .product p{margin:0 0 16px;color:#b8bcc7;line-height:1.65;font-size:14px;word-break:keep-all}
    .chips{display:flex;flex-wrap:wrap;gap:7px;margin-bottom:16px}
    .chips span{color:#e5e7eb;border:1px solid rgba(255,255,255,.10);background:rgba(255,255,255,.04);padding:7px 9px;border-radius:7px;font-size:12px;font-weight:800}
    .section-title{margin:30px 0 12px;font-size:18px;font-weight:900}
    .policy{margin:20px 0;color:#9aa1ad;font-size:12px;line-height:1.65;word-break:keep-all}
    .modal{display:none;position:fixed;inset:0;z-index:50;background:rgba(0,0,0,.72);align-items:center;justify-content:center;padding:24px}
    .modal.open{display:flex}
    .modal-card{width:min(760px,100%);background:#101014;border:1px solid var(--line);border-radius:10px;padding:28px;box-shadow:0 30px 80px rgba(0,0,0,.45)}
    .modal-head{display:flex;justify-content:space-between;gap:16px;align-items:start;margin-bottom:16px}
    .modal h2{margin:0;font-size:28px}
    .close{width:36px;height:36px;border:1px solid var(--line);background:#17171d;color:white;border-radius:8px;cursor:pointer;font-weight:900}
    .modal p,.modal li{color:#d4d4d8;line-height:1.8;word-break:keep-all}
    @media(max-width:980px){.nav{padding:12px 18px}.brand span{display:none}.shell{width:min(100% - 28px,1180px);padding-top:28px}.hero{min-height:auto}.hero-content{padding:48px 0}h1{font-size:46px}.trust,.products,.pricing,.preview-band{grid-template-columns:1fr}.hero-mark img{width:120vw}}
  </style>
</head>
<body>
  <nav class="nav">
    <div class="brand">
      <img src="/static/zenthex-mark.svg" alt="" />
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
        <span class="eyebrow">Studio + Trading + Stock SaaS</span>
        <h1>Zenthex</h1>
        <p class="lead">Zenthex는 AI 건축/3D 스튜디오, 코인 자동매매, 주식 장기·전략 투자를 하나의 계정과 구독 구조로 연결하는 SaaS 플랫폼입니다.</p>
        <div class="actions">
          <a class="cta main" href="studio.html">Studio 열기</a>
          <a class="cta trade" href="finance.html">Trading 열기</a>
          <a class="cta stock" href="stock.html">Stock 열기</a>
          <a class="cta sub" href="#pricing">구독 가격</a>
          <button class="cta sub" type="button" onclick="openModal('platform-modal')">Zenthex란?</button>
        </div>
        <div class="trust">
          <div><strong>Studio</strong><span>프롬프트와 2D 도면을 건축형 3D 이미지와 모델 결과로 확장합니다.</span></div>
          <div><strong>Trading</strong><span>상승 확인 조건을 통과한 코인만 검토하고, 손절선과 익절선을 기준으로 자동 관리합니다.</span></div>
          <div><strong>Stock</strong><span>단기 추격보다 저평가, 성장성, 호재, 장기 흐름을 함께 보는 주식 라인입니다.</span></div>
        </div>
      </div>
    </section>

    <section class="preview-band">
      <article class="visual-panel">
        <h3>Zenthex Studio Preview</h3>
        <p>문장과 도면을 공간 이미지로 바꾸는 AI 스튜디오입니다. 현재는 Google AI/Gemini 기반 이미지 결과를 우선 보여주고, GLB/OBJ는 3D Worker 단계에서 확장합니다.</p>
        <div class="floor" aria-hidden="true"><span></span><span></span><span></span><span></span></div>
      </article>
      <article class="visual-panel">
        <h3>Zenthex Trading Signals</h3>
        <p>코인 자동매매는 수익 보장이 아니라 리스크 제한형 도구입니다. 하락 중인 코인을 피하고 상승 확인, 거래량, 호가, 손절 쿨다운을 함께 봅니다.</p>
        <div class="signal-list" aria-hidden="true">
          <div class="signal-row"><span>KRW-XRP</span><b>상승 후보</b></div>
          <div class="signal-row"><span>KRW-ETH</span><b>거래량 확인</b></div>
          <div class="signal-row"><span>KRW-SOL</span><b>진입 대기</b></div>
        </div>
      </article>
      <article class="visual-panel">
        <h3>Zenthex Stock Outlook</h3>
        <p>주식은 코인과 다르게 장기 가치와 기업 흐름을 봅니다. 실적, 성장성, 저평가, 산업 호재, 시장 분위기를 기반으로 별도 엔진을 설계합니다.</p>
        <div class="stock-bars" aria-hidden="true">
          <div class="stock-row"><span>저평가 성장주</span><b>장기 감시</b></div>
          <div class="stock-row"><span>호재·실적 개선</span><b>후보 편입</b></div>
          <div class="stock-row"><span>과열·악재</span><b>진입 보류</b></div>
        </div>
      </article>
    </section>

    <section class="products">
      <article class="product">
        <span class="kicker">Zenthex Studio</span>
        <h3>건축 AI 스튜디오</h3>
        <p>대한민국 32평 아파트, 카페, 사무실 같은 프롬프트를 기반으로 공간 이미지를 만들고, 향후 2D 도면 분석과 3D 모델 변환으로 확장합니다.</p>
        <div class="chips"><span>Prompt to Image</span><span>2D 도면</span><span>JPG 저장</span><span>GLB 확장</span></div>
        <a class="cta main" href="studio.html">Studio 열기</a>
      </article>
      <article class="product">
        <span class="kicker">Zenthex Trading</span>
        <h3>코인 자동매매</h3>
        <p>Upbit, Bithumb, Binance를 목표로 상승 확인 조건을 통과한 코인만 검토합니다. 하락 중인 코인 진입을 막고 목표 익절과 손절선을 적용합니다.</p>
        <div class="chips"><span>Upbit</span><span>Bithumb</span><span>Binance 준비</span><span>손절/익절</span></div>
        <a class="cta trade" href="finance.html">Trading 열기</a>
      </article>
      <article class="product">
        <span class="kicker">Zenthex Stock</span>
        <h3>주식 전략 투자</h3>
        <p>주식은 단타만 보지 않고 미래 성장성, 저평가, 호재, 실적 개선, 장기 추세를 함께 봅니다. 첫 목표는 한국투자증권 API 기반 모의투자입니다.</p>
        <div class="chips"><span>장기 투자</span><span>저평가</span><span>호재 분석</span><span>Paper Trading</span></div>
        <a class="cta stock" href="stock.html">Stock 열기</a>
      </article>
    </section>

    <h2 class="section-title" id="pricing">구독 가격</h2>
    <section class="pricing">
      <article class="price-card"><strong>Studio Pro</strong><div class="price">월 49,000원</div><p>Studio 생성, JPG 저장, GLB 다운로드, 작업 히스토리</p></article>
      <article class="price-card"><strong>Trading Pro</strong><div class="price">월 99,000원</div><p>코인 실거래 권한, Signal Guard, 목표 익절/손절 리스크 매니저</p></article>
      <article class="price-card"><strong>Ultimate</strong><div class="price">월 149,000원</div><p>Studio + Trading 통합 권한. Stock은 설계/검증 후 별도 플랜으로 확장</p></article>
    </section>

    <p class="policy">Zenthex Trading과 Zenthex Stock은 자동매매 및 전략 실행 도구이며 투자 자문 또는 수익 보장 서비스가 아닙니다. 모든 투자 판단과 손익 책임은 사용자 본인에게 있습니다.</p>
  </main>

  <div class="modal" id="platform-modal">
    <div class="modal-card">
      <div class="modal-head"><h2>Zenthex란?</h2><button class="close" onclick="closeModal('platform-modal')">X</button></div>
      <p>Zenthex는 하나의 회사 안에서 Studio, Trading, Stock 3개 서비스 라인을 운영하는 AI 기반 SaaS 플랫폼입니다.</p>
      <ul>
        <li>Studio는 건축/공간 시각화 라인입니다.</li>
        <li>Trading은 코인 자동매매와 리스크 관리 라인입니다.</li>
        <li>Stock은 장기 성장성, 저평가, 호재 분석을 포함한 주식 전략 라인입니다.</li>
      </ul>
    </div>
  </div>

  <script>
    function openModal(id){document.getElementById(id).classList.add('open')}
    function closeModal(id){document.getElementById(id).classList.remove('open')}

    let token=localStorage.getItem('zx_token')
    let user=JSON.parse(localStorage.getItem('zx_user')||'null')
    const navActions=document.getElementById('nav-actions')

    function isOwner(u){return u&&u.role==='owner'}
    function clearSession(){localStorage.removeItem('zx_token');localStorage.removeItem('zx_user');localStorage.removeItem('zx_expires_at');token=null;user=null}
    function renderNav(u){
      if(!u){
        navActions.innerHTML='<a href="studio.html">Studio</a><a href="finance.html">Trading</a><a href="stock.html">Stock</a><a href="customer.html">고객센터</a><a href="login.html">로그인</a>'
        return
      }
      const ownerLink=isOwner(u)?'<a class="owner-pill" href="admin.html">CEO Dashboard</a>':''
      navActions.innerHTML=`${ownerLink}<a href="studio.html">Studio</a><a href="finance.html">Trading</a><a href="stock.html">Stock</a><a href="account.html">마이페이지</a><a href="customer.html">고객센터</a><button type="button" onclick="logout()">로그아웃</button>`
    }
    function logout(){clearSession();renderNav(null)}
    async function refreshUser(){
      const expiresAt=Number(localStorage.getItem('zx_expires_at')||0)
      if(token&&expiresAt&&Date.now()>expiresAt){clearSession();renderNav(null);return}
      if(!token){renderNav(null);return}
      if(user)renderNav(user)
      try{
        const res=await fetch('/api/auth/me',{headers:{'Authorization':`Bearer ${token}`}})
        if(res.ok){user=await res.json();localStorage.setItem('zx_user',JSON.stringify(user));renderNav(user);return}
        if(res.status===401)clearSession()
      }catch(e){console.error(e)}
      renderNav(user)
    }
    refreshUser()
  </script>
</body>
</html>
