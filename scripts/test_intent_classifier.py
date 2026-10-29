import re
from typing import Tuple, Dict, Any, Optional

def classify_user_intent(message: str, active_symbol: Optional[str] = None) -> Tuple[str, Dict[str, Any]]:
    msg = message.strip()
    lower = msg.lower()

    # 1. Help & Greeting intent
    if re.search(r"^(hi|hello|hey|help|who are you|what can you do|capabilities)\b", lower):
        return "HELP", {}

    # 2. Screener Performance intent (gainers, losers, fallen max, drops, rallies)
    screener_patterns = [
        r"fallen\s+max",
        r"fallen\s+most",
        r"fell\s+max",
        r"fell\s+most",
        r"drop(ped)?\s+max",
        r"drop(ped)?\s+most",
        r"top\s+loser",
        r"top\s+gainer",
        r"biggest\s+loser",
        r"biggest\s+gainer",
        r"worst\s+perform",
        r"best\s+perform",
        r"which\s+stock.*(fall|drop|down|gain|rise|rally)",
        r"(most|max)\s+fallen",
        r"down\s+most",
        r"up\s+most",
        r"top\s+\d+\s+(gainer|loser|mover)",
        r"volume\s+shocker",
        r"highest\s+volume",
    ]
    if any(re.search(pat, lower) for pat in screener_patterns):
        # Extract direction
        is_loser = any(w in lower for w in ["fall", "fell", "drop", "down", "loser", "worst", "crash", "dip", "bottom"])
        direction = "LOSERS" if is_loser else "GAINERS"

        # Extract days
        days = 5  # default
        days_match = re.search(r"(\d+)\s*(?:trading\s*)?days?", lower)
        if days_match:
            days = int(days_match.group(1))
        elif "today" in lower or "1 day" in lower:
            days = 1
        elif "week" in lower:
            days = 5
        elif "month" in lower:
            days = 20

        # Extract limit
        limit = 5
        limit_match = re.search(r"top\s*(\d+)", lower)
        if limit_match:
            limit = int(limit_match.group(1))

        return "SCREENER", {"direction": direction, "days": days, "limit": limit}

    # 3. Stock Comparison intent (e.g. "compare TCS and INFY", "TCS vs INFY")
    comp_match = re.search(r"\b([A-Z0-9&-]+)\s+(?:vs\.?|versus|and|compared\s+to)\s+([A-Z0-9&-]+)\b", msg, re.I)
    if "compare" in lower or (comp_match and len(comp_match.group(1)) >= 2 and len(comp_match.group(2)) >= 2):
        return "COMPARISON", {"raw": msg}

    # 4. Single Ticker Detail or Ambiguous
    return "TICKER_DETAIL", {"raw": msg}

# Test cases
test_queries = [
    "Tell me about which stock has fallen max in last 5 days",
    "Which stock has gained most today?",
    "top 10 losers this week",
    "What was TCS revenue and net profit in FY24?",
    "Compare TCS and INFY margins",
    "hello what can you do?",
    "What is the capex guidance for RELIANCE?"
]

for q in test_queries:
    intent, params = classify_user_intent(q)
    print(f"Query: '{q}'\n  -> Intent: {intent} | Params: {params}\n")
