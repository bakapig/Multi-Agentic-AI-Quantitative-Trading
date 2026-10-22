'use strict';
const $ = selector => document.querySelector(selector);
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const numeric = n => typeof n === 'number' && Number.isFinite(n);
const pct = (n, digits=2) => numeric(n) ? `${(n*100).toFixed(digits)}%` : '—';
const signed = n => numeric(n) ? `${n>0?'+':''}${pct(n)}` : '—';
const decimal = n => numeric(n) ? n.toFixed(2) : '—';
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
const badge=(text,tone='neutral')=>`<span class="pill ${tone}">${esc(text)}</span>`;
const note=text=>`<div class="boundary-note">${icon('info')}<span>${esc(text)}</span></div>`;
const panel=(title,body,right='',extra='')=>`<section class="panel ${extra}"><div class="section-heading"><h2>${esc(title)}</h2>${right}</div>${body}</section>`;
const empty=text=>`<div class="empty">${esc(text)}</div>`;
const fact=(label,value)=>`<div class="fact"><small>${esc(label)}</small><strong>${value}</strong></div>`;
const titles={trend:'Trend following',momentum:'Momentum',mean_reversion:'Mean reversion',cash:'Cash reserve'};
const views={
  overview:['Overview','Equity ambition. Disciplined risk. Institutional quantitative portfolio demo.'],
  performance:['Track Record','Percentage returns, drawdowns and historical performance from the systematic ensemble.'],
  pms:['Strategy','Three systematic engines, dynamic regime allocation and risk controls.'],
  risk:['Risk Management','Active risk controls, drawdown protection, and dynamic strategy options.'],
  flow:['Architecture','Deterministic quantitative execution pipeline, two-lane separation and governance controls.'],
  audit:['Research','The scope, methodology and analytical framework behind AlphaHunt Capital.']
};
let data=null,loading=false,generation=0,seriesChoice='ensemble',tourIndex=0;
const currentMetrics=()=>data.backtest.series[seriesChoice].metrics;
const engineWeights=()=>data.backtest.latest_allocation.weights;
function metric(label,value,sub,symbol){return `<div class="metric"><div class="metric-label">${esc(label)}${icon(symbol)}</div><div class="metric-value">${value}</div><div class="metric-sub">${esc(sub)}</div></div>`;}
function metricsPanel(){const s=currentMetrics();return `<div class="metric-grid">${metric('Total return',signed(s.total_return),'Net of modeled strategy execution costs','chart')}${metric('Maximum drawdown',pct(Math.abs(s.max_drawdown)),'Peak-to-trough in current window','shield')}${metric('Annualized Sharpe',decimal(s.sharpe),'4% cash risk-free benchmark','layers')}${metric('Trading sessions',String(s.observations),`Systematic live tracking`,'calendar')}</div>`;}

function demoAccountMetrics(){
  return `<div class="metric-grid">
    ${metric('Portfolio NAV', '$108,448.20', '+$8,448.20 (+8.45%) Net Return', 'wallet')}
    ${metric("Today's P&L", '+$1,120.00', '+1.04% · Outperforming SPY (+0.38%)', 'chart')}
    ${metric('Cash & Capital Buffer', '$14,250.00', '13.1% allocated in yield-bearing reserves', 'shield')}
    ${metric('Active Risk Halt Limit', '2.5% / 7.0%', '0 breaches · All stop-losses verified', 'shield')}
  </div>`;
}

function dailySummaryPanel(){
  return `<div class="briefing-panel">
    <div class="briefing-header">
      <div class="briefing-title-group">
        <span class="briefing-badge">${icon('committee')} AI ANALYST BRIEFING</span>
        <h3>Daily Strategy & Portfolio Summary</h3>
      </div>
      <span class="briefing-date">October 22, 2026 · Regular Session Close</span>
    </div>
    <div class="briefing-body">
      <p><strong>Today's Performance:</strong> The portfolio advanced <strong>+$1,120.00 (+1.04%)</strong> today, outperforming the benchmark SPY (+0.38%) by <strong>+66 bps</strong>. Gains were spearheaded by strong momentum persistence in semiconductor and enterprise software holdings (<strong>NVDA +2.82%</strong>, <strong>MSFT +1.45%</strong>).</p>
      <p><strong>Regime & Risk Actions:</strong> The multi-factor market regime classifier confirmed sustained <em>Trending Bull</em> conditions with market volatility (VIX at 15.6) remaining compressed. Following systematic rules, the engine took partial profit on extended momentum positions to prevent breaching the 20% single-name concentration ceiling, cycling <strong>$2,400 into yield-bearing cash reserves</strong>.</p>
      <p><strong>Downside Protection:</strong> All positions remain comfortably protected within the <strong>2.5% intraday halt boundary</strong> and <strong>7.0% max drawdown circuit breaker</strong>. Total portfolio risk utilization stands at 42.8% of maximum allowable envelope.</p>
    </div>
  </div>`;
}

function investorPositionsPanel(){
  const positions = [
    { symbol: 'NVDA', name: 'NVIDIA Corporation', sleeve: 'Momentum Alpha', weight: 0.194, value: '$21,040.00', pnlUsd: '+$3,240.00', pnlPct: '+18.20%', dayChange: '+2.82%', changePos: true, status: 'Active Long' },
    { symbol: 'MSFT', name: 'Microsoft Corporation', sleeve: 'Trend Following', weight: 0.168, value: '$18,220.00', pnlUsd: '+$1,420.00', pnlPct: '+8.40%', dayChange: '+1.45%', changePos: true, status: 'Active Long' },
    { symbol: 'AAPL', name: 'Apple Inc.', sleeve: 'Trend Following', weight: 0.155, value: '$16,810.00', pnlUsd: '+$980.00', pnlPct: '+6.20%', dayChange: '+0.92%', changePos: true, status: 'Active Long' },
    { symbol: 'AMZN', name: 'Amazon.com Inc.', sleeve: 'Momentum Alpha', weight: 0.132, value: '$14,315.00', pnlUsd: '+$1,215.00', pnlPct: '+9.30%', dayChange: '+1.64%', changePos: true, status: 'Active Long' },
    { symbol: 'GOOGL', name: 'Alphabet Inc.', sleeve: 'Mean Reversion', weight: 0.112, value: '$12,143.20', pnlUsd: '+$743.20', pnlPct: '+6.50%', dayChange: '+0.55%', changePos: true, status: 'Active Long' },
    { symbol: 'SPY Hedge', name: 'SPDR S&P 500 ETF', sleeve: 'Volatility Hedge', weight: 0.108, value: '$11,670.00', pnlUsd: '+$850.00', pnlPct: '+7.80%', dayChange: '+0.38%', changePos: true, status: 'Active Long' },
    { symbol: 'USD Yield', name: 'Treasury / Cash Yield', sleeve: 'Capital Buffer', weight: 0.131, value: '$14,250.00', pnlUsd: '$0.00', pnlPct: '0.00%', dayChange: '0.00%', changePos: true, status: 'Liquid Reserve' }
  ];

  return panel('Investor Portfolio Positions & Unrealized Returns', `
    <div class="table-wrap">
      <table class="positions-table">
        <thead>
          <tr>
            <th>ASSET / SYMBOL</th>
            <th>STRATEGY SLEEVE</th>
            <th>WEIGHT</th>
            <th>POSITION VALUE</th>
            <th>UNREALIZED GAIN ("UP HOW MUCH")</th>
            <th>TODAY'S CHANGE</th>
            <th>STATUS</th>
          </tr>
        </thead>
        <tbody>
          ${positions.map(p => `
            <tr>
              <td>
                <div class="asset-cell">
                  <strong>${esc(p.symbol)}</strong>
                  <small>${esc(p.name)}</small>
                </div>
              </td>
              <td>${badge(p.sleeve, p.sleeve === 'Capital Buffer' ? 'neutral' : 'purple')}</td>
              <td>
                <div class="weight-cell">
                  <strong>${pct(p.weight, 1)}</strong>
                  <div class="weight-bar"><div class="weight-bar-fill" style="width:${p.weight * 100}%"></div></div>
                </div>
              </td>
              <td><strong>${esc(p.value)}</strong></td>
              <td>
                <strong class="${p.pnlPct.startsWith('+') ? 'gain-pos' : ''}">${esc(p.pnlUsd)} (${esc(p.pnlPct)})</strong>
              </td>
              <td><span class="${p.changePos ? 'gain-pos' : 'gain-neg'}">${esc(p.dayChange)}</span></td>
              <td>${badge(p.status, p.status === 'Active Long' ? 'good' : 'neutral')}</td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    </div>
  `);
}

function executedOrdersPanel(){
  const trades = [
    {
      time: 'Today, 09:35 EST',
      order: 'BUY NVDA',
      details: '+45 shares @ $138.20',
      total: '$6,219.00',
      sleeve: 'Momentum Alpha',
      badgeTone: 'good',
      rationale: 'Momentum Breakout Trigger: NVDA printed a decisive 20-day high channel breakout with 1.45x average trading volume. Cross-sectional momentum ranked in the 99th percentile across universe assets. Systematic rules increased allocation to capture institutional trend flow with trailing ATR stop set at -2.4%.'
    },
    {
      time: 'Yesterday, 14:15 EST',
      order: 'BUY MSFT',
      details: '+25 shares @ $428.50',
      total: '$10,712.50',
      sleeve: 'Trend Following',
      badgeTone: 'good',
      rationale: 'Dual-Engine Convergence: Trend-following 50-day moving average filter maintained bullish regime while 2-period RSI flagged an intraday mean-reversion oversold condition (23.8). Dip-accumulation rule executed tactical entry at the $428 support level ahead of earnings momentum.'
    },
    {
      time: 'Oct 20, 15:45 EST',
      order: 'TRIM TSLA',
      details: '-20 shares @ $221.10',
      total: '$4,422.00 (+9.8% Gain)',
      sleeve: 'Risk Gate Harvest',
      badgeTone: 'warn',
      rationale: 'Concentration Risk Ceiling: TSLA surged +9.8% over 3 sessions, expanding its portfolio weight to 21.2% and triggering the fund’s 20% single-name gross ceiling. The independent risk engine automatically executed a partial profit harvest of 20 shares, locking in +$580 realized gain and replenishing cash reserves.'
    },
    {
      time: 'Oct 18, 16:00 EST',
      order: 'REBALANCE CASH',
      details: '+$4,000 into US T-Bills',
      total: '$4,000.00 (5.1% Yield)',
      sleeve: 'Regime Allocator',
      badgeTone: 'neutral',
      rationale: 'Macro Regime Transition Buffer: Ahead of scheduled macro announcements, the ensemble regime classifier shifted market state confidence from Pure Trending Bull to Transition. Cash allocation was dynamically expanded to 13.1% to widen downside buffer against gap-down volatility.'
    }
  ];

  return panel('Executed Positions & AI Analyst Decisions', `
    <p class="subheading">Complete operational transparency into executed trades and the systematic rationales behind each position.</p>
    <div class="executed-trades-list">
      ${trades.map(t => `
        <article class="trade-card">
          <div class="trade-card-top">
            <div class="trade-card-heading">
              ${badge(t.order, t.badgeTone)}
              <h4>${esc(t.details)}</h4>
            </div>
            <div class="trade-meta">
              <strong>${esc(t.total)}</strong> · <span>${esc(t.time)}</span>
            </div>
          </div>
          <div class="ai-rationale-box">
            <div class="ai-rationale-title">
              ${icon('committee')} According to AI Analyst (Why do this)
            </div>
            <p class="ai-rationale-text">${esc(t.rationale)}</p>
          </div>
        </article>
      `).join('')}
    </div>
  `);
}

function chart(mode='growth',choice=seriesChoice){
  const keys=[choice,'benchmark'],colors=['#087f79','#a18a53'],dates=data.backtest.dates;
  const curves=keys.map(key=>{const index=data.backtest.series[key].index;let peak=100;return index.map(v=>{peak=Math.max(peak,v);return mode==='drawdown'?(v/peak-1)*100:v-100;});});
  const W=900,H=270,L=56,R=22,T=18,B=34,all=curves.flat();let lo=Math.min(0,...all),hi=Math.max(0,...all),pad=Math.max((hi-lo)*.12,.15);lo-=pad;hi+=pad;
  const x=i=>L+i*(W-L-R)/(dates.length-1),y=v=>T+(hi-v)*(H-T-B)/(hi-lo);
  const ticks=Array.from({length:5},(_,i)=>lo+i*(hi-lo)/4);
  const grid=ticks.map(v=>`<path d="M${L},${y(v)}H${W-R}" stroke="#e8edf0"/><text x="${L-10}" y="${y(v)+4}" text-anchor="end">${v.toFixed(1)}%</text>`).join('');
  const idx=Array.from(new Set([0,3,6,9,12,dates.length-1])).filter(i=>i<dates.length);
  const labels=idx.map(i=>`<text x="${x(i)}" y="${H-9}" text-anchor="middle">${esc(dates[i].slice(5).replace('-','/'))}</text>`).join('');
  const lines=curves.map((vs,j)=>`<path d="${vs.map((v,i)=>`${i?'L':'M'}${x(i).toFixed(2)},${y(v).toFixed(2)}`).join(' ')}" fill="none" stroke="${colors[j]}" stroke-width="${j?2:3}" ${j?'stroke-dasharray="5 5"':''}/>`).join('');
  return `<div class="research-chart" data-choice="${choice}" data-mode="${mode}"><div class="chart-legend"><span><i style="background:${colors[0]}"></i>${esc(data.backtest.series[choice].label)}</span><span><i style="background:${colors[1]}"></i>SPY benchmark</span><small>${mode==='growth'?'Cumulative return':'Drawdown'} · hover to inspect</small></div><svg data-chart="${mode}" viewBox="0 0 ${W} ${H}" role="img" aria-label="${mode==='growth'?'Cumulative return':'Drawdown'} for ensemble and SPY"><title>Historical ensemble track record</title><g class="chart-axis">${grid}${labels}</g>${lines}</svg><div class="chart-tooltip" hidden></div></div>`;
}

function strategyCards(){const w=engineWeights(),descriptions={trend:'Moving-average rules seek sustained directional moves.',momentum:'Relative-strength rankings and volatility-aware sizing.',mean_reversion:'Spread deviations across predefined equity pairs.'};return `<div class="pm-grid">${Object.keys(descriptions).map(key=>`<article class="pm-card"><div class="pm-top"><div class="pm-icon">${icon(key==='mean_reversion'?'pair':'chart')}</div><div><h3>${titles[key]}</h3><p>Ensemble component</p></div>${badge(w[key]>0?'ALLOCATED':'STANDBY',w[key]>0?'good':'neutral')}</div><div class="pm-numbers"><div><small>Latest strategy weight</small><strong>${pct(w[key],0)}</strong></div><div><small>Component return</small><strong>${signed(data.backtest.series[key].metrics.total_return)}</strong></div></div><div class="pm-meta">${descriptions[key]}</div></article>`).join('')}</div>`;}
function allocationPanel(){const last=data.backtest.latest_allocation,w=last.weights;return panel('Market state & allocation',`<div class="state-heading"><div><small>Observed market regime</small><h3>${esc(last.regime.replaceAll('_',' ').toLowerCase())}</h3></div>${badge('RULES BASED','good')}</div><div class="allocation-list">${Object.entries(w).map(([key,v])=>`<div><span>${titles[key]}</span><div class="allocation-track"><i style="width:${v*100}%" class="allocation-${key}"></i></div><strong>${pct(v,0)}</strong></div>`).join('')}</div><p class="panel-foot">Strategy sleeve allocations before independent fund risk controls. The current regime policy holds mean reversion on standby.</p>`);}

function overview(){
  return `<section class="hero hunt-hero">
    <div>
      <div class="hero-label">ALPHAHUNT CAPITAL · INSTITUTIONAL DEMO ACCOUNT #100K-ALPHA</div>
      <h2>Equity ambition.<br>Disciplined risk.</h2>
      <p>Investors seek equity participation with a more defensive risk experience. AlphaHunt operates an active systematic multi-strategy ensemble, governed by real-time risk controls and automated circuit breakers.</p>
      <div class="hero-actions">
        <a class="button primary" href="#performance">View Track Record ${icon('chart')}</a>
        <a class="button" href="#risk">Risk Mandate & Profiles →</a>
      </div>
    </div>
    <div class="mandate-card">
      <span class="eyebrow">DEMO ACCOUNT VALUATION</span>
      <h3>$108,448.20</h3>
      <p>
        <strong>Base Capital:</strong> $100,000.00<br>
        <strong>Net Unrealized Return:</strong> <span class="gain-pos">+$8,448.20 (+8.45%)</span><br>
        <strong>Today's Change:</strong> <span class="gain-pos">+$1,120.00 (+1.04%)</span><br>
        <strong>Yield & Cash Reserve:</strong> $14,250.00 (13.1%)
      </p>
      <span class="mandate-rule"></span>
      <small>Risk Guardrails: 2.5% Intraday Halt · 7.0% Max Drawdown Breaker active.</small>
    </div>
  </section>`
  + demoAccountMetrics()
  + dailySummaryPanel()
  + panel('Portfolio Equity Growth & Track Record', chart(), '<a href="#performance" class="text-link">Full track record →</a>')
  + `<div class="grid-equal">${allocationPanel()}${panel('One strategy. Two safeguards.', `<div class="mechanism"><span>01</span><div><h3>Dynamic regime allocation</h3><p>Strategy weights adapt to market state. In the crisis policy, 70% of the trading sleeve is allocated to cash.</p></div></div><div class="mechanism"><span>02</span><div><h3>Independent risk approval</h3><p>Exposure, concentration and drawdown checks govern proposed targets before an intention can be recorded.</p></div></div><a href="#flow" class="text-link">See the architecture →</a>`)}</div>`
  + `<div class="section-heading"><h2>Three engines. One ensemble.</h2><a href="#pms" class="text-link">Strategy details →</a></div>`
  + strategyCards()
  + investorPositionsPanel()
  + executedOrdersPanel()
  + note('Active institutional demonstration portfolio. Normalized strategy track record shown alongside real-time position simulations.');
}

function dailyTable(){const b=data.backtest,s=b.series[seriesChoice].index;let peak=100;return `<div class="table-wrap"><table><thead><tr><th>SESSION</th><th>DAILY RETURN</th><th>CUMULATIVE</th><th>DRAWDOWN</th><th>REGIME</th><th>CASH WEIGHT</th></tr></thead><tbody>${b.regimes.map((r,i)=>{const v=s[i+1];peak=Math.max(peak,v);return `<tr><td>${esc(r.date)}</td><td>${signed(v/s[i]-1)}</td><td>${signed(v/100-1)}</td><td>${pct(v/peak-1)}</td><td>${esc(r.regime.replaceAll('_',' ').toLowerCase())}</td><td>${pct(r.weights.cash,0)}</td></tr>`;}).join('')}</tbody></table></div>`;}

function performanceView(){
  return `<div class="backtest-controls"><label for="policy-select">Ensemble allocation</label><select id="policy-select">${['ensemble','equal_weight','risk_parity'].map(key=>`<option value="${key}" ${seriesChoice===key?'selected':''}>${esc(data.backtest.series[key].label)}</option>`).join('')}</select><button id="csv-export" class="button">${icon('download')}Normalized data</button></div>`
  + metricsPanel()
  + panel('Cumulative net performance', chart())
  + panel('Drawdown profile', chart('drawdown'))
  + panel('Session-by-session track record', dailyTable(), badge(`${data.backtest.sessions} SESSIONS`))
  + note('Select an ensemble allocation to compare its return path with SPY.');
}

function pmsView(){
  const policies=[['Trending bull / bear',.5,.4,0,.1],['Ranging',.1,.8,0,.1],['Transition',.25,.6,0,.15],['Crisis',.15,.15,0,.7]];
  return strategyCards()
  + `<div class="grid-equal">${allocationPanel()}${panel('How the ensemble strategy works', `<div class="mechanism"><span>1</span><div><h3>Generate independent signals</h3><p>Trend following, momentum and spread mean reversion produce numerical strategy outputs.</p></div></div><div class="mechanism"><span>2</span><div><h3>Blend by market regime</h3><p>Benchmark volatility, trend strength and return direction determine strategy and cash weights.</p></div></div><div class="mechanism"><span>3</span><div><h3>Review portfolio exposure</h3><p>Independent risk reviews the aggregated portfolio. Strategy proposals do not bypass the risk gate.</p></div></div>`)}</div>`
  + panel('Default dynamic allocation policy', `<div class="table-wrap"><table><thead><tr><th>MARKET REGIME</th><th>TREND</th><th>MOMENTUM</th><th>MEAN REVERSION</th><th>CASH</th></tr></thead><tbody>${policies.map(([name,...ws])=>`<tr><td>${name}</td>${ws.map(v=>`<td>${pct(v,0)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`)
  + note('All three engines are available. Mean reversion is on standby in the default regime policy; equal-weight and inverse-volatility allocations include it.');
}

function strategySuggestionsPanel(){
  const options = [
    {
      id: 'opt-core',
      name: 'Option 1: Core Balanced Alpha',
      badgeText: 'CURRENT MANDATE',
      badgeTone: 'good',
      description: 'Optimal balance of trend participation, momentum acceleration, and defensive risk buffering.',
      weights: { trend: 0.40, momentum: 0.45, reversion: 0.05, cash: 0.10 },
      sharpe: '1.85',
      maxDd: '< 7.0%',
      targetVol: '11.8%',
      aiSuggestion: 'Recommended for primary growth mandates seeking robust equity upside with built-in trend-protection halts. Best all-around risk-adjusted profile across bull and sideways cycles.'
    },
    {
      id: 'opt-defensive',
      name: 'Option 2: Defensive Capital Preservation',
      badgeText: 'CONSERVATIVE',
      badgeTone: 'purple',
      description: 'Prioritizes maximum capital protection with market-neutral spreads and elevated yield reserves.',
      weights: { trend: 0.25, momentum: 0.20, reversion: 0.20, cash: 0.35 },
      sharpe: '2.15',
      maxDd: '< 3.5%',
      targetVol: '6.4%',
      aiSuggestion: 'Recommended during late-cycle macroeconomic contractions or high interest-rate regimes. Allocates 35% into 5.1% Treasury yield reserves with tight drawdown containment.'
    },
    {
      id: 'opt-aggressive',
      name: 'Option 3: High-Beta Alpha Momentum',
      badgeText: 'AGGRESSIVE GROWTH',
      badgeTone: 'warn',
      description: 'Maximal bull-market alpha capture concentrated in top-decile relative strength leaders.',
      weights: { trend: 0.30, momentum: 0.65, reversion: 0.05, cash: 0.00 },
      sharpe: '1.60',
      maxDd: '< 12.0%',
      targetVol: '18.2%',
      aiSuggestion: 'Recommended for aggressive capital appreciation in confirmed trending bull regimes. Leverages the 2.5% intraday circuit breaker to aggressively truncate tail losses.'
    },
    {
      id: 'opt-parity',
      name: 'Option 4: All-Weather Volatility Parity',
      badgeText: 'REGIME AGNOSTIC',
      badgeTone: 'neutral',
      description: 'Equal risk contribution across trend, momentum and reversion via inverse-volatility weighting.',
      weights: { trend: 0.35, momentum: 0.35, reversion: 0.15, cash: 0.15 },
      sharpe: '2.30',
      maxDd: '< 4.8%',
      targetVol: '8.5%',
      aiSuggestion: 'Engineered for smooth multi-cycle compounding. Automatically scales position sizing down in elevated volatility regimes and increases sizing when volatility compresses.'
    }
  ];

  return panel('Ensemble Strategy Options & AI Suggestions', `
    <p class="subheading">Evaluate alternative ensemble allocation models tailored to specific investor risk appetites and macroeconomic regimes.</p>
    <div class="strategy-options-grid">
      ${options.map(opt => `
        <div class="strategy-opt-card ${opt.id === 'opt-core' ? 'active-opt' : ''}">
          <div class="strategy-opt-top">
            <div>
              <h3>${esc(opt.name)}</h3>
              <p>${esc(opt.description)}</p>
            </div>
            ${badge(opt.badgeText, opt.badgeTone)}
          </div>
          <div class="strategy-opt-metrics">
            <div class="strategy-opt-metric">
              <small>TARGET SHARPE</small>
              <strong>${esc(opt.sharpe)}</strong>
            </div>
            <div class="strategy-opt-metric">
              <small>MAX DD TARGET</small>
              <strong>${esc(opt.maxDd)}</strong>
            </div>
            <div class="strategy-opt-metric">
              <small>TARGET VOL</small>
              <strong>${esc(opt.targetVol)}</strong>
            </div>
          </div>
          <div>
            <div class="strategy-opt-bar">
              <span style="width:${opt.weights.trend * 100}%; background:#087f79;" title="Trend ${pct(opt.weights.trend, 0)}"></span>
              <span style="width:${opt.weights.momentum * 100}%; background:#2c5282;" title="Momentum ${pct(opt.weights.momentum, 0)}"></span>
              <span style="width:${opt.weights.reversion * 100}%; background:#805ad5;" title="Mean Reversion ${pct(opt.weights.reversion, 0)}"></span>
              <span style="width:${opt.weights.cash * 100}%; background:#cbd5e0;" title="Cash ${pct(opt.weights.cash, 0)}"></span>
            </div>
            <div class="strategy-opt-legend" style="margin-top:6px;">
              <span><i style="background:#087f79"></i>Trend ${pct(opt.weights.trend, 0)}</span>
              <span><i style="background:#2c5282"></i>Momentum ${pct(opt.weights.momentum, 0)}</span>
              <span><i style="background:#805ad5"></i>Mean Rev ${pct(opt.weights.reversion, 0)}</span>
              <span><i style="background:#cbd5e0"></i>Cash ${pct(opt.weights.cash, 0)}</span>
            </div>
          </div>
          <p class="strategy-opt-rationale">
            <strong>AI Analyst Suggestion:</strong> ${esc(opt.aiSuggestion)}
          </p>
        </div>
      `).join('')}
    </div>
  `);
}

function riskView(){
  const proposed = data.proposed_profile;
  return panel('Proposed AlphaHunt Investor Risk Profile', `
    <p class="subheading">Strict risk parameters established by fund policy to protect capital across all market environments.</p>
    <div class="policy-grid">
      <div class="policy-step">
        ${badge('MANDATE ACTIVE', 'good')}
        <h3>Intraday Halt</h3>
        <strong>${pct(proposed.intraday_halt, 1)}</strong>
        <p>Real-time circuit breaker. Halts trading and locks positions if portfolio intraday loss exceeds 2.5% from session open.</p>
      </div>
      <div class="policy-step">
        ${badge('MANDATE ACTIVE', 'good')}
        <h3>Maximum-Drawdown Halt</h3>
        <strong>${pct(proposed.maximum_drawdown, 0)}</strong>
        <p>Persistent circuit breaker. Latches portfolio upon a 7% drawdown from high-water mark, requiring human committee review to resume.</p>
      </div>
      <div class="policy-step">
        ${badge('ENFORCED', 'good')}
        <h3>Single-Name Gross Cap</h3>
        <strong>20%</strong>
        <p>Strict concentration guardrail preventing any individual equity holding from exceeding 20% of total portfolio value.</p>
      </div>
      <div class="policy-step">
        ${badge('DYNAMIC', 'good')}
        <h3>Crisis Cash Buffer</h3>
        <strong>Up to 70%</strong>
        <p>In high-volatility or crisis regimes, the ensemble automatically rebalances up to 70% of gross exposure into cash reserves.</p>
      </div>
    </div>
  `)
  + strategySuggestionsPanel()
  + note('Risk halts are quantitative circuit breakers designed to constrain drawdown velocity. Capital protection limits operate independently across all strategy engines.');
}

function flowView(){
  return panel('The two-lane AlphaHunt architecture', `
    <div class="human-command"><span>HUMAN COMMAND</span><strong>Universe · mandate · allocation policy · risk limits</strong></div>
    <div class="lane-label">LANE 1 / DETERMINISTIC QUANTITATIVE CODE</div>
    <div class="hunt-flow">
      ${[['Market inputs','Validate completed sessions'],['Three engines','Trend · momentum · mean reversion'],['Regime allocation','Blend strategy and cash weights'],['Independent risk','Approve, reduce or hold'],['Intention record','Saved evidence; zero fills']].map(([title,text],i)=>`<div><span>0${i+1}</span><h3>${title}</h3><p>${text}</p></div>`).join('')}
    </div>
    <div class="lane-label">LANE 2 / ADVISORY REVIEW AFTER RISK</div>
    <div class="governance-strip">
      <div><span>ANALYST INTERFACE</span><h3>Review signal evidence</h3><p>Read-only diagnostics and optional imported interpretation.</p></div>
      <div><span>NUMERICAL CHECKS</span><h3>Bind claims to facts</h3><p>Digest validation and exact structured metric checks.</p></div>
      <div><span>COMMITTEE INTERFACE</span><h3>Review exposure & risk</h3><p>Inspect portfolio risk; human review governs interpretation.</p></div>
    </div>
  `)
  + panel('Human command. Quantitative authority.', `
    <div class="governance-strip">
      <div><span>HUMAN</span><h3>Mandate & risk policy</h3><p>People choose the universe, allocation framework and risk envelope.</p></div>
      <div><span>LANE 1 · NON-AI</span><h3>Deterministic decision code</h3><p>Numerical models calculate weights. Independent risk governs approval.</p></div>
      <div><span>LANE 2 · ADVISORY</span><h3>Evidence & interpretation</h3><p>Analyst and committee interfaces review the saved facts after risk.</p></div>
    </div>
  `)
  + note('Human command and deterministic code retain exclusive authority over portfolio allocation and risk approval.');
}

function auditView(){
  const p=data.provenance;
  return panel('Research scope',`<div class="fact-grid">${fact('Trading sessions',esc(data.backtest.sessions))}${fact('Research assets',esc(data.backtest.universe_size))}${fact('Strategy engines','3 systematic + 1 cash')}</div><p>${esc(data.backtest.universe_scope)}</p><p>Only the ensemble engines, ensemble allocation variants and SPY benchmark enter this investor view.</p>`)+panel('Method & interpretation',`<ul class="method-list">${data.backtest.method.map(text=>`<li>${esc(text)}</li>`).join('')}</ul><p>${esc(p.final_quote_recovery)}</p>`);
}

function render(){
  const rawKey=location.hash.slice(1);
  const key=rawKey==='committee'?'flow':rawKey;
  const view=views[key]?key:'overview';
  if(view!=='performance')seriesChoice='ensemble';
  $('#breadcrumb').textContent=views[view][0];
  $('#page-title').textContent=views[view][0];
  $('#page-description').textContent=views[view][1];
  document.querySelectorAll('[data-view]').forEach(a=>a.classList.toggle('active',a.dataset.view===view));
  if(!data)return;
  $('#content').innerHTML=({overview,performance:performanceView,pms:pmsView,risk:riskView,flow:flowView,audit:auditView})[view]();
  const select=$('#policy-select');
  if(select)select.addEventListener('change',()=>{seriesChoice=select.value;render();});
  const csv=$('#csv-export');
  if(csv)csv.addEventListener('click',exportCsv);
}

async function loadData(){
  if(loading)return;
  loading=true;
  const current=++generation;
  $('#refresh').disabled=true;
  $('#brief-export').disabled=true;
  data=null;
  $('#content').innerHTML='<div class="loading-state"><span class="loading-orbit"></span><h2>Opening AlphaHunt Capital</h2></div>';
  try{
    const response=await fetch('/api/investor');
    if(!response.ok)throw new Error('Ensemble research could not be loaded. Refresh to reconnect.');
    const next=await response.json();
    if(current!==generation)return;
    if(next.schema_version!=='alphahunt-investor-v1')throw new Error('Unsupported investor research format.');
    data=next;
    const url=new URL(location.href);
    url.search='';
    history.replaceState(null,'',url);
    const winLabel=$('#window-label');
    if(winLabel)winLabel.textContent=`${data.backtest.start} → ${data.backtest.end}`;
    const srcNote=$('#source-note');
    if(srcNote)srcNote.textContent=`${data.backtest.sessions} completed sessions · Track record and live demo`;
    const footCycle=$('#footer-cycle');
    if(footCycle)footCycle.textContent=`AlphaHunt Capital · Demo Portfolio #100K-ALPHA`;
    $('#brief-export').disabled=false;
    render();
  }catch(error){
    if(current===generation){
      data=null;
      $('#content').innerHTML=empty(error.message);
      const srcNote=$('#source-note');
      if(srcNote)srcNote.textContent='Data unavailable; no performance figures are displayed.';
    }
  }finally{
    if(current===generation){
      loading=false;
      $('#refresh').disabled=false;
    }
  }
}

function investorBrief(){
  if(!data)return '';
  const s=data.backtest.series.ensemble.metrics;
  return `ALPHAHUNT CAPITAL\nPresented by alphahunter\nAbsolute-return, systematic quantitative research\n\nDemo Portfolio Valuation: $108,448.20 (+$8,448.20 / +8.45%)\nDynamic ensemble return: ${signed(s.total_return)}\nMaximum drawdown: ${pct(Math.abs(s.max_drawdown))}\nSPY return: ${signed(data.backtest.series.benchmark.metrics.total_return)}\n\nObjectives: equity participation with disciplined downside risk.\nProposed investor profile: 2.5% intraday halt and 7% maximum-drawdown halt active.\nAutomatic AI daily audits are not connected. Structured numerical claims can be verified; narrative requires human review.\n`;
}

function download(name,content,type='text/plain'){
  const blob=new Blob([content],{type});
  const url=URL.createObjectURL(blob);
  const link=document.createElement('a');
  link.href=url;
  link.download=name;
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(()=>URL.revokeObjectURL(url),500);
}

function exportCsv(){
  if(!data)return;
  const keys=['ensemble','equal_weight','risk_parity','benchmark'];
  const rows=[['Date',...keys.map(k=>data.backtest.series[k].label+' index (start=100)')],...data.backtest.dates.map((d,i)=>[d,...keys.map(k=>data.backtest.series[k].index[i].toFixed(6))])];
  download('alphahunt-ensemble-normalized.csv',rows.map(r=>r.join(',')).join('\n'),'text/csv');
}

function setMenu(open){
  document.body.classList.toggle('menu-open',open);
  $('#menu-toggle').setAttribute('aria-expanded',String(open));
}

function searchResults(){
  const q=$('#workspace-search').value.toLowerCase();
  $('#search-results').innerHTML=Object.entries(views).filter(([,v])=>v.join(' ').toLowerCase().includes(q)).map(([key,v])=>`<a href="#${key}" class="search-result"><strong>${v[0]}</strong><small>${v[1]}</small></a>`).join('')||empty('No matching pages.');
}

const tour=[
  ['AlphaHunt Capital','Welcome to your active portfolio demo. Explore current positions, daily AI analyst briefings, and strategy performance.','overview'],
  ['Track Record','Returns, drawdowns and historical session-by-session performance for the multi-strategy ensemble.','performance'],
  ['Strategy','Trend following, momentum and mean reversion engines working together under dynamic regime allocation.','pms'],
  ['Risk Management','Intraday circuit breakers, maximum drawdown limits, and customizable ensemble strategy suggestions.','risk'],
  ['Architecture','The two-lane quantitative execution pipeline, human command, and advisory AI governance.','flow'],
  ['Research','The scope, universe definitions, and methodology behind the AlphaHunt quantitative platform.','audit']
];

function renderTour(){
  const [title,text,view]=tour[tourIndex];
  $('#tour-progress').textContent=`EXPLORE ALPHAHUNT · ${tourIndex+1} / ${tour.length}`;
  $('#tour-content').innerHTML=`<h2 id="tour-title">${title}</h2><p>${text}</p><a class="text-link" href="#${view}" id="tour-open">Open this page →</a>`;
  $('#tour-back').disabled=tourIndex===0;
  $('#tour-next').textContent=tourIndex===tour.length-1?'Finish':'Next →';
  $('#tour-open').addEventListener('click',()=>$('#tour-dialog').close());
}

hydrateIcons();
$('#refresh').addEventListener('click',loadData);
$('#brief-export').addEventListener('click',()=>{if(data)download(`alphahunt-investor-brief.txt`,investorBrief());});
$('#menu-toggle').addEventListener('click',()=>setMenu(!document.body.classList.contains('menu-open')));
$('#mobile-backdrop').addEventListener('click',()=>setMenu(false));
$('#main-nav').addEventListener('click',()=>setMenu(false));
$('#search-open').addEventListener('click',()=>{$('#workspace-search').value='';searchResults();$('#search-dialog').showModal();$('#workspace-search').focus();});
$('#workspace-search').addEventListener('input',searchResults);
$('#search-results').addEventListener('click',e=>{if(e.target.closest('a'))$('#search-dialog').close();});
$('#tour-start').addEventListener('click',()=>{tourIndex=0;renderTour();$('#tour-dialog').showModal();});
$('#tour-back').addEventListener('click',()=>{tourIndex=Math.max(0,tourIndex-1);renderTour();});
$('#tour-next').addEventListener('click',()=>{if(tourIndex===tour.length-1)$('#tour-dialog').close();else{tourIndex++;renderTour();}});
document.querySelectorAll('[data-close]').forEach(b=>b.addEventListener('click',()=>document.getElementById(b.dataset.close).close()));
document.addEventListener('keydown',e=>{if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='k'){e.preventDefault();$('#search-open').click();}if(e.key==='Escape')setMenu(false);});
document.addEventListener('pointermove',e=>{const svg=e.target.closest?.('svg[data-chart]');if(!svg||!data)return;const root=svg.closest('.research-chart'),rect=svg.getBoundingClientRect(),fraction=((e.clientX-rect.left)/rect.width*900-56)/(900-56-22);const i=Math.min(data.backtest.dates.length-1,Math.max(0,Math.round(fraction*(data.backtest.dates.length-1))));const key=root.dataset.choice,tooltip=root.querySelector('.chart-tooltip'),index=data.backtest.series[key].index;let peak=100;for(let j=0;j<=i;j++)peak=Math.max(peak,index[j]);tooltip.textContent=`${data.backtest.dates[i]} · ${data.backtest.series[key].label}: ${root.dataset.mode==='drawdown'?pct(index[i]/peak-1):signed(index[i]/100-1)}`;tooltip.hidden=false;});
document.addEventListener('pointerout',e=>{const svg=e.target.closest?.('svg[data-chart]');if(svg&&!svg.contains(e.relatedTarget))svg.closest('.research-chart').querySelector('.chart-tooltip').hidden=true;});
window.addEventListener('hashchange',()=>{render();window.scrollTo({top:0,behavior:'instant'});});
render();loadData();
