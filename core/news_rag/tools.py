"""
core/news_rag/tools.py
======================
LangChain Tools for News & FinBERT Sentiment Analytics.
Provides:
  - news_recent_headlines: Latest articles and sources
  - news_sentiment_summary: Aggregated FinBERT sentiment score & risk tags
  - news_explain_price_move: Correlates price action over N days with news catalysts
  - news_market_overview: Broad market sentiment pulse
"""

import os
import sys
import sqlite3
import pandas as pd
from typing import Optional
from langchain_core.tools import tool

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.ohlc_rag.chunker import DB_PATH


@tool
def news_recent_headlines(symbol: str, limit: int = 5) -> str:
    """
    Retrieves the most recent news headlines, publication dates, sources, and sentiment labels for a stock symbol.
    """
    sym = symbol.strip().upper()
    conn = sqlite3.connect(DB_PATH)
    query = """
        SELECT published_at, title, source, label, raw_score
        FROM news_sentiment
        WHERE symbol = ?
        ORDER BY published_at DESC
        LIMIT ?
    """
    df = pd.read_sql_query(query, conn, params=(sym, max(1, min(limit, 15))))
    conn.close()

    if df.empty:
        return f"No recent news articles found for symbol '{sym}' in the database."

    lines = [f"Recent News Headlines for {sym} (Latest {len(df)} articles):"]
    for idx, r in df.iterrows():
        score_val = r["raw_score"]
        score_str = f"({score_val:+.2f})" if pd.notna(score_val) else ""
        lines.append(
            f"{idx+1}. [{r['published_at']}] **{r['title']}**\n"
            f"   - Source: {r['source']} | Sentiment: {r['label']} {score_str}"
        )
    return "\n".join(lines)


@tool
def news_sentiment_summary(symbol: str) -> str:
    """
    Computes an aggregated FinBERT sentiment overview for a stock symbol over all tracked news articles.
    Provides bullish/bearish ratio, average sentiment score, and risk flags (regulatory, guidance, management).
    """
    sym = symbol.strip().upper()
    conn = sqlite3.connect(DB_PATH)
    query = """
        SELECT label, raw_score, finbert_prob_bullish, 
               is_guidance_raised, is_regulatory_risk, is_management_change
        FROM news_sentiment
        WHERE symbol = ?
        ORDER BY published_at DESC
        LIMIT 50
    """
    df = pd.read_sql_query(query, conn, params=(sym,))
    conn.close()

    if df.empty:
        return f"No sentiment data found for symbol '{sym}'."

    total = len(df)
    bullish_cnt = (df["label"].str.upper() == "BULLISH").sum()
    bearish_cnt = (df["label"].str.upper() == "BEARISH").sum()
    neutral_cnt = total - bullish_cnt - bearish_cnt

    avg_score = df["raw_score"].mean() if "raw_score" in df else 0.0
    reg_risks = (df["is_regulatory_risk"] == 1).sum()
    mgmt_changes = (df["is_management_change"] == 1).sum()
    guidance_ups = (df["is_guidance_raised"] == 1).sum()

    overall_stance = "Strongly Bullish" if avg_score > 0.3 else \
                     "Mildly Bullish" if avg_score > 0.05 else \
                     "Strongly Bearish" if avg_score < -0.3 else \
                     "Mildly Bearish" if avg_score < -0.05 else "Neutral"

    return (
        f"FinBERT Sentiment Profile for {sym} (Analyzed {total} articles):\n"
        f"- Overall Sentiment Bias: **{overall_stance}** (Composite Score: {avg_score:+.2f})\n"
        f"- Distribution: {bullish_cnt} Bullish ({bullish_cnt/total*100:.1f}%), "
        f"{bearish_cnt} Bearish ({bearish_cnt/total*100:.1f}%), {neutral_cnt} Neutral ({neutral_cnt/total*100:.1f}%)\n"
        f"- Risk & Catalyst Signals: "
        f"{reg_risks} Regulatory Risk flags, {mgmt_changes} Management Changes, {guidance_ups} Guidance Upgrades"
    )


@tool
def news_explain_price_move(symbol: str, days: int = 5) -> str:
    """
    Correlates a stock's price action over the last N trading sessions with the news headlines published during that exact period.
    Use this when the user asks WHY a stock dropped, fell, or gained.
    """
    sym = symbol.strip().upper()
    conn = sqlite3.connect(DB_PATH)
    
    # Get price move
    p_query = """
        SELECT trade_date, close, change_pct
        FROM daily_prices
        WHERE symbol = ?
        ORDER BY trade_date DESC
        LIMIT ?
    """
    pdf = pd.read_sql_query(p_query, conn, params=(sym, max(2, min(days, 30))))
    
    if pdf.empty or len(pdf) < 2:
        conn.close()
        return f"Insufficient price history to explain move for '{sym}'."

    pdf = pdf.sort_values("trade_date").reset_index(drop=True)
    start_date = pdf["trade_date"].iloc[0]
    end_date = pdf["trade_date"].iloc[-1]
    p_start = pdf["close"].iloc[0]
    p_end = pdf["close"].iloc[-1]
    ret_pct = ((p_end - p_start) / p_start) * 100.0

    # Get news in this date range
    n_query = """
        SELECT published_at, title, source, label, raw_score
        FROM news_sentiment
        WHERE symbol = ? AND published_at >= ?
        ORDER BY published_at DESC
        LIMIT 5
    """
    ndf = pd.read_sql_query(n_query, conn, params=(sym, start_date))
    conn.close()

    direction_verb = "fell" if ret_pct < 0 else "gained"
    lines = [
        f"Price Move Explanation for {sym} ({start_date} to {end_date}):",
        f"- Price Performance: {sym} {direction_verb} by **{abs(ret_pct):.2f}%** (from Rs. {p_start:.2f} to Rs. {p_end:.2f}).",
        f"- News Catalysts During This Period ({len(ndf)} articles found):"
    ]
    if ndf.empty:
        lines.append("  (No specific news headlines were published during this trading window. Move was likely driven by broader market sentiment or technical liquidation.)")
    else:
        for idx, r in ndf.iterrows():
            lines.append(f"  * [{r['published_at']}] {r['title']} (Sentiment: {r['label']}, Score: {r['raw_score']:+.2f})")

    return "\n".join(lines)


ALL_NEWS_TOOLS = [
    news_recent_headlines,
    news_sentiment_summary,
    news_explain_price_move
]


if __name__ == "__main__":
    print("[*] Testing News Tools...")
    print(news_sentiment_summary.invoke({"symbol": "RELIANCE"}))
    print(news_explain_price_move.invoke({"symbol": "BHARTIARTL", "days": 5}))
