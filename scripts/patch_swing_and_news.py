with open("core/chatbot_engine.py", "r", encoding="utf-8") as f:
    code = f.read()

# Add format_swing_setups_markdown before handle_chat_query
func_def = """def format_swing_setups_markdown(candidates: List[Dict[str, Any]], query_horizon: str = "10-15 days") -> str:
    lines = [
        f"### 🎯 Institutional Swing Trade Setups ({query_horizon})",
        "*Quantitative Trend Continuation & Pullback Engine (Multi-Timeframe Trend + 20-EMA Absorption + Volume Exhaustion)*",
        ""
    ]
    if not candidates:
        lines.append("No active swing setups met the minimum institutional confidence threshold today.")
        return "\\n".join(lines)

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

    lines.append("> 🛡️ **Risk Gate:** Always size positions to risk ≤ 1% of total portfolio equity. Invalidate position if price closes below the 20-EMA on 1D timeframe.")
    return "\\n".join(lines)
"""

old_target = "def handle_chat_query(params: Dict[str, Any]) -> Dict[str, Any]:"
if old_target in code and "format_swing_setups_markdown" not in code:
    code = code.replace(old_target, func_def + "\n" + old_target)

# Add SWING_SETUPS handler in handle_chat_query
old_screener_block = """    # ── INTENT A: QUANTITATIVE SCREENER ───────────────────────────────────────
    if intent == "SCREENER":"""

new_screener_block = """    # ── INTENT 0: SWING TRADE SETUPS (10-15 Days) ─────────────────────────────
    if intent == "SWING_SETUPS":
        from core.trend_continuation_engine import scan_trend_pullbacks
        horizon = intent_params.get("horizon", "10-15 days")
        candidates = scan_trend_pullbacks(horizon="swing", min_confidence=55, max_results=3)
        reply = format_swing_setups_markdown(candidates, query_horizon=horizon)
        latency_ms = int((time.time() - t0) * 1000)
        top_sym = candidates[0]["symbol"] if candidates else "NIFTY50"
        return {
            "reply": reply,
            "symbol": top_sym,
            "model_used": "Vprofitables-Trend-Continuation-Engine",
            "is_fallback": False,
            "latency_ms": latency_ms,
            "sources": [
                "Institutional Trend Continuation & Pullback Engine (20-EMA Dip & Rip)",
                "Daily Prices (Multi-Timeframe Trend + Volume Drying Up + RS vs NIFTY)"
            ],
            "metrics_summary": {
                "intent": "SWING_SETUPS",
                "horizon": horizon,
                "top_symbol": top_sym
            }
        }

    # ── INTENT A: QUANTITATIVE SCREENER ───────────────────────────────────────
    if intent == "SCREENER":"""

if old_screener_block in code:
    code = code.replace(old_screener_block, new_screener_block)
    print("Added SWING_SETUPS block (LF)")
else:
    old_screener_crlf = old_screener_block.replace("\n", "\r\n")
    new_screener_crlf = new_screener_block.replace("\n", "\r\n")
    if old_screener_crlf in code:
        code = code.replace(old_screener_crlf, new_screener_crlf)
        print("Added SWING_SETUPS block (CRLF)")

with open("core/chatbot_engine.py", "w", encoding="utf-8") as f:
    f.write(code)
print("Updated chatbot_engine.py with swing trading engine integration")
