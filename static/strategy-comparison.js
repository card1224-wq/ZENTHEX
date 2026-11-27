(() => {
  'use strict';
  const get=id=>document.getElementById(id);
  let bars=[], report=null, busy=false;
  const status=text=>{get('compare-status').textContent=text;};
  let source=null;
  get('compare-ticker').addEventListener('input',()=>{bars=[];source=null;invalidate();get('compare-run').disabled=true;status('종목이 변경됐습니다. 자료를 다시 가져오세요.');});
  get('compare-load').addEventListener('click',async()=>{
    if(busy)return;
    const ticker=get('compare-ticker').value.trim().toUpperCase();
    if(!/^KRW-[A-Z0-9]{1,15}$/.test(ticker)){status('KRW-BTC 같은 종목 코드를 입력하세요.');return;}
    busy=true;bars=[];source=null;invalidate();get('compare-run').disabled=true;
    for(const id of ['compare-load','compare-ticker','compare-csv'])get(id).disabled=true;
    status('최근 완료 1분봉 조회 중…');
    const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),60000);
    try{
      const response=await fetch('/api/research/upbit-minutes?ticker='+encodeURIComponent(ticker),{cache:'no-store',signal:controller.signal});
      const data=await response.json();if(!response.ok)throw Error(data.detail||'조회 실패');
      if(data.bars.length<500)throw Error('완료 봉이 500개 미만입니다. 다른 종목 또는 CSV를 사용하세요.');
      bars=data.bars;source=data.source;get('compare-run').disabled=false;status(`${source} · ${bars.length}개 봉. 짧은 예시 기간이며 수익성 검증용으로 충분하지 않습니다.`);
    }catch(error){status(error.name==='AbortError'?'시세 응답 시간이 초과됐습니다.':error.message);}
    finally{clearTimeout(timer);busy=false;for(const id of ['compare-load','compare-ticker','compare-csv'])get(id).disabled=false;}
  });
  function invalidate(){report=null;get('compare-output').hidden=true;get('compare-download').disabled=true;}
  for(const id of ['compare-fee','compare-slip','compare-spread'])get(id).addEventListener('input',()=>{invalidate();status('비용이 변경됐습니다. 다시 비교하세요.');});
  get('compare-csv').addEventListener('change',async()=>{
    bars=[];source=null;invalidate();get('compare-run').disabled=true;
    try{
      const file=get('compare-csv').files[0];if(!file)return;
      if(file.size>5_000_000)throw Error('CSV는 5MB 이하로 올리세요.');
      const lines=(await file.text()).trim().replace(/^\uFEFF/,'').split(/\r?\n/);
      if(lines.shift().trim()!=='time,open,high,low,close,volume')throw Error('헤더는 time,open,high,low,close,volume 입니다.');
      if(lines.length<500||lines.length>20000)throw Error('완료된 1분봉 500~20,000개가 필요합니다.');
      bars=lines.map(line=>{
        const a=line.split(',').map(x=>x.trim());
        if(a.length!==6||a.some(x=>x===''))throw Error('누락된 CSV 값을 확인하세요.');
        const n=a.map(Number);if(n.some(v=>!Number.isFinite(v))||!Number.isSafeInteger(n[0])||n.slice(0,5).some(v=>v<=0)||n[5]<0)throw Error('숫자 형식을 확인하세요.');
        return {time:n[0],open:n[1],high:n[2],low:n[3],close:n[4],volume:n[5]};
      });
      source=file.name;get('compare-run').disabled=false;status(`${file.name} · ${bars.length}개 봉. 업비트의 연속된 완료 1분봉인지 확인하세요.`);
    }catch(error){bars=[];status(error.message);}
  });
  function render(data){
    get('compare-results').replaceChildren();
    for(const row of data.results){
      const section=document.createElement('section'),h=document.createElement('h3');h.textContent=row.label;section.append(h);
      const state=document.createElement('p');state.textContent=`${row.decision} · 실거래 미승인`;section.append(state);
      const wrap=document.createElement('div');wrap.className='result';const table=document.createElement('table');
      const add=values=>{const tr=document.createElement('tr');for(const v of values){const td=document.createElement('td');td.textContent=v===null?'계산 불가':typeof v==='number'?String(Math.round(v*10000)/10000):String(v);tr.append(td);}table.append(tr);};
      add(['지표','앞 70% 연구','뒤 30% 검증','검증 비용 2배']);
      for(const [k,label] of [['returnPct','비용 반영 수익률 %'],['maxDrawdownPct','최대 낙폭 %'],['tradeCount','청산 횟수'],['winRatePct','승률 %'],['averageWinPct','평균 이익 %'],['averageLossPct','평균 손실 %'],['expectancyPct','평균 순수익 %'],['profitFactor','총수익/총손실'],['costRejected','비용으로 진입 제외']])add([label,row.training[k],row.validation[k],row.doubleCostValidation[k]]);
      wrap.append(table);section.append(wrap);get('compare-results').append(section);
    }
    get('compare-assumptions').replaceChildren();for(const text of data.assumptions){const li=document.createElement('li');li.textContent=text;get('compare-assumptions').append(li);}
    get('compare-output').hidden=false;get('compare-download').disabled=false;
  }
  get('compare-run').addEventListener('click',async()=>{
    if(busy||!bars.length)return;
    const fields=['compare-fee','compare-slip','compare-spread'];
    if(fields.some(id=>get(id).value.trim()===''||!get(id).checkValidity())){status('비용 가정 세 항목을 모두 입력하세요.');return;}
    busy=true;invalidate();get('compare-run').disabled=true;
    for(const id of [...fields,'compare-csv','compare-ticker','compare-load'])get(id).disabled=true;
    status('동일 구간과 비용으로 비교 중…');const controller=new AbortController();const timer=setTimeout(()=>controller.abort(),60000);
    try{
      const response=await fetch('/api/research/compare',{method:'POST',cache:'no-store',signal:controller.signal,headers:{'Content-Type':'application/json'},body:JSON.stringify({market:'upbit',feeBps:Number(get(fields[0]).value),slippageBps:Number(get(fields[1]).value),spreadBps:Number(get(fields[2]).value),bars})});
      const data=await response.json();if(!response.ok)throw Error(typeof data.detail==='string'?data.detail:'입력 자료를 확인하세요.');
      report={...data,dataSource:source};render(data);status('비교 완료. 실제 11건 재현이나 수익성 검증 완료를 뜻하지 않습니다.');
    }catch(error){status(error.name==='AbortError'?'응답 시간이 초과됐습니다.':error.message);}
    finally{clearTimeout(timer);busy=false;get('compare-run').disabled=false;for(const id of [...fields,'compare-csv','compare-ticker','compare-load'])get(id).disabled=false;}
  });
  get('compare-download').addEventListener('click',()=>{
    if(!report)return;const url=URL.createObjectURL(new Blob([JSON.stringify(report,null,2)],{type:'application/json'}));
    const a=document.createElement('a');a.href=url;a.download='zenthex-strategy-comparison.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  });
})();
