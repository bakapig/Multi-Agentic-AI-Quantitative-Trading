"""Nasdaq-100 universes: the repo's hard-coded list ("static", hindsight-biased) and point-in-time membership ("pit").
PIT is a compact port of pit_universe.py: roll BACKWARDS from the anchor list through the change log; a change dated D is effective before the open on D."""
import bisect
import csv
from .config import ANCHOR_DATE, DATA, NDX_100


class PIT:
    def __init__(self, anchor_file=DATA / "ndx_constituents_anchor.csv", changes_file=DATA / "ndx_changes.csv", anchor_date=ANCHOR_DATE):
        with open(anchor_file, newline="", encoding="utf-8-sig") as f:
            cur = {r["ticker"].strip() for r in csv.DictReader(f) if r["ticker"].strip()}
        with open(changes_file, newline="", encoding="utf-8-sig") as f:
            ch = sorted(((r["date"].strip(), r["added"].strip(), r["removed"].strip()) for r in csv.DictReader(f)), key=lambda c: c[0], reverse=True)
        snaps, i = [], 0
        while i < len(ch):
            d = ch[i][0]
            if d > anchor_date:
                raise ValueError(f"change {d} is after anchor date {anchor_date}")
            snaps.append((d, frozenset(cur)))
            while i < len(ch) and ch[i][0] == d:
                _, added, removed = ch[i]
                if added and added not in cur:
                    raise ValueError(f"{d}: added {added} not in the set after the change")
                cur.discard(added)
                if removed:
                    cur.add(removed)
                i += 1
        snaps.append(("1900-01-01", frozenset(cur)))
        snaps.sort(key=lambda s: s[0])
        self._from, self._sets = [s[0] for s in snaps], [s[1] for s in snaps]

    def members(self, d):
        return set(self._sets[bisect.bisect_right(self._from, str(d)[:10]) - 1])

    def all_tickers_since(self, start, end):
        lo, hi = bisect.bisect_right(self._from, start) - 1, bisect.bisect_right(self._from, end) - 1
        return set().union(*self._sets[lo:hi + 1])


def members_fn(universe, pit=None):
    if universe == "static":
        return lambda d: NDX_100
    if universe == "pit":
        pit = pit or PIT()
        return lambda d: pit.members(d)
    raise ValueError(f"unknown universe {universe!r}")
