"""
market_brain_local.py — Replicating Market Brain Reasoning engine locally and offline.
Uses sqlite3 to query news sentiment database and builds deterministic narratives,
sector ratings, and Q&A responses.
"""

import sqlite3
import os
import re
from datetime import datetime, timedelta

SECTOR_MAP = {
    "Broad Market": ["NIFTY50", "NIFTY50.NS", "^NSEI"],
    "Banking": ["BANKNIFTY", "^NSEBANK", "HDFCBANK", "ICICIBANK", "SBIN", "AXISBANK", "KOTAKBANK", "HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", "AXISBANK.NS", "KOTAKBANK.NS"],
    "Technology": ["NIFTYIT", "^CNXIT", "TCS", "INFY", "WIPRO", "HCLTECH", "TECHM", "TCS.NS", "INFY.NS", "WIPRO.NS", "HCLTECH.NS", "TECHM.NS"],
    "Energy & Power": ["RELIANCE", "ONGC", "NTPC", "POWERGRID", "COALINDIA", "RELIANCE.NS", "ONGC.NS", "NTPC.NS", "POWERGRID.NS", "COALINDIA.NS"],
    "FMCG": ["HINDUNILVR", "ITC", "HINDUNILVR.NS", "ITC.NS"],
    "Pharma": ["NIFTYPHARMA", "^CNXPHARMA", "SUNPHARMA", "DRREDDY", "CIPLA", "SUNPHARMA.NS", "DRREDDY.NS", "CIPLA.NS"],
    "Automobile": ["NIFTYAUTO", "^CNXAUTO", "MARUTI", "BAJAJ-AUTO", "M&M", "TATAMOTORS", "MARUTI.NS", "BAJAJ-AUTO.NS", "M&M.NS", "TATAMOTORS.NS"],
    "Metals & Cement": ["TATASTEEL", "HINDALCO", "ULTRACEMCO", "TATASTEEL.NS", "HINDALCO.NS", "ULTRACEMCO.NS"],
    "Finance & Insurance": ["BAJFINANCE", "HDFCLIFE", "SBILIFE", "BAJFINANCE.NS", "HDFCLIFE.NS", "SBILIFE.NS"],
    "Commodities": ["GOLD", "SILVER", "CRUDEOIL", "NATURALGAS", "COPPER", "GC=F", "SI=F", "CL=F", "NG=F", "HG=F"]
}

SECTOR_KEYWORDS = {
    "Banking": ["bank", "rate", "fed", "rbi", "lending", "loan", "npa", "hdfc", "sbi", "icici", "deposit"],
    "Technology": ["it ", "tech", "software", "infosys", "tcs", "wipro", "hcl", "cognizant", "dollar", "us client"],
    "Energy & Power": ["oil", "gas", "coal", "power", "grid", "ntpc", "reliance", "ongc", "crude", "energy"],
    "FMCG": ["unilever", "hul", "itc", "consumer", "soap", "cigarette", "biscuit", "fmcg", "inflation"],
    "Pharma": ["pharma", "drug", "fda", "sun", "reddy", "cipla", "health", "clinical", "medicine"],
    "Automobile": ["auto", "car", "suv", "ev ", "electric vehicle", "tatamotors", "maruti", "mahindra", "bajaj", "scooter"],
    "Metals & Cement": ["steel", "aluminum", "cement", "ultratech", "tata steel", "copper", "zinc", "infrastructure"],
    "Finance & Insurance": ["finance", "insurance", "loan", "credit", "bajaj", "mutual fund", "fii", "dii"],
    "Commodities": ["gold", "silver", "crude", "brent", "gas", "commodity", "metals", "price spike"]
}

def _conn(db_path):
    c = sqlite3.connect(db_path)
    c.row_factory = sqlite3.Row
    return c

def get_market_brain_digest(db_path):
    conn = _conn(db_path)
    # Check last 3 days of news
    cutoff = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
    
    rows = conn.execute("""
        SELECT symbol, title, snippet, source, url, published_at, fetched_at,
               COALESCE(calibrated_score, raw_score) AS score,
               market_label
        FROM news_sentiment
        WHERE published_at >= ? OR fetched_at >= ?
        ORDER BY published_at DESC LIMIT 500
    """, (cutoff, cutoff)).fetchall()
    
    # Fallback to latest 200 if database is empty or updates are lagging (e.g. on test systems)
    if len(rows) < 5:
        rows = conn.execute("""
            SELECT symbol, title, snippet, source, url, published_at, fetched_at,
                   COALESCE(calibrated_score, raw_score) AS score,
                   market_label
            FROM news_sentiment
            ORDER BY fetched_at DESC LIMIT 200
        """).fetchall()

    conn.close()

    if not rows:
        return {
            "digest_date": datetime.now().strftime("%Y-%m-%d"),
            "mood_state": "Neutral",
            "mood_score": 0.0,
            "mood_rationale": "No news events fetched recently to build a market outlook.",
            "confidence": 0.5,
            "narrative": "Awaiting news fetch routines to refresh. Run yfinance bulk fetch daily to keep database updated.",
            "sector_sentiments": [],
            "key_events": []
        }

    # Group news by sector mapping
    sector_news = {sec: [] for sec in SECTOR_MAP}
    for r in rows:
        sym = r["symbol"].upper()
        # Find matching sector
        matched = False
        for sec, syms in SECTOR_MAP.items():
            if sym in syms:
                sector_news[sec].append(r)
                matched = True
                break
        if not matched:
            # Fallback to keyword matching if symbol isn't listed in mapping
            text = (r["title"] + " " + (r["snippet"] or "")).lower()
            for sec, kws in SECTOR_KEYWORDS.items():
                if any(kw in text for kw in kws):
                    sector_news[sec].append(r)
                    break

    # Calculate sector stats
    sector_results = []
    overall_score_sum = 0.0
    overall_count = 0

    for sec, items in sector_news.items():
        if not items:
            sector_results.append({
                "sector": sec,
                "bias": "NEUTRAL",
                "score": 0.0,
                "confidence": 0.0,
                "rationale": "No recent headlines to evaluate. Monitoring broad indices."
            })
            continue

        scores = [float(it["score"]) for it in items]
        avg_score = sum(scores) / len(scores)
        overall_score_sum += sum(scores)
        overall_count += len(scores)

        # Bias boundaries
        if avg_score > 0.12:
            bias = "POSITIVE"
            rationale_prefix = "Bullish momentum driven by: "
        elif avg_score < -0.12:
            bias = "NEGATIVE"
            rationale_prefix = "Bearish sentiment due to: "
        else:
            bias = "NEUTRAL"
            rationale_prefix = "Balanced consolidation. Mixed news: "

        # Grab top 2 headlines
        sorted_items = sorted(items, key=lambda x: abs(x["score"]), reverse=True)
        top_titles = [it["title"][:70].strip() + "..." for it in sorted_items[:2]]
        rationale = rationale_prefix + " & ".join(top_titles)

        # Confidence: scales with number of articles, capped at 1.0
        confidence = min(1.0, round(len(items) / 6.0, 2))

        sector_results.append({
            "sector": sec,
            "bias": bias,
            "score": round(avg_score, 3),
            "confidence": confidence,
            "rationale": rationale
        })

    # Overall Mood calculation
    avg_market_score = overall_score_sum / max(overall_count, 1)
    if avg_market_score > 0.22:
        mood = "GREED / EUPHORIA"
        mood_color = "#26a69a"
        mood_rationale = f"Strong positive catalysts driving broad momentum (average score: {avg_market_score:.2f})."
    elif avg_market_score > 0.07:
        mood = "OPTIMISTIC"
        mood_color = "#7FFFD4"
        mood_rationale = "General market sentiment is positive. IT & Banking showing stable trends."
    elif avg_market_score < -0.22:
        mood = "EXTREME FEAR / PANIC"
        mood_color = "#ef5350"
        mood_rationale = f"Sharp bearish triggers, global rate concerns, or institutional selling detected (average score: {avg_market_score:.2f})."
    elif avg_market_score < -0.07:
        mood = "CAUTIOUS"
        mood_color = "#ffcc00"
        mood_rationale = "Elevated global risks or geopolitical tensions are triggering risk-off strategies."
    else:
        mood = "NEUTRAL"
        mood_color = "#7aa8c0"
        mood_rationale = "Chop and indecision. Mixed earnings signals and neutral macroeconomic flows."

    # Build dynamic narrative paragraph
    pos_sectors = [s["sector"] for s in sector_results if s["bias"] == "POSITIVE"]
    neg_sectors = [s["sector"] for s in sector_results if s["bias"] == "NEGATIVE"]
    
    narrative = f"Indian markets display a **{mood}** profile today. "
    if pos_sectors:
        narrative += f"Strengthening sentiment is concentrated in **{', '.join(pos_sectors[:3])}**, with optimistic news flow supporting buyers. "
    if neg_sectors:
        narrative += f"Conversely, headwind alerts are triggering in **{', '.join(neg_sectors[:3])}**, driven by profit-booking or unfavorable global developments. "
    if not pos_sectors and not neg_sectors:
        narrative += "Most key sectors are hovering in flat neutral ranges, awaiting macroeconomic breakouts or decisive policy triggers."

    # Highlight top 5 key events (absolute score intensity)
    sorted_all = sorted(rows, key=lambda x: abs(x["score"]), reverse=True)
    key_events = []
    seen_titles = set()
    for r in sorted_all:
        title = r["title"].strip()
        if title in seen_titles:
            continue
        seen_titles.add(title)
        
        # Sector matching for display tag
        item_sector = "Broad"
        for sec, syms in SECTOR_MAP.items():
            if r["symbol"].upper() in syms:
                item_sector = sec
                break

        key_events.append({
            "title": r["title"],
            "snippet": r["snippet"] or "",
            "symbol": r["symbol"],
            "sector": item_sector,
            "score": round(float(r["score"]), 3),
            "date": r["published_at"][:16] if r["published_at"] else r["fetched_at"][:10],
            "source": r["source"] or "Yahoo Finance"
        })
        if len(key_events) >= 5:
            break

    return {
        "digest_date": datetime.now().strftime("%Y-%m-%d"),
        "mood_state": mood,
        "mood_color": mood_color,
        "mood_score": round(avg_market_score, 3),
        "mood_rationale": mood_rationale,
        "confidence": round(min(1.0, 0.5 + len(rows)/300), 2),
        "narrative": narrative,
        "sector_sentiments": sector_results,
        "key_events": key_events
    }

def local_ask_market_brain(query, db_path):
    query = query.strip().lower()
    # Extract keywords
    words = re.findall(r'\b\w{3,15}\b', query)
    if not words:
        return "Please ask a more detailed question (e.g. *How does the Fed rate hike impact Banking?*)."

    conn = _conn(db_path)
    
    # 1. Look for matching headlines
    like_clauses = []
    params = []
    for w in words:
        like_clauses.append("(title LIKE ? OR snippet LIKE ?)")
        params.extend([f"%{w}%", f"%{w}%"])
        
    where_sql = " OR ".join(like_clauses)
    
    rows = conn.execute(f"""
        SELECT symbol, title, snippet, source, published_at,
               COALESCE(calibrated_score, raw_score) AS score
        FROM news_sentiment
        WHERE {where_sql}
        ORDER BY ABS(score) DESC LIMIT 15
    """, params).fetchall()
    
    conn.close()

    if not rows:
        return (f"### Market Brain Analysis\n\n"
                f"No articles found in the local database matching the keywords: **{', '.join(words)}**.\n\n"
                f"**Suggestion**: Try searching for broader terms such as *Fed, RBI, rate, earnings, inflation, tech, bank*.")

    # Process matches
    total_score = 0.0
    bull_count = 0
    bear_count = 0
    affected_symbols = set()
    
    headlines_md = []
    for r in rows:
        sym = r["symbol"].upper()
        affected_symbols.add(sym)
        score = float(r["score"])
        total_score += score
        if score >= 0.1:
            bull_count += 1
            emoji = "🟢"
        elif score <= -0.1:
            bear_count += 1
            emoji = "🔴"
        else:
            emoji = "⚪"
            
        headlines_md.append(f"- {emoji} **[{sym}]** {r['title']} *(Score: {score:+.2f} | {r['source']})*")

    avg_score = total_score / len(rows)
    bias = "BULLISH" if avg_score > 0.1 else "BEARISH" if avg_score < -0.1 else "NEUTRAL"
    bias_color = "green" if bias == "BULLISH" else "red" if bias == "BEARISH" else "yellow"

    # Analyze sector mapping
    sectors_hit = set()
    for sym in affected_symbols:
        for sec, syms in SECTOR_MAP.items():
            if sym in syms:
                sectors_hit.add(sec)

    response_md = f"""### 🧠 Market Brain Analysis for: *"{query}"*

#### Summary of Local Evidence
Based on **{len(rows)} recent news records** in the database:
- **Net Sentiment Verdict**: <span style="color:{bias_color}; font-weight:bold;">{bias}</span> (Average Score: **{avg_score:+.2f}**)
- **Catalyst Balance**: {bull_count} positive triggers vs {bear_count} negative triggers.
- **Affected Sectors**: {', '.join(sectors_hit) if sectors_hit else 'Broad Market'}
- **Key Symbols Under Review**: {', '.join(affected_symbols)}

---

#### 📐 Causal Logic & Impact Channels
1. **Direct Mechanism**: Headlines containing keywords like **{', '.join(words[:4])}** typically impact **{', '.join(sectors_hit) if sectors_hit else 'broad indices'}** by influencing valuation multiples and interest rate projections.
2. **Sentiment Alignment**: The average score of **{avg_score:+.2f}** suggests that current local news flow is **{bias.lower()}**. If price trends for these symbols are diverging (e.g. price is dropping while news is positive), it represents a prime contrarian watch zone.
3. **Execution Advice**: 
   - **Gann Pivots**: Cross-reference the affected symbols (e.g. *{', '.join(list(affected_symbols)[:3])}*) with the **Gann Analysis** or **Chart + S/R** screens.
   - **Simons Fourier cycles**: Verify if any of these symbols are approaching major cycle bottoms (Mark-up phase) to time entries safely.

---

#### 📰 Supporting Local Headlines
{chr(10).join(headlines_md)}
"""
    return response_md
