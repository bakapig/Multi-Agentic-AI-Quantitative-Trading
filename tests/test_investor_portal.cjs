/* Investor scope, demo account, and risk governance checks. node --test tests/test_investor_portal.cjs */
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const source=fs.readFileSync(path.join(__dirname,'../fund_agents/web/app.js'),'utf8');
function fixture(){
 const series={};for(const [key,label] of Object.entries({ensemble:'Dynamic ensemble',equal_weight:'Equal-weight ensemble',risk_parity:'Inverse-volatility ensemble',trend:'Trend following',momentum:'Momentum',mean_reversion:'Mean reversion',benchmark:'SPY benchmark'}))series[key]={label,index:[100,102,104.48],metrics:{total_return:.0448,max_drawdown:-.0116,sharpe:6.76,observations:14}};
 return {schema_version:'alphahunt-investor-v1',brand:{name:'AlphaHunt Capital'},backtest:{start:'2026-10-01',end:'2026-10-20',sessions:14,universe_size:878,universe_scope:'Global research universe',dates:['2026-09-30','2026-10-01','2026-10-20'],series,regimes:[{date:'2026-10-01',regime:'RANGING',weights:{trend:.1,momentum:.8,mean_reversion:0,cash:.1}},{date:'2026-10-20',regime:'TRENDING_BULL',weights:{trend:.5,momentum:.4,mean_reversion:0,cash:.1}}],latest_allocation:{date:'2026-10-20',regime:'TRENDING_BULL',weights:{trend:.5,momentum:.4,mean_reversion:0,cash:.1}},method:['Research simulation; no confirmed fills.']},risk_replay:{available:true,as_of:'2026-10-16',proposed_gross_fraction:.54,approved_gross_fraction:.54,removed_gross_fraction:0,policies:{soft_drawdown:.12,maximum_drawdown:.25,maximum_fund_gross:.8,maximum_name_gross:.2},chair_status:'NOT_REQUESTED'},proposed_profile:{intraday_halt:.025,maximum_drawdown:.07,status:'PROPOSED'},governance:{automatic_model_calls:false},provenance:{source_commit:'abc123',curve_sha256:'a'.repeat(64),regime_sha256:'b'.repeat(64),manifest_sha256:'c'.repeat(64),normalization:'100 at the start',final_quote_recovery:'Saved closing marks'}};
}
function portal(){
 const elements=new Map();function element(key){if(!elements.has(key))elements.set(key,{value:'',innerHTML:'',textContent:'',disabled:false,dataset:{},className:'',classList:{toggle(){}},addEventListener(){},querySelectorAll(){return[];},setAttribute(){},close(){},showModal(){},focus(){}});return elements.get(key);}
 const context=vm.createContext({document:{querySelector:element,querySelectorAll(){return[];},addEventListener(){},body:{classList:{toggle(){}}}},location:{href:'http://127.0.0.1:8765/#overview',search:'',hash:'#overview'},history:{replaceState(){}},window:{addEventListener(){},scrollTo(){}},URL,URLSearchParams,Intl,console,setTimeout,fetch:()=>new Promise(()=>{})});
 vm.runInContext(source+`\nglobalThis.portalTest={setData(v){data=v;loading=false;},getData(){return data;},overview,performanceView,pmsView,riskView,flowView,auditView,investorBrief,loadData,setFetch(v){globalThis.fetch=v;}};`,context);
 return {api:context.portalTest,elements};
}

test('overview renders institutional demo account, daily summary, positions, and AI rationales',()=>{
 const {api}=portal(),d=fixture();api.setData(d);
 const h=api.overview();
 assert.match(h,/100,000/);
 assert.match(h,/108,448/);
 assert.match(h,/8,448/);
 assert.match(h,/Daily Strategy/);
 assert.match(h,/Investor Portfolio Positions/);
 assert.match(h,/Executed Positions &amp; AI Analyst Decisions/);
 assert.match(h,/According to AI Analyst \(Why do this\)/);
 assert.doesNotMatch(h,/Phantom Book/i);
});

test('track record metrics and performance curves are rendered',()=>{
 const {api}=portal();api.setData(fixture());
 const h=api.performanceView();
 assert.match(h,/\+4\.48%/);
 assert.match(h,/1\.16%/);
 assert.match(h,/Cumulative net performance/);
 assert.match(h,/Session-by-session track record/);
});

test('strategy view explains the ensemble and dynamic allocations',()=>{
 const {api}=portal();api.setData(fixture());
 const h=api.pmsView();
 assert.match(h,/Trend following/);
 assert.match(h,/STANDBY/);
 assert.match(h,/70%/);
 assert.match(h,/Default dynamic allocation policy/);
});

test('proposed 2.5 and 7 risk profile is kept with strategy suggestions while old controls are removed',()=>{
 const {api}=portal();api.setData(fixture());
 const h=api.riskView();
 assert.match(h,/Proposed AlphaHunt Investor Risk Profile/);
 assert.match(h,/2\.5%/);
 assert.match(h,/7%/);
 assert.match(h,/Ensemble Strategy Options/);
 assert.match(h,/Core Balanced Alpha/);
 assert.match(h,/Defensive Capital Preservation/);
 assert.match(h,/High-Beta Alpha Momentum/);
 assert.match(h,/All-Weather Volatility Parity/);
 assert.doesNotMatch(h,/Phantom Book/i);
 assert.doesNotMatch(h,/Saved drawdown controls/i);
 assert.doesNotMatch(h,/Saved gross ceiling/i);
 assert.doesNotMatch(h,/Soft drawdown threshold/i);
});

test('architecture view shows two-lane pipeline with human command and quantitative authority',()=>{
 const {api}=portal();api.setData(fixture());
 const h=api.flowView();
 assert.match(h,/The two-lane AlphaHunt architecture/);
 assert.match(h,/LANE 1 \/ DETERMINISTIC QUANTITATIVE CODE/);
 assert.match(h,/LANE 2 \/ ADVISORY REVIEW AFTER RISK/);
 assert.match(h,/Human command\. Quantitative authority\./);
 assert.match(h,/Mandate & risk policy/);
 assert.match(h,/Deterministic decision code/);
 assert.doesNotMatch(h,/Numerical claim verification/i);
 assert.doesNotMatch(h,/Current AI status/i);
 assert.doesNotMatch(h,/Research recap/i);
 assert.doesNotMatch(h,/DETERMINISTIC EVIDENCE SUMMARY/i);
});

test('source fingerprints are removed from research',()=>{
 const {api}=portal();api.setData(fixture());
 assert.doesNotMatch(api.auditView(),/Source fingerprints/i);
 assert.doesNotMatch(api.auditView(),/Source commit/i);
});

test('untrusted source and regime strings are escaped',()=>{
 const {api}=portal(),d=fixture(),bad='<img src=x onerror=alert(1)>';
 d.backtest.latest_allocation.regime=bad;d.backtest.method=[bad];d.provenance.source_commit=bad;
 api.setData(d);
 assert.doesNotMatch(api.overview(),/<img src=x/);
 assert.match(api.auditView(),/&lt;img/);
});

test('failed refresh clears stale performance and disables export',async()=>{
 const {api,elements}=portal();api.setData(fixture());api.setFetch(async()=>({ok:false,status:503}));
 await api.loadData();
 assert.equal(api.getData(),null);
 assert.equal(elements.get('#brief-export').disabled,true);
 assert.match(elements.get('#content').innerHTML,/could not be loaded/);
});

test('successful load uses the investor endpoint and displays track record results',async()=>{
 const {api,elements}=portal();api.setData(null);let requested;
 api.setFetch(async url=>(requested=url,{ok:true,json:async()=>fixture()}));
 await api.loadData();
 assert.equal(requested,'/api/investor');
 assert.equal(elements.get('#brief-export').disabled,false);
 assert.match(api.performanceView(),/4\.48%/);
});
