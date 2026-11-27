(()=>{
  'use strict';
  const $=id=>document.getElementById(id);
  const set=(id,value)=>{$(id).textContent=value;};
  const money=value=>Number(value).toLocaleString('ko-KR',{maximumFractionDigits:0})+'원';
  const percent=value=>(Number(value)*100).toFixed(2)+'%';
  const token=()=>localStorage.getItem('zx_token')||'';
  let loading=false, exporting=false, installPrompt=null, preparedExport=null;

  async function request(path,auth){
    const controller=new AbortController();
    const timeout=setTimeout(()=>controller.abort(),20000);
    try{
      const response=await fetch(path,{headers:{Authorization:'Bearer '+auth},cache:'no-store',signal:controller.signal});
      if(!response.ok){const error=new Error('request failed');error.status=response.status;throw error;}
      return await response.json();
    }finally{clearTimeout(timeout);}
  }

  function clearPerformance(message){
    for(const id of ['pnl','count','win','expectancy']) set(id,'—');
    $('pnl').className='amount';set('result',message);set('performance-note','');
    $('trades').replaceChildren();set('trades','기록을 표시할 수 없습니다.');
  }

  function renderPerformance(data){
    const total=Number(data.totalPnlKrw||0);
    set('pnl',money(total));$('pnl').className='amount '+(total<0?'negative':total>0?'positive':'');
    set('count',String(data.tradeCount||0)+'회');
    set('win',data.tradeCount?percent(data.winRate):'—');
    set('expectancy',data.tradeCount?percent(data.expectancyPct):'—');
    set('result',`${data.winCount||0}승 · ${data.lossCount||0}패 · 확정 손익`);
    set('performance-note','과거 거래 성적입니다. 거래 횟수만으로 수익성을 확정할 수 없으며, 자료를 모으려고 실거래를 늘릴 필요는 없습니다.');
    $('trades').replaceChildren();
    if(!data.recentTrades?.length){set('trades','완료된 실거래가 없습니다.');return;}
    for(const trade of data.recentTrades){
      const item=document.createElement('div');item.className='trade';
      const row=document.createElement('div');row.className='row';
      const name=document.createElement('b');name.textContent=String(trade.ticker||'코인');
      const pnl=document.createElement('b');pnl.className=Number(trade.pnlKrw)<0?'negative':'positive';pnl.textContent=money(trade.pnlKrw||0);
      row.append(name,pnl);item.append(row);
      const reason=document.createElement('p');reason.textContent=String(trade.reason||'사유 기록 없음');item.append(reason);
      $('trades').append(item);
    }
  }

  async function refresh(){
    if(loading)return;
    const auth=token();
    $('account').textContent=auth?'계정':'로그인';
    $('account').href=auth?'/account.html':'/login.html?next=/app.html';
    $('share').disabled=$('download').disabled=!auth;
    if(!auth){clearPerformance('로그인하면 본인 성적을 불러옵니다.');set('household-preview','로그인하면 본인 가계부를 확인할 수 있습니다.');set('state','로그인 필요');set('decision','계정에 로그인해주세요.');set('session','로그인이 필요합니다.');return;}
    loading=true;$('refresh').disabled=true;
    set('session','서버에서 본인 현황을 확인하고 있습니다.');
    try{
      const [performance,state,household]=await Promise.allSettled([
        request('/api/finance/performance?mode=real',auth),request('/api/finance/status',auth),request('/api/household/summary',auth)
      ]);
      if(auth!==token()){clearPerformance('로그인이 변경됐습니다. 다시 확인해주세요.');set('household-preview','로그인 후 다시 확인하세요.');set('state','다시 확인');set('decision','로그인이 변경됐습니다.');return;}
      const unauthorized=[performance,state,household].some(result=>result.status==='rejected'&&result.reason.status===401);
      if(unauthorized){clearPerformance('로그인이 만료됐습니다. 다시 로그인해주세요.');set('household-preview','로그인 후 다시 확인하세요.');set('state','로그인 필요');set('decision','새 로그인 후 확인할 수 있습니다.');set('session','계정 메뉴에서 다시 로그인하세요.');$('account').textContent='다시 로그인';$('account').href='/login.html?next=/app.html';$('share').disabled=$('download').disabled=true;return;}
      if(household.status==='fulfilled'&&household.value.settings){
        const data=household.value;
        set('household-preview',`기준일 ${data.settings.as_of} · 가계 잔액 ${money(data.settings.cash_krw)} · 등록한 36일 계획의 최소 부족액 ${money(data.forecast.additional_needed_krw)}. 미등록 지출·미정 금액은 가계부에서 확인하세요.`);
      }else set('household-preview',household.status==='fulfilled'?'현재 실제 잔액과 수입·지출을 입력하면 자금계획을 볼 수 있습니다.':'가계부를 불러오지 못했습니다. 가계부를 열어 연결을 확인하세요.');
      if(performance.status==='fulfilled')renderPerformance(performance.value);
      else clearPerformance('성적 조회 실패 · 연결을 확인하고 새로고침하세요.');
      if(state.status==='fulfilled'){
        const labels={SCANNING:'후보 탐색',IDLE:'대기',BUYING:'매수 처리',HOLDING:'보유 감시',SELLING:'매도 처리',STOPPED:'정지',ERROR:'오류 확인 필요'};
        set('state',labels[state.value.state]||'상태 확인 필요');
        set('decision',state.value.decisionNote||'거래 상세 화면에서 상태를 확인하세요.');
      }else{set('state','조회 실패');set('decision',state.reason.status===403?'이 계정에서 조회할 수 없는 엔진입니다. 트레이딩 화면에서 확인하세요.':'현재 상태를 확인하지 못했습니다. 정지했다고 판단하지 마세요.');}
      const time=new Intl.DateTimeFormat('ko-KR',{timeZone:'Asia/Seoul',hour:'2-digit',minute:'2-digit',second:'2-digit'}).format(new Date());
      set('updated','조회 시각 '+time+' KST · 화면을 열어두면 15초마다 확인');
      set('session',performance.status==='fulfilled'&&state.status==='fulfilled'?'서버 연결 확인 · 본인 계정의 실거래 성적':'일부 정보를 확인하지 못했습니다. 위 실패 안내를 확인하세요.');
    }finally{loading=false;$('refresh').disabled=false;}
  }

  async function exportReport(share){
    if(exporting)return;
    const auth=token();if(!auth){set('share-status','먼저 로그인해주세요.');return;}
    exporting=true;$('share').disabled=$('download').disabled=true;
    set('share-status','본인 거래 자료를 준비하고 있습니다.');
    try{
      if(preparedExport?.auth!==auth){
        const report=await request('/api/finance/analysis-report',auth);
        if(auth!==token())throw new Error('session changed');
        preparedExport={auth,file:new File([JSON.stringify(report,null,2)],'zenthex-trading-report.json',{type:'application/json'})};
      }
      const file=preparedExport.file;
      if(share&&navigator.canShare?.({files:[file]})){
        await navigator.share({files:[file],title:'젠텍스 거래 분석 자료'});
        preparedExport=null;
        set('share-status','공유 메뉴에서 선택한 앱으로 전달했습니다. 이 대화에 첨부됐는지 확인해주세요.');
      }else{
        const url=URL.createObjectURL(file);const link=document.createElement('a');link.href=url;link.download=file.name;
        document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),60000);
        preparedExport=null;
        set('share-status','파일을 저장한 뒤 ChatGPT 대화의 첨부 버튼으로 올려주세요.');
      }
    }catch(error){set('share-status',error.name==='NotAllowedError'&&preparedExport?'파일 준비가 끝났습니다. 공유하기를 다시 누르거나 파일로 내려받기를 선택하세요.':error.name==='AbortError'?'공유를 취소했거나 연결 시간이 초과됐습니다.':error.status===401?'다시 로그인한 후 공유해주세요.':'파일을 만들지 못했습니다. 연결과 로그인 상태를 확인해주세요.');}
    finally{exporting=false;$('share').disabled=$('download').disabled=!token();}
  }

  $('refresh').addEventListener('click',refresh);
  $('share').addEventListener('click',()=>exportReport(true));
  $('download').addEventListener('click',()=>exportReport(false));
  window.addEventListener('beforeinstallprompt',event=>{event.preventDefault();installPrompt=event;$('install').hidden=false;});
  $('install').addEventListener('click',async()=>{if(installPrompt){await installPrompt.prompt();installPrompt=null;$('install').hidden=true;}});
  if(window.matchMedia('(display-mode: standalone)').matches||navigator.standalone)set('install-note','홈 화면 앱으로 실행 중입니다.');
  if('serviceWorker'in navigator)navigator.serviceWorker.register('/app-sw.js',{scope:'/'}).catch(()=>{set('install-note','홈 화면에 추가할 수 있습니다. 앱 구성 등록은 연결 후 다시 시도됩니다.');});
  document.addEventListener('visibilitychange',()=>{if(!document.hidden)refresh();});
  window.addEventListener('storage',()=>refresh());
  setInterval(()=>{if(!document.hidden)refresh();},15000);
  refresh();
})();
