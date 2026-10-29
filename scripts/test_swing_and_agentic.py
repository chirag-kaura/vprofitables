import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.trend_continuation_engine import scan_trend_pullbacks

def format_swing_setups_markdown(candidates, query_horizon="10-15 days"):
    lines = [
        f"### 🎯 Institutional Swing Trade Setups ({query_horizon})",
        "*Quantitative Trend Continuation & Pullback Engine (Multi-Timeframe Trend + 20-EMA Absorption + Volume Exhaustion)*",
        ""
    ]
    if not candidates:
        lines.append("No active swing setups met the minimum institutional confidence threshold today.")
        return "\n".join(lines)

    for i, c in enumerate(candidates, 1):
        lines.append(f"#### #{i}. **{c['symbol']}** — {c.get('name', c['symbol'])} ({c.get('sector', 'Sector N/A')})")
        lines.append(f"- **Setup:** `{c.get('setup_name', '20-EMA Dip & Rip')}` | **AI Confidence:** **{c.get('confidence')}%** | **R:R:** **{c.get('rr_ratio')}:1**")
        lines.append(f"- **Current LTP:** ₹{c.get('price', 0):,.2f}")
        lines.append(f"- **Entry Zone:** **₹{c.get('entry_zone_low', 0):,.2f} – ₹{c.get('entry_zone_high', 0):,.2f}** (Ideal: ₹{c.get('entry', 0):,.2f})")
        lines.append(f"- **Stop Loss (SL):** **₹{c.get('stop_loss', 0):,.2f}** (Risk: ₹{c.get('risk_per_share', 0):,.2f}/share)")
        lines.append(f"- **Target 1:** **₹{c.get('target1', 0):,.2f}** | **Target 2:** **₹{c.get('target2', 0):,.2f}**")
        lines.append(f"- **Estimated Hold Period:** **{c.get('hold_days', 12)} Trading Days**")
        lines.append(f"- **Technical & Quantitative 'Why':**")
        for r in c.get('reasons', []):
            lines.append(f"  • {r}")
        lines.append("")

    lines.append("> 🛡️ **Risk Gate:** Always size positions to risk ≤ 1% of total portfolio equity. Cancel order if price closes below the 20-EMA on 1D timeframe.")
    return "\n".join(lines)

candidates = scan_trend_pullbacks(horizon="swing", min_confidence=55, max_results=3)
md = format_swing_setups_markdown(candidates)
print("Preview:")
print(md[:600])
