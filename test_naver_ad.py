import os, time, hmac, hashlib, base64, requests
from dotenv import load_dotenv

load_dotenv(r'C:\Users\hsm29\Documents\AntiGravity_Project\Naverblog_Auto\.env')

BASE_URL = 'https://api.naver.com'
CUSTOMER_ID = os.getenv('NAVER_CUSTOMER_ID')
ACCESS_LICENSE = os.getenv('NAVER_ACCESS_LICENSE')
SECRET_KEY = os.getenv('NAVER_SECRET_KEY')

def generate_signature(timestamp, method, path):
    message = f"{timestamp}.{method}.{path}"
    sign = hmac.new(SECRET_KEY.encode('utf-8'), message.encode('utf-8'), hashlib.sha256)
    return base64.b64encode(sign.digest()).decode()

def get_header(method, path):
    timestamp = str(int(round(time.time() * 1000)))
    signature = generate_signature(timestamp, method, path)
    return {
        'X-Timestamp': timestamp,
        'X-API-KEY': ACCESS_LICENSE,
        'X-Customer': str(CUSTOMER_ID),
        'X-Signature': signature
    }

path = '/keywordstool'
url = BASE_URL + path
params = {'hintKeywords': '캠핑용품', 'showDetail': 1}
headers = get_header('GET', path)
response = requests.get(url, params=params, headers=headers)
print(response.status_code)
if response.status_code == 200:
    data = response.json()
    keywords = [k['relKeyword'] for k in data['keywordList'][:10]]
    print(keywords)
else:
    print(response.text)
