import os, json, random, re, time, hmac, hashlib, base64, urllib.parse, datetime, requests
import google.generativeai as genai
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO

# ----------------- CONFIGURATION -----------------
NAVER_CUSTOMER_ID = os.getenv('NAVER_CUSTOMER_ID', '1560667')
NAVER_ACCESS_LICENSE = os.getenv('NAVER_ACCESS_LICENSE', '0100000000275b3c8ab39dd56bad01b6c00904dfb52a7b55ec7176e7e42c48521f51cc0117')
NAVER_SECRET_KEY = os.getenv('NAVER_SECRET_KEY', 'AQAAAAAnWzyKs53Va60BtsAJBN+19kZUXy+tl4BrNzcRhWmIWw==')
COUPANG_ACCESS_KEY = os.getenv('COUPANG_ACCESS_KEY', 'd3f6de56-bd4a-4282-823f-a2d5f7a1898f')
COUPANG_SECRET_KEY = os.getenv('COUPANG_SECRET_KEY', 'dad5117274fc82084ad8276ca91e1cc465483134')

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

def generate_with_retry(prompt, is_json=False):
    for _ in range(3):
        try:
            res = model.generate_content(prompt)
            text = res.text.strip()
            if is_json:
                text = text.replace('```json', '').replace('```', '').strip()
            return text
        except Exception as e:
            time.sleep(2)
    return "{}" if is_json else ""

# ----------------- NAVER API (KEYWORD MINING) -----------------
def get_naver_signature(timestamp, method, path):
    message = f"{timestamp}.{method}.{path}"
    sign = hmac.new(NAVER_SECRET_KEY.encode('utf-8'), message.encode('utf-8'), hashlib.sha256)
    return base64.b64encode(sign.digest()).decode()

def get_trending_keywords(hint_keyword):
    path = '/keywordstool'
    url = 'https://api.naver.com' + path
    timestamp = str(int(round(time.time() * 1000)))
    headers = {
        'X-Timestamp': timestamp,
        'X-API-KEY': NAVER_ACCESS_LICENSE,
        'X-Customer': str(NAVER_CUSTOMER_ID),
        'X-Signature': get_naver_signature(timestamp, 'GET', path)
    }
    try:
        response = requests.get(url, params={'hintKeywords': hint_keyword, 'showDetail': 1}, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return [k['relKeyword'] for k in data.get('keywordList', [])[:50]]
    except Exception as e:
        print(f"Naver API error: {e}")
    return []

# ----------------- COUPANG API (PRODUCT FETCHING) -----------------
def get_coupang_signature(method, url_path):
    from time import gmtime, strftime
    datetime_gmt = strftime('%y%m%d', gmtime()) + 'T' + strftime('%H%M%S', gmtime()) + 'Z'
    path, *query_parts = url_path.split("?")
    query = query_parts[0] if query_parts else ""
    message = datetime_gmt + method + path + query
    signature = hmac.new(bytes(COUPANG_SECRET_KEY, "utf-8"), message.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"CEA algorithm=HmacSHA256, access-key={COUPANG_ACCESS_KEY}, signed-date={datetime_gmt}, signature={signature}"

def search_coupang_products(keyword, limit=3):
    method = 'GET'
    url_path = f"/v2/providers/affiliate_open_api/apis/openapi/products/search?keyword={urllib.parse.quote(keyword)}&limit={limit}"
    url = f"https://api-gateway.coupang.com{url_path}"
    headers = {"Authorization": get_coupang_signature(method, url_path), "Content-Type": "application/json"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json().get('data', {}).get('productData', [])
    except Exception as e:
        print(f"Coupang API error: {e}")
    return []

# ----------------- THUMBNAIL LOGIC -----------------
def create_text_thumbnail(text, filename_prefix):
    import urllib.request
    try:
        font_path = "NanumGothic-Bold.ttf"
        if not os.path.exists(font_path):
            urllib.request.urlretrieve("https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Bold.ttf", font_path)
            
        img_width, img_height = 800, 800
        bg_color = (20, 20, 25)
        text_color = (255, 255, 255)
        
        img = Image.new('RGB', (img_width, img_height), color=bg_color)
        draw = ImageDraw.Draw(img)
        font = ImageFont.truetype(font_path, 75)
        
        lines = text.split('\n')
        y_text = (img_height // 2) - (len(lines) * 50)
        for line in lines:
            line = line.strip()
            if not line: continue
            try:
                bbox = draw.textbbox((0, 0), line, font=font)
                width = bbox[2] - bbox[0]
                height = bbox[3] - bbox[1]
            except:
                width = len(line) * 20; height = 80
            draw.text(((img_width - width) / 2, y_text), line, font=font, fill=text_color)
            y_text += height + 40
            
        os.makedirs('assets/images', exist_ok=True)
        img_path = f'assets/images/{filename_prefix}.webp'
        img.save(img_path, 'WEBP', quality=85)
        return img_path
    except Exception as e:
        print(f"Thumbnail error: {e}")
        return ""

def download_vibe_image(img_url, filename_prefix):
    if not img_url: return ""
    try:
        os.makedirs('assets/images', exist_ok=True)
        img_r = requests.get(img_url, timeout=10)
        image = Image.open(BytesIO(img_r.content))
        base_width = 800
        if image.size[0] > base_width:
            wpercent = (base_width / float(image.size[0]))
            hsize = int((float(image.size[1]) * float(wpercent)))
            image = image.resize((base_width, hsize), Image.Resampling.LANCZOS)
        img_path = f'assets/images/{filename_prefix}.webp'
        image.save(img_path, 'WEBP', quality=85)
        return img_path
    except:
        return ""

# ----------------- POST GENERATION -----------------
def generate_post(keyword, products):
    # Formulate product info
    products_info = ""
    for idx, p in enumerate(products, 1):
        products_info += f"[{idx}위 상품]\n상품명: {p.get('productName')}\n가격: {p.get('productPrice')}원\n링크: {p.get('productUrl')}\n\n"

    # NEW: Advanced Copywriting Prompt
    rewrite_prompt = f"""
    당신은 네이버/구글 상위 1% 인플루언서 마케터입니다.
    이번 포스팅의 핵심 키워드는 '{keyword}'입니다. 
    
    [작성 원칙 - 매우 중요]
    1. 제목과 본문에 "추천", "리뷰", "BEST", "고르는 법" 같은 뻔한 광고성 단어를 절대 쓰지 마세요.
    2. 소비자의 일상적인 불편함(페인포인트)이나 호기심을 해결해주는 '순수 정보성 꿀팁 매거진' 톤으로 작성하세요.
    3. 글의 중반부 이후에 자연스럽게 아래의 [쿠팡 1~3위 상품 정보]를 해결책으로 제시하세요. (상품명과 장점을 자연스럽게 어필)
    4. 반드시 마크다운 포맷으로 작성하세요. 
    5. 본문의 적절한 위치(서론 직후)에 정확히 '[VIBE_IMAGE_HERE]' 라고 딱 1번만 입력하세요.
    6. 각 상품을 소개할 때, 제품의 링크 위치에 정확히 '[COUPANG_LINK_1]', '[COUPANG_LINK_2]', '[COUPANG_LINK_3]' 처럼 플레이스홀더를 삽입하세요.
    
    [쿠팡 1~3위 상품 정보]
    {products_info}
    
    글을 시작하세요.
    """
    final_text = generate_with_retry(rewrite_prompt)
    final_text = re.sub(r'(?i)^(?:#+\s*)?H[23]:\s*', '', final_text, flags=re.MULTILINE)
    final_text = re.sub(r'^---.*?---\s*', '', final_text, flags=re.DOTALL)

    meta_prompt = f"""
    방금 작성된 글에 대한 JSON 메타데이터를 반환하세요.
    {{ 
      'title': '{keyword}를 활용한 어그로성/호기심 자극형 블로그 제목 (광고 냄새 제거)', 
      'thumb_hook': '{keyword} 관련 썸네일에 들어갈 아주 짧고 강렬한 두 줄 텍스트', 
      'vibe_keywords': '픽사베이 영문 검색용 분위기 이미지 키워드 (예: car accessory, baby room)'
    }}
    """
    meta_json_str = generate_with_retry(meta_prompt, is_json=True)
    try:
        meta = json.loads(meta_json_str)
        title, thumb_hook, vibe_keywords = meta['title'], meta['thumb_hook'], meta['vibe_keywords']
    except:
        title, thumb_hook, vibe_keywords = f"{keyword} 완벽 가이드", f"{keyword}\n알아보기", "lifestyle"

    # Fetch Pixabay Image
    image_urls = []
    try:
        url = f"https://pixabay.com/api/?key=57366919-c2774ae5199cc6a6cdb9a301d&q={urllib.parse.quote(vibe_keywords)}&image_type=photo&orientation=horizontal&per_page=5"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data.get('hits'):
                image_urls = [hit.get('largeImageURL', hit.get('webformatURL')) for hit in data['hits']]
    except: pass

    # Replace VIBE image
    parts = final_text.split('[VIBE_IMAGE_HERE]')
    processed_text = parts[0]
    if len(parts) > 1:
        v_path = ""
        if image_urls:
            v_path = download_vibe_image(image_urls[0], f"vibe_{int(time.time())}")
        if v_path:
            processed_text += f"\n<br>\n![관련이미지]({{{{ '/' | append: '{v_path}' | relative_url }}}})\n<br>\n"
        processed_text += parts[1]
    
    # Generate Thumbnail
    thumb_rel_path = create_text_thumbnail(thumb_hook, f"thumb_{int(time.time())}")
    
    # Replace Coupang Links with full-width CTA buttons
    for idx, p in enumerate(products, 1):
        placeholder = f'[COUPANG_LINK_{idx}]'
        cta_html = f"""
<div style="margin: 30px 0; padding: 20px; text-align: center; border: 1px solid #e5e7eb; border-radius: 12px; background-color: #fafafa; box-shadow: 0 4px 6px rgba(0,0,0,0.02);">
    <h3 style="color: #111; margin-bottom: 12px; font-weight: bold; font-size: 18px; word-break: keep-all;">💡 실시간 {idx}위 상품 확인하기</h3>
    <a href="{p.get('productUrl')}" target="_blank" style="display: block; width: 100%; max-width: 320px; margin: 0 auto; padding: 16px 20px; box-sizing: border-box; background-color: #e52528; color: white; font-size: 17px; font-weight: bold; text-decoration: none; border-radius: 8px; box-shadow: 0 4px 6px rgba(229,37,40,0.3); word-break: keep-all;">🚀 제품 상세 및 후기 보러가기</a>
</div>
"""
        processed_text = processed_text.replace(placeholder, cta_html)

    ftc_text = '\n<p style="font-size: 12px; color: #999; text-align: center; margin-top: 40px; margin-bottom: 10px;">이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다.</p>\n'
    ad_bottom = '<div class="manual-ad-container" style="margin: 30px 0; text-align: center;">\n<ins class="adsbygoogle" style="display:block" data-ad-client="ca-pub-2228289204702106" data-ad-slot="2231432699" data-ad-format="auto" data-full-width-responsive="true"></ins>\n<script>(adsbygoogle = window.adsbygoogle || []).push({});</script>\n</div>\n'
    
    final_text = processed_text + ftc_text + ad_bottom
    return title, final_text, thumb_rel_path

def main():
    history_file = 'used_keywords.txt'
    used_keywords = set()
    if os.path.exists(history_file):
        with open(history_file, 'r', encoding='utf-8') as f:
            used_keywords = set([line.strip() for line in f if line.strip()])

    # Load broad categories (or leaf categories) from external file
    seed_categories = []
    if os.path.exists('coupang_categories.txt'):
        with open('coupang_categories.txt', 'r', encoding='utf-8') as f:
            seed_categories = [line.strip() for line in f if line.strip()]
    if not seed_categories:
        seed_categories = ['생활용품'] # fallback
        
    selected_seed = random.choice(seed_categories)
    print(f"Mining trending keywords for: {selected_seed}")
    
    trending = get_trending_keywords(selected_seed)
    
    target_keyword = None
    for kw in trending:
        if kw not in used_keywords:
            target_keyword = kw
            break
            
    if not target_keyword:
        # Fallback if somehow all are used or API fails
        print("Fallback keyword generated.")
        target_keyword = selected_seed + " 베스트"

    print(f"Selected Golden Keyword: {target_keyword}")
    
    # Fetch Top 3 from Coupang
    products = search_coupang_products(target_keyword, limit=3)
    if not products:
        print("Failed to fetch products from Coupang API.")
        return

    # Generate Blog Post
    title, post_content, thumb_path = generate_post(target_keyword, products)
    
    if post_content:
        # Save keyword to history
        with open(history_file, 'a', encoding='utf-8') as f:
            f.write(target_keyword + '\n')
            
        date_str = datetime.datetime.now().strftime('%Y-%m-%d')
        safe_title = target_keyword.replace(' ', '-').lower()
        filename = f'_posts/{date_str}-{safe_title}.md'
        os.makedirs('_posts', exist_ok=True)
        frontmatter = f"---\nlayout: post\ntitle: \"{title}\"\ndate: {date_str}\nimage: {thumb_path}\n---\n\n"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(frontmatter + post_content)
        print(f'Successfully generated {filename}')

if __name__ == '__main__':
    main()
