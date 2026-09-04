import hmac, hashlib, requests, urllib.parse
from time import gmtime, strftime

access_key = "d3f6de56-bd4a-4282-823f-a2d5f7a1898f"
secret_key = "dad5117274fc82084ad8276ca91e1cc465483134"

def generate_signature(method, url_path):
    datetime_gmt = strftime('%y%m%d', gmtime()) + 'T' + strftime('%H%M%S', gmtime()) + 'Z'
    path, *query_parts = url_path.split("?")
    query = query_parts[0] if query_parts else ""
    message = datetime_gmt + method + path + query
    signature = hmac.new(bytes(secret_key, "utf-8"), message.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"CEA algorithm=HmacSHA256, access-key={access_key}, signed-date={datetime_gmt}, signature={signature}"

url_path = f"/v2/providers/affiliate_open_api/apis/openapi/products/search?keyword={urllib.parse.quote('캠핑용품')}&limit=1"
url = f"https://api-gateway.coupang.com{url_path}"
headers = {"Authorization": generate_signature('GET', url_path), "Content-Type": "application/json"}

resp = requests.get(url, headers=headers)
if resp.status_code == 200:
    for d in resp.json().get('data', {}).get('productData', []):
        print(d.get('productUrl'))
