import os
import random

import requests
def download_vibe_image(keywords, filename):
    url = f"https://loremflickr.com/800/500/{keywords}/all"
    try:
        r = requests.get(url, timeout=10, allow_redirects=True)
        os.makedirs('assets/images', exist_ok=True)
        filepath = f'assets/images/{filename}.jpg'
        with open(filepath, 'wb') as f:
            f.write(r.content)
        return filepath
    except:
        return ""

from datetime import datetime, timedelta
import urllib.request
import google.generativeai as genai
import hmac
import hashlib
import time
import requests
import json
import urllib.parse
from PIL import Image, ImageDraw, ImageFont
import random

import requests
def download_vibe_image(keywords, filename):
    url = f"https://loremflickr.com/800/500/{keywords}/all"
    try:
        r = requests.get(url, timeout=10, allow_redirects=True)
        os.makedirs('assets/images', exist_ok=True)
        filepath = f'assets/images/{filename}.jpg'
        with open(filepath, 'wb') as f:
            f.write(r.content)
        return filepath
    except:
        return ""


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


def create_text_thumbnail(full_text, filename):
    # 배경색 랜덤 파스텔 톤
    colors = [(232, 244, 253), (253, 236, 232), (232, 253, 241), (249, 232, 253), (255, 249, 230)]
    bg_color = random.choice(colors)
    
    img = Image.new('RGB', (800, 450), color=bg_color)
    draw = ImageDraw.Draw(img)
    
    # 폰트 설정 (기본 폰트 사용, 가급적 맑은 고딕 등)
    try:
        font = ImageFont.truetype('/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf', 55)
    except:
        try:
            font = ImageFont.truetype('/usr/share/fonts/truetype/nanum/NanumGothic.ttf', 55)
        except:
            try:
                font = ImageFont.truetype('malgun.ttf', 55)
            except:
                font = ImageFont.load_default()
            
    # 텍스트 중앙 정렬 계산 로직
    text = full_text
    
    try:
        # Pillow 10+ 호환
        bbox = draw.textbbox((0, 0), text, font=font, align='center')
        w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    except AttributeError:
        # 하위 버전 호환
        w, h = draw.textsize(text, font=font)
        
    x = (800 - w) / 2
    y = (450 - h) / 2
    
    # 텍스트 그림자
    draw.text((x+3, y+3), text, fill=(200, 200, 200), font=font, align='center')
    draw.text((x, y), text, fill=(50, 50, 50), font=font, align='center')
    
    os.makedirs('assets/images', exist_ok=True)
    filepath = f'assets/images/{filename}.webp'
    img.save(filepath, 'WEBP', quality=90)
    return filepath

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



    # [1] 최상단 텍스트 썸네일 생성
    thumb_prompt = f"""당신은 센스있는 라이프스타일 에디터입니다.
키워드 '{best_keyword}'에 대한 정보성 블로그 글 썸네일용 2줄 텍스트를 작성하세요.
첫 줄: 상품과 관련된 일상적인 가벼운 고민이나 장점을 담은 짧은 문구 (주의: '벌레', '악취' 등 불쾌하거나 극단적인 단어 절대 사용 금지)
두 번째 줄: 키워드를 포함하여 해결책을 제시하는 자연스러운 문구
주의: '추천', '리뷰', '내돈내산' 단어 절대 금지. 과장되거나 뜬금없는 공포 조장 금지. 총 25자 이내로 아주 깔끔하게 작성.
예시 1:
자취방 욕실 앞 꿉꿉함
규조토 발매트로 뽀송하게
예시 2:
공간 차지 없는 완벽한
원룸 미니 건조대 활용법
"""
    try:
        thumb_text = generate_with_retry(thumb_prompt).strip().replace('"', '').replace("'", '')
    except:
        thumb_text = f"[{best_keyword}]\n나만 몰랐던 완벽 활용 팁"

    thumb_filename = f"thumb_{int(time.time())}"
    thumb_rel_path = create_text_thumbnail(thumb_text, thumb_filename)
    image_markdown = f"![{product_name}]({{{{ '/' | append: '{thumb_rel_path}' | relative_url }}}})\n\n"

    # [2] 본문 중간용 감성 실사 사진 다운로드 (1장만)
    vibe_prompt = f"""
Translate the following product keyword into 2 English keywords that represent a clean, aesthetic lifestyle or interior mood.
Example: '샤워기 필터' -> 'bathroom,clean'
Example: '무선 키보드' -> 'workspace,desk'
Example: '커피 캡슐' -> 'kitchen,coffee'
Do not use specific brand names, just generic mood keywords separated by comma. Output ONLY the keywords.
Keyword: {best_keyword}
"""
    try:
        vibe_keywords = generate_with_retry(vibe_prompt).strip()
    except:
        vibe_keywords = "interior,clean"
        
    vibe_rel_path = download_vibe_image(vibe_keywords, f"vibe_{int(time.time())}")
    if vibe_rel_path:
        vibe_markdown = f"![감성사진]({{{{ '/' | append: '{vibe_rel_path}' | relative_url }}}})"
    else:
        vibe_markdown = ""




    # [Pass 1: 초안 작성]
    draft_prompt = f"""당신은 생활 꿀팁과 유용한 정보를 전달하는 전문 에디터입니다.
다음 트렌드 키워드와 상품 정보를 바탕으로, 광고 느낌이 전혀 나지 않는 '문제 해결형 순수 정보글' 초안을 1000자 이상 작성하세요.

[트렌드 키워드]: {best_keyword}
[상품명]: {product_name}

지침:
- 소제목은 반드시 마크다운 문법(## 소제목, ### 하위소제목)만 사용하세요.
- 절대로 'H2', 'H3', '## H2.', '### H3.' 처럼 H숫자 글자를 제목 앞에 붙이지 마세요.
- 상품 추천글이 아니라, 독자의 일상적인 문제를 해결해주는 유익한 정보글(팁 공유) 형태로 작성하세요.
- '총평 및 추천 페르소나' 같은 딱딱한 마케팅 용어, 전문 용어를 절대 사용하지 마세요. 대신 '이런 분들께 추천해요' 처럼 친근하고 일상적인 표현을 사용하세요.
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
    rewrite_prompt = f"""당신은 상위 1% 라이프스타일 정보 매거진 에디터입니다. 
다음 [초안]에 [전문가 피드백]을 100% 반영하여 최종 리뷰 포스팅을 작성하세요.
주의: AI 특유의 번역투 문장('결론적으로', '안녕하세요 여러분')을 완벽히 삭제하고, 진짜 나만의 살림 노하우나 유용한 정보를 공유하는 정보성 글처럼 윤문하세요.

[전문가 피드백]
{feedback_content}

[초안]
{draft_content}

[필수 구조 규칙]
글의 맨 첫 줄은 반드시 'Title: 제목' 형식이어야 합니다.
글 서론과 결론 부근에 다음 버튼 HTML 태그를 그대로 2회 삽입하세요.
단, HTML 내의 [DYNAMIC_BUTTON_TEXT] 부분을 지우고, 문맥에 맞게 호기심을 유발하는 부드러운 정보성 문구(예: '이 유리창 청소기 수압에 맞는 필터 찾아보기', '이 안전 차단되는 멀티탭 스펙 비교하기')를 직접 작성해서 덮어씌우세요. 단순한 '구매하기'는 안 됩니다.
{button_html}

[시각적 강조 규칙 - 반드시 사용]
1. 본문의 소제목(H2)은 마크다운 `##` 대신 아래의 소제목 디자인 배너(HTML)로 무조건 감싸주세요. (단, 텍스트는 문맥에 맞게 수정)
<div style="background-color: #34495e; color: white; padding: 12px 20px; border-radius: 8px; font-weight: bold; font-size: 1.1em; margin-top: 30px; margin-bottom: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
  📌 [소제목 내용 여기에 작성]
</div>

2. 글 중간에 딱 1번, 아래의 제공된 감성 실사 사진 마크다운을 본문의 가장 자연스러운 위치에 그대로 삽입하세요.
{vibe_markdown}

3. 글 전체에서 최소 2회 이상, 독자에게 꼭 전달해야 할 핵심 정보(예: 가격 팁, 주의사항)를 아래 박스로 감싸세요.
노란 꿀팁 박스:
<div style="background:#fffbe6; border-left:4px solid #f5c518; padding:14px 18px; margin:20px 0; border-radius:6px; font-size:0.97em;">
💡 <strong>여기에 핵심 꿀팁 내용 작성</strong>
</div>

파란 정보 박스:
<div style="background:#e8f4fd; border-left:4px solid #2196F3; padding:14px 18px; margin:20px 0; border-radius:6px; font-size:0.97em;">
📌 <strong>여기에 스펙/수치 정보 작성</strong>
</div>
"""


    
    final_text = generate_with_retry(rewrite_prompt).strip()

    lines = final_text.split('\n')
    title = f"{best_keyword} 똑똑하게 활용하는 방법"
    body_content = final_text
    
    if lines and lines[0].lower().startswith("title:"):
        title = lines[0][6:].strip().replace('"', "'")
        title = title.replace('추천', '').replace('리뷰', '').replace('내돈내산', '').replace('[', '').replace(']', '')
        title = " ".join(title.split())
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
