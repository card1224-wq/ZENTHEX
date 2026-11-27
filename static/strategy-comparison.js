(() => {
  'use strict';
  const get=id=>document.getElementById(id);
  let bars=[], report=null, busy=false, dataReady=false, candidate=null, coverage=null;
  const status=text=>{get('compare-status').textContent=text;};
  const reveal=()=>get('compare-status').scrollIntoView?.({behavior:'smooth',block:'center'});
  function clearData(){bars=[];source=null;candidate=null;coverage=null;dataReady=false;invalidate();get('compare-run').disabled=true;get('compare-contiguous').hidden=true;get('compare-coverage').textContent='';}
  function prepareBars(data,label){
    if(data.length<500||data.length>20000)throw Error('완료된 1분봉 500~20,000개가 필요합니다.');
    const segments=[];let start=0,gaps=0;
    for(let i=0;i<data.length;i++){
      if(!Number.isSafeInteger(data[i].time)||data[i].time<=0)throw Error('봉 시작 시각 형식을 확인하세요.');
      if(i&&data[i].time<=data[i-1].time)throw Error('시간 오름차순이며 중복 없는 자료가 필요합니다.');
      if(i&&data[i].time-data[i-1].time!==60000){segments.push(data.slice(start,i));start=i;gaps++;}
    }
    segments.push(data.slice(start));bars=data;source=label;
    coverage={inputBars:data.length,usedBars:data.length,gapCount:gaps,selection:'full'};
    if(gaps){
      candidate=segments.reduce((best,part)=>part.length>best.length?part:best,[]);
      get('compare-coverage').textContent=`전체 ${data.length}개 · 불연속 ${gaps}곳 · 가장 긴 연속 구간 ${candidate.length}개. 누락 봉은 생성하지 않습니다.`;
      if(candidate.length>=500){get('compare-contiguous').hidden=false;get('compare-contiguous').textContent=`연속 ${candidate.length}개 봉만 선택`;status('자료에 빠진 시간이 있어 비교를 보류했습니다. 아래 버튼으로 연속 구간을 선택하면 그 구간만 비교합니다. 전체 기간의 결과가 아닙니다.');}
      else{candidate=null;status('연속 구간이 500개 미만이라 비교할 수 없습니다. 다른 종목이나 더 긴 CSV를 사용하세요.');}
      reveal();return;
    }
    candidate=null;dataReady=true;get('compare-run').disabled=false;
    get('compare-coverage').textContent=`전체 ${data.length}개 봉 사용 · 누락 구간 없음`;
    status(`${label} · ${data.length}개 봉. ‘세 방식 비교’를 누르세요. 짧은 기간만으로 수익성을 판단할 수 없습니다.`);
  }
  get('compare-contiguous').addEventListener('click',()=>{
    if(busy||!candidate)return;
    bars=candidate;candidate=null;coverage={...coverage,usedBars:bars.length,selection:'longest_contiguous'};
    dataReady=true;get('compare-run').disabled=false;get('compare-contiguous').hidden=true;
    const from=new Date(bars[0].time).toLocaleString('ko-KR',{timeZone:'Asia/Seoul'}),to=new Date(bars.at(-1).time).toLocaleString('ko-KR',{timeZone:'Asia/Seoul'});
    get('compare-coverage').textContent=`전체 ${coverage.inputBars}개 중 연속 ${bars.length}개만 사용 · 한국시간 ${from} ~ ${to}. 제외 구간은 계산하지 않습니다.`;
    status('연속 구간을 선택했습니다. ‘세 방식 비교’를 누르세요.');
  });
  let source=null;
  get('compare-ticker').addEventListener('input',()=>{clearData();status('종목이 변경됐습니다. 자료를 다시 가져오세요.');});
  get('compare-load').addEventListener('click',async()=>{
    if(busy)return;
    const ticker=get('compare-ticker').value.trim().toUpperCase();
    if(!/^KRW-[A-Z0-9]{1,15}$/.test(ticker)){status('KRW-BTC 같은 종목 코드를 입력하세요.');return;}
    busy=true;clearData();
    for(const id of ['compare-load','compare-ticker','compare-csv'])get(id).disabled=true;
    status('최근 완료 1분봉 조회 중…');
    const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),60000);
    try{
      const response=await fetch('/api/research/upbit-minutes?ticker='+encodeURIComponent(ticker),{cache:'no-store',signal:controller.signal});
      const data=await response.json();if(!response.ok)throw Error(data.detail||'조회 실패');
      prepareBars(data.bars,data.source);
    }catch(error){clearData();status(error.name==='AbortError'?'시세 응답 시간이 초과됐습니다.':error.message);reveal();}
    finally{clearTimeout(timer);busy=false;for(const id of ['compare-load','compare-ticker','compare-csv'])get(id).disabled=false;}
  });
  function invalidate(){report=null;get('compare-output').hidden=true;get('compare-download').disabled=true;}
  for(const id of ['compare-fee','compare-slip','compare-spread'])get(id).addEventListener('input',()=>{invalidate();status('비용이 변경됐습니다. 다시 비교하세요.');});
  get('compare-csv').addEventListener('change',async()=>{
    clearData();
    try{
      const file=get('compare-csv').files[0];if(!file)return;
      if(file.size>5_000_000)throw Error('CSV는 5MB 이하로 올리세요.');
      const lines=(await file.text()).trim().replace(/^\uFEFF/,'').split(/\r?\n/);
      if(lines.shift().trim()!=='time,open,high,low,close,volume')throw Error('헤더는 time,open,high,low,close,volume 입니다.');
      if(lines.length<500||lines.length>20000)throw Error('완료된 1분봉 500~20,000개가 필요합니다.');
      const parsed=lines.map(line=>{
        const a=line.split(',').map(x=>x.trim());
        if(a.length!==6||a.some(x=>x===''))throw Error('누락된 CSV 값을 확인하세요.');
        const n=a.map(Number);if(n.some(v=>!Number.isFinite(v))||!Number.isSafeInteger(n[0])||n.slice(0,5).some(v=>v<=0)||n[5]<0)throw Error('숫자 형식을 확인하세요.');
        return {time:n[0],open:n[1],high:n[2],low:n[3],close:n[4],volume:n[5]};
      });
      prepareBars(parsed,file.name);
    }catch(error){clearData();status(error.message);reveal();}
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
    if(busy||!dataReady||!bars.length)return;
    const fields=['compare-fee','compare-slip','compare-spread'];
    if(fields.some(id=>get(id).value.trim()===''||!get(id).checkValidity())){status('비용 가정 세 항목을 모두 입력하세요.');return;}
    busy=true;invalidate();get('compare-run').disabled=true;
    for(const id of [...fields,'compare-csv','compare-ticker','compare-load'])get(id).disabled=true;
    status('동일 구간과 비용으로 비교 중…');const controller=new AbortController();const timer=setTimeout(()=>controller.abort(),60000);
    try{
      const response=await fetch('/api/research/compare',{method:'POST',cache:'no-store',signal:controller.signal,headers:{'Content-Type':'application/json'},body:JSON.stringify({market:'upbit',feeBps:Number(get(fields[0]).value),slippageBps:Number(get(fields[1]).value),spreadBps:Number(get(fields[2]).value),bars})});
      const data=await response.json();if(!response.ok)throw Error(typeof data.detail==='string'?data.detail:'입력 자료를 확인하세요.');
      report={...data,dataSource:source,dataCoverage:{...coverage,fromTime:bars[0].time,toTime:bars.at(-1).time}};render(data);status('비교 완료. 아래에 세 방식의 결과가 있습니다. 실제 11건 재현이나 수익성 검증 완료를 뜻하지 않습니다.');get('compare-output').scrollIntoView?.({behavior:'smooth',block:'start'});
    }catch(error){status(error.name==='AbortError'?'응답 시간이 초과됐습니다.':error.message);reveal();}
    finally{clearTimeout(timer);busy=false;get('compare-run').disabled=false;for(const id of [...fields,'compare-csv','compare-ticker','compare-load'])get(id).disabled=false;}
  });
  get('compare-download').addEventListener('click',()=>{
    if(!report)return;const url=URL.createObjectURL(new Blob([JSON.stringify(report,null,2)],{type:'application/json'}));
    const a=document.createElement('a');a.href=url;a.download='zenthex-strategy-comparison.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  });
})();
