"""The NDX momentum-hedge rule (ndx-momentum-hedge-main), ported from the standalone replication.
Every HOLD trading days, at the close of day t: candidates = universe on t; keep 20-day momentum > 0; rank by 5-day momentum; top 5 equal weight
(50% of capital) + 50% in PSQ (1x inverse QQQ), held to t+5. Calendar = QQQ trading days from START_DATE, so the weekly grid is fixed by the data.
`static` universe reproduces the repo's v2.0 engine (look-ahead filter: a stock needs a price at t+5). `pit` uses point-in-time members, one share class
per company, and a stock that stops trading is sold at its last price."""
import math
import statistics
from datetime import datetime
import numpy as np
import pandas as pd
from .config import *
from .universe import members_fn


def calendar(prices, start=START_DATE, end=None):
    return [d for d in sorted(prices[BENCH]) if start <= d and (end is None or d <= end)]


def select(prices, dates, idx, members, lookahead_filter=False, dedupe=False, top_k=TOP_K):
    """Picks decided at the close of dates[idx] from prices dated <= dates[idx] only (plus, if lookahead_filter, the repo's t+HOLD price-exists filter)."""
    cur, nxt = dates[idx], (dates[idx + HOLD] if idx + HOLD < len(dates) else None)
    d20, d5 = dates[idx - LOOKBACK], dates[idx - MOM_5D]
    cands = []
    for t in members:
        px = prices.get(t)
        if not px or cur not in px or px.get(d20, 0) <= 0 or px.get(d5, 0) <= 0:
            continue
        if lookahead_filter and nxt is not None and px.get(nxt, 0) <= 0:
            continue
        m20 = px[cur] / px[d20] - 1
        if m20 > 0:
            cands.append((t, px[cur] / px[d5] - 1, m20))
    cands.sort(key=(lambda c: (-c[1], c[0])) if dedupe else (lambda c: -c[1]))   # pit: ties by ticker; static: list order (as the repo)
    out, chosen = [], set()
    for t, m5, m20 in cands:
        if dedupe and CLASS_MATE.get(t) in chosen:
            continue
        out.append((t, m5, m20))
        chosen.add(t)
        if len(out) == top_k:
            break
    return out


def pick_return(px, dates, i0, i1):
    p0 = px.get(dates[i0], 0)
    if p0 <= 0:
        return None
    return next((px[dates[j]] for j in range(i1, i0, -1) if px.get(dates[j], 0) > 0), p0) / p0 - 1


def backtest(prices, universe="static", start=START_DATE, end=REPO_END, lag=0, cost_bps=0.0, lookahead_filter=None, pit=None):
    """Weekly backtest as the repo engines: NAV on a 10,000 base, returns per HOLD-day period, cost_bps on stock turnover (one-way)."""
    mf, is_pit = members_fn(universe, pit), universe == "pit"
    lookahead_filter = (not is_pit) if lookahead_filter is None else lookahead_filter
    qqq, psq = prices[BENCH], prices[HEDGE]
    dates = calendar(prices, start, end)
    reb = list(range(LOOKBACK, len(dates) - HOLD - lag, HOLD))
    strat, qv = 10000.0, 10000.0
    vals, qvals, nav_dates, log, prev_w = [strat], [qv], [dates[reb[0] + lag]], [], {}
    for idx in reb:
        picks = select(prices, dates, idx, mf(dates[idx]), lookahead_filter, dedupe=is_pit)
        k, i0, i1 = len(picks), idx + lag, idx + lag + HOLD
        rs = [r for t, *_ in picks if (r := pick_return(prices[t], dates, i0, i1)) is not None]
        stock = float(np.mean(rs)) if rs else 0.0
        w = {t: 1 / k for t, *_ in picks}
        turn = sum(abs(w.get(t, 0) - prev_w.get(t, 0)) for t in set(w) | set(prev_w))
        prev_w = w
        a, b = dates[i0], dates[i1]
        p_ret = psq[b] / psq[a] - 1 if a in psq and b in psq else 0.0
        r = (stock - cost_bps / 1e4 * turn) * STOCK_FRAC + p_ret * HEDGE_FRAC
        strat *= 1 + r
        qv *= qqq[b] / qqq[a]
        vals.append(strat)
        qvals.append(qv)
        nav_dates.append(b)
        log.append(dict(date=dates[idx], next_date=b, selected=",".join(t for t, *_ in picks), stock_ret_pct=round(100 * stock, 2),
                        psq_ret_pct=round(100 * p_ret, 2), strat_ret_pct=round(100 * r, 2), turnover=round(turn, 3)))
    return dict(values=vals, qqq_values=qvals, dates=nav_dates, log=log)


def stats(values, dates):
    """Repo compute_stats definitions: weekly returns, population stdev, sqrt(52), calendar-year CAGR, Sharpe with rf = 0."""
    wk = [values[i] / values[i - 1] - 1 for i in range(1, len(values))]
    yrs = (datetime.strptime(dates[-1], "%Y-%m-%d") - datetime.strptime(dates[0], "%Y-%m-%d")).days / 365.25
    peak, mdd = values[0], 0.0
    for v in values:
        peak = max(peak, v)
        mdd = min(mdd, v / peak - 1)
    sd = statistics.pstdev(wk)
    return dict(total_return_pct=100 * (values[-1] / values[0] - 1), cagr_pct=100 * ((values[-1] / values[0]) ** (1 / yrs) - 1),
                sharpe_rf0=statistics.mean(wk) / sd * math.sqrt(52) if sd else 0.0, max_drawdown_pct=100 * mdd, weeks=len(wk))


def daily_returns(prices, w0, w1, universe="pit", lag=1, cost_bps=0.0, start=START_DATE, pit=None):
    """Daily returns in [w0, w1] on the weekly grid anchored at START_DATE, including the final partial week. Weights are treated as
    rebalanced daily inside the week (a close approximation to the weekly buy-and-hold)."""
    mf, is_pit = members_fn(universe, pit), universe == "pit"
    qqq, psq = prices[BENCH], prices[HEDGE]
    dates = calendar(prices, start, w1)
    rows, prev_w = [], {}
    for idx in range(LOOKBACK, len(dates) - 1, HOLD):
        picks = select(prices, dates, idx, mf(dates[idx]), lookahead_filter=(not is_pit) and idx + HOLD < len(dates), dedupe=is_pit)
        sel = [t for t, *_ in picks]
        w = {t: 1 / len(sel) for t in sel}
        turn = sum(abs(w.get(t, 0) - prev_w.get(t, 0)) for t in set(w) | set(prev_w))
        prev_w = w
        for j in range(idx + lag + 1, min(idx + lag + HOLD, len(dates) - 1) + 1):
            d0, d1 = dates[j - 1], dates[j]
            if not (w0 <= d1 <= w1):
                continue
            rs = [prices[t][d1] / prices[t][d0] - 1 for t in sel if prices[t].get(d1, 0) > 0 and prices[t].get(d0, 0) > 0]
            cost = cost_bps / 1e4 * turn if j == idx + lag + 1 else 0.0
            rows.append((pd.Timestamp(d1), STOCK_FRAC * ((np.mean(rs) if rs else 0.0) - cost) + HEDGE_FRAC * (psq[d1] / psq[d0] - 1),
                         qqq[d1] / qqq[d0] - 1, ",".join(sel)))
    return pd.DataFrame(rows, columns=["Date", "strategy", "qqq", "picks"]).set_index("Date")


def current_book(prices, universe="pit", lag=1, pit=None):
    """Latest rebalance on or before the last completed bar: the picks, the next fill and the trading days to the next rebalance."""
    mf, is_pit = members_fn(universe, pit), universe == "pit"
    dates = calendar(prices)
    last = len(dates) - 1
    r = last - ((last - LOOKBACK) % HOLD)
    picks = select(prices, dates, r, mf(dates[r]), lookahead_filter=False, dedupe=is_pit)
    return dict(decided_at=dates[r], fills_at=dates[r + lag] if r + lag <= last else "next close", last_bar=dates[last],
                days_to_next_rebalance=r + HOLD - last,
                picks=[dict(ticker=t, weight=STOCK_FRAC / max(len(picks), 1), mom5=m5, mom20=m20, price=prices[t][dates[r]]) for t, m5, m20 in picks],
                hedge=dict(ticker=HEDGE, weight=HEDGE_FRAC), pool_size=sum(1 for t in mf(dates[r]) if t in prices))


def window_stats(x):
    eq = (1 + x).cumprod()
    return dict(cumulative_return=float(eq.iloc[-1] - 1), ann_vol=float(x.std(ddof=1) * math.sqrt(252)),
                sharpe_rf0=float(x.mean() / x.std(ddof=1) * math.sqrt(252)) if x.std() > 0 else None,
                max_dd=float((eq / eq.cummax() - 1).min()), days=int(len(x)))
