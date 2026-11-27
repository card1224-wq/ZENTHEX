const fs=require('fs'),vm=require('vm'),assert=require('assert');
class Element{
 constructor(){this.value='5';this.disabled=false;this.hidden=true;this.handlers={};this.children=[];this.textContent='';}
 addEventListener(n,f){this.handlers[n]=f;}checkValidity(){return Number(this.value)>=0&&Number(this.value)<=1000;}
 append(x){this.children.push(x);}replaceChildren(){this.children=[];}scrollIntoView(){this.scrolled=true;}
 set innerHTML(x){throw Error('Unsafe HTML');}
}
const elements=new Map(),get=id=>{if(!elements.has(id))elements.set(id,new Element());return elements.get(id);};
get('compare-ticker').value='KRW-BTC';let calls=[];
const data=Array.from({length:500},(_,i)=>({time:1700000000000+i*60000,open:100,high:100,low:100,close:100,volume:1}));
let candleData=data;
const stats={returnPct:0,maxDrawdownPct:0,tradeCount:0,winRatePct:null,averageWinPct:null,averageLossPct:null,expectancyPct:null,profitFactor:null,costRejected:0};
const context={document:{getElementById:get,createElement:()=>new Element()},fetch:async(url,options={})=>{calls.push({url,options});return {ok:true,json:async()=>url.includes('upbit-minutes')?{source:'Public candles',bars:candleData}:{results:[{label:'<img src=x onerror=bad()>',decision:'연구 기준 미달',training:stats,validation:stats,doubleCostValidation:stats}],assumptions:['Research only']}};},AbortController,setTimeout,clearTimeout,Blob,URL};
vm.runInNewContext(fs.readFileSync('static/strategy-comparison.js','utf8'),context);
(async()=>{
 assert.equal(calls.length,0);
 await get('compare-load').handlers.click();assert.equal(calls.length,1);assert(calls[0].url.includes('KRW-BTC'));assert.equal(calls[0].options.cache,'no-store');
 await get('compare-run').handlers.click();assert.equal(calls.length,2);assert.equal(calls[1].url,'/api/research/compare');
 const body=JSON.parse(calls[1].options.body);assert.equal(body.bars.length,500);assert.equal(body.market,'upbit');assert.equal(body.spreadBps,5);
 assert.equal(get('compare-output').hidden,false);assert.equal(get('compare-results').children[0].children[0].textContent,'<img src=x onerror=bad()>');
 get('compare-spread').handlers.input();assert.equal(get('compare-output').hidden,true);assert.equal(get('compare-download').disabled,true);
 get('compare-ticker').value='https://evil.invalid';await get('compare-load').handlers.click();assert.equal(calls.length,2);
 get('compare-ticker').handlers.input();assert.equal(get('compare-run').disabled,true);
 get('compare-ticker').value='KRW-BTC';
 candleData=Array.from({length:530},(_,i)=>({...data[0],time:1700000000000+i*60000+(i>=30?60000:0)}));
 await get('compare-load').handlers.click();
 assert.equal(get('compare-run').disabled,true);assert.equal(get('compare-contiguous').hidden,false);
 assert(get('compare-coverage').textContent.includes('530'));assert(get('compare-status').textContent.includes('보류'));
 const before=calls.length;await get('compare-run').handlers.click();assert.equal(calls.length,before);
 get('compare-contiguous').handlers.click();assert.equal(get('compare-run').disabled,false);assert.equal(get('compare-contiguous').hidden,true);
 assert(get('compare-coverage').textContent.includes('연속 500개만'));
 await get('compare-run').handlers.click();
 const subset=JSON.parse(calls.at(-1).options.body).bars;
 assert.equal(subset.length,500);assert.equal(subset[0].time,candleData[30].time);
 assert.equal(get('compare-output').scrolled,true);
 candleData=Array.from({length:600},(_,i)=>({...data[0],time:1700000000000+i*60000+(i>=300?60000:0)}));
 await get('compare-load').handlers.click();assert.equal(get('compare-run').disabled,true);assert.equal(get('compare-contiguous').hidden,true);
 assert(get('compare-status').textContent.includes('500개 미만'));assert(get('compare-status').scrolled);
 candleData=[...data];candleData[10]={...data[10],time:data[9].time};
 await get('compare-load').handlers.click();assert.equal(get('compare-run').disabled,true);assert(get('compare-status').textContent.includes('중복 없는'));
 assert(calls.every(c=>c.url.startsWith('/api/research/')));
 console.log('Strategy UI checks OK: public fetch, no order calls, cost invalidation, safe text, ticker validation');
})().catch(e=>{console.error(e);process.exit(1);});
