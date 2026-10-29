import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.screener_sync import parse_html_financials
import requests
from bs4 import BeautifulSoup

url = "https://www.screener.in/company/TCS/consolidated/"
r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
soup = BeautifulSoup(r.text, "html.parser")
records = parse_html_financials(soup, "TCS")

print(f"Total parsed records for TCS: {len(records)}")
# Print sample record for Mar 2024 and Jun 2024
for rec in records:
    if rec['fiscal_period'] in ['2024-03-31', '2024-06-30', 'Mar 2024', 'Jun 2024', '2024-Q1', '2024-Q4']:
        print(rec['period_type'], rec['fiscal_period'], "Sales:", rec.get('sales'), "OpProfit:", rec.get('operating_profit'), "EPS:", rec.get('eps'))
