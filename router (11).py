<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Zenthex Customer Center</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800;900&display=swap');
    * { box-sizing:border-box; }
    body { margin:0; min-height:100vh; background:#06070a; color:white; font-family:Inter,system-ui,sans-serif; padding:24px; }
    .wrap { width:min(1080px,100%); margin:0 auto; }
    .top { display:flex; justify-content:space-between; gap:12px; align-items:center; flex-wrap:wrap; margin-bottom:24px; }
    a, button { font-family:inherit; }
    a { color:#a1a1aa; text-decoration:none; font-weight:900; }
    .card { border:1px solid rgba(255,255,255,.12); background:rgba(255,255,255,.035); border-radius:10px; padding:24px; margin-bottom:14px; }
    h1 { margin:0 0 10px; font-size:34px; letter-spacing:0; }
    h2 { margin:0 0 12px; font-size:20px; }
    p, li { color:#c7c9d1; line-height:1.75; }
    .grid { display:grid; grid-template-columns:1fr 1fr; gap:14px; align-items:start; }
    .pill { display:inline-flex; padding:8px 10px; border-radius:999px; border:1px solid rgba(0,230,195,.35); color:#99f6e4; background:rgba(0,230,195,.08); font-size:12px; font-weight:900; }
    label { display:block; color:#d4d4d8; font-size:13px; font-weight:900; margin:14px 0 7px; }
    input, select, textarea { width:100%; border:1px solid rgba(255,255,255,.14); background:#0b0d12; color:#fff; border-radius:8px; padding:12px; font:inherit; outline:none; }
    textarea { min-height:150px; resize:vertical; }
    input:focus, select:focus, textarea:focus { border-color:#00e6c3; box-shadow:0 0 0 3px rgba(0,230,195,.12); }
    .submit { width:100%; margin-top:16px; border:0; background:#00e6c3; color:#00110e; border-radius:8px; padding:14px 16px; font-weight:900; cursor:pointer; }
    .ghost { border:1px solid rgba(255,255,255,.12); background:rgba(255,255,255,.05); color:#fff; border-radius:8px; padding:10px 12px; font-weight:900; cursor:pointer; }
    .status { margin-top:12px; color:#99f6e4; font-size:13px; font-weight:800; min-height:20px; }
    .ticket { border:1px solid rgba(255,255,255,.1); background:rgba(0,0,0,.24); border-radius:8px; padding:14px; margin-top:10px; }
    .ticket strong { display:block; margin-bottom:5px; }
    .ticket small { color:#8b93a7; }
    @media (max-width:820px){ .grid{grid-template-columns:1fr;} h1{font-size:28px;} body{padding:18px;} }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="top">
      <a href="index.html">Zenthex 메인</a>
      <a href="account.html" id="account-link">마이페이지</a>
    </div>

    <section class="card">
      <span class="pill">Customer Center</span>
      <h1>Zenthex 고객센터</h1>
      <p>계정, 구독, Studio 생성, Trading 및 Upbit 키 문제를 남겨주세요. 접수된 문의는 대표 대시보드에서 확인하고 처리 상태를 관리합니다.</p>
    </section>

    <section class="grid">
      <article class="card">
        <h2>문의 남기기</h2>
        <form id="ticket-form">
          <label for="ticket-email">답변 받을 이메일</label>
          <input id="ticket-email" type="email" placeholder="you@example.com" required />

          <label for="ticket-category">문의 유형</label>
          <select id="ticket-category">
            <option value="account">계정 / 로그인</option>
            <option value="billing">구독 / 결제 / 영수증</option>
            <option value="studio">Zenthex Studio</option>
            <option value="trading">Zenthex Trading / Upbit</option>
            <option value="general">기타 문의</option>
          </select>

          <label for="ticket-title">제목</label>
          <input id="ticket-title" maxlength="160" placeholder="문의 제목을 입력하세요" required />

          <label for="ticket-message">내용</label>
          <textarea id="ticket-message" maxlength="4000" placeholder="문제가 발생한 화면, 입력값, 오류 문구를 함께 적어주시면 더 빠르게 확인할 수 있습니다." required></textarea>

          <button class="submit" type="submit">문의 접수하기</button>
          <div id="ticket-status" class="status"></div>
        </form>
      </article>

      <article class="card">
        <h2>빠른 확인</h2>
        <ul>
          <li>로그인은 이메일 주소로 진행합니다.</li>
          <li>비밀번호 재설정은 힌트 질문과 이메일 인증 코드로 진행합니다.</li>
          <li>Studio 체험은 하루 1회 보기 전용이며, 다운로드는 구독 후 가능합니다.</li>
          <li>Trading 실거래는 로그인 및 구독 권한 또는 대표 권한이 필요합니다.</li>
          <li>Upbit 키는 자산조회와 주문 권한, Zenthex 서버 IP 허용이 필요합니다.</li>
        </ul>
        <button class="ghost" type="button" onclick="loadMyTickets()">내 문의 확인</button>
        <div id="my-ticket-list"></div>
      </article>
    </section>
  </div>

  <script>
    let token=localStorage.getItem('zx_token');
    let user=JSON.parse(localStorage.getItem('zx_user')||'null');
    const expiresAt=Number(localStorage.getItem('zx_expires_at')||0);
    const accountLink=document.getElementById('account-link');
    if(token&&expiresAt&&Date.now()>expiresAt){
      localStorage.removeItem('zx_token');
      localStorage.removeItem('zx_user');
      localStorage.removeItem('zx_expires_at');
      token=null;
      user=null;
    }
    if(!token){
      accountLink.href='login.html';
      accountLink.innerText='로그인';
    }
    if(user&&user.email){
      document.getElementById('ticket-email').value=user.email;
    }

    function headers(){
      const base={'Content-Type':'application/json'};
      if(token)base.Authorization=`Bearer ${token}`;
      return base;
    }

    document.getElementById('ticket-form').addEventListener('submit',async(e)=>{
      e.preventDefault();
      const status=document.getElementById('ticket-status');
      status.innerText='문의 접수 중입니다...';
      const payload={
        email:document.getElementById('ticket-email').value,
        category:document.getElementById('ticket-category').value,
        title:document.getElementById('ticket-title').value,
        message:document.getElementById('ticket-message').value
      };
      try{
        const res=await fetch('/api/support/tickets',{method:'POST',headers:headers(),body:JSON.stringify(payload)});
        const data=await res.json();
        if(!res.ok)throw new Error(data.detail||'문의 접수에 실패했습니다.');
        status.innerText=`문의가 접수되었습니다. 접수번호: #${data.ticket.id}`;
        document.getElementById('ticket-title').value='';
        document.getElementById('ticket-message').value='';
        if(token)loadMyTickets();
      }catch(err){
        status.innerText=err.message;
      }
    });

    async function loadMyTickets(){
      const box=document.getElementById('my-ticket-list');
      if(!token){
        box.innerHTML='<div class="ticket"><strong>로그인이 필요합니다.</strong><small>로그인 후 내 문의 내역을 볼 수 있습니다.</small></div>';
        return;
      }
      box.innerHTML='<div class="ticket"><small>문의 내역을 불러오는 중...</small></div>';
      try{
        const res=await fetch('/api/support/my-tickets',{headers:headers()});
        const data=await res.json();
        if(!res.ok)throw new Error(data.detail||'문의 내역 조회 실패');
        if(!data.tickets.length){
          box.innerHTML='<div class="ticket"><small>아직 접수된 문의가 없습니다.</small></div>';
          return;
        }
        box.innerHTML=data.tickets.map(row=>`<div class="ticket"><strong>#${row.id} ${row.title}</strong><small>${row.category} / ${row.status} / ${row.created_at||''}</small><p>${row.message}</p>${row.admin_reply?`<p><b>답변:</b> ${row.admin_reply}</p>`:''}</div>`).join('');
      }catch(err){
        box.innerHTML=`<div class="ticket"><small>${err.message}</small></div>`;
      }
    }
  </script>
</body>
</html>
