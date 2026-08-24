import os
import random
from datetime import datetime
from google import genai
import hmac
import hashlib
import time
import requests
import json
import urllib.parse
import xml.etree.ElementTree as ET

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
COUPANG_ACCESS_KEY = "d3f6de56-bd4a-4282-823f-a2d5f7a1898f"
COUPANG_SECRET_KEY = "dad5117274fc82084ad8276ca91e1cc465483134"

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment variables.")

client = genai.Client(api_key=GEMINI_API_KEY)

def generate_hmac(method, url, secret_key, access_key):
    path, *query = url.split("?")
    os.environ['TZ'] = 'GMT+0'
    time.tzset() if hasattr(time, 'tzset') else None
    dt = time.strftime('%y%m%d') + 'T' + time.strftime('%H%M%S') + 'Z'
    message = dt + method + path + (query[0] if query else "")
    signature = hmac.new(secret_key.encode('utf-8'), message.encode('utf-8'), hashlib.sha256).hexdigest()
    return f"CEA algorithm=HmacSHA256, access-key={access_key}, signed-date={dt}, signature={signature}"

def search_coupang_product(keyword):
    encoded_keyword = urllib.parse.quote(keyword)
    url = f"/v2/providers/affiliate_open_api/apis/openapi/products/search?keyword={encoded_keyword}&limit=3"
    full_url = f"https://api-gateway.coupang.com{url}"
    authorization = generate_hmac('GET', url, COUPANG_SECRET_KEY, COUPANG_ACCESS_KEY)
    headers = {"Authorization": authorization, "Content-Type": "application/json"}
    
    try:
        response = requests.get(full_url, headers=headers)
        if response.status_code == 200:
            data = response.json().get('data', {}).get('productData', [])
            if data:
                return data[0]
    except Exception as e:
        pass
    return None

def get_trending_keywords():
    try:
        url = "https://trends.google.com/trends/trendingsearches/daily/rss?geo=KR"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        root = ET.fromstring(response.content)
        keywords = [item.find('title').text for item in root.findall('.//item') if item.find('title') is not None]
        return ", ".join(keywords[:10])
    except Exception as e:
        return "자취생 필수템, 가성비 주방용품, 여름휴가 준비물"

def generate_post():
    trends = get_trending_keywords()
    
    # 먼저 트렌드 키워드 중 하나를 골라 상품을 검색합니다.
    product = search_coupang_product(trends.split(",")[0] if trends else "가성비템")
    
    product_url = product.get('productUrl', '#') if product else '#'
    
    button_html = f'''
<div style="text-align: center; margin: 35px 0;">
  <a href="{product_url}" rel="nofollow noopener" style="background-color: #f8f9fa; color: #111; padding: 16px 32px; text-decoration: none; font-size: 18px; font-weight: bold; border-radius: 8px; display: inline-block; border: 1px solid #ced4da; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">👉 [버튼 문구]</a>
  <p style="font-size: 0.8em; color: #999; margin-top: 10px;">이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다.</p>
</div>
'''

    prompt = f"""당신은 '라이프해킹' 생존 꿀팁 전문 블로거입니다.
다음 실시간 트렌드 키워드 중 하나를 골라, 실생활 꿀팁과 엮어 매력적인 블로그 포스팅을 한글로 작성해주세요:
[현재 트렌드]: {trends}

작성 지침:
1. 분량: 1000자 이상.
2. H2, H3 소제목 사용, 중요한 문장은 굵게(Bold) 처리.
3. 소프트셀링 버튼 삽입: 글의 중간(해결책 제시 직후)과 글 맨 마지막 요약 뒤, **총 2곳**에 아래의 링크 박스 HTML을 직접 삽입하세요.
   단 HTML 코드 안의 [버튼 문구] 부분을 지우고, 문맥에 맞게 호기심을 유발하는 부드러운 정보성 문구(예: '👉 우리집 수압에 맞는 필터 찾아보기', '👉 누전 차단되는 멀티탭 스펙 비교하기')로 직접 작성해서 채워넣어주세요.
{button_html}

Important: The very first line of your response MUST be the exact title of the post, starting with 'Title: '. Do not use markdown formatting for the title line.
The rest of the response should be the body of the post in standard Markdown format."""

    models_to_try = ['gemini-3.5-flash-lite', 'gemini-3.1-flash-lite']
    response = None
    for model_name in models_to_try:
        try:
            response = client.models.generate_content(model=model_name, contents=prompt)
            break
        except:
            continue
            
    text = response.text.strip() if response else ""
    
    eval_prompt = f"""You are a master Editor. Review the draft:
{text}

Evaluate on SEO/AEO/GEO. If below 285/300, completely REWRITE it.
CRITICAL: Maintain the 'Title: ...' at the very first line.
CRITICAL: Do NOT remove or modify the raw HTML `<div>` blocks containing the soft-sell buttons. Ensure there are exactly two button HTML blocks in the text.
The rest of the response should be the heavily revised body of the post in standard Markdown format."""

    revised_response = None
    for model_name in models_to_try:
        try:
            revised_response = client.models.generate_content(model=model_name, contents=eval_prompt)
            break
        except:
            continue
            
    if revised_response and revised_response.text.strip():
        text = revised_response.text.strip()

    lines = text.split('\n')
    title = "Life Tips Update"
    if lines and lines[0].lower().startswith("title:"):
        title = lines[0][6:].strip().replace('"', "'")
        body = '\n'.join(lines[1:]).strip()
    else:
        body = text
        

    ad_top = '''
<div class="manual-ad-container" style="margin: 25px 0; text-align: center;">
    <ins class="adsbygoogle"
         style="display:block"
         data-ad-client="ca-pub-2228289204702106"
         data-ad-slot="9807209388"
         data-ad-format="auto"
         data-full-width-responsive="true"></ins>
    <script>(adsbygoogle = window.adsbygoogle || []).push({});</script>
</div>'''
    ad_bottom = '''
<div class="manual-ad-container" style="margin: 35px 0 10px 0; text-align: center;">
    <ins class="adsbygoogle"
         style="display:block"
         data-ad-client="ca-pub-2228289204702106"
         data-ad-slot="1633205896"
         data-ad-format="auto"
         data-full-width-responsive="true"></ins>
    <script>(adsbygoogle = window.adsbygoogle || []).push({});</script>
</div>'''

    body = ad_top + "\n" + body + "\n" + ad_bottom
    return title, body


def save_post(title, body):
    now = datetime.utcnow()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%Y-%m-%d %H:%M:%S")
    slug = "".join(c if c.isalnum() else "-" for c in title.lower())
    slug = "-".join(filter(None, slug.split("-")))[:50]
    filename = f"{date_str}-{slug}.md"
    filepath = os.path.join('_posts', filename)
    os.makedirs('_posts', exist_ok=True)
    
    frontmatter = f"---\nlayout: post\ntitle: \"{title}\"\ndate: {time_str}\ncategories: [Life]\n---\n\n{body}\n"
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(frontmatter)

if __name__ == "__main__":
    title, body = generate_post()
    save_post(title, body)
