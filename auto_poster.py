import os
import random
from datetime import datetime, timedelta
import urllib.request
import google.generativeai as genai
import hmac
import hashlib
import time
import requests
import json
import urllib.parse
import xml.etree.ElementTree as ET

from dotenv import load_dotenv
load_dotenv()

COUPANG_ACCESS_KEY = "d3f6de56-bd4a-4282-823f-a2d5f7a1898f"
COUPANG_SECRET_KEY = "dad5117274fc82084ad8276ca91e1cc465483134"

# =================================================================
# 1. API & Failover Setup (Dynamic Rotation)
# =================================================================
api_keys_str = os.environ.get('GEMINI_API_KEY', '')
if not api_keys_str:
    print('GEMINI_API_KEY is not set.')
    exit(1)

API_KEYS = [k.strip() for k in api_keys_str.split(',') if k.strip()]
MODELS = ['gemini-3.5-flash-lite', 'gemini-3.1-flash-lite']

def generate_with_retry(prompt, is_json=False):
    generation_config = {"response_mime_type": "application/json"} if is_json else None
    
    for key in API_KEYS:
        genai.configure(api_key=key)
        for model_name in MODELS:
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(prompt, generation_config=generation_config)
                return response.text
            except Exception as e:
                print(f"Fallback triggered: Failed on {model_name} with key ...{key[-4:]} -> {e}")
                time.sleep(2)
                continue
                
    raise Exception("Critical: All API keys and models are exhausted!")

# =================================================================
# 2. Coupang API Logic (DO NOT MODIFY)
# =================================================================
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
        return "자취 필수템, 가성비 주방용품, 여름휴가 준비물"

def get_best_naver_keyword(keywords):
    CLIENT_ID = "yfjf88u5j9"
    CLIENT_SECRET = "caO9XsoqsjFbsZv60ruCAFx41diF7vA8aOyoMI8a"
    try:
        top_5 = keywords[:5]
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        keyword_groups = [{"groupName": kw, "keywords": [kw]} for kw in top_5]
        
        body = {
            "startDate": start_date, "endDate": end_date,
            "timeUnit": "date", "keywordGroups": keyword_groups
        }
        url = "https://naverapihub.apigw.ntruss.com/search-trend/v1/search"
        req = urllib.request.Request(url)
        req.add_header("X-NCP-APIGW-API-KEY-ID", CLIENT_ID)
        req.add_header("X-NCP-APIGW-API-KEY", CLIENT_SECRET)
        req.add_header("Content-Type", "application/json")
        
        response = urllib.request.urlopen(req, data=json.dumps(body).encode("utf-8"))
        if response.getcode() == 200:
            data = json.loads(response.read().decode('utf-8'))
            best_kw, max_val = top_5[0], -1
            for res in data.get("results", []):
                total_ratio = sum(item.get("ratio", 0) for item in res.get("data", []))
                if total_ratio > max_val:
                    max_val = total_ratio
                    best_kw = res["groupName"]
            return best_kw
    except Exception:
        pass
    return keywords[0] if keywords else "가성비템"

def generate_post():
    trends = get_trending_keywords()
    keyword_list = [k.strip() for k in trends.split(",") if k.strip()]
    best_keyword = get_best_naver_keyword(keyword_list)
    product = search_coupang_product(best_keyword)
    
    product_url = product.get('productUrl', '#') if product else '#'
    product_image = product.get('productImage', '') if product else ''
    product_name = product.get('productName', best_keyword) if product else best_keyword
    
    button_html = f'''
<div style="text-align: center; margin: 35px 0;">
  <a href="{product_url}" rel="nofollow noopener" style="background-color: #f8f9fa; color: #111; padding: 16px 32px; text-decoration: none; font-size: 18px; font-weight: bold; border-radius: 8px; display: inline-block; border: 1px solid #ced4da; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">👉 [DYNAMIC_BUTTON_TEXT]</a>
  <p style="font-size: 0.8em; color: #999; margin-top: 10px;">이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다.</p>
</div>
'''

    image_markdown = f"![{product_name}]({product_image})\n\n" if product_image else ""

    # [Pass 1: 초안 작성]
    draft_prompt = f"""당신은 '내돈내산' 리뷰 전문가입니다.
다음 트렌드 키워드와 쿠팡 상품 정보를 바탕으로 생생한 리뷰 포스팅 초안을 1000자 이상 작성하세요.

[트렌드 키워드]: {best_keyword}
[상품명]: {product_name}

지침:
- H2, H3 제목을 적절히 사용하세요.
- 실제 사용해본 것처럼 솔직한 장단점을 적어주세요.
"""
    draft_content = generate_with_retry(draft_prompt).strip()

    # [Pass 2: 검사]
    check_prompt = f"""다음은 작성된 쿠팡 제품 리뷰 초안입니다. 이 초안을 최고 수준의 SEO, AEO, GEO 전문가 관점에서 꼼꼼하게 검사하고 비판하세요.

[초안]
{draft_content}

[검사 지침]
1. SEO: 롱테일 키워드({best_keyword})가 제목, 서론, 본문에 자연스럽게 배치되었는가?
2. AEO: 독자의 구매 고민(배송, 가격, 성능)에 대한 답변이 포함되었는가?
위 관점에서 무엇을 수정해야 완벽해질지 5가지 피드백을 작성하세요.
"""
    feedback_content = generate_with_retry(check_prompt).strip()

    # [Pass 3: 최종 윤문]
    rewrite_prompt = f"""당신은 상위 1% 리뷰 인플루언서입니다. 
다음 [초안]에 [전문가 피드백]을 100% 반영하여 최종 리뷰 포스팅을 작성하세요.
주의: AI 특유의 번역투 문장('결론적으로', '안녕하세요 여러분')을 완벽히 삭제하고, 진짜 내돈내산 한 것 같은 찰진 말투로 윤문하세요.

[전문가 피드백]
{feedback_content}

[초안]
{draft_content}

[필수 구조 규칙]
글의 맨 첫 줄은 반드시 'Title: 제목' 형식이어야 합니다.
글 서론과 결론 부근에 다음 버튼 HTML 태그를 그대로 2회 삽입하세요.
단, HTML 내의 [DYNAMIC_BUTTON_TEXT] 부분을 지우고, 문맥에 맞게 호기심을 유발하는 부드러운 정보성 문구(예: '이 유리창 청소기 수압에 맞는 필터 찾아보기', '이 안전 차단되는 멀티탭 스펙 비교하기')를 직접 작성해서 덮어씌우세요. 단순한 '구매하기'는 안 됩니다.
{button_html}
"""
    
    final_text = generate_with_retry(rewrite_prompt).strip()

    lines = final_text.split('\n')
    title = f"{best_keyword} 추천"
    body_content = final_text
    
    if lines and lines[0].lower().startswith("title:"):
        title = lines[0][6:].strip().replace('"', "'")
        body_content = '\n'.join(lines[1:]).strip()
        
    # 쿠팡 원본 이미지 최상단 추가
    body_content = image_markdown + body_content

    # 애드센스 (수동 코드 보호)
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

    final_body = ad_top + "\n" + body_content + "\n" + ad_bottom
    return title, final_body


def save_post(title, body):
    now = datetime.utcnow()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%Y-%m-%d %H:%M:%S")
    slug = "".join(c if c.isalnum() else "-" for c in title.lower())
    slug = "-".join(filter(None, slug.split("-")))[:50]
    if not slug:
        slug = str(int(time.time()))
    filename = f"{date_str}-{slug}.md"
    filepath = os.path.join('_posts', filename)
    os.makedirs('_posts', exist_ok=True)
    
    frontmatter = f"---\nlayout: post\ntitle: \"{title}\"\ndate: {time_str}\ncategories: [Life]\n---\n\n{body}\n"
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(frontmatter)

if __name__ == "__main__":
    title, body = generate_post()
    save_post(title, body)
