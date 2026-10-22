"""Adapt the teammate's three research engines into next-session fund targets."""

import exchange_calendars as xcals
import numpy as np
import pandas as pd

from multi_strategy_ensemble.trend_strategy import TrendFollowingStrategy
from multi_strategy_ensemble.momentum_strategy import MomentumStrategy
from multi_strategy_ensemble.reversion_strategy import MeanReversionStrategy
from multi_strategy_ensemble.regime_detector import RegimeDetector

from .evidence import fingerprint
from .models import PMProposal, TargetGroup, TargetLeg, date
from .strategy import strategy_evidence


STRATEGIES = ("trend", "momentum", "mean_reversion")


class EnsemblePM:
    def __init__(self, config):
        self.config = config

    def propose(self, prices, snapshot, *, source_sha256, sector_mapping=None):
        cfg = self.config
        diagnostics = {"strategy": strategy_evidence(cfg), "source_sha256": source_sha256,
                       "currency": "USD", "allocation_method": cfg.allocation_method,
                       "sector_mapping_sha256": fingerprint(sector_mapping or {})}
        try:
            cutoff = date(snapshot.as_of)
            if not isinstance(prices.index, pd.DatetimeIndex) or prices.index.tz is not None:
                raise ValueError("prices require timezone-free exchange session dates")
            if not prices.index.is_unique or not prices.index.is_monotonic_increasing or not prices.columns.is_unique:
                raise ValueError("price sessions and columns must be unique and ordered")
            if not prices.index.equals(prices.index.normalize()):
                raise ValueError("price index must contain dates without intraday times")
            history = prices.loc[prices.index <= cutoff]
            required = (*cfg.universe, cfg.benchmark)
            if not set(required).issubset(history.columns):
                raise ValueError("missing required equities or benchmark: " + str(sorted(set(required) - set(history.columns))))
            history = history.loc[:, list(required)]
            if len(history) < cfg.minimum_history:
                raise ValueError("insufficient price history")
            calendar = xcals.get_calendar(cfg.calendar, start=str((history.index[0] - pd.Timedelta(days=14)).date()),
                                         end=str((cutoff + pd.Timedelta(days=14)).date()))
            last = calendar.date_to_session(cutoff, direction="previous")
            expected = calendar.sessions_in_range(history.index[0], last)
            if not expected.isin(history.index).all():
                raise ValueError("missing or stale required exchange sessions; no gap filling")
            diagnostics["excluded_non_session_rows"] = len(history) - len(expected)
            history = history.loc[expected]
            if len(history) < cfg.minimum_history:
                raise ValueError("insufficient exchange-session price history")
            values = history.to_numpy(dtype=float)
            if not np.isfinite(values).all() or (values <= 0).any():
                raise ValueError("all required equity and benchmark closes must be finite and positive")
            if any(h.group != "portfolio" or h.symbol not in cfg.universe for h in snapshot.holdings):
                raise ValueError("confirmed holdings must belong to the configured ensemble portfolio")

            assets = history.loc[:, list(cfg.universe)]
            benchmark = history[cfg.benchmark]
            results = {
                "trend": TrendFollowingStrategy(fast_window=cfg.fast_window, slow_window=cfg.slow_window).run_strategy(assets, benchmark),
                "momentum": MomentumStrategy(lookback_days=cfg.momentum_lookback,
                    rebalance_interval=cfg.momentum_rebalance, top_k=cfg.momentum_top_k,
                    sector_neutral=bool(sector_mapping), sector_mapping=sector_mapping).run_strategy(assets),
                "mean_reversion": MeanReversionStrategy(window=cfg.reversion_window,
                    entry_z=cfg.reversion_entry_z, exit_z=cfg.reversion_exit_z,
                    stop_loss_z=cfg.reversion_stop_z).run_strategy(assets),
            }
            regimes = RegimeDetector().detect_regimes(benchmark)
            regime = regimes.iloc[-1]
            if cfg.allocation_method == "regime":
                allocations = {"trend": float(regime.weight_trend), "momentum": float(regime.weight_momentum),
                               "mean_reversion": float(regime.weight_reversion), "cash": float(regime.weight_cash)}
            elif cfg.allocation_method == "equal_weight":
                allocations = dict.fromkeys(STRATEGIES, 1 / 3)
                allocations["cash"] = 0.0
            else:
                # Observations through the signal close size the next session.
                vols = np.array([results[name].daily_return.tail(60).std() for name in STRATEGIES])
                inverse = 1 / np.maximum(vols, 1e-6)
                allocations = dict(zip(STRATEGIES, (inverse / inverse.sum()).tolist()))
                allocations["cash"] = 0.0
            targets = pd.Series(0.0, index=assets.columns)
            engines = {}
            for name, result in results.items():
                weights = result.attrs["target_weights"].iloc[-1]
                targets += allocations[name] * weights
                engines[name] = {"allocation": allocations[name], "target_gross_fraction": float(weights.abs().sum()),
                                 "target_weights": {s: float(w) for s, w in weights.items()}}
            ensemble_nav = snapshot.ensemble_cash_usd + sum(h.units * float(assets[h.symbol].iloc[-1]) for h in snapshot.holdings)
            if ensemble_nav <= 0:
                raise ValueError("ensemble sleeve NAV must be positive")
            budget = min(ensemble_nav, cfg.ensemble_budget_usd)
            actionable = last == cutoff
            legs = tuple(TargetLeg(symbol, float(targets[symbol] * budget / assets[symbol].iloc[-1]) if actionable
                                   else snapshot.units("ensemble", "portfolio", symbol), float(assets[symbol].iloc[-1]))
                         for symbol in cfg.universe)
            group = TargetGroup("ensemble", "portfolio", snapshot.as_of, str(last.date()), legs,
                                "Next-session ensemble targets" if actionable else "Exchange closed; retain confirmed units",
                                actionable=actionable)
            diagnostics.update(signal_session=str(last.date()), history_rows=len(history),
                               regime=str(regime.regime), allocations=allocations, engines=engines,
                               sector_neutral=bool(sector_mapping),
                               strategy_cash_fraction=max(0.0, 1 - float(targets.abs().sum())),
                               timing="Computed at the completed close; eligible for a later session only",
                               data_sha256=fingerprint({"dates": history.index.strftime("%Y-%m-%d").tolist(),
                                                        "columns": list(history.columns), "values": values.tolist()}))
            return PMProposal("ensemble", "READY", (group,), diagnostics, fingerprint(diagnostics))
        except (ValueError, KeyError, TypeError) as exc:
            diagnostics["error"] = str(exc)
            return PMProposal("ensemble", "INPUT_HOLD", (), diagnostics, fingerprint(diagnostics))
