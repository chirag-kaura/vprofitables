import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from bs4 import BeautifulSoup
from core.screener_sync import parse_html_financials

url = "https://www.screener.in/company/ADANIENT/consolidated/"
r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
soup = BeautifulSoup(r.text, "html.parser")
records = parse_html_financials(soup, "ADANIENT")

print(f"Total parsed records for ADANIENT: {len(records)}")
for rec in records[-4:]:
    print(rec['period_type'], rec['fiscal_period'], "Sales:", rec.get('sales'), "OpProfit:", rec.get('operating_profit'), "EPS:", rec.get('eps'))
