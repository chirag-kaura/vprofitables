import requests
from bs4 import BeautifulSoup

url = "https://www.screener.in/company/TCS/consolidated/"
r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
soup = BeautifulSoup(r.text, "html.parser")

for sec_id in ['profit-loss', 'quarters']:
    sec = soup.find('section', id=sec_id)
    if sec:
        table = sec.find('table')
        if table:
            headers = [th.text.strip() for th in table.find_all('th')]
            print(f"=== SECTION: {sec_id} ===")
            print("Headers:", headers)
            for tr in table.find('tbody').find_all('tr'):
                tds = tr.find_all('td')
                if tds:
                    raw = tds[0].text.strip().replace('\xa0', ' ')
                    clean = raw.replace('+', '').strip().lower()
                    print(f"  raw: '{raw}' -> clean: '{clean}' | val: '{tds[1].text.strip()}'")
