# FE5209 investor materials

The current system uses one Ensemble PM with trend, momentum and mean-reversion
engines. The standalone Pairs PM is retired. Use the current architecture diagram:

- [Editable vector diagram with AI and non-AI labels](architecture_20261020/ensemble_architecture.svg)
- [Browser slide view](architecture_20261020/ensemble_architecture.html)
- [PNG](architecture_20261020/ensemble_architecture.png) and [JPEG](architecture_20261020/ensemble_architecture.jpg)
- [PDF](../output/pdf/Ensemble_Fund_Architecture_20261020.pdf)
- [Source builder](source/build_ensemble_diagram.py)
- [Written architecture](../ARCHITECTURE.md)
- [FE5209 technical investor pitch and examiner Q&A](architecture_20261020/FE5209_Technical_Investor_Pitch_Script.txt): main pitch with web-app cues, formulas and a 120-word video version.
- [Developer build explanation and web-app tour](architecture_20261020/Ensemble_System_Build_and_Demo_Script.txt)
- [PowerShell app launcher](../scripts/start_ensemble_web_app.ps1)

### Bruce Tech inspired proposal

The [companion slide](architecture_20261020/bruce_inspired_proposal.html) adds a
proposed signal-agreement gate and attributed 7%/15% risk envelopes alongside
the implemented baseline. These are proposals; the trading code and active
12% soft / 25% hard drawdown policy have not been replaced.

- [PNG](architecture_20261020/bruce_inspired_proposal.png) and [editable SVG](architecture_20261020/bruce_inspired_proposal.svg)
- [PDF](../output/pdf/Bruce_Inspired_Architecture_Proposal_20261020.pdf)
- [Builder](source/build_bruce_reference_diagram.py)
- Design reference: [Bruce Tech](https://bruce-tech.com/)

## Backtest results

The [October comparison](../reports/october_2026/index.html) presents the original
ensemble and the separate 20-asset momentum strategy. The plot and report state
the exact data coverage and different execution assumptions. Retired mandate
materials and their builders were removed from the active project.
