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
# ----------------- POST GENERATION (3-Pass 최적화) -----------------
def generate_post(keyword, products):
    # Formulate product info
    products_info = ""
    for idx, p in enumerate(products, 1):
        products_info += f"[{idx}위 상품]\n상품명: {p.get('productName')}\n가격: {p.get('productPrice')}원\n링크: {p.get('productUrl')}\n\n"

    # ▶ [Pass 1] 타겟 분석 + 목차 + 고밀도 1차 본문 초안 작성 (1회 호출)
    print("  ▶ [Pass 1/3] 타겟 분석 및 고밀도 초안 작성 중...")
    pass1_prompt = f"""당신은 실패 없는 현명한 가성비 소비를 연구하는 15년 차 베테랑 리빙·살림 큐레이터이자 수석 에디터입니다.
주제 키워드: '{keyword}'

아래 쿠팡 1~3위 추천 상품 정보를 참고하여 독자가 일상에서 겪는 결핍과 문제를 해결하는 1,500자 내외의 정보성 블로그 1차 초안을 작성하세요.

[쿠팡 1~3위 해결책 상품 정보]:
{products_info}

[작성 지침]
1. 첫 문장은 독자의 현실적인 불편함과 돈 낭비의 위험에 깊이 공감하며 시작하세요.
2. 전문 정보성 매거진 목차(H2 소제목 3개)를 구성하여 단계별 가이드를 제시하세요.
3. '내가 써봤는데', '100% 수익 보장' 같은 가짜 경험담이나 과장 광고는 절대 금지합니다.
4. 본문 서론 직후 단독 줄로 정확히 '[VIBE_IMAGE_HERE]' 라는 플레이스홀더를 1회만 삽입하세요.
5. 글의 중반부 이후 문제 해결책으로 1~3위 상품을 소개하되, 각 상품 설명이 끝난 다음 줄에 단독 줄로 '[COUPANG_LINK_1]', '[COUPANG_LINK_2]', '[COUPANG_LINK_3]' 마커를 1회씩만 배치하세요.
"""
    draft = generate_with_retry(pass1_prompt)
    time.sleep(1)

    # ▶ [Pass 2] 기계적 문체/가독성/신뢰도 결함 비판 Critic (1회 호출)
    print("  ▶ [Pass 2/3] 기계적 문체 및 가독성 결함 비판(Critic) 중...")
    critic_prompt = f"""당신은 혹독한 구글 Reviews System 및 SEO/AEO 알고리즘 평가관입니다.
아래 초안을 면밀히 분석하여 독자의 구매 결정과 글의 신뢰도를 저해하는 결함을 신랄하게 지적하세요.

[초안]:
{draft}

[지적 기준]
1. AI 특유의 판에 박힌 번역투, 공허한 미사여구, 뻔한 칭찬 지적
2. 구체적이고 현실적인 스펙/단점 부족 지적
3. 문단 가독성 및 호흡 지적
4. 플레이스홀더 '[VIBE_IMAGE_HERE]', '[COUPANG_LINK_1]', '[COUPANG_LINK_2]', '[COUPANG_LINK_3]'의 보존 여부 확인

반드시 개선 가이드 3~4가지를 구체적이고 간결하게 요약하여 답변하세요.
"""
    critique = generate_with_retry(critic_prompt)
    time.sleep(1)

    # ▶ [Pass 3] 비판 100% 수용 최종 재작성 및 메타데이터 일괄 완성 (1회 호출)
    print("  ▶ [Pass 3/3] 비판 수용 최종 재작성 및 메타데이터 일괄 완성 중...")
    pass3_prompt = f"""당신은 상위 1% 전문 에디터입니다. [1차 초안]에 [전문가 비판]을 100% 수용하여 최종 2000자 내외의 완성도 높은 블로그 본문과 메타데이터를 일괄 완성하세요.

[전문가 비판]:
{critique}

[1차 초안]:
{draft}

[쿠팡 1~3위 해결책 상품 정보]:
{products_info}

[필수 배치 및 포맷 규칙]
1. 번역투와 기계적 문체를 완전히 제거하고 한국인이 직접 쓴 것처럼 자연스럽게 작성하세요.
2. 서론 직후 단독 줄로 '[VIBE_IMAGE_HERE]' 마커를 반드시 유지하세요.
3. 1~3위 상품 설명 문단 직후 단독 줄로 '[COUPANG_LINK_1]', '[COUPANG_LINK_2]', '[COUPANG_LINK_3]' 마커를 1회씩 반드시 배치하세요.
4. 마크다운 코드블록(```)으로 전체 본문을 감싸지 마세요.

반드시 다음 JSON 형식으로만 최종 답변하세요:
{{
  "title": "{keyword}를 활용한 호기심 자극형 블로그 제목 (1줄)",
  "thumb_hook": "{keyword} 썸네일에 들어갈 2줄 카피 (줄바꿈은 \\n 사용)",
  "vibe_keywords": "픽사베이 영문 검색용 단어 1~2개 (예: clean room, robot vacuum)",
  "content": "비판이 100% 반영되어 완전히 재작성된 최종 마크다운 본문 전체"
}}
"""
    pass3_json_str = generate_with_retry(pass3_prompt, is_json=True)
    try:
        data = json.loads(pass3_json_str)
        title = data.get('title', f"{keyword} 완벽 가이드")
        thumb_hook = data.get('thumb_hook', f"{keyword}\n알아보기")
        vibe_keywords = data.get('vibe_keywords', "lifestyle")
        final_text = data.get('content', draft)
    except:
        title = f"{keyword} 완벽 비교 가이드"
        thumb_hook = f"{keyword}\n비교 분석"
        vibe_keywords = "technology"
        final_text = draft

    final_text = re.sub(r'(?i)^(?:#+\s*)?H[23]:\s*', '', final_text, flags=re.MULTILINE)
    final_text = re.sub(r'^---.*?---\s*', '', final_text, flags=re.DOTALL)
    # Dummy links / Fake URLs cleanup
    dummy_md_pattern = r'\[([^\]]+)\]\((?:https?:\/\/)?(?:www\.)?(?:example\.(?:com|org)|test\.com|yourlink\.com|sample\.com)[^\)]*\)'
    final_text = re.sub(dummy_md_pattern, r'\1', final_text)
    dummy_html_pattern = r'<a\s+[^>]*href=[\'"](?:https?:\/\/)?(?:www\.)?(?:example\.(?:com|org)|test\.com|yourlink\.com|sample\.com)[^\'"]*[\'"][^>]*>(.*?)<\/a>'
    final_text = re.sub(dummy_html_pattern, r'\1', final_text)

    # Fetch Pixabay Image
    image_urls = []
    try:
        url = f"https://pixabay.com/api/?key=57366919-c2774ae5199cc6a6cdb9a301d&q={urllib.parse.quote(vibe_keywords)}&image_type=photo&orientation=horizontal&per_page=5"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            p_data = r.json()
            if p_data.get('hits'):
                image_urls = [hit.get('largeImageURL', hit.get('webformatURL')) for hit in p_data['hits']]
    except: pass

    # Replace VIBE image (개선: <br> 제거 및 ALT 태그 고도화)
    parts = final_text.split('[VIBE_IMAGE_HERE]')
    processed_text = parts[0]
    if len(parts) > 1:
        v_path = ""
        if image_urls:
            v_path = download_vibe_image(image_urls[0], f"vibe_{int(time.time())}")
        if v_path:
            img_alt = f"{keyword} 관련 추천 제품 인포그래픽"
            processed_text += f"\n\n![{img_alt}]({{{{ '/' | append: '{v_path}' | relative_url }}}})\n\n"
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
        processed_text = processed_text.replace(placeholder, f"\n{cta_html}\n")
        # Clean up any closing tags or malformed variants created by AI
        processed_text = re.sub(rf'\[/COUPANG_LINK_{idx}\]', '', processed_text)

    # Clean up any orphan link tags
    processed_text = re.sub(r'\[/?COUPANG_LINK_\d+\]', '', processed_text)

    # 2번째 H2 앞에 중간 애드센스 삽입
    ad_mid = """
<div class="ad-slot-wrap" style="margin: 35px 0; text-align: center;">
  <ins class="adsbygoogle"
       style="display:block"
       data-ad-client="ca-pub-2228289204702106"
       data-ad-slot="5979106011"
       data-ad-format="auto"
       data-full-width-responsive="true"></ins>
  <script>(adsbygoogle = window.adsbygoogle || []).push({});</script>
</div>
"""
    h2_indices = [m.start() for m in re.finditer(r'(?m)^##\s+', processed_text)]
    if len(h2_indices) >= 2:
        insert_pos = h2_indices[1]
        processed_text = processed_text[:insert_pos] + ad_mid + "\n\n" + processed_text[insert_pos:]
    else:
        # H2가 2개 미만이면 본문 절반 지점에 삽입
        mid_idx = len(processed_text) // 2
        processed_text = processed_text[:mid_idx] + "\n\n" + ad_mid + "\n\n" + processed_text[mid_idx:]

    ftc_text = '\n<p style="font-size: 12px; color: #999; text-align: center; margin-top: 40px; margin-bottom: 10px;">이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다.</p>\n'
    
    final_text = processed_text + ftc_text
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
        clean_kw = re.sub(r'[^\w\s-]', '', target_keyword).strip()
        safe_title = re.sub(r'[-\s]+', '-', clean_kw)
        filename = f'_posts/{date_str}-{safe_title}.md'
        os.makedirs('_posts', exist_ok=True)
        frontmatter = f"---\nlayout: post\ntitle: \"{title}\"\ndate: {date_str}\nimage: {thumb_path}\n---\n\n"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(frontmatter + post_content)
        print(f'Successfully generated {filename}')

if __name__ == '__main__':
    main()
