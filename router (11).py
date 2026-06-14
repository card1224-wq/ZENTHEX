<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Zenthex Login</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800;900&display=swap');
    * { box-sizing: border-box; }
    body { margin:0; min-height:100vh; display:flex; align-items:center; justify-content:center; background:#050507; color:white; font-family:Inter,system-ui,sans-serif; padding:24px; }
    .card { width:min(520px,100%); background:#111116; border:1px solid rgba(255,255,255,.12); border-radius:12px; padding:32px; box-shadow:0 30px 80px rgba(0,0,0,.45); }
    a { color:#a1a1aa; text-decoration:none; font-size:13px; font-weight:800; }
    h1 { margin:16px 0 6px; letter-spacing:4px; font-size:28px; }
    p { color:#a1a1aa; line-height:1.6; margin:0 0 22px; font-size:14px; }
    .tabs { display:grid; grid-template-columns:1fr 1fr; border:1px solid rgba(255,255,255,.1); border-radius:8px; overflow:hidden; margin-bottom:18px; }
    .tab { padding:12px; text-align:center; cursor:pointer; color:#a1a1aa; font-weight:900; background:#0b0b10; }
    .tab.active { color:#04110e; background:#00ffcc; }
    .panel { display:none; }
    .panel.active { display:block; }
    label { display:block; color:#d4d4d8; font-size:13px; font-weight:800; margin:14px 0 7px; }
    input, select { width:100%; padding:13px; border-radius:8px; border:1px solid rgba(255,255,255,.14); background:#060609; color:white; font-size:15px; }
    button.submit { width:100%; margin-top:18px; padding:14px; border:0; border-radius:8px; background:#00ffcc; color:#04110e; font-weight:900; cursor:pointer; }
    .link-row { display:flex; justify-content:center; gap:12px; margin-top:14px; flex-wrap:wrap; }
    .link-row button { background:none; border:0; color:#a1a1aa; font-weight:800; cursor:pointer; }
    .inline-actions { display:grid; grid-template-columns:1fr auto; gap:8px; align-items:center; }
    .mini { padding:12px 14px; border:0; border-radius:8px; background:#24242c; color:white; font-weight:900; cursor:pointer; white-space:nowrap; }
    .err { color:#ff6b6b; min-height:18px; margin-top:10px; font-size:13px; text-align:center; line-height:1.5; }
    .ok { color:#00ffcc; min-height:18px; margin-top:10px; font-size:13px; text-align:center; line-height:1.5; }
    .muted { color:#71717a; font-size:12px; margin-top:6px; line-height:1.5; }
  </style>
</head>
<body>
  <div class="card">
    <a href="index.html">← 메인으로</a>
    <h1>ZENTHEX</h1>
    <p>이메일 주소로 로그인합니다. 비밀번호를 잊은 경우 힌트 질문 또는 인증 코드로 새 비밀번호를 만들 수 있습니다.</p>

    <div class="tabs">
      <div class="tab active" onclick="switchTab('login')">로그인</div>
      <div class="tab" onclick="switchTab('signup')">회원가입</div>
    </div>

    <section id="login-panel" class="panel active">
      <label>이메일</label>
      <input type="email" id="login-email" placeholder="example@zenthex.com" />
      <label>비밀번호</label>
      <input type="password" id="login-password" />
      <button class="submit" onclick="doLogin()">로그인</button>
      <div class="link-row">
        <button onclick="findId()">아이디 찾기</button>
        <button onclick="requestReset()">비밀번호 찾기</button>
      </div>
      <div id="login-error" class="err"></div>
      <div id="login-ok" class="ok"></div>
    </section>

    <section id="signup-panel" class="panel">
      <label>이름</label>
      <input id="signup-name" placeholder="홍길동" />
      <label>이메일</label>
      <input type="email" id="signup-email" placeholder="example@zenthex.com" />
      <label>비밀번호</label>
      <input type="password" id="signup-password" />
      <label>비밀번호 확인</label>
      <input type="password" id="signup-password-confirm" />
      <label>생년월일</label>
      <input type="date" id="signup-birth-date" />
      <p class="muted">본인 확인과 결제 계정 관리를 위해 생년월일을 입력합니다.</p>
      <label>휴대폰 번호</label>
      <div class="inline-actions">
        <input id="signup-phone" placeholder="01012345678" oninput="phoneVerified=false; document.getElementById('phone-status').innerText='';" />
        <button class="mini" onclick="sendPhoneCode()">인증코드 받기</button>
      </div>
      <label>휴대폰 인증코드</label>
      <div class="inline-actions">
        <input id="signup-phone-code" placeholder="테스트 코드 122492" />
        <button class="mini" onclick="verifyPhoneCode()">인증 확인</button>
      </div>
      <div id="phone-status" class="ok"></div>
      <label>비밀번호 힌트 질문</label>
      <select id="signup-hint-question">
        <option value="">질문을 선택하세요</option>
        <option value="처음 다닌 초등학교 이름은?">처음 다닌 초등학교 이름은?</option>
        <option value="가장 기억에 남는 여행지는?">가장 기억에 남는 여행지는?</option>
        <option value="처음 키운 반려동물 이름은?">처음 키운 반려동물 이름은?</option>
        <option value="가장 좋아하는 음식은?">가장 좋아하는 음식은?</option>
        <option value="어릴 때 별명은?">어릴 때 별명은?</option>
      </select>
      <label>힌트 답변</label>
      <input id="signup-hint-answer" placeholder="본인만 알 수 있는 답변" />
      <p class="muted">힌트 답변에는 실제 비밀번호를 적지 마세요. 비밀번호 찾기 때 본인 확인용으로만 사용됩니다.</p>
      <button class="submit" onclick="doSignup()">회원가입</button>
      <div id="signup-error" class="err"></div>
    </section>

    <section id="reset-panel" class="panel">
      <label>이메일</label>
      <input type="email" id="reset-email" />
      <label>비밀번호 힌트 질문</label>
      <input id="reset-hint-question" readonly placeholder="이메일 입력 후 질문을 불러오세요" />
      <button class="submit" onclick="loadHintQuestion()">힌트 질문 불러오기</button>
      <div id="hint-answer-box">
        <label>힌트 답변</label>
        <input id="reset-hint-answer" />
        <button class="submit" onclick="checkHintAndSendCode()">힌트 확인 후 코드 받기</button>
      </div>
      <button id="direct-reset-btn" class="submit" style="display:none" onclick="requestResetCodeOnly()">이메일 코드 받기</button>
      <label>재설정 코드</label>
      <input id="reset-code" placeholder="테스트 코드 122492" />
      <label>새 비밀번호</label>
      <input type="password" id="reset-password" />
      <button class="submit" onclick="resetPassword()">비밀번호 변경</button>
      <div class="link-row"><button onclick="switchTab('login')">로그인으로 돌아가기</button></div>
      <div id="reset-msg" class="ok"></div>
    </section>
  </div>

  <script>
    let phoneVerified = false;
    let resetWithoutHint = false;

    function switchTab(tab){
      document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
      document.querySelectorAll('.panel').forEach(p=>p.classList.remove('active'));
      if(tab==='login'){
        document.querySelectorAll('.tab')[0].classList.add('active');
        document.getElementById('login-panel').classList.add('active');
      } else if(tab==='signup') {
        document.querySelectorAll('.tab')[1].classList.add('active');
        document.getElementById('signup-panel').classList.add('active');
      } else {
        document.getElementById('reset-panel').classList.add('active');
      }
    }

    function messageFrom(data,fallback){
      if(!data) return fallback;
      if(typeof data.detail==='string') return data.detail;
      if(Array.isArray(data.detail)) return data.detail.map(item=>item.msg||JSON.stringify(item)).join(' / ');
      return data.message||fallback;
    }

    function showCodeMessage(box, data, fallback){
      box.innerText = data && data.dev_code ? `${data.message || fallback} 테스트 코드: ${data.dev_code}` : messageFrom(data, fallback);
    }

    async function doLogin(){
      const email=document.getElementById('login-email').value.trim();
      const password=document.getElementById('login-password').value;
      const errorDiv=document.getElementById('login-error');
      errorDiv.innerText='';
      if(!email){ errorDiv.innerText='이메일을 입력해주세요.'; return; }
      if(!password){ errorDiv.innerText='비밀번호를 입력해주세요.'; return; }
      try{
        const res=await fetch('/api/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email,password})});
        const data=await res.json().catch(()=>null);
        if(!res.ok) throw new Error(messageFrom(data,'로그인에 실패했습니다.'));
        localStorage.setItem('zx_token',data.access_token);
        localStorage.setItem('zx_user',JSON.stringify(data.user_info));
        localStorage.setItem('zx_expires_at',String(Date.now()+((data.expires_in||86400)*1000)));
        location.href=data.user_info.role==='owner'?'admin.html':'account.html';
      }catch(e){ errorDiv.innerText=e.message; }
    }

    async function doSignup(){
      const full_name=document.getElementById('signup-name').value.trim();
      const email=document.getElementById('signup-email').value.trim();
      const password=document.getElementById('signup-password').value;
      const passwordConfirm=document.getElementById('signup-password-confirm').value;
      const birth_date=document.getElementById('signup-birth-date').value;
      const phone_number=document.getElementById('signup-phone').value.trim();
      const password_hint_question=document.getElementById('signup-hint-question').value;
      const password_hint_answer=document.getElementById('signup-hint-answer').value.trim();
      const errorDiv=document.getElementById('signup-error');
      errorDiv.innerText='';
      if(full_name.length<2){ errorDiv.innerText='이름을 입력해주세요.'; return; }
      if(!email){ errorDiv.innerText='이메일을 입력해주세요.'; return; }
      if(!birth_date){ errorDiv.innerText='생년월일을 입력해주세요.'; return; }
      if(!phone_number){ errorDiv.innerText='휴대폰 번호를 입력해주세요.'; return; }
      if(!phoneVerified){ errorDiv.innerText='휴대폰 인증을 완료해주세요.'; return; }
      if(password.length<6){ errorDiv.innerText='비밀번호는 6자 이상이어야 합니다.'; return; }
      if(password!==passwordConfirm){ errorDiv.innerText='비밀번호 확인이 일치하지 않습니다.'; return; }
      if(!password_hint_question){ errorDiv.innerText='비밀번호 힌트 질문을 선택해주세요.'; return; }
      if(password_hint_answer.length<2){ errorDiv.innerText='힌트 답변을 입력해주세요.'; return; }
      if(password_hint_answer.includes(password)){ errorDiv.innerText='힌트 답변에 비밀번호를 그대로 넣으면 안 됩니다.'; return; }
      try{
        const res=await fetch('/api/auth/signup',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email,password,full_name,birth_date,phone_number,password_hint_question,password_hint_answer})});
        const data=await res.json().catch(()=>null);
        if(!res.ok) throw new Error(messageFrom(data,'회원가입에 실패했습니다.'));
        alert(data.role==='owner' ? '대표 계정 회원가입이 완료되었습니다. 로그인 후 이메일 인증을 진행하세요.' : '회원가입 신청이 접수되었습니다. 대표 승인 후 로그인할 수 있습니다.');
        document.getElementById('login-email').value=email;
        switchTab('login');
      }catch(e){ errorDiv.innerText=e.message||'회원가입에 실패했습니다.'; }
    }

    async function sendPhoneCode(){
      const phone_number=document.getElementById('signup-phone').value.trim();
      const box=document.getElementById('phone-status');
      phoneVerified=false;
      box.innerText='';
      if(!phone_number){ box.innerText='휴대폰 번호를 입력해주세요.'; return; }
      const res=await fetch('/api/auth/phone/send-code',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({phone_number})});
      const data=await res.json().catch(()=>null);
      if(!res.ok){ box.innerText=messageFrom(data,'인증코드 발송에 실패했습니다.'); return; }
      showCodeMessage(box, data, '인증코드를 발송했습니다.');
    }

    async function verifyPhoneCode(){
      const phone_number=document.getElementById('signup-phone').value.trim();
      const code=document.getElementById('signup-phone-code').value.trim();
      const box=document.getElementById('phone-status');
      if(!phone_number || !code){ box.innerText='휴대폰 번호와 인증코드를 입력해주세요.'; return; }
      const res=await fetch('/api/auth/phone/verify',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({phone_number,code})});
      const data=await res.json().catch(()=>null);
      if(!res.ok){ phoneVerified=false; box.innerText=messageFrom(data,'휴대폰 인증에 실패했습니다.'); return; }
      phoneVerified=true;
      box.innerText='휴대폰 인증이 완료되었습니다.';
    }

    async function findId(){
      const email=document.getElementById('login-email').value.trim();
      const box=document.getElementById('login-ok');
      if(!email){ box.innerText='이메일을 입력해주세요.'; return; }
      const res=await fetch('/api/auth/find-id',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email})});
      const data=await res.json().catch(()=>null);
      box.innerText=messageFrom(data,'가입 정보가 있다면 이메일로 안내됩니다.');
    }

    function requestReset(){
      document.getElementById('reset-email').value=document.getElementById('login-email').value.trim();
      document.getElementById('reset-msg').innerText='';
      document.getElementById('reset-hint-question').value='';
      document.getElementById('reset-hint-answer').value='';
      document.getElementById('reset-code').value='';
      document.getElementById('reset-password').value='';
      resetWithoutHint=false;
      document.getElementById('hint-answer-box').style.display='block';
      document.getElementById('direct-reset-btn').style.display='none';
      switchTab('reset');
    }

    async function loadHintQuestion(){
      const email=document.getElementById('reset-email').value.trim();
      const box=document.getElementById('reset-msg');
      box.innerText='';
      if(!email){ box.innerText='이메일을 입력해주세요.'; return; }
      const res=await fetch('/api/auth/password/question',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email})});
      const data=await res.json().catch(()=>null);
      if(!res.ok){ box.innerText=messageFrom(data,'힌트 질문을 찾을 수 없습니다.'); return; }
      document.getElementById('reset-hint-question').value=data.password_hint_question;
      resetWithoutHint=!!data.reset_without_hint;
      document.getElementById('hint-answer-box').style.display=resetWithoutHint?'none':'block';
      document.getElementById('direct-reset-btn').style.display=resetWithoutHint?'block':'none';
      box.innerText=resetWithoutHint?'기존 계정입니다. 이메일 코드 받기를 눌러 재설정하세요.':'힌트 질문을 불러왔습니다. 답변을 입력해주세요.';
    }

    async function requestResetCodeOnly(){
      const email=document.getElementById('reset-email').value.trim();
      const box=document.getElementById('reset-msg');
      if(!email){ box.innerText='이메일을 입력해주세요.'; return; }
      const res=await fetch('/api/auth/password/request-reset',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email})});
      const data=await res.json().catch(()=>null);
      showCodeMessage(box, data, res.ok?'재설정 코드를 발송했습니다.':'재설정 코드 발송 실패');
    }

    async function checkHintAndSendCode(){
      if(resetWithoutHint){ await requestResetCodeOnly(); return; }
      const email=document.getElementById('reset-email').value.trim();
      const password_hint_question=document.getElementById('reset-hint-question').value;
      const password_hint_answer=document.getElementById('reset-hint-answer').value.trim();
      const box=document.getElementById('reset-msg');
      box.innerText='';
      if(!email){ box.innerText='이메일을 입력해주세요.'; return; }
      if(!password_hint_question){ box.innerText='힌트 질문을 먼저 불러와주세요.'; return; }
      if(!password_hint_answer){ box.innerText='힌트 답변을 입력해주세요.'; return; }
      const res=await fetch('/api/auth/password/hint',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email,password_hint_question,password_hint_answer})});
      const data=await res.json().catch(()=>null);
      showCodeMessage(box, data, res.ok?'재설정 코드를 발송했습니다.':'힌트 확인 실패');
    }

    async function resetPassword(){
      const email=document.getElementById('reset-email').value.trim();
      const code=document.getElementById('reset-code').value.trim();
      const new_password=document.getElementById('reset-password').value;
      const box=document.getElementById('reset-msg');
      if(!email){ box.innerText='이메일을 입력해주세요.'; return; }
      if(!code){ box.innerText='재설정 코드를 입력해주세요.'; return; }
      if(new_password.length<6){ box.innerText='새 비밀번호는 6자 이상이어야 합니다.'; return; }
      const res=await fetch('/api/auth/password/reset',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email,code,new_password})});
      const data=await res.json().catch(()=>null);
      box.innerText=messageFrom(data,res.ok?'비밀번호가 변경되었습니다.':'비밀번호 변경 실패');
      if(res.ok){
        document.getElementById('login-email').value=email;
        setTimeout(()=>switchTab('login'),900);
      }
    }
  </script>
</body>
</html>
