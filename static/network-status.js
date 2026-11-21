// Server-configured public IPv4; does not infer static allocation from a setting.
(() => {
  const host = document.querySelector('[data-network-status]');
  if (!host) return;
  const text = document.createElement('p');
  const ip = document.createElement('strong');
  const note = document.createElement('p');
  const copy = document.createElement('button');
  const verify = document.createElement('button');
  text.textContent = '거래소 허용 IP · 서버 공인 IPv4: ';
  ip.textContent = '확인 중'; text.append(ip);
  copy.textContent = 'IP 복사'; verify.textContent = '발신 IPv4 비교';
  for (const b of [copy, verify]) { b.type = 'button'; b.style.cssText='padding:8px 12px;margin-right:8px;border:1px solid #64748b;border-radius:6px;color:inherit;background:transparent'; }
  host.append(text, copy, verify, note);
  let address = null;
  copy.disabled = true;
  copy.onclick = async () => {
    if (!address) return;
    try { await navigator.clipboard.writeText(address); note.textContent='IP를 복사했습니다.'; }
    catch (_) { note.textContent='위 IP를 직접 선택해 복사하세요. HTTPS에서는 자동 복사를 사용할 수 있습니다.'; }
  };
  verify.onclick = async () => {
    verify.disabled = true; note.textContent='실제 발신 IPv4 비교 중…';
    try {const r=await fetch('/api/finance/server-ip/verify');const d=await r.json();if(!r.ok)throw Error();note.textContent=d.message || JSON.stringify(d);}
    catch (_) {note.textContent='확인 실패. 서버 연결과 네트워크를 확인하세요.';}
    finally {verify.disabled=false;}
  };
  fetch('/api/finance/server-ip').then(r=>{if(!r.ok)throw Error();return r.json();}).then(d=>{
    address=d.server_ip || null; ip.textContent=address || '미설정';copy.disabled=!address;
    note.textContent='표시값은 서버 설정입니다. 고정 여부는 AWS 고정 IP 연결과 발신 IP 비교로 확인하세요.';
  }).catch(()=>{ip.textContent='조회 실패';note.textContent='FastAPI 서버 연결을 확인하세요.';});
})();
