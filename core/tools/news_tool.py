"""
core/tools/news_tool.py
=======================
Atomic News Sentiment & Catalyst Intelligence Tool.
Retrieves recent financial news headlines, FinBERT sentiment classifications,
and calibrated sentiment polarity scores for an NSE ticker.
"""

from typing import Dict, Any, List
try:
    from langchain_core.tools import tool
except ImportError:
    def tool(func):
        return func

from core.paths import get_db_connection

@tool
def get_news_sentiment_tool(symbol: str, limit: int = 5) -> Dict[str, Any]:
    """
    Retrieves recent news headlines, sentiment scores, and catalyst summaries for an NSE equity.
    
    Args:
        symbol: NSE ticker symbol (e.g., 'RELIANCE', 'TCS').
        limit: Number of recent news items to fetch (default: 5).
        
    Returns:
        Dict containing average sentiment polarity, confidence score, and recent headline list.
    """
    clean_sym = symbol.strip().upper()
    try:
        conn = get_db_connection(readonly=True)
        rows = conn.execute("""
            SELECT title, summary, label, calibrated_score, published_date, source
            FROM news_sentiment
            WHERE symbol = ?
            ORDER BY published_date DESC
            LIMIT ?
        """, (clean_sym, limit)).fetchall()
        conn.close()
        
        if not rows:
            return {
                "symbol": clean_sym,
                "news_count": 0,
                "overall_sentiment": "NEUTRAL",
                "avg_score": 0.0,
                "headlines": []
            }
            
        headlines = []
        score_sum = 0.0
        for r in rows:
            title = r[0] or ""
            summary = r[1] or ""
            label = r[2] or "NEUTRAL"
            score = float(r[3] or 0.0)
            pub_date = r[4] or ""
            source = r[5] or "News"
            
            score_sum += score
            headlines.append({
                "title": title,
                "label": label,
                "score": score,
                "date": pub_date,
                "source": source
            })
            
        avg_score = round(score_sum / len(rows), 2)
        overall = "POSITIVE" if avg_score > 0.15 else ("NEGATIVE" if avg_score < -0.15 else "NEUTRAL")
        
        return {
            "symbol": clean_sym,
            "news_count": len(headlines),
            "overall_sentiment": overall,
            "avg_score": avg_score,
            "headlines": headlines
        }
    except Exception as e:
        return {
            "symbol": clean_sym,
            "news_count": 0,
            "error": str(e),
            "headlines": []
        }
