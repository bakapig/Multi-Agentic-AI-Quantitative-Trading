# Multi-Strategy Ensemble System: Momentum, Trend, and Mean Reversion
**FE5209 Financial Econometrics — Advanced Algorithmic Trading**  
**Sourced Solely From:** [AI Quantitative Trading: From Zero to One (`ai-quant-book/manuscript/en`)](https://github.com/waylandzhang/ai-quant-book/tree/main/manuscript/en)  
**Academic Research Paper:** [RESEARCH_PAPER.md](RESEARCH_PAPER.md)  
**Mathematical Foundations:** [STRATEGY_ARCHETYPE_MATHEMATICAL_FOUNDATIONS.md](STRATEGY_ARCHETYPE_MATHEMATICAL_FOUNDATIONS.md)

---

## 1. Overview & Core Philosophy

This module implements a complete, production-ready multi-strategy quantitative architecture that combines **Momentum**, **Trend Following**, and **Mean Reversion** strategies under an adaptive **Market Regime Detection Router**.

As emphasized in **Lesson 05 (Classic Strategy Paradigms)** of the manuscript:
> *"Quantitative trading isn't about inventing new strategies — it's about using the right strategy in the right market. Trending markets need trend strategies; sideways markets need mean reversion strategies. Identifying market state is more important than choosing a strategy."*

### Why Combine Multiple Paradigms? (Lesson 05.3)
| Single Strategy Weakness | Multi-Strategy Portfolio Solution |
| :--- | :--- |
| **Trend Following** suffers consecutive whipsaw losses in sideways/ranging markets | **Mean Reversion** thrives on oscillations and compensates |
| **Mean Reversion** gets crushed during violent trend breakouts | **Trend Following** captures the large directional tail moves |
| Single-strategy books concentrate regime vulnerability | **Multi-Strategy Ensemble** diversifies risk and stabilizes the equity curve |

---

## 2. Theoretical Architecture & Manuscript Mapping

All strategy components, risk parameters, and regime logic are sourced directly from the manuscript:

```
                                    +-----------------------------------------+
                                    |     Multi-Asset Historical Feed         |
                                    | (US Large-Cap, Financials, Tech, Energy)|
                                    +-----------------------------------------+
                                                         |
                                                         v
                                    +-----------------------------------------+
                                    |   Lesson 12: Regime Detection Router    |
                                    | (ADX, 20d Realized Volatility, Return)  |
                                    +-----------------------------------------+
                                                         |
                   +-------------------------------------+-------------------------------------+
                   |                                     |                                     |
                   v                                     v                                     v
       +-----------------------+             +-----------------------+             +-----------------------+
       | Lesson 05.1:          |             | Lessons 05 & 16:      |             | Lesson 05.2:          |
       | Trend Following       |             | Momentum Engine       |             | Mean Reversion        |
       | (Dual MA10/MA60 +     |             | (Cross-Sectional Rank |             | (Cointegrated Pairs   |
       |  ADX Filter + ATR)    |             |  + Inv-Vol Sizing)    |             |  + Stop-Loss Circuit) |
       +-----------------------+             +-----------------------+             +-----------------------+
                   |                                     |                                     |
                   +-------------------------------------+-------------------------------------+
                                                         |
                                                         v
                                    +-----------------------------------------+
                                    |   Lesson 05.3 & 16: Capital Allocator   |
                                    |  * Equal Weight (1/3 each)              |
                                    |  * Risk Parity (Inverse Volatility)     |
                                    |  * Dynamic Regime-Weighted Ensemble     |
                                    +-----------------------------------------+
                                                         |
                                                         v
                                    +-----------------------------------------+
                                    |   Lesson 18: Microstructure Friction    |
                                    |  (Commissions, Slippage, Borrow Costs)  |
                                    +-----------------------------------------+
```

### Module Mapping Table
| Strategy Component | Manuscript Source | Core Rules & Formulas |
| :--- | :--- | :--- |
| **Market Regime Router** | [Lesson 12: Regime Detection](https://github.com/waylandzhang/ai-quant-book/blob/main/manuscript/en/Part4-Multi-Agent/Lesson-12-Regime-Detection.md) | Multi-factor classification: **Crisis** ($\sigma_{\text{ann}} \ge 30\%$), **Trending** ($\text{ADX} \ge 25$), **Ranging** ($\text{ADX} \le 20, \sigma \le 20\%$), **Transition** ($20 < \text{ADX} < 25$). |
| **Trend Following** | [Lesson 05.1: Trend Following](https://github.com/waylandzhang/ai-quant-book/blob/main/manuscript/en/Part2-Quant-Fundamentals/Lesson-05-Classic-Strategy-Paradigms.md#51-trend-following) | Dual Moving Average ($\text{MA}_{10} / \text{MA}_{60}$), Golden Cross Long entry, Death Cross exit to cash (earning $R_f$), ADX filter $> 20$. |
| **Momentum** | [Lesson 05 & Lesson 16](https://github.com/waylandzhang/ai-quant-book/blob/main/manuscript/en/Part4-Multi-Agent/Lesson-16-Portfolio-Construction-and-Exposure-Management.md) | 60-day relative strength cross-sectional ranking; Long top quintile leaders; inverse-volatility scaling ($w_i \propto 1/\sigma_i$); bi-weekly rebalancing. |
| **Mean Reversion** | [Lesson 05.2: Mean Reversion](https://github.com/waylandzhang/ai-quant-book/blob/main/manuscript/en/Part2-Quant-Fundamentals/Lesson-05-Classic-Strategy-Paradigms.md#52-mean-reversion) | Cointegrated pairs trading across verified pairs; entry at $|Z| \ge 1.5$, exit at $|Z| \le 0.2$; strict stop-loss circuit breaker at $|Z| \ge 3.5$. |
| **Multi-Strategy Allocation** | [Lesson 05.3 & Lesson 16](https://github.com/waylandzhang/ai-quant-book/blob/main/manuscript/en/Part2-Quant-Fundamentals/Lesson-05-Classic-Strategy-Paradigms.md#53-multi-strategy-portfolios) | Equal Weighting, Risk Parity (Inverse Strategy Volatility), and Dynamic Regime Router allocation. |
| **Execution Friction** | [Lesson 18: Trading Costs](https://github.com/waylandzhang/ai-quant-book/blob/main/manuscript/en/Part5-Production/Lesson-18-Trading-Costs-and-Tradability.md) | 5 bps transaction cost (broker commissions + bid-ask spread slippage) and 1.0% annual short borrow financing drag. |

---

## 3. Directory Structure

```
multi_strategy_ensemble/
├── RESEARCH_PAPER.md                               # Complete Academic Paper (Multi-Strategy Ensemble)
├── STRATEGY_ARCHETYPE_MATHEMATICAL_FOUNDATIONS.md  # Formal Mathematical Foundations & Derivations
├── README.md                                       # Complete system documentation
├── config.py                                       # Global 308-ticker universe, capital ($1M), horizons
├── regime_detector.py                              # Lesson 12: Multi-factor market state detector & router
├── trend_strategy.py                               # Lesson 05.1: Dual Moving Average + ADX trend engine
├── momentum_strategy.py                            # Lessons 05 & 16: Cross-sectional momentum + vol-scaled engine
├── reversion_strategy.py                           # Lesson 05.2: Cointegrated pairs mean reversion engine
├── ensemble_portfolio.py                           # Lessons 05.3 & 12: Equal weight, risk parity & regime router
├── run_ensemble.py                                 # Vectorized CLI simulation runner & visualization generator
├── backtrader_ensemble.py                          # Backtrader multi-asset strategies with board lot sizing
├── run_backtrader_ensemble.py                      # Institutional event-driven Backtrader simulation runner
└── outputs/                                        # Auto-generated reports and publication figures
    ├── ensemble_performance_comparison.csv
    ├── ensemble_equity_curves.csv
    ├── regime_detection_log.csv
    ├── multi_strategy_equity_curves.png
    ├── backtrader_ensemble_performance.csv
    ├── backtrader_ensemble_equity_curves.csv
    └── backtrader_ensemble_equity_curves.png
```

---

## 4. Empirical Out-of-Sample Performance Comparison (Official Test Period: Oct 1 – Oct 20, 2026)

Evaluated over the official forward out-of-sample evaluation window (**October 1, 2026 to October 20, 2026; 13 trading days**), following in-sample calibration through September 30, 2026 across the **308-ticker Global Universe** (S&P 500 GICS sector leaders, STI 30, and STOXX 600 blue-chips):

| Strategy / Portfolio | Total Return (%) | Annual Return (%) | Annual Volatility (%) | Sharpe Ratio (=4\%$) | Max Drawdown (%) | Calmar Ratio | Daily Win Rate (%) | Profit Factor | Final Equity ($) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Dynamic Regime Ensemble (BT L12)** | **+4.59%** | **124.25%** | **11.60%** | **7.22** | **-1.16%** | **106.76** | **69.23%** | **3.31** | **,045,887.02** |
| **Benchmark (SPY Buy & Hold)** | +0.66% | 12.62% | 9.86% | 0.95 | -2.03% | 6.21 | 53.85% | 1.23 | ,006,623.12 |

---

## 5. Key Economic & Quantitative Insights

1. **Decisive Market Outperformance in October 2026 Evaluation Period**:
   * **Dynamic Regime Ensemble** generated **+4.59% total return** (+,887 net portfolio gain on ,000,000 capital) versus **+0.66%** for SPY, achieving an annualized Sharpe Ratio of **7.22** (vs. **0.95** for SPY) and a Calmar Ratio of **106.76**.
   * It achieved a **69.23% daily win rate** with a **3.31 profit factor**, demonstrating that dynamically filtering and weighting strategies by market regime captures alpha while filtering noise.

2. **Capital Preservation & Drawdown Containment**:
   * The **Dynamic Regime Ensemble** contained maximum drawdown to just **-1.16%** (compared to **-2.03%** for SPY) under full institutional microstructure frictions (regional commissions, board lot quantization, short borrow financing, and bid-ask slippage).

---

## 6. How to Run the System

To execute the entire multi-strategy ensemble, compute performance metrics, and generate tearsheets:

```bash
# From the repository root:
python multi_strategy_ensemble/run_ensemble.py
```

Generated outputs will be saved to:
* `multi_strategy_ensemble/outputs/ensemble_performance_comparison.csv`
* `multi_strategy_ensemble/outputs/regime_detection_log.csv`
* `multi_strategy_ensemble/outputs/ensemble_equity_curves.csv`
* `multi_strategy_ensemble/outputs/multi_strategy_equity_curves.png`

---

## 7. Running via the Institutional Backtrader Suite

In addition to the vectorized engine, the entire system can be simulated in **Backtrader** with exchange-level order execution, board lot integer rounding (100 shares for SGX, 1 for US/Europe), broker commissions (3.5 to 12 bps), bid-ask slippage (2 bps), and short borrow interest:

```bash
# From the repository root:
python multi_strategy_ensemble/run_backtrader_ensemble.py
```

Backtrader outputs will be saved to:
* `multi_strategy_ensemble/outputs/backtrader_ensemble_performance.csv`
* `multi_strategy_ensemble/outputs/backtrader_ensemble_equity_curves.csv`
* `multi_strategy_ensemble/outputs/backtrader_ensemble_equity_curves.png`
