<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Zenthex CEO Dashboard</title>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-[#07070a] text-white min-h-screen p-6">
  <div class="max-w-6xl mx-auto">
    <div class="flex items-center justify-between mb-6 gap-4 flex-wrap">
      <a href="index.html" class="text-sm text-gray-400 hover:text-white font-bold">← 메인으로</a>
      <button onclick="logout()" class="px-4 py-2 rounded-lg bg-white/10 border border-white/10 text-sm font-bold">로그아웃</button>
    </div>

    <header class="p-6 rounded-xl bg-white/[.03] border border-white/10 mb-6 flex justify-between gap-4 flex-wrap items-center">
      <div>
        <p class="text-xs tracking-[.3em] text-red-400 font-black uppercase">Operations Workspace</p>
        <h1 class="text-3xl font-black tracking-tight mt-2">Zenthex CEO Dashboard</h1>
        <p class="text-gray-400 mt-2">운영, 가입자, 구독, 고객 문의, 출시 전 검토, 긴급 정지를 관리합니다.</p>
      </div>
      <div id="system-status" class="px-4 py-2 rounded-lg bg-green-500/15 text-green-300 border border-green-500/40 font-black">SYSTEM ONLINE</div>
    </header>

    <section class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
      <div class="p-5 rounded-xl bg-white/[.03] border border-white/10"><p class="text-gray-500 text-xs font-black uppercase">가입자</p><strong id="stat-users" class="text-4xl mt-2 block">0</strong></div>
      <div class="p-5 rounded-xl bg-white/[.03] border border-white/10"><p class="text-gray-500 text-xs font-black uppercase">유료 사용자</p><strong id="stat-paid" class="text-4xl mt-2 block text-[#00ffcc]">0</strong></div>
      <div class="p-5 rounded-xl bg-white/[.03] border border-white/10"><p class="text-gray-500 text-xs font-black uppercase">예상 MRR</p><strong id="stat-mrr" class="text-4xl mt-2 block">0</strong></div>
      <div class="p-5 rounded-xl bg-white/[.03] border border-white/10"><p class="text-gray-500 text-xs font-black uppercase">실행 봇</p><strong id="stat-bots" class="text-4xl mt-2 block text-amber-300">0</strong></div>
    </section>

    <section class="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-6">
      <div class="lg:col-span-2 p-6 rounded-xl bg-white/[.03] border border-white/10">
        <div class="flex items-center justify-between gap-3 flex-wrap mb-4">
          <h2 class="font-black text-xl">출시 전 검토</h2>
          <button onclick="fetchReview()" class="px-4 py-2 rounded-lg bg-[#00ffcc] text-black text-sm font-black">다시 검사</button>
        </div>
        <div class="grid grid-cols-1 md:grid-cols-[150px_1fr] gap-4 mb-4">
          <div class="p-5 rounded-xl bg-black/30 border border-white/10">
            <p class="text-gray-500 text-xs font-black uppercase">검사 점수</p>
            <strong id="review-score" class="text-4xl mt-2 block">-</strong>
            <p id="review-ready" class="text-xs mt-2 text-gray-400">검사 대기</p>
          </div>
          <div id="review-list" class="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm"></div>
        </div>
        <p class="text-xs text-gray-500 leading-5">자동 검토는 코드와 환경설정 기준입니다. 실제 결제, 실제 문자/메일 발송, 실거래 주문은 별도 운영 테스트가 필요합니다.</p>
      </div>

      <div class="p-6 rounded-xl bg-red-500/[.06] border border-red-500/30">
        <h2 class="text-red-300 font-black text-xl mb-3">GLOBAL KILL SWITCH</h2>
        <p class="text-sm text-gray-400 leading-6 mb-5">전체 트레이딩 엔진의 신규 매매를 즉시 정지합니다. 긴급 상황에서만 사용하세요.</p>
        <button id="btn-kill" onclick="toggleKillSwitch()" class="w-full py-5 rounded-xl bg-red-600 hover:bg-red-500 font-black">ACTIVATE</button>
      </div>
    </section>

    <section class="p-6 rounded-xl bg-white/[.03] border border-white/10 mb-6">
      <div class="flex items-center justify-between gap-3 flex-wrap mb-4">
        <h2 class="font-black text-xl">고객 문의</h2>
        <button onclick="fetchSupportTickets()" class="px-4 py-2 rounded-lg bg-white/10 border border-white/10 text-sm font-bold">새로고침</button>
      </div>
      <div id="support-list" class="space-y-3 text-sm"></div>
    </section>

    <section class="p-6 rounded-xl bg-white/[.03] border border-white/10 mb-6">
      <div class="flex items-center justify-between gap-3 flex-wrap mb-4">
        <h2 class="font-black text-xl">가입자 관리</h2>
        <button onclick="fetchUsers()" class="px-4 py-2 rounded-lg bg-white/10 border border-white/10 text-sm font-bold">새로고침</button>
      </div>
      <div id="user-list" class="space-y-3 text-sm"></div>
    </section>

    <section class="p-6 rounded-xl bg-white/[.03] border border-white/10">
      <h2 class="font-black text-xl mb-4">운영 체크</h2>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm text-gray-300">
        <div class="p-4 bg-black/30 rounded-lg border border-white/10">Studio 사용량과 GPU Queue는 다음 단계에서 연결</div>
        <div class="p-4 bg-black/30 rounded-lg border border-white/10">Trading Signal Guard / 전략 검증 상태 감시</div>
        <div class="p-4 bg-black/30 rounded-lg border border-white/10">대표 계정은 구독 체크 없이 전체 권한</div>
        <div class="p-4 bg-black/30 rounded-lg border border-white/10">사용자는 체험 후 필요한 서비스만 구독 전환</div>
      </div>
    </section>
  </div>

  <script>
    const token=localStorage.getItem('zx_token');
    const user=JSON.parse(localStorage.getItem('zx_user')||'null');
    const expiresAt=Number(localStorage.getItem('zx_expires_at')||0);
    let isKillSwitchActive=false;

    if(token&&expiresAt&&Date.now()>expiresAt){logout();}
    if(!token||!user||user.role!=='owner'){
      alert('운영 권한 로그인이 필요합니다.');
      location.href='login.html';
    }

    function logout(){localStorage.removeItem('zx_token');localStorage.removeItem('zx_user');localStorage.removeItem('zx_expires_at');location.href='index.html'}
    function authHeaders(){return {'Content-Type':'application/json','Authorization':`Bearer ${token}`}}
    function escapeHtml(value){
      return String(value||'').replace(/[&<>"']/g,(ch)=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
    }

    async function fetchStatus(){
      try{
        const res=await fetch('/api/admin/status',{headers:authHeaders()});
        const data=await res.json();
        if(!res.ok)throw new Error(data.detail||'권한 오류');
        document.getElementById('stat-users').innerText=data.total_users;
        document.getElementById('stat-paid').innerText=data.paid_users;
        document.getElementById('stat-mrr').innerText=(data.mrr_krw||0).toLocaleString()+'원';
        document.getElementById('stat-bots').innerText=data.active_finance_bots;
        isKillSwitchActive=data.global_kill_switch;
        updateUI();
      }catch(e){alert(e.message);location.href='login.html'}
    }

    async function fetchReview(){
      const scoreEl=document.getElementById('review-score');
      const readyEl=document.getElementById('review-ready');
      const listEl=document.getElementById('review-list');
      scoreEl.innerText='...';
      readyEl.innerText='검사 중';
      listEl.innerHTML='';
      try{
        const res=await fetch('/api/admin/review',{headers:authHeaders()});
        const data=await res.json();
        if(!res.ok)throw new Error(data.detail||'검사 실패');
        scoreEl.innerText=data.score+'점';
        readyEl.innerText=data.ready?'필수 항목 통과':'필수 항목 보완 필요';
        readyEl.className=data.ready?'text-xs mt-2 text-[#00ffcc]':'text-xs mt-2 text-amber-300';
        listEl.innerHTML=(data.checks||[]).map(item=>{
          const pass=item.status==='pass';
          const color=pass?'border-emerald-500/30 bg-emerald-500/[.06] text-emerald-200':'border-amber-500/30 bg-amber-500/[.06] text-amber-200';
          const label=pass?'PASS':(item.level==='recommended'?'WARN':'FIX');
          const titleKo=item.title_ko||item.title;
          const detailKo=item.detail_ko||item.detail;
          const titleEn=item.title_en&&item.title_en!==titleKo?item.title_en:'';
          const detailEn=item.detail_en&&item.detail_en!==detailKo?item.detail_en:'';
          return `<div class="p-4 rounded-lg border ${color}"><div class="flex justify-between gap-3 mb-2"><div><strong class="block">${escapeHtml(titleKo)}</strong>${titleEn?`<span class="text-[11px] text-gray-400">${escapeHtml(titleEn)}</span>`:''}</div><span class="text-xs font-black">${label}</span></div><p class="text-xs leading-5 text-gray-300">${escapeHtml(detailKo)}</p>${detailEn?`<p class="text-[11px] leading-5 text-gray-500 mt-2">${escapeHtml(detailEn)}</p>`:''}</div>`;
        }).join('');
      }catch(e){scoreEl.innerText='-';readyEl.innerText=e.message;readyEl.className='text-xs mt-2 text-red-300'}
    }

    async function fetchSupportTickets(){
      const box=document.getElementById('support-list');
      box.innerHTML='<div class="text-gray-500">문의 내역을 불러오는 중...</div>';
      try{
        const res=await fetch('/api/support/admin/tickets',{headers:authHeaders()});
        const data=await res.json();
        if(!res.ok)throw new Error(data.detail||'문의 조회 실패');
        if(!data.tickets.length){box.innerHTML='<div class="text-gray-500">접수된 문의가 없습니다.</div>';return;}
        box.innerHTML=data.tickets.map(row=>`<div class="p-4 rounded-lg bg-black/30 border border-white/10">
          <div class="grid grid-cols-1 lg:grid-cols-[1fr_160px] gap-3">
            <div>
              <strong class="block text-white">#${row.id} ${escapeHtml(row.title)}</strong>
              <span class="text-xs text-gray-400">${escapeHtml(row.email)} / ${escapeHtml(row.category)} / ${escapeHtml(row.created_at||'')}</span>
              <p class="mt-3 text-gray-300 leading-6 whitespace-pre-wrap">${escapeHtml(row.message)}</p>
            </div>
            <div>
              <select id="ticket-status-${row.id}" class="w-full bg-black border border-white/10 rounded-lg p-2 mb-2">
                <option value="open" ${row.status==='open'?'selected':''}>접수</option>
                <option value="reviewing" ${row.status==='reviewing'?'selected':''}>확인 중</option>
                <option value="answered" ${row.status==='answered'?'selected':''}>답변 완료</option>
                <option value="closed" ${row.status==='closed'?'selected':''}>종료</option>
              </select>
              <textarea id="ticket-reply-${row.id}" class="w-full min-h-[90px] bg-black border border-white/10 rounded-lg p-2 text-sm" placeholder="대표 메모 또는 답변">${escapeHtml(row.admin_reply||'')}</textarea>
              <button onclick="updateTicket(${row.id})" class="mt-2 w-full px-3 py-2 rounded-lg bg-[#00ffcc] text-black font-black">처리 저장</button>
            </div>
          </div>
        </div>`).join('');
      }catch(e){box.innerHTML=`<div class="text-red-300">${escapeHtml(e.message)}</div>`}
    }

    async function updateTicket(id){
      const status=document.getElementById(`ticket-status-${id}`).value;
      const admin_reply=document.getElementById(`ticket-reply-${id}`).value;
      const res=await fetch(`/api/support/admin/tickets/${id}`,{method:'PATCH',headers:authHeaders(),body:JSON.stringify({status,admin_reply})});
      const data=await res.json().catch(()=>null);
      if(!res.ok){alert((data&&data.detail)||'문의 처리 저장 실패');return;}
      fetchSupportTickets();
    }

    async function fetchUsers(){
      const box=document.getElementById('user-list');
      box.innerHTML='<div class="text-gray-500">불러오는 중...</div>';
      try{
        const res=await fetch('/api/admin/users',{headers:authHeaders()});
        const data=await res.json();
        if(!res.ok)throw new Error(data.detail||'가입자 조회 실패');
        if(!data.users.length){box.innerHTML='<div class="text-gray-500">가입자가 없습니다.</div>';return;}
        box.innerHTML=data.users.map(row=>`<div class="p-4 rounded-lg bg-black/30 border border-white/10 grid grid-cols-1 xl:grid-cols-[1fr_140px_140px_140px_auto] gap-3 items-center"><div><strong class="block text-white">${escapeHtml(row.email)}</strong><span class="text-xs text-gray-400">${escapeHtml(row.full_name||'-')} / 이메일 ${row.email_verified?'인증':'미인증'} / 휴대폰 ${row.phone_verified?'인증':'미인증'} / 가입승인 ${escapeHtml(row.approval_status||'approved')}</span></div><select onchange="changePlan(${row.id},this.value)" class="bg-black border border-white/10 rounded-lg p-2"><option value="free" ${row.plan==='free'?'selected':''}>free</option><option value="studio_pro" ${row.plan==='studio_pro'?'selected':''}>studio_pro</option><option value="trading_pro" ${row.plan==='trading_pro'?'selected':''}>trading_pro</option><option value="ultimate" ${row.plan==='ultimate'?'selected':''}>ultimate</option></select><select onchange="changeRole(${row.id},this.value)" class="bg-black border border-white/10 rounded-lg p-2"><option value="user" ${row.role==='user'?'selected':''}>user</option><option value="admin" ${row.role==='admin'?'selected':''}>admin</option><option value="owner" ${row.role==='owner'?'selected':''}>owner</option></select><select onchange="changeApproval(${row.id},this.value)" class="bg-black border border-white/10 rounded-lg p-2"><option value="pending" ${row.approval_status==='pending'?'selected':''}>승인 대기</option><option value="approved" ${(row.approval_status||'approved')==='approved'?'selected':''}>승인 완료</option><option value="rejected" ${row.approval_status==='rejected'?'selected':''}>거절</option></select><button onclick="deleteUser(${row.id},'${escapeHtml(row.email)}')" class="px-4 py-2 rounded-lg bg-red-600 text-white font-black">삭제</button></div>`).join('');
      }catch(e){box.innerHTML=`<div class="text-red-300">${escapeHtml(e.message)}</div>`}
    }

    async function changePlan(id,plan){await fetch(`/api/admin/users/${id}`,{method:'PATCH',headers:authHeaders(),body:JSON.stringify({plan})});fetchStatus();fetchUsers()}
    async function changeRole(id,role){await fetch(`/api/admin/users/${id}`,{method:'PATCH',headers:authHeaders(),body:JSON.stringify({role})});fetchStatus();fetchUsers()}
    async function changeApproval(id,approval_status){await fetch(`/api/admin/users/${id}`,{method:'PATCH',headers:authHeaders(),body:JSON.stringify({approval_status})});fetchStatus();fetchUsers()}
    async function deleteUser(id,email){if(!confirm(`${email} 계정을 삭제할까요?`))return;const res=await fetch(`/api/admin/users/${id}`,{method:'DELETE',headers:authHeaders()});const data=await res.json().catch(()=>null);if(!res.ok){alert((data&&data.detail)||'삭제 실패');return;}fetchStatus();fetchUsers()}

    async function toggleKillSwitch(){
      const next=!isKillSwitchActive;
      if(next&&!confirm('전체 트레이딩 엔진을 긴급 정지할까요?'))return;
      const res=await fetch('/api/admin/killswitch',{method:'POST',headers:authHeaders(),body:JSON.stringify({enabled:next})});
      const data=await res.json();
      if(!res.ok){alert(data.detail||'실패');return}
      isKillSwitchActive=data.kill_switch_active;
      updateUI();
    }

    function updateUI(){
      const status=document.getElementById('system-status');
      const btn=document.getElementById('btn-kill');
      if(isKillSwitchActive){
        status.innerText='SYSTEM HALTED';
        status.className='px-4 py-2 rounded-lg bg-red-500/15 text-red-300 border border-red-500/50 font-black';
        btn.innerText='RELEASE HALT';
        btn.className='w-full py-5 rounded-xl bg-white text-black font-black';
      }else{
        status.innerText='SYSTEM ONLINE';
        status.className='px-4 py-2 rounded-lg bg-green-500/15 text-green-300 border border-green-500/40 font-black';
        btn.innerText='ACTIVATE';
        btn.className='w-full py-5 rounded-xl bg-red-600 hover:bg-red-500 font-black';
      }
    }

    fetchStatus();
    fetchReview();
    fetchSupportTickets();
    fetchUsers();
    setInterval(fetchStatus,5000);
  </script>
</body>
</html>
