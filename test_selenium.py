from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
import json

def fetch_nse_json_selenium(url):
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64)')
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    try:
        driver.get('https://www.nseindia.com')
        time.sleep(2)
        driver.get(url)
        time.sleep(2)
        content = driver.find_element("tag name", "body").text
        data = json.loads(content)
        return list(data.keys())
    except Exception as e:
        print("Err:", e)
        return None
    finally:
        driver.quit()

print(fetch_nse_json_selenium('https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY'))
