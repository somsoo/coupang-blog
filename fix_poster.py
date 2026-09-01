import re
import os

with open(r'C:\Users\hsm29\Documents\coupang-blog\auto_poster.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add download_vibe_image function
download_func = '''
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
'''
content = content.replace('import random', 'import random\n' + download_func)

# 2. Fix create_text_thumbnail return path (remove leading slash for Jekyll relative_url)
content = content.replace("return f'/{filepath}'", "return filepath")

# 3. Fix generation logic: 1 image download, correct markdown syntax
search_logic = r'    # \[1\] 최상단 텍스트.*?flickr_url_2 = f"https://loremflickr.com/800/500/\{vibe_keywords\}/all\?lock=2"'

new_logic = '''
    # [1] 최상단 텍스트 썸네일 생성
    thumb_filename = f"thumb_{int(time.time())}"
    thumb_rel_path = create_text_thumbnail(best_keyword, thumb_filename)
    image_markdown = f"![{product_name}]({{{{ '/' | append: '{thumb_rel_path}' | relative_url }}}})\\n\\n"

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
'''
content = re.sub(search_logic, new_logic, content, flags=re.DOTALL)

# 4. Fix rewrite_prompt (Remove 사진2, Use vibe_markdown)
search_rewrite = r'2\. 글 중간에 딱 2번.*?사진 2: \{flickr_url_2\}'
new_rewrite = '''2. 글 중간에 딱 1번, 아래의 제공된 감성 실사 사진 마크다운을 본문의 가장 자연스러운 위치에 그대로 삽입하세요.
{vibe_markdown}'''
content = re.sub(search_rewrite, new_rewrite, content, flags=re.DOTALL)

with open(r'C:\Users\hsm29\Documents\coupang-blog\auto_poster.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('파이썬 파일 수정 완료')
