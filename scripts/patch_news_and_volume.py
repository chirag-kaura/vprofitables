with open("core/chatbot_engine.py", "r", encoding="utf-8") as f:
    code = f.read()

# 1. Update get_market_price_snapshot to calculate 5D change and 20D volume accumulation trend
old_snap = """        pct_from_52w_high = round(((ltp - high_52w) / high_52w) * 100, 1) if high_52w else 0.0

        return {
            "symbol": symbol,
            "ltp": ltp,
            "trade_date": trade_date,
            "high_52w": high_52w,
            "low_52w": low_52w,
            "pct_from_52w_high": pct_from_52w_high
        }"""

new_snap = """        pct_from_52w_high = round(((ltp - high_52w) / high_52w) * 100, 1) if high_52w else 0.0

        # Calculate 5-Day price return and 20-Day volume accumulation trend
        change_5d_pct = None
        if len(hist) >= 5 and hist[4][0]:
            p_5d_ago = float(hist[4][0])
            if p_5d_ago > 0:
                change_5d_pct = round(((ltp - p_5d_ago) / p_5d_ago) * 100, 2)

        vol_20d_note = "Volume data steady"
        cur_vol = 0
        try:
            # Query recent volume from daily_prices
            v_rows = conn.execute("SELECT volume FROM daily_prices WHERE symbol=? ORDER BY trade_date DESC LIMIT 20", (symbol,)).fetchall()
            vols = [float(vr[0]) for vr in v_rows if vr[0] is not None]
            if vols:
                cur_vol = vols[0]
                avg_vol = sum(vols) / len(vols)
                ratio = cur_vol / max(1.0, avg_vol)
                if ratio >= 1.25:
                    vol_20d_note = f"Volume expanding ({ratio:.1f}x of 20D average) — institutional accumulation signature"
                elif ratio <= 0.75:
                    vol_20d_note = f"Volume drying up ({ratio:.1f}x of 20D average) — selling exhaustion / absorption"
                else:
                    vol_20d_note = f"Volume in-line with 20D average ({ratio:.1f}x)"
        except Exception:
            pass

        return {
            "symbol": symbol,
            "ltp": ltp,
            "trade_date": trade_date,
            "high_52w": high_52w,
            "low_52w": low_52w,
            "pct_from_52w_high": pct_from_52w_high,
            "change_5d_pct": change_5d_pct,
            "volume_latest": cur_vol,
            "vol_accumulation_note": vol_20d_note
        }"""

if old_snap in code:
    code = code.replace(old_snap, new_snap)
    print("Replaced get_market_price_snapshot (LF)")
else:
    old_snap_crlf = old_snap.replace("\n", "\r\n")
    new_snap_crlf = new_snap.replace("\n", "\r\n")
    if old_snap_crlf in code:
        code = code.replace(old_snap_crlf, new_snap_crlf)
        print("Replaced get_market_price_snapshot (CRLF)")

# 2. Add News Sentiment query into handle_chat_query
old_collect = """    # Collect Grounded Context for Target Symbol
    annual_fin = get_company_financials(target_symbol, period_type="ANNUAL", limit=3)
    quarterly_fin = get_company_financials(target_symbol, period_type="QUARTERLY", limit=4)
    transcripts = get_transcript_guidance(target_symbol, user_msg, k=3, executive_only=False)
    price_snap = get_market_price_snapshot(target_symbol)"""

new_collect = """    # Collect Grounded Context for Target Symbol
    annual_fin = get_company_financials(target_symbol, period_type="ANNUAL", limit=3)
    quarterly_fin = get_company_financials(target_symbol, period_type="QUARTERLY", limit=4)
    transcripts = get_transcript_guidance(target_symbol, user_msg, k=3, executive_only=False)
    price_snap = get_market_price_snapshot(target_symbol)

    # 5. News Sentiment Pulse
    recent_news = []
    try:
        conn_n = get_db_connection(readonly=True)
        n_rows = conn_n.execute(\"\"\"
            SELECT title, label, calibrated_score, published_at, source
            FROM news_sentiment
            WHERE symbol = ?
            ORDER BY published_at DESC
            LIMIT 3
        \"\"\", (target_symbol,)).fetchall()
        conn_n.close()
        for nr in n_rows:
            recent_news.append({
                "title": nr[0],
                "label": nr[1] or "NEUTRAL",
                "score": round(float(nr[2]), 2) if nr[2] is not None else 0.0,
                "published_at": nr[3],
                "source": nr[4]
            })
    except Exception:
        recent_news = []"""

if old_collect in code:
    code = code.replace(old_collect, new_collect)
    print("Replaced context collection (LF)")
else:
    old_collect_crlf = old_collect.replace("\n", "\r\n")
    new_collect_crlf = new_collect.replace("\n", "\r\n")
    if old_collect_crlf in code:
        code = code.replace(old_collect_crlf, new_collect_crlf)
        print("Replaced context collection (CRLF)")

# Add recent_news to context dict
code = code.replace('"options_pcr": options_pcr,', '"options_pcr": options_pcr,\n        "recent_news": recent_news,')

# 3. Add News & Volume to synthesize_deterministic_reply
old_synth_price = """    if price.get("ltp"):
        lines.append(
            f"**Current Price:** ₹{price['ltp']:,.2f} | "
            f"**52W High:** ₹{price.get('high_52w', 0):,.2f} | "
            f"**52W Low:** ₹{price.get('low_52w', 0):,.2f} ({price.get('pct_from_52w_high', 0):+.1f}% from peak)"
        )
        lines.append("")"""

new_synth_price = """    if price.get("ltp"):
        chg_5d = f" | **5-Day Return:** {price.get('change_5d_pct'):+.2f}%" if price.get('change_5d_pct') is not None else ""
        lines.append(
            f"**Current Price:** ₹{price['ltp']:,.2f}{chg_5d} | "
            f"**52W High:** ₹{price.get('high_52w', 0):,.2f} | "
            f"**52W Low:** ₹{price.get('low_52w', 0):,.2f} ({price.get('pct_from_52w_high', 0):+.1f}% from peak)"
        )
        if price.get("vol_accumulation_note"):
            lines.append(f"📊 **Volume Trend:** {price.get('vol_accumulation_note')}")
        lines.append("")

    news = context.get("recent_news", [])
    if news:
        lines.append("#### 📰 Latest News & Market Sentiment Pulse")
        for n in news:
            lines.append(f"- **[{n['label']}]** {n['title']} *({n['published_at']}, Source: {n['source']})*")
        lines.append("")"""

if old_synth_price in code:
    code = code.replace(old_synth_price, new_synth_price)
    print("Replaced synth price (LF)")
else:
    old_synth_crlf = old_synth_price.replace("\n", "\r\n")
    new_synth_crlf = new_synth_price.replace("\n", "\r\n")
    if old_synth_crlf in code:
        code = code.replace(old_synth_crlf, new_synth_crlf)
        print("Replaced synth price (CRLF)")

with open("core/chatbot_engine.py", "w", encoding="utf-8") as f:
    f.write(code)
print("Updated chatbot_engine.py with news and volume accumulation analysis")
