import requests, json

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}
# Naver Shopping Categories (Category Dictionary API is sometimes open or we can scrape Naver Shopping)
url = "https://shopping.naver.com/home"
try:
    r = requests.get(url, headers=headers, timeout=5)
    print("Naver:", r.status_code)
except Exception as e:
    print(e)
