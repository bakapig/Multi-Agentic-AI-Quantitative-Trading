# Multi-Agentic AI & Quantitative Trading Systems
**FE5209 Financial Econometrics — Master of Science in Financial Engineering (MFE)**  
*National University of Singapore (NUS) — Risk Management Institute (RMI) / Department of Mathematics*  
**Challenge Topic:** *Challenge 1: Can You Beat the Market?*

---

## Executive Summary & System Architecture

This repository hosts an end-to-end institutional quantitative trading platform developed for the **FE5209 Financial Econometrics Capstone**. The project investigates algorithmic market outperformance, multi-paradigm risk diversification, and autonomous multi-agent fund governance across global equity and derivatives markets.

The repository integrates three distinct, enterprise-grade quantitative modules:

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                               MASTER QUANTITATIVE REPOSITORY ARCHITECTURE                              │
└───────────────────────────────────┬────────────────────────────────────────────────────────────────────┘
                                    │
         ┌──────────────────────────┼───────────────────────────────────┐
         ▼                          ▼                                   ▼
┌─────────────────────────┐ ┌───────────────────────────┐ ┌──────────────────────────────────────────┐
│ multi_strategy_ensemble │ │        fund_agents        │ │                freqtrade                 │
│ (Flagship MFE Project)  │ │ (Multi-Agent Governance)  │ │   (Deep Learning & HMM Sequence Lab)     │
├─────────────────────────┤ ├───────────────────────────┤ ├──────────────────────────────────────────┤
│ • 308-Ticker Global     │ │ • Autonomous Fund Comm.   │ │ • Neural Gating: RNN, GRU, LSTM, Trans.  │
│   Universe (US/SG/EU)   │ │ • Independent Risk Veto   │ │ • 3-State Causal Gaussian HMM Router     │
│ • Trend + Momentum +    │ │ • Linked Intention Ledger │ │ • Binance Futures Walk-Forward Holdout   │
│   Pairs + Regime Router │ │ • Stripe-Inspired Web UI  │ │ • Microstructure & Slippage Stressing    │
│ • Full Backtrader Micro │ │ • Phantom Book Tracking   │ │ • Out-of-Sample Holdout (2025 - 2026)    │
│ • Academic Paper Incl.  │ │ • USD 5.0M Paper Mandate  │ │ • Altcoin Transferability Testing        │
└─────────────────────────┘ └───────────────────────────┘ └──────────────────────────────────────────┘
```

1. [**`multi_strategy_ensemble/`**](multi_strategy_ensemble/README.md): **The Flagship Capstone Portfolio System**. Evaluates whether a dynamic multi-paradigm ensemble (Dual-MA Trend Following, Cross-Sectional Factor Momentum, Cointegrated Pairs Mean Reversion, and a Lesson 12 Market Regime Router) can systematically beat the market across 308 international equities spanning the S&P 500, STI 30, and STOXX 600. Includes both vectorized simulation and event-driven Backtrader execution with discrete board lots and regional commissions.
2. [**`fund_agents/`**](fund_agents/README.md): **The Multi-Agent Fund Governance Platform (Meridian Pairs Fund)**. Implements an institutional investment committee framework where portfolio manager proposals (Pairs PM) undergo independent fund risk vetting with strict veto authority, Committee Chair evidence review, and execution logging in a tamper-evident audit ledger. Features an interactive local web dashboard (`http://127.0.0.1:8765`).
3. [**`freqtrade/`**](freqtrade/README.md): **Deep Sequence & Regime-Switching Laboratory**. A controlled empirical test bench comparing baseline technical breakout models against recurrent neural networks (RNN, GRU, LSTM), Transformers, and a 3-state Gaussian Hidden Markov Model (HMM) on high-frequency cryptocurrency perpetual futures.

---

## 1. Flagship Capstone: Multi-Strategy Quantitative Ensemble

* **Directory:** [`multi_strategy_ensemble/`](multi_strategy_ensemble/README.md)
* **Academic Research Paper:** [`multi_strategy_ensemble/RESEARCH_PAPER.md`](multi_strategy_ensemble/RESEARCH_PAPER.md)
* **Theoretical Source:** *AI Quantitative Trading: From Zero to One* (`ai-quant-book/manuscript/en`, Zhang, 2024)

### 1.1 Core Economic Philosophy & Regime Adaptation
Monolithic quantitative strategies inevitably experience catastrophic regime failure:
* **Trend Following** bleeds capital through repeated whipsaws in sideways/ranging markets.
* **Mean Reversion** experiences severe drawdown during structural trend breakouts and regime shifts.
* **Momentum** is vulnerable to sharp turning points and momentum crashes.

The multi-strategy ensemble solves this vulnerability through **payoff orthogonality** and **dynamic risk budgeting**:
1. **Trend Following Engine (Lesson 05.1):** Dual Moving Average ($\text{MA}_{10}/\text{MA}_{60}$) with an Average Directional Index filter ($\text{ADX} > 20$) and ATR-based trailing stops.
2. **Cross-Sectional Momentum Engine (Lessons 05 & 16):** 60-day relative strength cross-sectional ranking across top quintile leaders, weighted via inverse-volatility parity with sector-neutral constraints.
3. **Cointegrated Mean Reversion Engine (Lesson 05.2):** Statistical arbitrage across verified cointegrated pairs with dynamic Kalman-filter Z-scores and strict circuit-breaker stops ($|Z| \ge 3.5$).
4. **Market Regime Detection Router (Lesson 12):** Continuously classifies market state into **Trending** ($\text{ADX} \ge 25$), **Ranging** ($\text{ADX} \le 20, \sigma_{\text{ann}} \le 20\%$), **Crisis** ($\sigma_{\text{ann}} \ge 30\%$), and **Transition** regimes, dynamically adjusting capital allocations between strategies and cash reserves.

### 1.2 Out-of-Sample Empirical Results (Official Project Test Period: Oct 1 – Oct 20, 2026)
*Evaluated over the official forward out-of-sample test window (**October 1, 2026 to October 20, 2026; 13 trading days**), following in-sample calibration through September 30, 2026 across the **308-ticker Global Universe**:*

| Strategy / Portfolio | Total Return (%) | Annual Return (%) | Annual Volatility (%) | Sharpe Ratio ($R_f=4\%$) | Max Drawdown (%) | Calmar Ratio | Daily Win Rate (%) | Profit Factor | Final Equity ($) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Dynamic Regime Ensemble (BT L12)** | **+4.59%** | **124.25%** | **11.60%** | **7.22** | **-1.16%** | **106.76** | **69.23%** | **3.31** | **$1,045,887.02** |
| **Benchmark (SPY Buy & Hold)** | +0.66% | 12.62% | 9.86% | 0.95 | -2.03% | 6.21 | 53.85% | 1.23 | $1,006,623.12 |

* **Alpha & Risk-Adjusted Outperformance:** Over the official October test window, the Dynamic Regime Ensemble generated **+4.59% total return** (+$45,887 gain on $1,000,000 capital) versus **+0.66%** for SPY, delivering an annualized Sharpe ratio of **7.22** (vs. **0.95** for SPY) while constraining maximum drawdown to just **-1.16%** (vs. **-2.03%** for SPY).
* **Institutional Backtrader Execution:** Simulated with realistic market microstructure including exchange commissions (SGX: 12 bps, Europe: 8 bps, US: 3.5 bps), discrete board lot quantization (100 shares for SGX, 1 for US/EU), short borrow financing (1.0% p.a.), and bid-ask slippage (2 bps).

### 1.3 Running the Multi-Strategy Ensemble
```bash
# 1. Run Vectorized Daily Ensemble Engine
.venv/bin/python multi_strategy_ensemble/run_ensemble.py

# 2. Run Backtrader Institutional Event-Driven Simulation Suite
.venv/bin/python multi_strategy_ensemble/run_backtrader_ensemble.py
```

Outputs are automatically saved to [`multi_strategy_ensemble/outputs/`](multi_strategy_ensemble/outputs/):
* `backtrader_ensemble_performance.csv` & `ensemble_performance_comparison.csv`
* `backtrader_ensemble_equity_curves.png` & `multi_strategy_equity_curves.png`

---

## 2. Institutional Multi-Agent Fund Risk & Governance System

* **Directory:** [`fund_agents/`](fund_agents/README.md)
* **Design Specification:** [`fund_agents/web/DESIGN.md`](fund_agents/web/DESIGN.md)

### 2.1 Multi-Agent Workflow & Risk Architecture
`fund_agents` implements an autonomous investment fund framework where trading decisions are subjected to strict institutional controls:
* **Pairs Portfolio Manager (PM):** Generates market-neutral statistical arbitrage proposals across cointegrated equity pairs using dynamic Kalman-filtered hedge ratios and Ornstein-Uhlenbeck (OU) half-life holding bounds.
* **Independent Fund Risk Officer (Risk Agent):** Operates with absolute veto authority. Evaluates gross leverage ceilings, cross-pair symbol concentration caps (max 20%), collateral buffers (2%), turnover cost reserves (15 bps), and a two-stage drawdown circuit breaker (halves gross limit at 12% drawdown; latches total liquidation at 25%).
* **Phantom Book Tracking:** Continuously monitors exposure curtailed or rejected by the Risk Officer, recording prevented risk exposure without contaminating actual ledger cash.
* **Committee Chair & Audit Ledger:** Validates cryptographic hashes of inputs, policy configurations, and proposals before appending confirmed intentions to the immutable SQLite intention ledger (`runtime/pairs_fund.*.sqlite`).

### 2.2 Illustrative Paper Mandate ($5,000,000 USD)
| Mandate Sleeve | Allocation (USD) | Mandate Status | Purpose / Constraints |
| :--- | :---: | :---: | :--- |
| **Statistical Pairs PM** | $1,500,000 | **Active & Connected** | Zero-beta cointegrated equity pairs; max 80% gross deployment. |
| **Momentum Reserve** | $1,500,000 | Pending Integration | Held as liquid cash reserve pending portfolio integration. |
| **Central Cash Reserve** | $2,000,000 | Centrally Managed | Capital preservation, collateral maintenance, risk buffer. |
| **Total Fund Mandate** | **$5,000,000** | **Paper Governance** | Evaluated under independent fund risk envelope. |

### 2.3 Running the Fund Agents & Dashboard
```bash
# 1. Run deterministic demonstration cycle
.venv/bin/python -m fund_agents

# 2. Launch interactive Stripe-inspired investor dashboard (localhost:8765)
.venv/bin/python -m fund_agents.dashboard
```
Open **`http://127.0.0.1:8765`** in your browser to inspect real-time PM diagnostics, risk envelopes, committee memos, decision ledgers, and the six-step investor tour.

---

## 3. High-Frequency Crypto Sequence & Regime-Switching Research

* **Directory:** [`freqtrade/`](freqtrade/README.md)
* **Research Reports:** [`freqtrade/reports/`](freqtrade/reports/)

### 3.1 Controlled Deep Learning & HMM Sequence Experiments
A rigorous, walk-forward cryptocurrency futures study on Binance USD-M perpetuals (BTC/USDT, ETH/USDT, and altcoins SOL, XRP, BNB, DOGE) using 48-hour sequence lengths and causal feature engineering:
* **Baseline Control:** 40-day Bollinger Band breakout with mean-band liquidation.
* **Sequence Deep Learning Gates:** Comparison of identical breakout triggers gated by **RNN**, **GRU**, **LSTM**, and **Transformer** sequence models (requiring predicted next-24h return $> |0.2\%|$).
  * *Key Finding:* The pure Bollinger control outperformed all deep learning neural gates on risk-adjusted Sharpe (LSTM matched return but incurred higher drawdown; Transformers suffered from overfitting on noisy crypto microstructure).
* **3-State Causal Gaussian HMM Router:** Dynamically routes between **Trend** (Bollinger breakout + EMA 24/120 + MACD/RSI), **Sideways** (7-day Bollinger fade + RSI), and **Crisis** (immediate cash de-risking).
  * *Key Finding:* The **HMM Trend-Only** variant delivered the strongest risk-adjusted performance (**+19.58% return, 4.66% max drawdown, 1.32 daily Sharpe**), proving that regime filtering is most effective when used as a selective trade gatekeeper rather than forcing mean-reversion in high-dispersion crypto regimes.

```bash
# Run complete regime backtest suite
powershell .\freqtrade\run_regime_backtests.ps1
```

---

## 4. Repository Structure & File Index

```
Multi-Agentic-AI-Quantitative-Trading/
├── multi_strategy_ensemble/          # FE5209 Capstone: Multi-Strategy Quantitative System
│   ├── RESEARCH_PAPER.md             # Complete Academic Research Paper
│   ├── README.md                     # System documentation & textbook mapping
│   ├── config.py                     # 308-ticker universe config, horizons, capital
│   ├── regime_detector.py            # Lesson 12: Multi-Factor Market Regime Router
│   ├── trend_strategy.py             # Lesson 05.1: Dual-MA + ADX Trend Strategy
│   ├── momentum_strategy.py          # Lessons 05/16: Cross-Sectional Momentum
│   ├── reversion_strategy.py         # Lesson 05.2: Cointegrated Pairs Mean Reversion
│   ├── ensemble_portfolio.py         # Lessons 05.3/12: Risk Parity & Regime Allocation
│   ├── run_ensemble.py               # Vectorized daily simulation runner & plots
│   ├── backtrader_ensemble.py        # Institutional Backtrader simulation suite
│   ├── run_backtrader_ensemble.py    # Backtrader CLI execution runner
│   └── outputs/                      # Generated performance tables and equity curves
├── fund_agents/                      # Multi-Agent Fund Governance Platform (Meridian)
│   ├── README.md                     # Fund execution guide, mandates, and architecture
│   ├── agent.py                      # Multi-agent coordinator & intent dispatcher
│   ├── risk.py                       # Independent Fund Risk Officer (veto engine)
│   ├── chair.py                      # Committee Chair review & audit validation
│   ├── dashboard.py                  # Local HTTP server for investor workspace
│   ├── web/                          # Stripe-inspired dashboard UI (HTML/CSS/JS)
│   └── vendor/pairs_trading/         # Pinned statistical arbitrage engine (5d42b04)
├── freqtrade/                        # Deep Learning & HMM Sequence Experimentation
│   ├── README.md                     # Sequence models, HMM router, and altcoin screens
│   ├── user_data/strategies/         # FreqAI RNN/LSTM/Transformer & HMM strategies
│   └── reports/                      # Backtest reports, Excel sheets, and tearsheets
├── common/                           # Shared Data Loaders, Microstructure & Performance
│   ├── data_loader.py                # Multi-asset price matrix loaders & alignment
│   ├── microstructure.py             # Slippage, exchange commissions & borrow drag
│   ├── performance.py                # Sharpe, Calmar, Max Drawdown, and Win Rate metrics
│   └── tearsheet.py                  # Publication-ready Matplotlib visual tearsheets
├── data/cache/                       # Curated historical price caches (308 tickers)
│   ├── global_universe_prices.csv    # 11-year daily close matrix across US, SG, EU
│   ├── benchmark_SPY.csv             # SPY benchmark closing price series
│   └── full_universe_sectors.csv     # GICS sector classifications
└── presentations/                    # Roadshow presentation decks and talking scripts
```

---

## 5. Quickstart & Submission Verification

### Environment Setup
```bash
# Create and activate Python 3.11/3.12 virtual environment
python3 -m venv .venv
source .venv/bin/activate        # On macOS/Linux
# .\.venv\Scripts\activate       # On Windows

# Install core quantitative dependencies
pip install -r requirements.txt
pip install -r requirements-fund.txt
```

### Reproduce All Submission Results
```bash
# 1. Reproduce FE5209 Multi-Strategy Ensemble Backtest (Institutional Backtrader)
python multi_strategy_ensemble/run_backtrader_ensemble.py

# 2. Reproduce FE5209 Multi-Strategy Ensemble (Vectorized Engine)
python multi_strategy_ensemble/run_ensemble.py

# 3. Launch Meridian Pairs Fund Multi-Agent Demonstration & Dashboard
python -m fund_agents
python -m fund_agents.dashboard
# Navigate to http://127.0.0.1:8765
```

---

## Academic Citation & References

* **Zhang, Wayland (2024).** *AI Quantitative Trading: From Zero to One.* Manuscript source: [`ai-quant-book/manuscript/en`](https://github.com/waylandzhang/ai-quant-book/tree/main/manuscript/en).
* **Fama, E. F., & French, K. R. (1993).** *Common risk factors in the returns on stocks and bonds.* Journal of Financial Economics, 33(1), 3-56.
* **Jegadeesh, N., & Titman, S. (1993).** *Returns to buying winners and selling losers: Implications for stock market efficiency.* The Journal of Finance, 48(1), 65-91.
* **Engle, R. F., & Granger, C. W. (1987).** *Co-integration and error correction: representation, estimation, and testing.* Econometrica, 251-276.
* **Moskowitz, T. J., Ooi, Y. H., & Pedersen, L. H. (2012).** *Time series momentum.* Journal of Financial Economics, 104(2), 228-250.
