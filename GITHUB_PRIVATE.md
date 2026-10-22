# GitHub repository workflow

Remote: `bakapig/Multi-Agentic-AI-Quantitative-Trading`.

The working tree contains the ensemble, standalone momentum strategy, shared
utilities, fund prototype, tests and research reports. Runtime databases,
credentials, virtual environments and scratch directories stay local.

Before publishing a reviewed change:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
git status --short
git diff --stat
git diff --cached --stat
.\.venv\Scripts\python.exe scripts/check_publication.py
```

Stage only reviewed source and report files. Publication does not install a
schedule, activate a strategy or place orders. Repository visibility is managed
separately. The legacy filename of this document is retained.
