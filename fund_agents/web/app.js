'use strict';

const $ = selector => document.querySelector(selector);
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const numeric = value => typeof value === 'number' && Number.isFinite(value);
const money = value => numeric(value) ? new Intl.NumberFormat('en-US', {style:'currency',currency:'USD',maximumFractionDigits:0}).format(Math.abs(value)<.5?0:value) : '—';
const compact = value => !numeric(value) ? '—' : Math.abs(value) >= 1e6 ? `$${(value/1e6).toFixed(2)}m` : money(value);
const pct = value => numeric(value) ? `${(value*100).toFixed(1)}%` : '—';
const decimal = (value, digits=2) => numeric(value) ? (Math.abs(value)<.5*10**(-digits)?0:value).toLocaleString('en-US',{maximumFractionDigits:digits,minimumFractionDigits:digits}) : '—';
const human = value => String(value || 'unavailable').replaceAll('_',' ').toLowerCase();
const pmTitle = pm => ({ensemble:'Ensemble PM'}[pm] || pm);
const basis = mode => mode === 'demo' ? 'Synthetic demo' : 'Historical replay';
const paths = {
  overview:'<rect x="3" y="3" width="7" height="7" rx="1.3"/><rect x="14" y="3" width="7" height="7" rx="1.3"/><rect x="3" y="14" width="7" height="7" rx="1.3"/><rect x="14" y="14" width="7" height="7" rx="1.3"/>',
  managers:'<circle cx="9" cy="7" r="3"/><path d="M3 21v-3a6 6 0 0 1 12 0v3M16 4a3 3 0 0 1 0 6M21 21v-3a6 6 0 0 0-4-5"/>',
  shield:'<path d="M12 3 4 6v6c0 5 8 9 8 9s8-4 8-9V6Z"/><path d="m8 12 3 3 5-6"/>',
  committee:'<path d="M8 3h8v4H8zM12 7v5M5 12h14M5 12v4M19 12v4M12 12v4"/><rect x="2" y="16" width="6" height="5" rx="1"/><rect x="9" y="16" width="6" height="5" rx="1"/><rect x="16" y="16" width="6" height="5" rx="1"/>',
  flow:'<rect x="2" y="8" width="6" height="8" rx="1"/><rect x="16" y="2" width="6" height="6" rx="1"/><rect x="16" y="16" width="6" height="6" rx="1"/><path d="M8 12h4V5h4M12 12v7h4"/>',
  ledger:'<path d="M5 3h14v18H5zM8 7h8M8 11h8M8 15h5"/>',
  compass:'<circle cx="12" cy="12" r="9"/><path d="m16 8-2 6-6 2 2-6Z"/>',
  lock:'<rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3M12 14v3"/>',
  search:'<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/>',
  refresh:'<path d="M20 7v5h-5M4 17v-5h5M6 7a7 7 0 0 1 12-2l2 3M4 16l2 3a7 7 0 0 0 12-2"/>',
  download:'<path d="M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5"/>',
  calendar:'<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v5M16 3v5"/>',
  close:'<path d="m6 6 12 12M6 18 18 6"/>',
  menu:'<path d="M4 6h16M4 12h16M4 18h16"/>',
  chart:'<path d="M4 3v18h17M8 16l4-6 4 3 5-8"/>',
  wallet:'<rect x="3" y="5" width="18" height="15" rx="2"/><path d="M3 7V4l14-2v3M16 11h5v5h-5z"/>',
  check:'<path d="m5 12 4 4L19 6"/>',
  info:'<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7h.01"/>',
  layers:'<path d="m12 2 10 6-10 6L2 8ZM2 13l10 6 10-6M2 18l10 6 10-6"/>',
  pair:'<path d="M3 7h17l-4-4M21 17H4l4 4M20 7l-4 4M4 17l4-4"/>',
};
const icon = name => `<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths[name] || paths.info}</svg>`;
function hydrateIcons(root=document) { root.querySelectorAll('[data-icon]').forEach(el => { el.innerHTML=icon(el.dataset.icon); }); }
const badge = (label,tone='neutral') => `<span class="pill ${tone}">${esc(label)}</span>`;
const statusBadge = status => badge(human(status).toUpperCase(),['READY','REVIEWED','PASS','INTENTS_RECORDED','STRUCTURED_CLAIMS_VALIDATED'].includes(status)?'good':['INPUT_HOLD','RISK_VETO','BREAKER_LATCHED','REJECTED'].includes(status)?'bad':'neutral');
const details = (label,value) => `<details><summary class="detail-summary">${esc(label)}</summary><pre class="json">${esc(JSON.stringify(value,null,2))}</pre></details>`;
const empty = text => `<div class="empty">${esc(text)}</div>`;
const note = text => `<div class="boundary-note">${icon('info')}<span>${esc(text)}</span></div>`;
const heading = (title,right='') => `<div class="section-heading"><h2>${esc(title)}</h2>${right}</div>`;
const panel = (title,body,right='',extra='') => `<section class="panel ${extra}">${heading(title,right)}${body}</section>`;
const foot = text => `<div class="panel-foot">${esc(text)}</div>`;
const gross = group => (group.legs||[]).reduce((sum,l) => sum+Math.abs(l.units*l.price_usd),0);
const sumGross = groups => (groups||[]).reduce((sum,g)=>sum+gross(g),0);
const views = {
  overview:['Overview','A clear view of your fund, its managers, and every proposed decision.','overview'],
  pms:['Portfolio managers','Understand each strategy, inspect its signals, and follow the proposed positions.','managers'],
  risk:['Risk & protection','See what the managers proposed, what risk approved, and what changed.','shield'],
  committee:['Committee review','Follow the PM evidence and the Investment Committee Chair’s recorded review.','committee'],
  flow:['System flow','Follow the two lanes from market data to an inspectable investment decision.','flow'],
  audit:['Decision ledger','A saved trail of inputs, approvals, and portfolio intentions for this cycle.','ledger'],
};
let report=null,reportList=[],selectedId=new URLSearchParams(location.search).get('cycle'),indexWarnings=[];
let modeFilter='all',activeNode='risk',loading=false,loadGeneration=0,tourIndex=0,toastTimer,managerFocus=null;

function context() {
  const risk=report.fund_risk||{},cfg=report.config||{},snapshot=report.portfolio_before||{},metrics=risk.metrics||{};
  const groups=risk.approved_groups||[],phantom=risk.phantom_book;
  const nav=numeric(metrics.marked_nav_usd)?metrics.marked_nav_usd:null;
  const peaks=[snapshot.peak_nav_usd,risk.state?.peak_nav_usd].filter(numeric),peak=peaks.length?Math.max(...peaks):null;
  const drawdown=nav!==null&&peak>0?Math.max(0,1-nav/peak):null;
  const names={}; groups.forEach(g=>(g.legs||[]).forEach(l=>{names[l.symbol]=(names[l.symbol]||0)+Math.abs(l.units*l.price_usd);}));
  const largestName=nav&&groups.length?Math.max(0,...Object.values(names))/nav:nav&&risk.status==='REVIEWED'?0:null;
  const softActive=phantom?.soft_throttle_active===true||(risk.alerts||[]).includes('SOFT_DRAWDOWN_THROTTLE');
  const envelope=cfg.risk_envelope==='conservative'?.75:1;
  const effectiveCap=numeric(cfg.maximum_fund_gross)&&(!softActive||numeric(cfg.soft_drawdown_scale))?cfg.maximum_fund_gross*envelope*(softActive?cfg.soft_drawdown_scale:1):null;
  return {risk,cfg,snapshot,metrics,groups,phantom,nav,drawdown,names,largestName,softActive,effectiveCap};
}

async function getJson(url) {
  const response=await fetch(url); if(!response.ok)throw new Error(`Saved evidence could not be loaded (${response.status}).`);
  return response.json();
}
function clearReport(message,isError=false,invalidate=true) {
  report=null;if(invalidate)loadGeneration++;$('#brief-export').disabled=true;
  $('#mode-badge').textContent=isError?'CONNECTION ERROR':'NO SAVED CYCLES';
  $('#mode-badge').className=`pill ${isError?'bad':'neutral'}`;
  $('#source-note').textContent=isError?'Fund evidence is unavailable. Refresh to reconnect.':'No saved cycles match this selection.';
  $('#footer-cycle').textContent='Paper fund · No cycle selected';
  $('#content').innerHTML=`<div class="empty ${isError?'error':''}">${esc(message)}</div>`;
}
function syncCycleUrl() {
  const url=new URL(location.href);selectedId?url.searchParams.set('cycle',selectedId):url.searchParams.delete('cycle');
  history.replaceState(null,'',url);
}
async function chooseFilteredReport() {
  const list=reportList.filter(r=>modeFilter==='all'||r.mode===modeFilter);
  $('#cycle-select').innerHTML=list.map(r=>`<option value="${esc(r.id)}">${esc(`${basis(r.mode)} · ${r.as_of} · ${r.cycle_id.slice(0,8)}`)}</option>`).join('');
  if(!list.length) {
    selectedId=null;syncCycleUrl();$('#cycle-select').disabled=true;
    clearReport(reportList.length?'No saved reports match this evidence type. Choose another filter.':'No fund cycles have been saved yet. Generate a demo with python -m fund_agents, then refresh.');return;
  }
  if(!list.some(r=>r.id===selectedId))selectedId=list[0].id;
  $('#cycle-select').value=selectedId;await loadSelected();
}
async function loadReports() {
  if(loading)return;loading=true;$('#refresh').disabled=true;
  try {
    const data=await getJson('/api/reports');reportList=data.reports;indexWarnings=data.warnings||[];
    await chooseFilteredReport();
  } catch(error) {clearReport(error.message,true);}
  finally {loading=false;$('#refresh').disabled=false;}
}
async function loadSelected() {
  const generation=++loadGeneration;$('#cycle-select').disabled=true;$('#brief-export').disabled=true;
  report=null;
  $('#source-note').textContent='Opening the selected saved cycle…';
  $('#mode-badge').textContent='LOADING';
  $('#content').innerHTML='<div class="loading-state"><span class="loading-orbit"></span><h2>Loading this decision</h2><p>Opening the account snapshot, risk verdict, and committee evidence together.</p></div>';
  try {
    const next=await getJson(`/api/report?${new URLSearchParams({id:selectedId})}`);
    if(generation!==loadGeneration)return;
    report=next;syncCycleUrl();
    $('#mode-badge').textContent=basis(report.mode).toUpperCase();$('#mode-badge').className=`pill ${report.mode==='demo'?'warn':'purple'}`;
    const generated=new Date(report.generated_at_utc).toLocaleString('en-GB',{timeZone:'Asia/Singapore',day:'2-digit',month:'short',hour:'2-digit',minute:'2-digit',hour12:false});
    $('#source-note').innerHTML=`<b>Valuation ${esc(report.as_of)}</b><span class="source-divider">·</span><span>${report.mode==='demo'?'Invented market inputs':'Saved historical inputs'}</span><span class="source-divider">·</span><span>Saved ${esc(generated)} SGT</span><span class="source-divider">·</span><span>Snapshot, not a live account${indexWarnings.length?` · ${indexWarnings.length} unreadable reports skipped`:''}</span>`;
    $('#footer-cycle').textContent=`Cycle ${report.cycle_id.slice(0,8)} · ${report.config.account_key||'Saved account'} · USD`;
    $('#brief-export').disabled=false;render();
  } catch(error) {if(generation===loadGeneration)clearReport(error.message,true,false);}
  finally {if(generation===loadGeneration)$('#cycle-select').disabled=false;}
}

function alerts() {
  const messages=[...(report.fund_risk.alerts||[])];
  for(const [pm,p] of Object.entries(report.pm_proposals||{}))if(p.diagnostics?.error)messages.push(`${pmTitle(pm)}: ${p.diagnostics.error}`);
  return messages.length?`<div class="alert" role="status">${messages.map(esc).join('<br>')}</div>`:'';
}
function metric(label,value,sub,symbol) {
  return `<div class="metric"><div class="metric-label">${esc(label)}${icon(symbol)}</div><div class="metric-value">${value}</div><div class="metric-sub">${sub}</div></div>`;
}
function metricsPanel() {
  const {nav,metrics,snapshot,phantom}=context();
  return `<div class="metric-grid">${metric('Marked fund value',money(nav),nav===null?'Valuation held · unavailable':(snapshot.holdings||[]).length?'From confirmed account holdings':'Supplied capital · cash-only snapshot','wallet')}${metric('Approved target gross',money(metrics.target_gross_usd),`${pct(metrics.target_gross_fraction)} of marked NAV · proposed holdings`,'chart')}${metric('Exposure reduced by risk',money(phantom?.throttled_gross_usd),phantom?'Submitted targets minus approved targets':'Not measured in this saved cycle','shield')}${metric('Recorded intentions',String((report.execution_receipts||[]).length),`${numeric(metrics.filled_orders)?metrics.filled_orders:'—'} fills · holdings unchanged`,'ledger')}</div>`;
}
function hero() {
  const ready=Object.values(report.pm_proposals||{}).filter(p=>p.status==='READY').length;
  return `<section class="hero"><div><div class="hero-label">A FUND BUILT TO BE INSPECTED</div><h2>Your portfolio.<br>A clear line of sight.</h2><p>Understand what each manager proposed, how independent risk responded, and the evidence behind every decision.</p><div class="hero-actions"><a class="button on-dark" href="#audit">Review this decision →</a><a class="button ghost-dark" href="#flow">Explore the system</a></div></div><div class="hero-diagram" aria-label="Decision process"><div class="hero-stage"><span>01</span><div><b>Ensemble PM</b><small>Trend · Momentum · Mean reversion</small></div><em>${ready}/1 ready</em></div><div class="hero-stage"><span>02</span><div><b>Independent risk</b><small>Exposure, concentration & drawdown</small></div><em>${esc(human(report.fund_risk.status))}</em></div><div class="hero-stage"><span>03</span><div><b>Evidence & oversight</b><small>PM diagnostics + Committee Chair</small></div><em>Read-only</em></div></div></section>`;
}
function allocationPanel() {
  const {cfg}=context(),sleeves=[['Ensemble PM',cfg.ensemble_budget_usd,'#635bff','Three strategy engines'],['Central cash',cfg.central_cash_usd,'#e9edf5','Liquidity reserve']];
  if(sleeves.some(s=>!numeric(s[1])))return panel('Capital mandates',empty('Capital policy is unavailable in this saved report.'));
  const total=sleeves.reduce((sum,s)=>sum+s[1],0);let stop=0;
  const gradient=sleeves.map(s=>{const start=stop;stop+=total?s[1]/total*100:0;return `${s[2]} ${start}% ${stop}%`;}).join(',');
  return panel('Capital mandates',`<div class="allocation-content"><div class="donut" style="background:conic-gradient(${gradient})" role="img" aria-label="Initial capital mandates"><div class="donut-inner"><strong>${compact(total)}</strong><small>initial fund mandate</small></div></div><div class="legend">${sleeves.map(s=>`<div class="legend-row"><i class="swatch" style="background:${s[2]}"></i><div>${s[0]}<small>${s[3]}</small></div><strong>${pct(total?s[1]/total:null)}</strong></div>`).join('')}</div></div>${foot('Mandates are capital budgets. They are separate from approved targets and confirmed holdings.')}`,'<span>Initial allocation</span>');
}
function riskRow(label,value,limit,caption) {
  const ratio=numeric(value)&&numeric(limit)&&limit>0?value/limit:null;
  const color=ratio===null?'#d8deea':ratio>=1?'#c86470':ratio>=.8?'#d0a551':'#8a7af3';
  return `<div class="risk-row"><div class="risk-label"><span>${esc(label)}</span><strong>${pct(value)} <span class="muted">/ ${pct(limit)}</span></strong></div><div class="track"><span style="width:${ratio===null?0:Math.min(100,Math.max(0,ratio*100))}%;background:${color}"></span></div><div class="risk-caption"><span>${esc(caption)}</span><span>${ratio===null?'Unavailable':`${Math.round(ratio*100)}% of limit`}</span></div></div>`;
}
function riskPanel() {
  const {risk,cfg,metrics,drawdown,largestName,effectiveCap,softActive}=context();
  const summary=risk.status==='INPUT_HOLD'?'Missing inputs · approvals held':risk.state?.breaker_latched?'Drawdown breaker latched':risk.status==='RISK_VETO'?'Final fund risk veto':softActive?'Soft drawdown control active':'Independent fund review complete';
  return panel('Risk guardrails',riskRow('Fund gross exposure',metrics.target_gross_fraction,effectiveCap,softActive?'Effective cap · soft control active':'Approved target · before netting')+riskRow('Largest symbol',largestName,cfg.maximum_name_gross,'Combined gross across portfolio groups')+riskRow('Snapshot drawdown',drawdown,cfg.maximum_drawdown,'Confirmed value against recorded peak')+`<div class="risk-summary"><span>${esc(summary)}</span><a class="text-link" href="#risk">Inspect →</a></div>`,statusBadge(risk.status));
}
function exposureChart() {
  const {risk,groups,cfg}=context();
  if(!numeric(risk.metrics?.target_gross_usd))return empty('Submitted and approved exposures cannot be compared for this held or vetoed cycle.');
  const rows=['ensemble'].map(pm=>({pm,proposed:sumGross(report.pm_proposals?.[pm]?.groups),approved:sumGross(groups.filter(g=>g.pm===pm)),budget:cfg[`${pm}_budget_usd`]}));
  const max=Math.max(1,...rows.map(r=>Math.max(r.proposed,r.approved,numeric(r.budget)?r.budget:0)));
  return `<div class="exposure-bars">${rows.map(r=>`<div class="exposure-row"><div class="exposure-label">${pmTitle(r.pm)}<small>Target gross, USD</small></div><div class="exposure-pair"><div class="exposure-track"><span style="width:${r.proposed/max*100}%" title="Submitted ${money(r.proposed)}"></span></div><div class="exposure-track approved"><span style="width:${r.approved/max*100}%" title="Approved ${money(r.approved)}"></span></div></div><div class="exposure-amount">${compact(r.approved)}<small>of ${compact(r.proposed)} submitted</small></div></div>`).join('')}</div><div class="chart-legend"><span><i style="background:#d6d2ff"></i>Submitted to fund risk</span><span><i style="background:#635bff"></i>Approved</span></div>`;
}
function chairSummary() {
  const chair=report.committee_chair;
  return panel('Investment committee',chair?`<div class="review-summary"><div class="review-icon">${icon('committee')}</div><div><h3>Committee Chair review</h3><p>${esc(chair.computed_memo?.summary||'Open the recorded evidence to review the Chair’s diagnostics.')}</p><a class="text-link" href="#committee">Read the committee evidence →</a></div></div><div class="review-meta"><span><b>${chair.tool_calls?.length||0}</b> diagnostic calls</span><span>${chair.status==='NOT_REQUESTED'?'Computed summary · no imported model reply':esc(human(chair.status))}</span></div>`:empty('This earlier cycle has no Committee Chair record. Select a newer cycle to inspect the review.'),chair?badge('ADVISORY','purple'):'');
}
const strategyTitles={trend:'Trend following',momentum:'Momentum',mean_reversion:'Mean reversion'};
function pmCards() {
  const d=report.pm_proposals?.ensemble?.diagnostics||{}, engines=d.engines||{};
  return heading('One Ensemble PM · three strategy engines',`<span>${esc(human(d.allocation_method))} allocation</span>`)+`<div class="pm-grid">${Object.entries(strategyTitles).map(([key,title])=>{
    const e=engines[key], descriptions={trend:'10 / 60-day moving averages and a market filter.',momentum:'Relative-strength ranking with volatility-based sizing.',mean_reversion:'Rolling spread Z-scores across predefined equity pairs.'};
    return `<article class="pm-card"><div class="pm-top"><div class="pm-icon">${icon('chart')}</div><div><h3>${title}</h3><p>Ensemble component</p></div>${badge(e?e.allocation>0?'ALLOCATED':'STANDBY':'UNAVAILABLE')}</div><div class="pm-numbers"><div><small>Strategy allocation</small><strong>${pct(e?.allocation)}</strong></div><div><small>Engine target gross</small><strong>${pct(e?.target_gross_fraction)}</strong></div></div><div class="pm-meta">${descriptions[key]}</div><a class="pm-link" href="#pms">Inspect ensemble evidence →</a></article>`;
  }).join('')}</div>`;
}

function overview() {
  return alerts()+hero()+metricsPanel()+`<div class="grid-main">${allocationPanel()}${riskPanel()}</div>`+pmCards()+`<div class="grid-main">${panel('From proposals to approved exposure',exposureChart()+foot('A comparison within this saved cycle. These amounts are target exposures, not traded positions.'),'<a class="text-link" href="#risk">Explore Phantom Book →</a>')}${chairSummary()}</div>`;
}

function targetTable(groups,showReviews=false) {
  if(!groups.length)return empty('No approved targets are available. Input holds or risk vetoes can prevent approval.');
  return `<div class="table-wrap"><table><thead><tr><th>MANAGER / GROUP</th><th>SYMBOL / DIRECTION</th><th>TARGET UNITS</th><th>SIGNED NOTIONAL</th><th>${showReviews?'RISK / SCALE':'PRICE SESSION'}</th></tr></thead><tbody>${groups.flatMap(g=>(g.legs||[]).map((l,i)=>{
    const review=(report.fund_risk.reviews||[]).find(r=>r.approved.group===g.group&&r.approved.pm===g.pm);
    return `<tr><td>${i===0?`<span class="group-label">${esc(g.group)}</span><small>${esc(pmTitle(g.pm))}</small>`:'<small>↳ Portfolio component</small>'}</td><td>${esc(l.symbol)}<small>${l.units>0?'Long target':l.units<0?'Short target':'Flat'}</small></td><td>${decimal(l.units,4)}</td><td>${money(l.units*l.price_usd)}</td><td>${showReviews?`${review?statusBadge(review.outcome):'—'}<small>Scale ${pct(review?.scale)}</small>`:`${esc(g.signal_session)}<small>${g.actionable?'Eligible session':'Market closed · retained units'}</small>`}</td></tr>`;
  })).join('')}</tbody></table></div>`;
}
function phantomPanel() {
  const {phantom}=context();
  if(!phantom)return panel('Phantom Book',empty('Exposure-reduction accounting was not recorded for this cycle. No counterfactual figures have been filled in.'),badge('UNAVAILABLE'),'wide');
  return panel('Phantom Book',`<p class="subheading">A transparent record of how independent fund risk changed the managers’ submitted exposure.</p><div class="phantom-stats"><div class="phantom-stat"><small>Submitted gross</small><strong>${money(phantom.proposed_gross_usd)}</strong></div><div class="phantom-stat"><small>Approved gross</small><strong>${money(phantom.approved_gross_usd)}</strong></div><div class="phantom-stat"><small>Exposure removed</small><strong>${money(phantom.throttled_gross_usd)}</strong></div></div>${exposureChart()}${foot('Exposure accounting only. Removed gross is not money saved, profit, or a simulated return. NAV minus gross is not spendable cash.')}${details('Inspect saved Phantom Book',phantom)}`,badge(phantom.soft_throttle_active?'SOFT CONTROL ACTIVE':'EXPOSURE ACCOUNTING',phantom.soft_throttle_active?'warn':'purple'),'wide');
}
function riskView() {
  const {risk,cfg,names,nav,groups,snapshot,softActive}=context();
  const concentration=nav===null?empty('Concentration is unavailable while fund valuation is held.'):Object.keys(names).length?Object.entries(names).sort((a,b)=>b[1]-a[1]).map(([name,value])=>riskRow(name,value/nav,cfg.maximum_name_gross,money(value))).join(''):empty('No approved symbol exposure in this cycle.');
  const policy=`<div class="policy-grid"><div class="policy-step">${badge(softActive?'ACTIVE':'SOFT CONTROL',softActive?'warn':'purple')}<h3>Soft drawdown threshold</h3><strong>${pct(cfg.soft_drawdown)}</strong><p>When active, the fund gross ceiling is multiplied by ${numeric(cfg.soft_drawdown_scale)?pct(cfg.soft_drawdown_scale):'the saved scale, if available'}. Positions already below the effective ceiling may be unchanged.</p></div><div class="policy-step">${badge(risk.state?.breaker_latched?'LATCHED':'HARD CONTROL',risk.state?.breaker_latched?'bad':'neutral')}<h3>Persistent drawdown breaker</h3><strong>${pct(cfg.maximum_drawdown)}</strong><p>Requests exits on eligible sessions and stays latched across restarts. An exit request cannot guarantee a realized loss limit.</p></div></div>`;
  return alerts()+metricsPanel()+`<div class="grid-equal">${riskPanel()}${panel('Concentration by symbol',concentration,'<span>Gross before netting</span>')}</div>`+phantomPanel()+panel('Drawdown protection',policy,`<span>${esc(cfg.risk_envelope||'Saved')} envelope</span>`,'wide')+panel('Approved targets & risk outcomes',targetTable(groups,true)+details('Inspect exact risk decision',risk),'<span>Targets are separate from holdings</span>','wide')+panel('Confirmed account holdings',(snapshot.holdings||[]).length?details('Inspect supplied confirmed holdings',snapshot.holdings):empty('The supplied account is flat. Recorded intentions have not changed its holdings.'),`<span>${(snapshot.holdings||[]).length} confirmed positions</span>`);
}


function fact(label,value) {return `<div class="fact"><small>${esc(label)}</small><strong>${value}</strong></div>`;}
function pmsView() {
  const proposal=report.pm_proposals?.ensemble||{},d=proposal.diagnostics||{},a=d.allocations||{};
  const allocations=Object.entries({...strategyTitles,cash:'Cash reserve'}).map(([key,title])=>`<tr><td>${title}</td><td>${pct(a[key])}</td></tr>`).join('');
  return alerts()+pmCards()+panel('Ensemble PM · market state',`<div class="fact-grid">${fact('Regime',esc(human(d.regime)))}${fact('Signal close',esc(d.signal_session||'Unavailable'))}${fact('Validated sessions',esc(d.history_rows??'Unavailable'))}</div>${d.error?note(d.error):''}<div class="table-wrap"><table><thead><tr><th>STRATEGY</th><th>CAPITAL WEIGHT</th></tr></thead><tbody>${allocations}</tbody></table></div>${note('The current regime policy allocates 0% to mean reversion. Equal-weight and inverse-volatility policies can allocate to all three engines. Strategy weights precede fund risk and may include uninvested cash.')}${details('Inspect strategy signals and portfolio weights',proposal)}`,'','wide')+panel('Strategy source & policy',`<p class="subheading">Numerical engines from the teammate’s multi-strategy ensemble. This cycle records the local engine hashes and effective fund policy.</p>${details('Inspect engine provenance',d.strategy||{})}`)+panel('Approved ensemble targets',targetTable(context().groups));
}

const toolTitles={inspect_cross_sleeve_exposure:['Combined exposure','Gross symbol exposure and the saved fund risk verdict.','layers'],inspect_phantom_book:['Phantom Book','Proposed, approved, and removed gross exposure.','shield'],inspect_pm_memos:['PM memo summaries','Computed summaries and validation status for each connected PM.','managers'],inspect_signals:['Signals','Saved signals and target groups.','chart'],inspect_model_health:['Model health','Saved model diagnostics and input checks.','shield'],inspect_positions:['Positions','Target reviews and execution boundary.','wallet']};
function toolCards(memo) {
  return `<div class="tools-grid">${(memo.tool_calls||[]).map(call=>{
    const [title,description,symbol]=toolTitles[call.tool]||[human(call.tool),'Saved diagnostic result.','info'];
    return `<article class="tool-card"><div class="tool-icon">${icon(symbol)}</div><h3>${esc(title)}</h3><p>${esc(description)}</p><span class="mono">Digest ${esc((call.result_sha256||'unavailable').slice(0,16))}${call.result_sha256?'…':''}</span>${details('Inspect recorded tool result',call)}</article>`;
  }).join('')}</div>`;
}
function modelReply(memo) {
  if(memo.status==='NOT_REQUESTED')return '<span>Computed diagnostics. No model reply was imported.</span>';
  return `<span>${esc(human(memo.status))}${memo.rejection_reason?` · ${esc(memo.rejection_reason)}`:''}</span>`;
}
function importedNarrative(memo) {
  if(memo.status!=='STRUCTURED_CLAIMS_VALIDATED'||!memo.output_parsed)return '';
  const output=memo.output_parsed;
  return `<div class="imported-narrative"><h3>Imported model commentary</h3><div class="memo-meta">Claimed model: ${esc(memo.model||'Unspecified')} · Narrative requires human review</div><p>${esc(output.summary)}</p>${[['Observations',output.observations],['Risk flags',output.risk_flags],['Suggested research',output.suggested_research]].filter(([,items])=>items?.length).map(([label,items])=>`<h4>${label}</h4><ul>${items.map(item=>`<li>${esc(item)}</li>`).join('')}</ul>`).join('')}</div>`;
}
function committeeView() {
  const chair=report.committee_chair;
  const chairBody=chair?`<section class="committee-card">${heading('Investment Committee Chair',statusBadge(chair.status))}<div class="review-summary"><div class="review-icon">${icon('committee')}</div><div><h3>Fund evidence review</h3><p>${esc(chair.computed_memo?.summary||'No computed summary was saved.')}</p><div class="memo-meta">${modelReply(chair)}</div></div></div>${importedNarrative(chair)}${toolCards(chair)}${details('Inspect Chair memo, input facts, and provenance',chair)}${note('The Chair reviews evidence after the quantitative decision. Digest and structured-metric checks do not validate all free-text claims. Human review remains necessary.')}</section>`:panel('Investment Committee Chair',empty('This saved cycle predates the Committee Chair or did not include its record. Select a newer cycle to inspect its evidence.'),badge('NOT RECORDED'),'wide');
  const memos=Object.entries(report.pm_representatives||{});
  const pmBody=memos.length?`<div class="memo-grid">${memos.map(([pm,m])=>`<article class="memo-card"><div class="audit-head"><h3>${esc(pmTitle(pm))}</h3>${statusBadge(m.status)}</div><p>${esc(m.computed_memo?.summary||'No computed summary was saved.')}</p><div class="memo-meta">${modelReply(m)}<br>${m.tool_calls?.length||0} diagnostic calls · ${esc(m.tool_selection_source||'No tool-selection provenance')}</div>${importedNarrative(m)}${details('Inspect PM tools and memo',m)}</article>`).join('')}</div>`:empty('No PM representative records were saved.');
  return alerts()+chairBody+heading('Specialist PM evidence','<span>Advisory · read-only diagnostic tools</span>')+pmBody+phantomPanel()+note('Automatic LLM provider calls are not connected. Default diagnostics and computed summaries do not mean a language model ran. Memos cannot change targets, risk decisions, or intention records.');
}

const nodeDefinitions={
  inputs:['Market inputs','Complete USD equity sessions and benchmark closes. Missing, nonfinite, duplicate or stale required data holds the cycle.','fund_agents/__main__.py · ensemble.py'],
  ensemble:['Ensemble PM','Trend, momentum and mean-reversion engines expose closing-session targets. The allocator combines them by regime, equal weight or inverse volatility and aggregates shared symbols.','fund_agents/ensemble.py · multi_strategy_ensemble/'],
  risk:['Independent fund risk','Checks sleeve capital, fee reserves, gross exposure, concentration and drawdown. It scales the portfolio consistently and retains final approval authority.','fund_agents/risk.py'],
  execution:['Portfolio intentions','Requires the exact persisted risk approval and account snapshot. Records the aggregate portfolio basket with zero fills.','fund_agents/store.py'],
  audit:['Decision record','Atomic SQLite cycles save approvals, intentions, state and advisory evidence. JSON exports feed this read-only portal.','fund_agents/coordinator.py'],
  representatives:['Ensemble evidence analyst','Inspects saved signals, model health and positions after risk. Optional imported model replies cannot change targets or approvals.','fund_agents/representative.py'],
  chair:['Committee Chair','Reviews portfolio exposure, the Phantom Book and ensemble evidence. Automatic model-provider calls are pending.','fund_agents/representative.py'],
  phantom:['Phantom Book','Compares proposed and approved gross exposure. The difference measures exposure removed, without claiming profits or losses.','fund_agents/risk.py'],
};
function nodeEvidence() {
  if(activeNode==='inputs')return {as_of:report.as_of,mode:report.mode,source_sha256:report.pm_proposals?.ensemble?.diagnostics?.source_sha256};
  return ({ensemble:report.pm_proposals?.ensemble,risk:report.fund_risk,execution:report.execution_receipts,audit:{cycle_id:report.cycle_id,config_sha256:report.config_sha256,decision_id:report.fund_risk.decision_id},representatives:report.pm_representatives,chair:report.committee_chair,phantom:report.fund_risk.phantom_book})[activeNode]??{status:'Not recorded in this cycle'};
}

function flowNode(key,step,sub,tone='') {return `<button class="flow-node ${tone} ${activeNode===key?'selected':''}" data-node="${key}" aria-pressed="${activeNode===key}"><span class="node-step">${esc(step)}</span><b>${nodeDefinitions[key][0]}</b><small>${esc(sub)}</small></button>`;}
function nodeDetail() {
  const [title,text,source]=nodeDefinitions[activeNode];
  return `<h3>${title}</h3><p>${text}</p><div class="code-ref">${source}</div>${details('Inspect this component’s saved evidence',nodeEvidence())}`;
}
function flowView() {
  return panel('The two-lane ensemble architecture',`<p class="subheading">The Ensemble PM combines trend following, momentum and mean reversion. Independent risk approves quantitative targets before advisory evidence review.</p><div class="lane-label">01 / QUANTITATIVE DECISION LANE</div>${pmCards()}<div class="flow-grid"><div>${flowNode('inputs','VALIDATE',basis(report.mode))}</div><span class="flow-arrow">→</span><div>${flowNode('ensemble','ALLOCATE',human(report.pm_proposals?.ensemble?.diagnostics?.regime))}</div><span class="flow-arrow">→</span><div>${flowNode('risk','APPROVE',human(report.fund_risk.status))}</div><span class="flow-arrow">→</span><div class="flow-stack">${flowNode('execution','RECORD',`${(report.execution_receipts||[]).length} portfolio groups · zero fills`)}${flowNode('audit','PERSIST','Saved decisions + evidence')}</div></div><div class="lane-label">02 / ADVISORY REVIEW LANE · READ-ONLY</div><div class="advisory-lane">${flowNode('representatives','INVESTIGATE','Signals · model health · positions')}<span class="flow-arrow">→</span>${flowNode('chair','REVIEW','Recorded committee evidence')}<span class="flow-arrow">←</span>${flowNode('phantom','COMPARE','Submitted vs. approved exposure')}</div><div id="flow-detail" class="flow-detail">${nodeDetail()}</div>${note('Closing-session targets are intentions for a later eligible session. The prototype records zero fills. Advisory summaries use deterministic diagnostics unless a validated model reply is imported.')}`,statusBadge(report.status));
}

function auditView() {
  const {risk,snapshot}=context(),receipts=report.execution_receipts||[];
  const identity=`<div class="fact-grid">${fact('Valuation date',esc(report.as_of))}${fact('Execution mode','Record only')}${fact('Recorded fills',numeric(risk.metrics?.filled_orders)?risk.metrics.filled_orders:'—')}</div>${[['Cycle ID',report.cycle_id],['Decision ID',risk.decision_id],['Snapshot SHA-256',risk.snapshot_sha256]].map(([label,value])=>`<div class="hash-row"><span>${label}</span><span class="mono">${esc(value||'Not recorded')}</span></div>`).join('')}<div style="display:flex;gap:10px;margin:18px 0"><button class="button" id="raw-export">${icon('download')}Original cycle JSON</button><button class="button" id="link-copy">Copy cycle link</button></div>${details('Inspect confirmed account before and after',{before:snapshot,after:report.portfolio_after})}`;
  const receiptBody=receipts.length?receipts.map(r=>`<article class="receipt"><div class="audit-head"><h3>${esc(r.group)} <span class="muted">/ ${esc(pmTitle(r.pm))}</span></h3>${statusBadge(r.status)}</div><div class="table-wrap"><table><thead><tr><th>SYMBOL</th><th>INTENDED SIDE</th><th>CURRENT UNITS</th><th>TARGET UNITS</th><th>DELTA UNITS</th></tr></thead><tbody>${(r.intent?.legs||[]).map(l=>`<tr><td>${esc(l.symbol)}</td><td>${esc(l.side)}</td><td>${decimal(l.current_units,4)}</td><td>${decimal(l.units,4)}</td><td>${decimal(l.delta_units,4)}</td></tr>`).join('')}</tbody></table></div>${details('Inspect portfolio intention and approval digest',r)}</article>`).join(''):empty('No intention groups were recorded in this cycle. Confirmed holdings remain unchanged.');
  return alerts()+panel('Decision identity',identity,statusBadge(report.status),'wide')+panel('Portfolio intention records',receiptBody,`<span>${receipts.length} groups · no execution fills</span>`,'wide')+panel('Original evidence',`<p class="subheading">${(report.limitations||[]).map(esc).join('<br>')}</p>${details('Inspect original complete report',report)}${indexWarnings.length?details('Reports skipped during indexing',indexWarnings):''}${foot('Append-only controls apply inside the trusted local process. Hashes are content bindings, not external tamper-proof attestation.')}`);
}

function render() {
  const view=Object.hasOwn(views,location.hash.slice(1))?location.hash.slice(1):'overview';
  const [title,description]=views[view];$('#breadcrumb').textContent=title;$('#page-title').textContent=title;$('#page-description').textContent=description;
  document.querySelectorAll('nav a').forEach(a=>{a.classList.toggle('active',a.dataset.view===view);a.dataset.view===view?a.setAttribute('aria-current','page'):a.removeAttribute('aria-current');});
  if(!report)return;
  $('#content').innerHTML=({overview,pms:pmsView,risk:riskView,committee:committeeView,flow:flowView,audit:auditView}[view])();
  document.querySelectorAll('[data-node]').forEach(b=>b.addEventListener('click',()=>{activeNode=b.dataset.node;document.querySelectorAll('[data-node]').forEach(n=>{n.classList.toggle('selected',n===b);n.setAttribute('aria-pressed',String(n===b));});$('#flow-detail').innerHTML=nodeDetail();}));
  $('#raw-export')?.addEventListener('click',()=>download(`fund-cycle-${report.mode}-${report.as_of}-${report.cycle_id}.json`,JSON.stringify(report,null,2),'application/json'));
  $('#link-copy')?.addEventListener('click',async()=>{try{await navigator.clipboard.writeText(location.href);toast('Cycle link copied. It opens on this local workspace.');}catch{toast('Copy this page’s address to return to the same saved cycle.');}});
}
function download(filename,content,type='text/plain') {
  const url=URL.createObjectURL(new Blob([content],{type}));const a=document.createElement('a');a.href=url;a.download=filename;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
function investorBrief() {
  const {risk,cfg,metrics,phantom,nav}=context(),chair=report.committee_chair;
  return ['MERIDIAN INVESTOR BRIEF',`Valuation date: ${report.as_of}`,`Evidence: ${basis(report.mode)}`,`Cycle: ${report.cycle_id}`,`Account: ${cfg.account_key}`,`Saved: ${report.generated_at_utc}`,'','STRATEGY',`Connected PM: Ensemble PM`,`Source: ${report.pm_proposals?.ensemble?.diagnostics?.strategy?.repository||'Unavailable'}`,`Upstream contribution: ${report.pm_proposals?.ensemble?.diagnostics?.strategy?.upstream_commit||'Unavailable'}`,'','ACCOUNT AND TARGETS',`Marked fund value: ${money(nav)} (supplied confirmed snapshot)`,`Approved target gross: ${money(metrics.target_gross_usd)} (${pct(metrics.target_gross_fraction)} of NAV)`,`Fund risk: ${risk.status}`,`Recorded intention groups: ${(report.execution_receipts||[]).length}`,`Recorded fills: ${numeric(metrics.filled_orders)?metrics.filled_orders:'Unavailable'}`,'','PHANTOM BOOK',`Submitted gross: ${money(phantom?.proposed_gross_usd)}`,`Approved gross: ${money(phantom?.approved_gross_usd)}`,`Exposure removed: ${money(phantom?.throttled_gross_usd)}`,'Exposure reductions are not profit or money saved.','','COMMITTEE REVIEW',chair?.computed_memo?.summary||'No Chair record in this cycle.',`Model reply status: ${chair?.status||'Not recorded'}`,...Object.entries(report.pm_representatives||{}).map(([pm,m])=>`${pmTitle(pm)}: ${m.computed_memo?.summary||'No summary'} | ${m.status}`),'','BOUNDARY','Saved record-only fund prototype. Intentions do not become holdings or fills. Default computed diagnostics do not establish that an LLM ran. No consolidated fund return history is implemented.','',...(report.limitations||[])].join('\n');
}
function toast(message) {clearTimeout(toastTimer);$('#toast').textContent=message;$('#toast').hidden=false;toastTimer=setTimeout(()=>$('#toast').hidden=true,4200);}
function setMenu(open) {document.body.classList.toggle('menu-open',open);$('#menu-toggle').setAttribute('aria-expanded',String(open));$('#menu-toggle').setAttribute('aria-label',open?'Close navigation':'Open navigation');}
function focusManager() {
  if(!managerFocus)return false;
  const target=document.getElementById(`${managerFocus}-evidence`);managerFocus=null;
  if(target){target.scrollIntoView({block:'start'});return true;}return false;
}
function searchResults() {
  const q=$('#workspace-search').value.trim().toLowerCase();
  const pages=Object.entries(views).filter(([key,v])=>`${key} ${v[0]} ${v[1]}`.toLowerCase().includes(q));
  const reports=reportList.filter(r=>`${r.as_of} ${r.cycle_id} ${r.mode} ${basis(r.mode)} ${r.status}`.toLowerCase().includes(q)).slice(0,8);
  $('#search-results').innerHTML=(pages.length?'<div class="search-section">WORKSPACE</div>'+pages.map(([key,v])=>`<button class="search-result" data-search-view="${key}"><span>${esc(v[0])}</span><small>Open page →</small></button>`).join(''):'')+(reports.length?'<div class="search-section">SAVED EVIDENCE</div>'+reports.map(r=>`<button class="search-result" data-search-cycle="${esc(r.id)}"><span>${esc(r.as_of)}<small> · ${esc(basis(r.mode))} · ${esc(r.cycle_id.slice(0,8))}</small></span><small>Open cycle →</small></button>`).join(''):'')+(!pages.length&&!reports.length?empty('No matching pages or saved cycles. Try a valuation date or “risk”.'):'');
  document.querySelectorAll('[data-search-view]').forEach(b=>b.addEventListener('click',()=>{$('#search-dialog').close();location.hash=b.dataset.searchView;}));
  document.querySelectorAll('[data-search-cycle]').forEach(b=>b.addEventListener('click',()=>{$('#search-dialog').close();modeFilter='all';$('#mode-filter').value='all';selectedId=b.dataset.searchCycle;chooseFilteredReport();}));
}
const tour=[
  ['overview','Your fund at a glance','Start with the supplied account value and approved target exposure. Capital mandates are budgets, while confirmed holdings describe the actual account snapshot. The selected cycle’s label identifies invented or historical inputs.'],
  ['pms','Meet the specialist managers','The Ensemble PM combines trend following, momentum and mean reversion. Inspect the saved market regime, allocation weights and current target portfolio. A zero allocation marks a standby engine.'],
  ['risk','See what risk changed','Independent fund risk reviews gross exposure, symbol concentration, and drawdown. The Phantom Book records submitted and approved exposure. Removed gross is an exposure difference, not money saved.'],
  ['committee','Read the committee evidence','PM representatives and the Committee Chair inspect saved diagnostics after risk. Structured imported claims are checked against facts. Default computed summaries are clearly labeled when no model reply was imported.'],
  ['flow','Follow the two lanes','The quantitative lane produces targets and risk decisions. The advisory lane organizes evidence. Select each component to inspect the actual record connected to it.'],
  ['audit','Inspect the approval trail','Review the exact approval, confirmed account snapshot, and portfolio intention groups. Export an investor brief or the original JSON. This integration records zero fills and has no consolidated return history.'],
];
function renderTour() {
  const [view,title,text]=tour[tourIndex];$('#tour-progress').textContent=`INVESTOR WALKTHROUGH · ${tourIndex+1} OF ${tour.length}`;
  $('#tour-content').innerHTML=`<div class="tour-symbol">${icon(views[view][2])}</div><h2 id="tour-title">${title}</h2><p>${text}</p><button class="tour-open-screen" id="tour-open-screen">Open ${esc(views[view][0].toLowerCase())} →</button>`;
  $('#tour-back').disabled=tourIndex===0;$('#tour-next').textContent=tourIndex===tour.length-1?'Finish walkthrough':'Next step →';
  $('#tour-open-screen').addEventListener('click',()=>{location.hash=view;$('#tour-dialog').close();});
}

hydrateIcons();
$('#refresh').addEventListener('click',loadReports);
$('#cycle-select').addEventListener('change',()=>{selectedId=$('#cycle-select').value;loadSelected();});
$('#mode-filter').addEventListener('change',()=>{modeFilter=$('#mode-filter').value;chooseFilteredReport();});
$('#brief-export').addEventListener('click',()=>{if(report){download(`meridian-investor-brief-${report.as_of}-${report.cycle_id.slice(0,8)}.txt`,investorBrief());toast('Investor brief downloaded for the selected cycle.');}});
$('#menu-toggle').addEventListener('click',()=>setMenu(!document.body.classList.contains('menu-open')));
$('#mobile-backdrop').addEventListener('click',()=>setMenu(false));
$('#main-nav').addEventListener('click',e=>{if(e.target.closest('a'))setMenu(false);});
$('#search-open').addEventListener('click',()=>{$('#workspace-search').value='';searchResults();$('#search-dialog').showModal();$('#workspace-search').focus();});
$('#workspace-search').addEventListener('input',searchResults);
$('#tour-start').addEventListener('click',()=>{setMenu(false);tourIndex=0;renderTour();$('#tour-dialog').showModal();});
$('#tour-back').addEventListener('click',()=>{tourIndex=Math.max(0,tourIndex-1);renderTour();});
$('#tour-next').addEventListener('click',()=>{if(tourIndex===tour.length-1)$('#tour-dialog').close();else{tourIndex++;renderTour();}});
document.querySelectorAll('[data-close]').forEach(b=>b.addEventListener('click',()=>document.getElementById(b.dataset.close).close()));
document.addEventListener('keydown',e=>{if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='k'){e.preventDefault();if(!$('#tour-dialog').open&&!$('#search-dialog').open)$('#search-open').click();}if(e.key==='Escape')setMenu(false);});
document.addEventListener('click',e=>{const link=e.target.closest('[data-manager]');if(link){e.preventDefault();managerFocus=link.dataset.manager;if(location.hash==='#pms')focusManager();else location.hash='pms';}});
window.addEventListener('hashchange',()=>{render();if(!focusManager())window.scrollTo({top:0,behavior:'instant'});});
render();loadReports();
