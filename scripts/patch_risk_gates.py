with open('core/risk_gates.py', 'r', encoding='utf-8') as f:
    c = f.read()

target = "return True, f\"All risk gates passed"
replacement = """    # 5. Earnings / Board Meeting Event Risk Gate (Avoid gap risk)
    try:
        from core.corporate_calendar import is_earnings_imminent
        imminent = is_earnings_imminent(candidate['symbol'], window_days=2)
        if imminent.get('imminent'):
            return False, f"Event Risk Gate: {imminent['risk_message']}. Avoid new breakout entry into imminent earnings announcement."
    except Exception:
        pass

    return True, f\"All risk gates passed"""

if target in c:
    c = c.replace(target, replacement, 1)
    with open('core/risk_gates.py', 'w', encoding='utf-8') as f:
        f.write(c)
    print("Successfully patched core/risk_gates.py")
else:
    print("Target not found in core/risk_gates.py")
