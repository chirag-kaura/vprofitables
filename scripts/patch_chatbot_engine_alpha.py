with open("core/chatbot_engine.py", "r", encoding="utf-8") as f:
    code = f.read()

# 1. Update context gathering in handle_chat_query
target_context = """    context = {
        "symbol": target_symbol,
        "annual_financials": annual_fin,
        "quarterly_financials": quarterly_fin,
        "transcripts": transcripts,
        "price_snapshot": price_snap,
    }"""

replacement_context = """    # Alpha Datasets: Shareholding, Options PCR & Event Risk
    try:
        from core.shareholding_engine import get_shareholding_trend
        shareholding = get_shareholding_trend(target_symbol)
    except Exception:
        shareholding = {}

    try:
        from core.corporate_calendar import is_earnings_imminent
        imminent_event = is_earnings_imminent(target_symbol)
    except Exception:
        imminent_event = {}

    try:
        from core.options_pcr_engine import calculate_iv_skew_and_moneyness
        options_pcr = calculate_iv_skew_and_moneyness(target_symbol)
    except Exception:
        options_pcr = {}

    context = {
        "symbol": target_symbol,
        "annual_financials": annual_fin,
        "quarterly_financials": quarterly_fin,
        "transcripts": transcripts,
        "price_snapshot": price_snap,
        "shareholding": shareholding,
        "imminent_event": imminent_event,
        "options_pcr": options_pcr,
    }"""

if target_context in code:
    code = code.replace(target_context, replacement_context, 1)

# 2. Update synthesize_deterministic_reply
target_synth = """    if quarterly:
        q_latest = quarterly[0]
        lines.append(f"#### ⏱️ Recent Quarter: {q_latest.get('fiscal_period')}")
        lines.append(f"- **Quarterly Sales:** {q_latest.get('sales_fmt')} | **Op Margin:** {q_latest.get('opm_pct_fmt')}")
        lines.append(f"- **Quarterly Net Profit:** {q_latest.get('net_profit_fmt')}")
        lines.append("")"""

replacement_synth = """    if quarterly:
        q_latest = quarterly[0]
        lines.append(f"#### ⏱️ Recent Quarter: {q_latest.get('fiscal_period')}")
        lines.append(f"- **Quarterly Sales:** {q_latest.get('sales_fmt')} | **Op Margin:** {q_latest.get('opm_pct_fmt')}")
        lines.append(f"- **Quarterly Net Profit:** {q_latest.get('net_profit_fmt')}")
        lines.append("")

    sh = context.get("shareholding", {})
    if sh and sh.get("promoter_pct") is not None:
        lines.append(f"#### 🏛️ Smart Money & Shareholding ({sh.get('latest_period', 'Latest')})")
        lines.append(f"- **Promoter Holding:** {sh.get('promoter_pct')}% (Pledged: **{sh.get('pledged_pct', 0.0)}%**)")
        lines.append(f"- **FII Stake:** {sh.get('fii_pct')}% ({sh.get('fii_qoq_delta', 0.0):+.2f}% QoQ) | **DII:** {sh.get('dii_pct')}% ({sh.get('dii_qoq_delta', 0.0):+.2f}% QoQ)")
        lines.append(f"- **Institutional Flow Signal:** `{sh.get('institutional_signal', 'STABLE')}`")
        lines.append("")

    pcr_info = context.get("options_pcr", {})
    if pcr_info and pcr_info.get("pcr") is not None:
        lines.append(f"#### 🎯 Derivatives & Options Sentiment")
        lines.append(f"- **PCR (Put-Call Ratio):** {pcr_info.get('pcr')} ({pcr_info.get('regime')})")
        lines.append(f"- **Max Pain Strike:** ₹{pcr_info.get('max_pain')} (Spot Gap: {pcr_info.get('max_pain_gap_pct'):+.1f}%)")
        lines.append("")

    ev = context.get("imminent_event", {})
    if ev and ev.get("imminent"):
        lines.append(f"> ⚠️ **EVENT RISK ALERT:** {ev.get('risk_message')}")
        lines.append("")"""

if target_synth in code:
    code = code.replace(target_synth, replacement_synth, 1)

with open("core/chatbot_engine.py", "w", encoding="utf-8") as f:
    f.write(code)

print("Successfully injected Alpha datasets into core/chatbot_engine.py")
