import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.tools.personalization_tool import parse_and_update_preferences, get_user_risk_profile

res = parse_and_update_preferences("I dont like investing in PSU banks or Adani stocks, and I prefer companies that pay regular dividends. Keep this in mind.")
print('Result text:', res['summary_text'])
print('Updated Profile:', get_user_risk_profile())
