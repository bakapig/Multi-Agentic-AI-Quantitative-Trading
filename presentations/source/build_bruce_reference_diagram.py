"""Draw an attributed Bruce Tech-inspired proposal beside the current baseline.

This authoring script changes no strategy, account, or risk configuration.
"""
from build_ensemble_diagram import Diagram, ROOT, INK, MUTED, PURPLE, GREEN


AMBER = "#956100"


def main():
    d = Diagram(stem="bruce_inspired_proposal",
        pdf_path=ROOT / "output/pdf/Bruce_Inspired_Architecture_Proposal_20261020.pdf",
        title="Proposed confluence strategy and two risk envelopes",
        description="Attributed Bruce Tech design reference, not implemented in Meridian. Tension, momentum and structure feed a proposed non-AI agreement gate and one portfolio decision. Two proposed risk envelopes use 7% and 15% drawdown halts. Current Meridian remains a weighted three-engine ensemble with a 12% soft and 25% hard drawdown policy. Advisory interfaces are AI-ready; automatic model calls are not connected.")
    d.rect(0, 0, 1920, 1080, "#F4F7FC", radius=0)
    d.text(80, 65, "MERIDIAN / STRATEGY AND RISK DESIGN REFERENCE", 18, PURPLE, True)
    d.text(1590, 65, "20 OCTOBER 2026", 18, MUTED, True)
    d.text(80, 131, "One signal engine. Two proposed risk envelopes.", 48, INK, True)
    d.text(80, 170, "Bruce Tech reference: Manifest MX5. The confluence gate and named envelopes are not implemented in Meridian.", 23, MUTED)
    d.rect(80, 204, 1760, 62, "#FFF1D5", radius=12)
    d.text(106, 244, "PROPOSED / NON-AI SIGNAL RULES + RISK POLICY", 21, AMBER, True)
    d.text(1000, 244, "Halt thresholds are policy triggers, not loss guarantees.", 22, INK)

    d.rect(80, 292, 1110, 638, "#FFF8E9", "#E4D2AC", 18)
    d.text(112, 328, "PROPOSED CONFLUENCE DESIGN | NON-AI", 19, AMBER, True)
    d.box(112, 350, 329, 107, "Tension", ["Stretch from equilibrium", "Definition to be validated"], AMBER)
    d.box(465, 350, 329, 107, "Momentum", ["Directional acceleration", "Definition to be validated"], AMBER)
    d.box(818, 350, 330, 107, "Structure", ["Recent price-path shape", "Definition to be validated"], AMBER)
    for x in (276, 630, 983):
        d.line([(x, 457), (x, 477)], "#B29D77")
    d.line([(276, 477), (983, 477)], "#B29D77")
    d.line([(630, 477), (630, 492)], "#B29D77", True)
    d.box(112, 492, 1036, 105, "Signal agreement gate | NON-AI proposal", [
        "Require the defined readings to agree before a new entry.",
        "No agreement: no new entry. Existing-position exits need a separate rule."], AMBER)
    d.line([(630, 597), (630, 623)], "#B29D77", True)
    d.box(112, 623, 1036, 80, "One portfolio decision | NON-AI proposal", [
        "This would change or gate the current signals; it requires separate validation."], AMBER)
    d.line([(630, 703), (630, 724)], "#B29D77")
    d.line([(362, 724), (897, 724)], "#B29D77")
    for x in (362, 897):
        d.line([(x, 724), (x, 746)], "#B29D77", True)
    d.box(112, 746, 500, 115, "Safe Harbor | 7% halt", [
        "Proposed drawdown-triggered halt", "Soft threshold must be below 7%"], AMBER)
    d.box(647, 746, 501, 115, "Ride the Waves | 15% halt", [
        "Proposed drawdown-triggered halt", "Account state and reset policy required"], AMBER)
    d.text(112, 903, "These envelopes are risk profiles. Instruments are a separate asset universe.", 20, AMBER)

    d.rect(1226, 292, 614, 638, "#EDF6F3", "#CEDFD9", 18)
    d.text(1258, 328, "CURRENT MERIDIAN / IMPLEMENTED", 19, GREEN, True)
    d.box(1258, 350, 550, 112, "Weighted ensemble | NON-AI", [
        "Trend + momentum + mean reversion", "No tension/structure agreement gate"], GREEN)
    d.box(1258, 499, 550, 112, "Fund risk | NON-AI", [
        "12% soft / 25% hard drawdown", "7% / 15% named profiles are not configured"], GREEN)
    d.box(1258, 648, 550, 112, "Advisory roles | AI-READY", [
        "Code-based analyst and Chair reviews", "Automatic LLM calls are not connected"], PURPLE)
    d.text(1258, 805, "Before implementation", 23, INK, True)
    d.text(1258, 838, "Define metrics, timeframe and agreement rule.", 20, MUTED)
    d.text(1258, 867, "Select fund or sleeve NAV for each halt.", 20, MUTED)
    d.text(1258, 896, "Validate costs, exits, holdings and reset rules.", 20, MUTED)

    d.rect(80, 956, 1760, 70, INK, radius=14)
    d.text(108, 1000, "Reference concept added. Trading code and current risk limits are unchanged.", 24, "#FFFFFF", True)
    d.text(1644, 1000, "DESIGN ONLY", 20, "#F2D79C", True)
    d.text(80, 1054, "Design source: https://bruce-tech.com/ | Manifest MX5, Safe Harbor and Ride the Waves are Bruce Tech reference names.", 17, MUTED)
    d.save()


if __name__ == "__main__":
    main()
