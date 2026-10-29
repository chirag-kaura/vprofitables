import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pages import (
    page_auth, page_onboarding,
    page_overview, page_dashboard, page_scanner, page_chart,
    page_simons, page_gann, page_natal, page_tools,
    page_advisor, page_sentiment, page_fundamentals,
    page_trading, page_research, page_risk,
    page_watchlist, page_analytics, page_admin,
)

with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pages", "_shared.js"), "r", encoding="utf-8") as f:
    shared_js = f.read()

# Let's test page_auth.JS alone first
with open("scripts/auth_only.js", "w", encoding="utf-8") as f:
    f.write(page_auth.JS)

# Let's also test combined
combined = "\n;\n".join([
    shared_js,
    page_auth.JS,
    page_onboarding.JS,
    page_overview.JS,
    page_dashboard.JS,
    page_scanner.JS,
    page_chart.JS,
    page_simons.JS,
    page_gann.JS,
    page_natal.JS,
    page_tools.JS,
    page_advisor.JS,
    page_sentiment.JS,
    page_fundamentals.JS,
    page_trading.JS,
    page_research.JS,
    page_risk.JS,
    page_watchlist.JS,
    page_analytics.JS,
    page_admin.JS
])

with open("scripts/combined.js", "w", encoding="utf-8") as f:
    f.write(combined)

print("Wrote scripts/auth_only.js and scripts/combined.js")
