(()=>{
  'use strict';
  const $=id=>document.getElementById(id), set=(id,value)=>{$(id).textContent=value;};
  const token=()=>localStorage.getItem('zx_token')||'';
  const today=()=>new Intl.DateTimeFormat('sv-SE',{timeZone:'Asia/Seoul',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
  const money=value=>value===null||value===undefined?'미확정':Number(value).toLocaleString('ko-KR',{maximumFractionDigits:0})+'원';
  const amount=value=>value===''?null:Number(value);
  const kinds={income:'수입',expense:'지출',card_purchase:'카드 사용',card_payment:'카드 결제',transfer:'내부이체'};
  const activities={household:'가계',zenthex_business:'젠텍스 사업',betman:'베트맨',other:'기타 활동'};
  let editing=null,items=new Map(),busy=false,loading=false,reloadPending=false,nextOffset=null,lastAuth=token();
  const buttons=()=>['save-entry','refresh','more','export'].map($);
  function authenticated(){
    const auth=token();
    if(!auth){set('notice','로그인하면 본인 가계부를 사용할 수 있습니다.');return null;}
    return auth;
  }
  async function api(path,method='GET',body){
    const auth=authenticated();if(!auth)throw new Error('로그인이 필요합니다.');
    const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),20000);
    try{
      const response=await fetch('/api/household'+path,{method,headers:{Authorization:'Bearer '+auth,'Content-Type':'application/json'},body:body===undefined?undefined:JSON.stringify(body),cache:'no-store',signal:controller.signal});
      if(auth!==token())throw new Error('로그인이 변경됐습니다. 다시 불러오세요.');
      if(!response.ok){
        if(response.status===401){$('login').href='/login.html?next=/household.html';set('login','다시 로그인');throw new Error('로그인이 만료됐습니다. 다시 로그인해주세요.');}
        const data=await response.json().catch(()=>({}));
        throw new Error(typeof data.detail==='string'?data.detail:response.status===422?'날짜·금액과 완료 상태를 확인해주세요.':'요청을 처리하지 못했습니다. 다시 확인해주세요.');
      }
      return await response.json();
    }catch(error){
      if(error.name==='AbortError')throw new Error(method==='GET'?'연결 시간이 초과됐습니다.':'저장 결과를 확인하지 못했습니다. 새로고침해 내역을 먼저 확인하세요.');
      throw error;
    }finally{clearTimeout(timeout);}
  }
  function line(parent,label,value,note=''){
    const row=document.createElement('div');row.className='line';
    const name=document.createElement('span');name.textContent=label;
    const result=document.createElement('span');result.textContent=value;
    row.append(name,result);parent.append(row);
    if(note){const p=document.createElement('p');p.className='muted small';p.textContent=note;parent.append(p);}
  }
  function clearPrivate(){
    for(const id of ['income','expense','net','card-spend','gap'])set(id,'—');
    for(const id of ['entries','categories','side-results','forecast-days'])$(id).replaceChildren();
    set('forecast-note','로그인과 연결을 확인한 뒤 다시 불러오세요.');set('entry-count','');
    items.clear();nextOffset=null;$('more').hidden=true;
    $('settings-form').reset();resetForm();
  }
  function renderSummary(data){
    const actual=data.actual,has=actual.count>0;
    set('income',has?money(actual.income_krw):'기록없음');
    set('expense',has?money(actual.outflow_krw):'기록없음');
    set('net',has?money(actual.net_krw):'기록없음');
    $('net').className=actual.net_krw<0?'negative':'';
    set('card-spend',has?money(actual.card_purchases_krw):'기록없음');
    $('categories').replaceChildren();for(const [category,value] of Object.entries(actual.categories))line($('categories'),category,money(value));
    const settings=data.settings,forecast=data.forecast;
    if(settings){
      $('as-of').value=settings.as_of;$('cash').value=settings.cash_krw;$('reserve').value=settings.reserve_krw??'';
      set('gap',money(forecast.additional_needed_krw));$('gap').className='amount '+(forecast.additional_needed_krw>0?'negative':'');
      set('forecast-note',`잔액 기준일 ${settings.as_of} · 이후 36일의 등록된 확정 예정거래 기준 최소 부족액입니다. `+
        (forecast.unknown_amounts?`금액 미정 ${forecast.unknown_amounts}건 이후는 잔액 미확정입니다. `:'')+
        (!forecast.reserve_entered?'생활비 예비금은 아직 반영하지 않았습니다. ':'')+
        (forecast.overdue_expenses?`기일이 지난 예정 지출 ${forecast.overdue_expenses}건을 첫날에 포함했습니다.`:'')+
        '미등록 지출은 반영되지 않습니다.');
    }else{
      set('gap','설정 필요');set('forecast-note','현재 실제 잔액과 기준일을 입력하면 부족한 날짜를 계산합니다.');$('settings-panel').open=true;
    }
    $('forecast-days').replaceChildren();
    for(const day of forecast.days){
      line($('forecast-days'),day.date,money(day.balance_krw),
        day.income_krw||day.outflow_krw?`예정 입금 ${money(day.income_krw)} · 예정 출금 ${money(day.outflow_krw)}`:'');
    }
    $('side-results').replaceChildren();
    line($('side-results'),'젠텍스 매매',data.trading.count?money(data.trading.realized_pnl_krw):'기록없음');
    for(const activity of ['zenthex_business','betman','other']){
      const result=data.side_activities[activity];line($('side-results'),activities[activity],result.count?money(result.net_krw):'기록없음');
    }
  }
  function resetForm(){
    editing=null;$('entry-form').reset();$('entry-date').value=today();$('kind').value='expense';
    $('entry-status').value='done';$('confirmed').value='true';$('method').value='계좌';
    set('entry-title','내역 입력');set('save-entry','내역 저장');$('cancel-edit').hidden=true;
  }
  function renderEntries(data,append=false){
    if(!append){items.clear();$('entries').replaceChildren();}
    set('entry-count',`${data.total}건`);nextOffset=data.next_offset;$('more').hidden=nextOffset===null;
    if(!data.total){const p=document.createElement('p');p.className='empty';p.textContent='이 달에 등록한 내역이 없습니다.';$('entries').append(p);return;}
    for(const entry of data.entries){
      items.set(entry.id,entry);
      const div=document.createElement('div');div.className='entry';
      const row=document.createElement('div');row.className='row';
      const name=document.createElement('strong');name.textContent=entry.description;
      const value=document.createElement('strong');value.textContent=money(entry.amount_krw);row.append(name,value);div.append(row);
      const note=document.createElement('p');note.textContent=`${entry.date} · ${activities[entry.activity]} · ${kinds[entry.kind]} · ${entry.category} · ${entry.status==='done'?'완료':'예정'}${entry.confirmed?'':' · 미확정'}`;div.append(note);
      const controls=document.createElement('div');controls.className='controls';
      const edit=document.createElement('button');edit.type='button';edit.textContent='수정';edit.addEventListener('click',()=>editItem(entry.id));
      const remove=document.createElement('button');remove.type='button';remove.textContent='삭제';remove.addEventListener('click',()=>removeItem(entry.id));
      controls.append(edit,remove);div.append(controls);$('entries').append(div);
    }
  }
  async function load(append=false){
    if(loading){reloadPending=true;return;}
    if(!authenticated())return;
    loading=true;$('refresh').disabled=true;
    const auth=token(),month=$('month').value;
    try{
      if(append){renderEntries(await api('/entries?month='+month+'&offset='+nextOffset),true);return;}
      set('notice','서버에서 본인 가계부를 불러오고 있습니다.');
      const [data,list]=await Promise.all([api('/summary?month='+month),api('/entries?month='+month)]);
      if(auth!==token()||month!==$('month').value)return;
      renderSummary(data);renderEntries(list);
      set('notice','본인 계정의 가계부를 불러왔습니다. 입력된 내역만 계산하며, 실제 은행 잔액과 대조해주세요.');
      $('login').href='/account.html';set('login','계정');
    }catch(error){clearPrivate();set('notice',error.message);}
    finally{loading=false;$('refresh').disabled=false;if(reloadPending){reloadPending=false;load();}}
  }
  async function mutate(action){
    if(busy||!authenticated())return;
    busy=true;buttons().forEach(button=>{button.disabled=true;});
    try{await action();set('notice','저장했습니다.');await load();}
    catch(error){set('notice',error.message);}
    finally{busy=false;buttons().forEach(button=>{button.disabled=false;});}
  }
  function editItem(id){
    if(busy)return;const entry=items.get(id);if(!entry)return;
    editing=id;
    for(const [field,name] of [['entry-date','date'],['activity','activity'],['kind','kind'],['category','category'],['description','description'],['method','method'],['entry-status','status']])$(field).value=entry[name];
    $('entry-amount').value=entry.amount_krw??'';$('confirmed').value=String(entry.confirmed);
    set('entry-title','내역 수정');set('save-entry','수정 저장');$('cancel-edit').hidden=false;
    $('entry-form').scrollIntoView({behavior:'smooth',block:'start'});
  }
  async function removeItem(id){
    if(busy||!window.confirm('이 내역을 가계부에서 삭제할까요?'))return;
    await mutate(async()=>{await api('/entries/'+id,'DELETE');if(editing===id)resetForm();});
  }
  $('settings-form').addEventListener('submit',event=>{
    event.preventDefault();mutate(()=>api('/settings','PUT',{as_of:$('as-of').value,cash_krw:amount($('cash').value),reserve_krw:amount($('reserve').value)}));
  });
  $('entry-form').addEventListener('submit',event=>{
    event.preventDefault();const data={date:$('entry-date').value,activity:$('activity').value,kind:$('kind').value,
      category:$('category').value.trim(),description:$('description').value.trim(),method:$('method').value.trim(),
      amount_krw:amount($('entry-amount').value),status:$('entry-status').value,confirmed:$('confirmed').value==='true'};
    if(data.amount_krw===null&&data.status==='done'){set('notice','완료한 거래는 실제 금액을 입력하세요.');return;}
    if(data.activity!=='household'&&!['income','expense'].includes(data.kind)){set('notice','별도 활동은 수입 또는 지출로 기록하세요.');return;}
    mutate(async()=>{await api(editing===null?'/entries':'/entries/'+editing,editing===null?'POST':'PUT',data);resetForm();});
  });
  $('export').addEventListener('click',async()=>{
    if(busy||!authenticated())return;
    try{
      const data=await api('/export'),file=new Blob([JSON.stringify(data,null,2)],{type:'application/json'});
      const url=URL.createObjectURL(file),link=document.createElement('a');link.href=url;link.download='zenthex-household.json';
      document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),60000);
      set('export-note','파일을 저장했습니다. 원할 때 이 대화에 첨부해주세요.');
    }catch(error){set('export-note',error.message);}
  });
  $('refresh').addEventListener('click',()=>load());$('month').addEventListener('change',()=>{resetForm();load();});
  $('more').addEventListener('click',()=>load(true));$('cancel-edit').addEventListener('click',resetForm);
  window.addEventListener('storage',()=>{if(lastAuth!==token()){lastAuth=token();clearPrivate();load();}});
  $('month').value=today().slice(0,7);$('as-of').value=today();resetForm();
  if('serviceWorker'in navigator)navigator.serviceWorker.register('/app-sw.js',{scope:'/'}).catch(()=>{});
  load();
})();
