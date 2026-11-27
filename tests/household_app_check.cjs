const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
const root=path.resolve(__dirname,'..');
class Element{
  constructor(){this.value='';this.textContent='';this.children=[];this.handlers={};this.hidden=false;}
  addEventListener(name,fn){this.handlers[name]=fn;}
  append(...items){this.children.push(...items);}
  replaceChildren(){this.children=[];this.textContent='';}
  reset(){}
  scrollIntoView(){}
  set innerHTML(value){throw new Error('Private input must be rendered as text');}
}
const elements=new Map(),storage=new Map(),events={},calls=[];
const get=id=>{if(!elements.has(id))elements.set(id,new Element());return elements.get(id);};
const context={document:{getElementById:get,createElement:()=>new Element(),body:new Element()},
  window:{addEventListener:(name,fn)=>{events[name]=fn;},confirm:()=>true},
  navigator:{},localStorage:{getItem:key=>storage.get(key)||null},Intl,Date,Number,Map,Set,JSON,AbortController,console,
  setTimeout(){return 0;},clearTimeout(){},
  fetch:async(url,options)=>{
    calls.push({url,options});
    let value={};
    if(url.includes('/summary'))value={settings:{as_of:'2026-11-27',cash_krw:700000,reserve_krw:0},
      actual:{count:1,income_krw:0,outflow_krw:100,net_krw:-100,card_purchases_krw:0,categories:{'<img src=x>':100}},
      forecast:{additional_needed_krw:1800000,unknown_amounts:1,reserve_entered:true,overdue_expenses:0,days:[{date:'2026-12-10',income_krw:0,outflow_krw:0,balance_krw:null}]},
      trading:{count:1,realized_pnl_krw:-98},side_activities:{zenthex_business:{count:0,net_krw:0},betman:{count:1,net_krw:-7000},other:{count:0,net_krw:0}}};
    else if(url.includes('/entries?'))value={total:1,next_offset:null,entries:[{id:1,date:'2026-11-27',activity:'household',kind:'expense',category:'식비',description:'<img src=x onerror=alert(1)>',method:'계좌',amount_krw:100,status:'done',confirmed:true}]};
    return {ok:true,json:async()=>value};
  }
};
const settle=async()=>{for(let n=0;n<8;n++)await new Promise(resolve=>setImmediate(resolve));};
(async()=>{
  vm.runInNewContext(fs.readFileSync(root+'/static/household.js','utf8'),context);
  await settle();assert.equal(calls.length,0,'No private reads without login');
  storage.set('zx_token','test-user');events.storage();await settle();
  assert.equal(get('gap').textContent,'1,800,000원');
  assert(get('forecast-note').textContent.includes('미확정'));
  assert.equal(get('entries').children[0].children[0].children[0].textContent,'<img src=x onerror=alert(1)>');
  assert(calls.every(call=>call.options.cache==='no-store'));
  const before=calls.length;
  get('entry-status').value='done';get('entry-amount').value='';get('activity').value='household';get('kind').value='expense';
  get('entry-form').handlers.submit({preventDefault(){}});await settle();
  assert.equal(calls.length,before,'Unknown actual amount must not be posted');
  get('entry-date').value='2026-11-27';get('category').value='식비';get('description').value='입력';get('method').value='현금';get('confirmed').value='true';get('entry-amount').value='100';
  get('entry-form').handlers.submit({preventDefault(){}});await settle();
  const post=calls.find(call=>call.options.method==='POST');assert(post);
  const payload=JSON.parse(post.options.body);assert.equal(payload.amount_krw,100);assert.equal(payload.activity,'household');assert(!('user_id'in payload));
  storage.delete('zx_token');events.storage();await settle();
  assert.equal(get('gap').textContent,'—');assert.equal(get('entries').children.length,0);
  console.log('Household mobile checks OK: auth, money units, safe text, unknown amount, owned create, logout clear');
})().catch(error=>{console.error(error);process.exitCode=1;});
