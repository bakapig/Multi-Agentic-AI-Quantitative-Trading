"""Confirmed ensemble holdings and portfolio target groups, valued in USD."""

from dataclasses import dataclass
import math

import pandas as pd

from .evidence import fingerprint, json_value


def finite(value, name, minimum=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    if minimum is not None and value < minimum:
        raise ValueError(f"{name} must be >= {minimum}")


def date(value):
    stamp = pd.Timestamp(value)
    if pd.isna(stamp) or stamp.tz is not None or str(stamp.date()) != value:
        raise ValueError("as_of and session labels must be YYYY-MM-DD dates")
    return stamp


@dataclass(frozen=True)
class FundConfig:
    mode: str = "demo"
    account_key: str = "ensemble-fund-demo"
    execution_mode: str = "record_only"
    ensemble_budget_usd: float = 3_000_000.0
    central_cash_usd: float = 2_000_000.0
    maximum_fund_gross: float = 0.8
    maximum_name_gross: float = 0.2
    maximum_drawdown: float = 0.25
    risk_envelope: str = "standard"
    soft_drawdown: float = 0.12
    soft_drawdown_scale: float = 0.50
    fee_buffer_bps: float = 15.0
    collateral_buffer: float = 0.02
    allocation_method: str = "regime"
    calendar: str = "XNYS"
    currency: str = "USD"
    minimum_history: int = 80
    fast_window: int = 10
    slow_window: int = 60
    momentum_lookback: int = 60
    momentum_rebalance: int = 10
    momentum_top_k: int = 5
    reversion_window: int = 20
    reversion_entry_z: float = 2.0
    reversion_exit_z: float = 0.2
    reversion_stop_z: float = 3.5
    state_path: str = "runtime/ensemble_fund.demo.sqlite"
    report_directory: str = "runs/fund_agents/ensemble/demo"
    universe: tuple[str, ...] = ("CAT", "DE", "UNP", "CSX", "V", "MA", "JNJ", "ABBV", "KO", "PEP", "XOM", "CVX", "JPM", "BAC")
    benchmark: str = "SPY"

    def __post_init__(self):
        if self.mode not in ("demo", "research") or self.execution_mode != "record_only" or not self.account_key:
            raise ValueError("fund supports demo/research with record_only execution")
        if self.risk_envelope not in ("standard", "conservative", "aggressive"):
            raise ValueError("invalid risk_envelope")
        if self.allocation_method not in ("regime", "equal_weight", "risk_parity"):
            raise ValueError("allocation_method must be regime, equal_weight or risk_parity")
        if self.currency != "USD" or self.calendar != "XNYS":
            raise ValueError("the fund adapter currently requires USD equities on XNYS sessions")
        finite(self.ensemble_budget_usd, "ensemble_budget_usd", 1e-12)
        for name in ("central_cash_usd", "fee_buffer_bps", "collateral_buffer"):
            finite(getattr(self, name), name, 0)
        for name in ("maximum_fund_gross", "maximum_name_gross", "maximum_drawdown", "soft_drawdown", "soft_drawdown_scale"):
            finite(getattr(self, name), name, 1e-12)
            if getattr(self, name) > 1:
                raise ValueError(name + " cannot exceed one")
        if self.soft_drawdown >= self.maximum_drawdown or self.collateral_buffer >= 1:
            raise ValueError("invalid risk thresholds")
        for name in ("minimum_history", "fast_window", "slow_window", "momentum_lookback", "momentum_rebalance", "momentum_top_k", "reversion_window"):
            if type(getattr(self, name)) is not int or getattr(self, name) < 1:
                raise ValueError(name + " must be a positive integer")
        if self.fast_window >= self.slow_window or self.minimum_history < max(self.slow_window, self.momentum_lookback + 1, self.reversion_window, 60):
            raise ValueError("insufficient history or invalid moving-average windows")
        for name in ("reversion_entry_z", "reversion_exit_z", "reversion_stop_z"):
            finite(getattr(self, name), name, 1e-12)
        if not self.reversion_exit_z < self.reversion_entry_z < self.reversion_stop_z:
            raise ValueError("invalid mean-reversion thresholds")
        if not self.universe or len(set(self.universe)) != len(self.universe) or self.benchmark in self.universe:
            raise ValueError("universe must be unique, nonempty and exclude the benchmark")
        if any(not isinstance(s, str) or not s.isalnum() or s != s.upper() for s in (*self.universe, self.benchmark)):
            raise ValueError("the fund adapter requires explicit US equity ticker symbols")

    @property
    def initial_nav_usd(self):
        return self.ensemble_budget_usd + self.central_cash_usd


@dataclass(frozen=True)
class PhantomBook:
    """Shadow accounting of unscaled PM proposals vs. risk-approved exposure."""

    proposed_gross_usd: float
    approved_gross_usd: float
    throttled_gross_usd: float
    preserved_buffer_usd: float
    envelope_tier: str
    soft_throttle_active: bool
    sleeve_throttled_usd: dict[str, float]



@dataclass(frozen=True)
class Holding:
    pm: str
    group: str
    symbol: str
    units: float
    entry_price_usd: float
    opened_on: str | None = None

    def __post_init__(self):
        if self.pm != "ensemble" or not self.group or not self.symbol:
            raise ValueError("unknown PM or empty holding identity")
        finite(self.units, "signed units")
        finite(self.entry_price_usd, "entry price", 1e-12)
        if self.opened_on is not None:
            date(self.opened_on)


@dataclass(frozen=True)
class FundSnapshot:
    as_of: str
    ensemble_cash_usd: float
    central_cash_usd: float
    peak_nav_usd: float
    holdings: tuple[Holding, ...] = ()
    valuation_note: str = "Confirmed USD cash and signed USD equity holdings"

    def __post_init__(self):
        date(self.as_of)
        for name in ("ensemble_cash_usd", "central_cash_usd"):
            finite(getattr(self, name), name, 0)
        finite(self.peak_nav_usd, "peak NAV", 1e-12)
        identities = [(h.pm, h.group, h.symbol) for h in self.holdings]
        if len(set(identities)) != len(identities) or any(h.opened_on and h.opened_on > self.as_of for h in self.holdings):
            raise ValueError("duplicate holdings or future opening session")

    @classmethod
    def initial(cls, config, as_of):
        return cls(as_of, config.ensemble_budget_usd, config.central_cash_usd, config.initial_nav_usd)

    def group_holdings(self, pm, group):
        return tuple(h for h in self.holdings if (h.pm, h.group) == (pm, group))

    def units(self, pm, group, symbol):
        return next((h.units for h in self.group_holdings(pm, group) if h.symbol == symbol), 0.0)


@dataclass(frozen=True)
class TargetLeg:
    symbol: str
    units: float
    price_usd: float

    def __post_init__(self):
        if not self.symbol:
            raise ValueError("empty target symbol")
        finite(self.units, "target signed units")
        finite(self.price_usd, "USD reference price", 1e-12)


@dataclass(frozen=True)
class TargetGroup:
    pm: str
    group: str
    as_of: str
    signal_session: str
    legs: tuple[TargetLeg, ...]
    reason: str
    actionable: bool = True

    def __post_init__(self):
        date(self.as_of)
        date(self.signal_session)
        if self.signal_session > self.as_of or not self.group or self.pm != "ensemble":
            raise ValueError("invalid target identity or future signal session")
        if not self.legs or len({l.symbol for l in self.legs}) != len(self.legs):
            raise ValueError("target group needs unique legs")

    @property
    def gross_usd(self):
        return sum(abs(l.units * l.price_usd) for l in self.legs)

    @property
    def identity(self):
        return fingerprint(self)


@dataclass(frozen=True)
class PMProposal:
    pm: str
    status: str
    groups: tuple[TargetGroup, ...]
    diagnostics: dict
    evidence_sha256: str

    def __post_init__(self):
        if self.pm != "ensemble" or self.status not in ("READY", "INPUT_HOLD"):
            raise ValueError("invalid PM proposal")
        if any(g.pm != self.pm for g in self.groups) or len({g.group for g in self.groups}) != len(self.groups):
            raise ValueError("PM group identities must be unique and match their owner")
        # Enforce finite, serializable evidence before it reaches AI or persistence.
        fingerprint(json_value(self.diagnostics))
