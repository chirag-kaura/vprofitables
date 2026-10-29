import re

with open("core/chatbot_engine.py", "r", encoding="utf-8") as f:
    code = f.read()

# 1. Update classify_user_intent to support SWING_SETUPS and clear sticky context
old_classify = """def classify_user_intent(message: str, active_symbol: Optional[str] = None) -> Tuple[str, Dict[str, Any]]:
    \"\"\"
    Categorize user query into distinct execution intents:
      - 'SCREENER': Quantitative performance scans (gainers, losers, 5-day drops, volume)
      - 'COMPARISON': Comparing 2 or more stocks (e.g. TCS vs INFY)
      - 'HELP': Help, capabilities, greetings
      - 'TICKER_DETAIL': Deep dive into a specific stock's fundamentals or guidance
      - 'AMBIGUOUS': Question without any stock specified
    \"\"\"
    msg = message.strip()
    lower = msg.lower()
    _load_symbol_map()

    # 1. Help & Greeting intent
    if re.search(r"^(hi|hello|hey|help|who are you|what can you do|capabilities|guide)\\b", lower):
        return "HELP", {}"""

new_classify = """def classify_user_intent(message: str, active_symbol: Optional[str] = None) -> Tuple[str, Dict[str, Any]]:
    \"\"\"
    Categorize user query into distinct execution intents:
      - 'SWING_SETUPS': Short-term / swing trades (10-15 days, Wyckoff, trend continuation)
      - 'SCREENER': Quantitative performance scans (gainers, losers, 5-day drops, volume)
      - 'COMPARISON': Comparing 2 or more stocks (e.g. TCS vs INFY)
      - 'HELP': Help, capabilities, greetings
      - 'TICKER_DETAIL': Deep dive into a specific stock's fundamentals or guidance
      - 'AMBIGUOUS': Question without any stock specified
    \"\"\"
    msg = message.strip()
    lower = msg.lower()
    _load_symbol_map()

    # Guardrail: If query is market discovery or asking for stock ideas, decouple active_symbol
    is_market_discovery = bool(re.search(
        r"\\b(what\\s+all\\s+stocks|which\\s+stocks|suggest|short\\s+term|swing|ideas|look\\s+for|screener|scanner|recommend|best\\s+stocks|top\\s+stocks|any\\s+stocks)\\b",
        lower
    ))
    if is_market_discovery:
        active_symbol = None

    # 1. Help & Greeting intent
    if re.search(r"^(hi|hello|hey|help|who are you|what can you do|capabilities|guide)\\b", lower):
        return "HELP", {}

    # 2. Short-Term Swing Trade Setup intent (10-15 days, swing trade suggestions)
    swing_patterns = [
        r"short\\s*term\\s*trade",
        r"10[- ](?:to[- ])?15\\s*days?",
        r"swing\\s*trade",
        r"swing\\s*trading",
        r"what\\s+all\\s+stocks\\s+can\\s+i\\s+look\\s+for",
        r"suggest.*stocks",
        r"stocks\\s+to\\s+(buy|trade|watch)",
        r"trade\\s*setups?",
        r"trading\\s*ideas?",
    ]
    if any(re.search(pat, lower) for pat in swing_patterns):
        # Extract horizon if present
        horizon_days = "10-15 days"
        h_match = re.search(r"(\\d+[- ](?:to[- ])?\\d+\\s*days?)", lower)
        if h_match:
            horizon_days = h_match.group(1)
        return "SWING_SETUPS", {"horizon": horizon_days}"""

old_crlf = old_classify.replace("\n", "\r\n")
new_crlf = new_classify.replace("\n", "\r\n")

if old_classify in code:
    code = code.replace(old_classify, new_classify)
    print("Replaced classify_user_intent (LF)")
elif old_crlf in code:
    code = code.replace(old_crlf, new_crlf)
    print("Replaced classify_user_intent (CRLF)")
else:
    print("Failed to find old_classify")

with open("core/chatbot_engine.py", "w", encoding="utf-8") as f:
    f.write(code)
print("Updated chatbot_engine.py intent classification")
