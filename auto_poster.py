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

api_keys_str = os.getenv("GEMINI_API_KEY", "")
if not api_keys_str:
    print("Critical: GEMINI_API_KEY is not set.")
    exit(1)

API_KEYS = [k.strip() for k in api_keys_str.split(',') if k.strip()]
MODELS = ['gemini-3.5-flash-lite', 'gemini-3.1-flash-lite']

def generate_with_retry(prompt, is_json=False):
    for key in API_KEYS:
        genai.configure(api_key=key)
        for model_name in MODELS:
            try:
                model = genai.GenerativeModel(model_name)
                config = genai.GenerationConfig(response_mime_type="application/json") if is_json else None
                res = model.generate_content(prompt, generation_config=config)
                if res.text and res.text.strip():
                    text = res.text.strip()
                    if is_json:
                        text = text.replace('```json', '').replace('```', '').strip()
                    return text
            except Exception as e:
                print(f"Fallback triggered: Failed on {model_name} with key ...{key[-4:]} -> {e}")
                time.sleep(1)
                continue
    raise Exception("Critical: Failed to generate content from all Gemini models!")

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
            kw_list = []
            for item in data.get('keywordList', []):
                rel_kw = item.get('relKeyword', '').strip()
                if not rel_kw:
                    continue
                # Parse monthly search volume
                pc_qc = item.get('monthlyPcQcCnt', 0)
                mo_qc = item.get('monthlyMobileQcCnt', 0)
                pc_cnt = int(pc_qc) if str(pc_qc).isdigit() else 10
                mo_cnt = int(mo_qc) if str(mo_qc).isdigit() else 10
                total_qc = pc_cnt + mo_cnt
                kw_list.append({'keyword': rel_kw, 'volume': total_qc})
            return kw_list
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
            try:
                urllib.request.urlretrieve("https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Bold.ttf", font_path)
            except:
                pass
            
        img_width, img_height = 1200, 675
        bg_color = (24, 28, 36)
        text_color = (255, 255, 255)
        accent_color = (59, 130, 246)
        
        img = Image.new('RGB', (img_width, img_height), color=bg_color)
        draw = ImageDraw.Draw(img)
        
        # Decorative border
        draw.rectangle([40, 40, img_width - 40, img_height - 40], outline=accent_color, width=4)
        
        # Font load with safe fallback
        try:
            font = ImageFont.truetype(font_path, 80)
        except:
            font = ImageFont.load_default()
        
        raw_lines = text.strip().split('\n')
        lines = [line.strip() for line in raw_lines if line.strip()][:3]
        if not lines:
            lines = ["알아두면 유용한", "생활 꿀팁 가이드"]
            
        total_text_height = len(lines) * 110
        y_text = (img_height - total_text_height) // 2
        
        for line in lines:
            try:
                bbox = draw.textbbox((0, 0), line, font=font)
                width = bbox[2] - bbox[0]
                height = bbox[3] - bbox[1]
            except:
                width = len(line) * 40
                height = 80
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

    # Pass 1: Target Profiling
    profile_prompt = f"""당신은 30~50대를 타겟으로 하는 최상위 한국어 마케팅 카피라이터입니다.
'{keyword}'에 대해 소비자가 가장 겪고 있는 일상적 불편함, 결핍, 갈망하는 점이 무엇인지 3문장으로 날카롭게 분석하세요."""
    profiling = generate_with_retry(profile_prompt)

    # Pass 2: Outline Design
    outline_prompt = f"""'{profiling}'을 바탕으로 '{keyword}'에 대해 소비자의 호기심을 자극하고 해결책을 제시하는 전문 정보성 매거진 목차(H2 3~4개, 각 H2당 하위 H3 포함)를 마크다운 형식으로 설계하세요.
광고성 단어(추천, BEST 등)는 일체 배제하세요."""
    outline = generate_with_retry(outline_prompt)

    # Pass 3: Informational Draft
    draft_prompt = f"""아래 목차를 바탕으로 '{keyword}'에 대해 1500자 분량의 순수 정보성 블로그 초안을 작성하세요.
[타겟 분석]: {profiling}
[목차]:
{outline}

[작성 규칙]
1. 첫 문장은 독자의 결핍과 불편함에 깊이 공감하며 시작하세요.
2. 각 문단은 3줄을 넘지 않도록 가독성 있게 작성하세요.
3. '내가 써봤는데' 같은 가짜 경험담이나 과장 광고는 절대 금지합니다."""
    draft = generate_with_retry(draft_prompt)

    # Pass 4: Critique
    critique_prompt = f"""당신은 혹독한 SEO/AEO 및 콘텐츠 마케팅 전문가입니다.
다음 초안을 읽고 개선해야 할 핵심 단점 3가지를 신랄하게 지적하세요.
기준: 가독성, AI 특유의 기계적인 말투 여부, 실질적인 정보성 가치, 자연스러운 몰입도.
[초안]:
{draft}"""
    critique = generate_with_retry(critique_prompt)

    # Pass 5: Rewrite with Coupang Products Integration
    rewrite_prompt = f"""당신은 상위 1% 전문 에디터입니다. [초안]에 [전문가 비판]을 100% 수용하여 최종 2000자 내외의 완성도 높은 블로그 본문으로 리라이트하세요.
인공지능 특유의 번역투나 기계적 문체를 완전히 제거하고, 한국인이 직접 쓴 것처럼 자연스럽고 매끄럽게 작성하세요.

[전문가 비판]:
{critique}

[초안]:
{draft}

[쿠팡 1~3위 해결책 상품 정보]:
{products_info}

[필수 삽입 및 배치 규칙]
1. 본문 서론 직후 적절한 위치에 정확히 '[VIBE_IMAGE_HERE]' 라는 텍스트를 딱 1번만 단독 줄로 삽입하세요.
2. 글의 중반부 이후 문제 해결책으로 위 1~3위 상품을 자연스럽게 언급하고, 각 제품 소개 위치에 각각 '[COUPANG_LINK_1]', '[COUPANG_LINK_2]', '[COUPANG_LINK_3]' 플레이스홀더를 정확히 삽입하세요.
3. 마크다운 코드 블록(```)으로 전체 본문을 감싸지 마세요.
"""
    final_text = generate_with_retry(rewrite_prompt)
    final_text = re.sub(r'(?i)^(?:#+\s*)?H[23]:\s*', '', final_text, flags=re.MULTILINE)
    final_text = re.sub(r'^---.*?---\s*', '', final_text, flags=re.DOTALL)

    # Pass 6: Metadata Generation
    meta_prompt = f"""방금 작성된 글에 대한 메타데이터를 JSON 형식으로 반환하세요.
{{ 
  "title": "{keyword}를 활용한 어그로성/호기심 자극형 블로그 제목 (광고 냄새 없는 1줄)", 
  "thumb_hook": "{keyword} 관련 썸네일에 들어갈 2줄짜리 강력한 카피 (줄바꿈은 \\n 사용)", 
  "vibe_keywords": "픽사베이 영문 검색용 분위기 이미지 키워드 1~2개 (예: clean room, kitchen)"
}}"""
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

    # 1. Load leaf categories from refined Coupang/Naver file
    seed_categories = []
    if os.path.exists('coupang_categories.txt'):
        with open('coupang_categories.txt', 'r', encoding='utf-8') as f:
            seed_categories = [line.strip() for line in f if line.strip()]
    if not seed_categories:
        seed_categories = ['생활용품', '주방용품', '청소용품']
        
    random.shuffle(seed_categories)
    
    target_keyword = None
    target_seed = None
    
    # 2. Iterate through seed categories to find an unused golden keyword
    for seed in seed_categories[:10]:
        print(f"Mining trending keywords for seed: {seed}")
        kw_metrics = get_trending_keywords(seed)
        if not kw_metrics:
            continue
            
        # Sort keywords: prioritize golden search volumes (1,000 ~ 50,000)
        # Filter out already used keywords
        available_kws = [k for k in kw_metrics if k['keyword'] not in used_keywords]
        if not available_kws:
            continue
            
        # Try to find high-traffic or balanced golden keyword
        golden_kws = [k for k in available_kws if 500 <= k['volume'] <= 50000]
        if golden_kws:
            # Pick top volume in golden range
            golden_kws.sort(key=lambda x: x['volume'], reverse=True)
            target_keyword = golden_kws[0]['keyword']
        else:
            # Fallback to the highest volume available
            available_kws.sort(key=lambda x: x['volume'], reverse=True)
            target_keyword = available_kws[0]['keyword']
            
        target_seed = seed
        break
            
    if not target_keyword:
        # Ultimate fallback
        target_seed = random.choice(seed_categories)
        target_keyword = f"{target_seed} 추천"

    print(f"Selected Golden Keyword: {target_keyword} (Seed: {target_seed})")
    
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
        safe_title = target_keyword.replace(' ', '-').replace('/', '-').replace('\\', '-').replace('\ufeff', '').lower()
        filename = f'_posts/{date_str}-{safe_title}.md'
        os.makedirs('_posts', exist_ok=True)
        frontmatter = f"---\nlayout: post\ntitle: \"{title}\"\ndate: {date_str}\nimage: {thumb_path}\n---\n\n"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(frontmatter + post_content)
        print(f'Successfully generated {filename}')

if __name__ == '__main__':
    main()
