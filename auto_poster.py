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
                return data[0] # Return top product
    except Exception as e:
        print(f"Coupang API Error: {e}")
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
        print(f"Trend Fetch Error: {e}")
        return "자취생 필수템, 가성비 주방용품, 여름휴가 준비물" # fallback

def generate_post():
    trends = get_trending_keywords()
    
    prompt = f"""당신은 친근한 한국인 라이프스타일/생활꿀팁 전문 SEO 마케터이자 블로거입니다.
다음 실시간 트렌드 키워드 중 하나를 골라, 실생활 꿀팁과 엮어 SEO/AEO/GEO 최적화된 매력적인 블로그 포스팅을 한글로 작성해주세요:
[현재 트렌드]: {trends}

작성 지침:
1. 분량: 1000자 이상, 상세하고 유용한 정보 제공.
2. 구조: H2, H3 태그를 활용한 소제목 분할, 가독성 높은 문단 구조, 핵심 요약(Bullet points), 결론.
3. SEO/AEO/GEO: 독자의 검색 의도와 질문에 직접적으로 답변하는 형태(AEO)를 취하고, 자연스럽게 키워드를 배치하세요.
4. 어조: 친구에게 꿀팁을 전수하듯 자연스럽고 친근한 인간적인 말투 (로봇 같은 딱딱한 말투 절대 금지). 공감과 경험을 바탕으로 한 스토리텔링 기법 적용.
5. 중간중간 [COUPANG_AD] 라는 텍스트를 정확히 2번 삽입하세요. 이 위치에 실제 상품 광고가 들어갈 것입니다.

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
            
    if not response:
        raise Exception('All models failed.')
    
    text = response.text.strip()
    
    # --- 2nd Pass: Review and Revise ---
    eval_prompt = f"""You are a master Editor and SEO/AEO/GEO Specialist.
Review the following blog post draft:

Draft:
{text}

Evaluate the draft on three criteria (0-100 score each):
1. SEO: Keyword usage, headers, readability.
2. GEO: Clear structured data, bullet points, concise facts.
3. AEO: Direct answers to the user's implicit question.

If the total score is below 285/300, completely REWRITE the draft to be perfectly optimized. 
CRITICAL: The very first line of your response MUST still be the exact title of the post, starting with 'Title: '. Do not use markdown formatting for the title line.
Make sure the 2 [COUPANG_AD] placeholders are still present in the text.
The rest of the response should be the heavily revised and optimized body of the post in standard Markdown format."""

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
        
    # Replace [COUPANG_AD] with actual product links based on the title
    product = search_coupang_product(title.split()[0] if title else "가성비템")
    if product:
        ad_html = f"""<div style="text-align: center; margin: 20px 0; padding: 15px; border: 1px solid #eee; border-radius: 8px;">
    <a href="{product.get('productUrl')}" target="_blank" rel="nofollow">
        <img src="{product.get('productImage')}" style="max-width: 200px; border-radius: 4px;" alt="{product.get('productName')}">
        <h4 style="margin: 10px 0; color: #333;">{product.get('productName')}</h4>
        <p style="color: #e52528; font-weight: bold; font-size: 1.2em;">{product.get('productPrice'):,}원</p>
        <button style="background: #0073e9; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer;">👉 최저가 확인하기</button>
    </a>
    <p style="font-size: 0.8em; color: #999; margin-top: 10px;">이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다.</p>
</div>"""
        body = body.replace("[COUPANG_AD]", ad_html)
    else:
        body = body.replace("[COUPANG_AD]", "") # Remove placeholder if API fails
        
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
