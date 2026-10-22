"""Compatibility entry point for AlphaHunt ensemble-only backtesting."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.run_ensemble_backtest import complete_window, metrics, main

if __name__ == '__main__':
    main()
