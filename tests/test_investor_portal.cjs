/* Run with node --test tests/test_investor_portal.cjs. No browser or packages needed. */
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');

const source=fs.readFileSync(path.join(__dirname,'../fund_agents/web/app.js'),'utf8');
function portal() {
  const elements=new Map();
  function element(key) {
    if(!elements.has(key))elements.set(key,{value:'all',innerHTML:'',textContent:'',disabled:false,hidden:false,dataset:{},className:'',classList:{toggle(){}},addEventListener(){},querySelectorAll(){return[];},setAttribute(){},removeAttribute(){},close(){},showModal(){},focus(){}});
    return elements.get(key);
  }
  const location={href:'http://127.0.0.1:8765/',search:'',hash:''};
  const context=vm.createContext({document:{querySelector:element,querySelectorAll(){return[];},addEventListener(){},body:{classList:{toggle(){}}}},location,history:{replaceState(){}},window:{addEventListener(){}},URL,URLSearchParams,Intl,console,setTimeout,clearTimeout,fetch:()=>new Promise(()=>{})});
  vm.runInContext(source+`\n globalThis.portalTest={setReport(value){report=value;},context,overview,pmsView,riskView,committeeView,flowView,auditView,investorBrief,targetTable,loadSelected,setSelected(value){selectedId=value;},setFetch(value){globalThis.fetch=value;}};`,context);
  return {api:context.portalTest,elements,context};
}
function cycle() {
  const group=gross=>({pm:'ensemble',group:'portfolio',as_of:'2026-10-16',signal_session:'2026-10-16',actionable:true,legs:[{symbol:'V',units:gross/200,price_usd:100},{symbol:'MA',units:-gross/200,price_usd:100}]});
  return {schema_version:'ensemble-fund-v3',cycle_id:'verified-cycle',as_of:'2026-10-16',mode:'research',generated_at_utc:'2026-10-20T01:00:00Z',status:'INTENTS_RECORDED',execution_mode:'record_only',config:{account_key:'fixture-account',ensemble_budget_usd:3000000,central_cash_usd:2000000,maximum_fund_gross:.8,maximum_name_gross:.2,maximum_drawdown:.25,soft_drawdown:.12,soft_drawdown_scale:.5,risk_envelope:'standard'},portfolio_before:{peak_nav_usd:5000000,holdings:[]},portfolio_after:{holdings:[]},fund_risk:{status:'REVIEWED',metrics:{marked_nav_usd:5000000,target_gross_usd:1000000,target_gross_fraction:.2,filled_orders:0},state:{peak_nav_usd:5000000,breaker_latched:false},approved_groups:[group(1000000)],alerts:[],reviews:[],phantom_book:{proposed_gross_usd:1300000,approved_gross_usd:1000000,throttled_gross_usd:300000,soft_throttle_active:false}},pm_proposals:{ensemble:{status:'READY',groups:[group(1300000)],diagnostics:{regime:'TRENDING_BULL',allocation_method:'regime',allocations:{trend:.5,momentum:.4,mean_reversion:0,cash:.1},engines:{trend:{allocation:.5,target_gross_fraction:1},momentum:{allocation:.4,target_gross_fraction:1},mean_reversion:{allocation:0,target_gross_fraction:.2}}}}},pm_representatives:{},execution_receipts:[],limitations:['No fills.']};
}

test('legacy reports show missing Chair and Phantom Book instead of invented measurements',()=>{
  const {api}=portal(),r=cycle();delete r.fund_risk.phantom_book;api.setReport(r);
  assert.match(api.committeeView(),/predates the Committee Chair/);
  assert.match(api.riskView(),/Exposure-reduction accounting was not recorded/);
  assert.match(api.investorBrief(),/Exposure removed: —/);
  assert.doesNotMatch(api.committeeView(),/Committee Chair reviewed/);
});
test('input holds leave fund and concentration measurements unavailable',()=>{
  const {api}=portal(),r=cycle();r.fund_risk={status:'INPUT_HOLD',metrics:{},approved_groups:[],alerts:[]};api.setReport(r);
  assert.equal(api.context().nav,null);assert.equal(api.context().largestName,null);
  assert.match(api.riskView(),/Concentration is unavailable/);
  assert.doesNotMatch(api.overview(),/\$0/);
});
test('soft drawdown and envelope affect the displayed ceiling without halving targets again',()=>{
  const {api}=portal(),r=cycle();r.config.risk_envelope='conservative';r.fund_risk.phantom_book.soft_throttle_active=true;api.setReport(r);
  assert.ok(Math.abs(api.context().effectiveCap-.3)<1e-12);
  assert.equal(api.context().metrics.target_gross_usd,1000000);
  assert.match(api.riskView(),/SOFT CONTROL ACTIVE/);
});
test('exported investor brief binds quantities and provenance to the selected cycle',()=>{
  const {api}=portal(),r=cycle();api.setReport(r);const brief=api.investorBrief();
  assert.match(brief,/Cycle: verified-cycle/);assert.match(brief,/Evidence: Historical replay/);
  assert.match(brief,/Exposure removed: \$300,000/);assert.match(brief,/Recorded fills: 0/);
  assert.match(brief,/No Chair record/);assert.match(brief,/not profit or money saved/);
});
test('saved free text is escaped in overview, committee, flow and audit views',()=>{
  const {api}=portal(),r=cycle(),payload='<img src=x onerror=alert(1)>';
  r.committee_chair={status:'NOT_REQUESTED',computed_memo:{summary:payload},tool_calls:[]};
  r.pm_proposals.ensemble.diagnostics.error=payload;r.fund_risk.alerts=[payload];r.cycle_id=payload;r.limitations=[payload];api.setReport(r);
  for(const render of [api.overview,api.committeeView,api.flowView,api.auditView]){const html=render();assert.doesNotMatch(html,/<img src=x/);assert.match(html,/&lt;img/);}
});
test('portfolio basket retains signed targets without an obsolete hedge identity',()=>{
  const {api}=portal();api.setReport(cycle());
  const g={pm:'ensemble',group:'portfolio',signal_session:'2026-10-16',actionable:true,legs:[{symbol:'V',units:1800,price_usd:100},{symbol:'MA',units:-2700,price_usd:100}]};
  const html=api.targetTable([g],true);assert.match(html,/\$180,000/);assert.match(html,/-\$270,000/);assert.match(html,/Portfolio component/);assert.doesNotMatch(html,/hedge|Pairs PM/);
});
test('failed report fetch clears stale financial data and permits another cycle selection',async()=>{
  const {api,elements}=portal();api.setReport(cycle());api.setSelected('missing.json');api.setFetch(async()=>({ok:false,status:404}));
  await api.loadSelected();assert.equal(elements.get('#cycle-select').disabled,false);
  assert.equal(elements.get('#brief-export').disabled,true);assert.match(elements.get('#content').innerHTML,/could not be loaded/);
  assert.doesNotMatch(elements.get('#content').innerHTML,/5,000,000/);
});
test('only validated imported commentary is displayed with human-review attribution',()=>{
  const {api}=portal(),r=cycle();
  r.committee_chair={status:'STRUCTURED_CLAIMS_VALIDATED',model:'claimed-model',computed_memo:{summary:'Computed evidence'},tool_calls:[],output_parsed:{summary:'Imported interpretation',observations:['Review this evidence'],risk_flags:[],suggested_research:[]}};
  api.setReport(r);assert.match(api.committeeView(),/Imported interpretation/);assert.match(api.committeeView(),/Narrative requires human review/);
  r.committee_chair.status='REJECTED';api.setReport(r);assert.doesNotMatch(api.committeeView(),/<p>Imported interpretation/);
});

test('all active views and exports use the ensemble mandate',()=>{
  const {api}=portal();api.setReport(cycle());
  for(const render of [api.overview,api.pmsView,api.riskView,api.committeeView,api.flowView,api.auditView,api.investorBrief]){
    assert.doesNotMatch(render(),/Pairs PM|Kalman|OU forecasts|Momentum reserve/i);
  }
  for(const name of ['Trend following','Momentum','Mean reversion'])assert.match(api.flowView(),new RegExp(name));
  assert.match(api.overview(),/60\.0%/);assert.match(api.overview(),/Central cash/);
  assert.match(api.pmsView(),/STANDBY/);assert.match(api.pmsView(),/0% to mean reversion/);
});
test('successful cycle loading displays fresh ensemble evidence',async()=>{
  const {api,elements}=portal();api.setSelected('test.json');api.setFetch(async()=>({ok:true,json:async()=>cycle()}));
  await api.loadSelected();assert.equal(elements.get('#brief-export').disabled,false);
  assert.match(elements.get('#content').innerHTML,/Ensemble PM/);
  assert.equal(elements.get('#cycle-select').disabled,false);
});
