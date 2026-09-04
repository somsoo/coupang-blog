import requests
from bs4 import BeautifulSoup
import re

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
}

url = "https://www.coupang.com/"
try:
    response = requests.get(url, headers=headers, timeout=10)
    print("Status:", response.status_code)
    
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        # Coupang's categories are usually in a ul with class 'menu' or 'gnb'
        # Let's just look for category links
        category_links = soup.select('a[href*="/np/categories/"]')
        cats = set()
        for link in category_links:
            text = link.get_text(strip=True)
            if text and len(text) > 1:
                cats.add(text)
        
        with open('coupang_categories_test.txt', 'w', encoding='utf-8') as f:
            for c in sorted(cats):
                f.write(c + '\n')
        print(f"Found {len(cats)} categories.")
    else:
        print("Blocked by Coupang.")
except Exception as e:
    print("Error:", e)
