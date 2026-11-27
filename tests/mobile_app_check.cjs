const fs=require('node:fs');
const vm=require('node:vm');
const assert=require('node:assert/strict');
const root=require('node:path').resolve(__dirname,'..');
class Element{
  constructor(){this.textContent='';this.children=[];this.handlers={};}
  addEventListener(name,fn){this.handlers[name]=fn;}
  replaceChildren(){this.children=[];this.textContent='';}
  append(...children){this.children.push(...children);}
  set innerHTML(value){throw new Error('Unsafe HTML rendering');}
}
const elements=new Map(),storage=new Map(),handlers={},calls=[];
const get=id=>{if(!elements.has(id))elements.set(id,new Element());return elements.get(id);};
let failStatus=false;
const context={
  document:{getElementById:get,createElement:()=>new Element(),addEventListener(){},hidden:false},
  window:{addEventListener:(name,fn)=>{handlers[name]=fn;},matchMedia:()=>({matches:false})},
  navigator:{},localStorage:{getItem:key=>storage.get(key)||null},
  setInterval(){},setTimeout(){return 0;},clearTimeout(){},AbortController,Intl,console,
  fetch:async(path,options)=>{
    calls.push({path,options});
    if(path.endsWith('/status'))return {ok:!failStatus,status:503,json:async()=>({state:'SCANNING',decisionNote:'후보 탐색 중'})};
    return {ok:true,json:async()=>({tradeCount:6,winCount:1,lossCount:5,winRate:1/6,totalPnlKrw:-607,expectancyPct:-.0037,recentTrades:[{ticker:'KRW-MBL',pnlKrw:-98,reason:'<img src=x onerror=alert(1)>'}]})};
  }
};
const settle=async()=>{for(let i=0;i<5;i++)await new Promise(resolve=>setImmediate(resolve));};
(async()=>{
  vm.runInNewContext(fs.readFileSync(root+'/static/app.js','utf8'),context);
  await settle();
  assert.equal(calls.length,0,'Anonymous user must not query account data');
  assert.equal(get('share').disabled,true);
  storage.set('zx_token','test-session');handlers.storage();await settle();
  assert.equal(get('count').textContent,'6회');
  assert.equal(get('pnl').textContent,'-607원');
  assert.equal(get('state').textContent,'후보 탐색');
  assert.equal(get('trades').children[0].children[1].textContent,'<img src=x onerror=alert(1)>');
  assert(calls.every(call=>call.options.cache==='no-store'));
  assert(calls.every(call=>!call.options.method||call.options.method==='GET'));
  failStatus=true;await get('refresh').handlers.click();
  assert.equal(get('state').textContent,'조회 실패');
  assert(get('decision').textContent.includes('정지했다고 판단하지 마세요'));
  const listeners={};
  vm.runInNewContext(fs.readFileSync(root+'/static/app-sw.js','utf8'),{
    self:{addEventListener:(name,fn)=>{listeners[name]=fn;},location:{origin:'https://example.test'}},URL
  });
  let intercepted=false;
  for(const url of ['https://example.test/api/finance/status','https://example.test/api/finance/analysis-report','https://example.test/api/household/summary','https://example.test/api/household/export','https://other.test/app.html']){
    listeners.fetch({request:{url,method:'GET'},respondWith(){intercepted=true;}});
  }
  assert.equal(intercepted,false,'Account APIs and external requests must bypass app cache');
  console.log('Mobile checks OK: auth gate, correct units, safe text, read-only requests, stale-state warning, private API cache bypass');
})().catch(error=>{console.error(error);process.exitCode=1;});
