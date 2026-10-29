from curl_cffi import requests
import time

s = requests.Session(impersonate='chrome116')
s.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br, zstd',
    'Connection': 'keep-alive',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
    'Upgrade-Insecure-Requests': '1'
})

print('Warming up...')
try:
    r1 = s.get('https://www.nseindia.com/')
    print('Home:', r1.status_code)
    time.sleep(2)
    
    r2 = s.get('https://www.nseindia.com/option-chain')
    print('Option Chain Page:', r2.status_code)
    time.sleep(2)
    
    s.headers.update({
        'Accept': 'application/json, text/plain, */*',
        'Referer': 'https://www.nseindia.com/option-chain',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
    })
    url = 'https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY'
    r3 = s.get(url)
    print('API:', r3.status_code)
    if r3.status_code == 200:
        print(list(r3.json().keys())[:5])
    else:
        print(r3.text[:100])
except Exception as e:
    print('Err:', e)
