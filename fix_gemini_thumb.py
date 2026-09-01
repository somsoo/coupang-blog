import re

filepath = r'C:\Users\hsm29\Documents\coupang-blog\auto_poster.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update create_text_thumbnail to accept full_text
search_def = r'def create_text_thumbnail\(keyword, filename\):'
replace_def = 'def create_text_thumbnail(full_text, filename):'
content = re.sub(search_def, replace_def, content)

# 2. Remove the catchphrases logic inside create_text_thumbnail
catchphrase_logic = """    catchphrases = [
        "나만 몰랐던 200% 활용 노하우",
        "삶의 질 수직 상승! 완벽 해결 팁",
        "돈 아끼고 시간 버는 진짜 꿀팁",
        "단점은 없애고 장점만 살리는 비법",
        "더 이상 고민 끝! 완벽 가이드"
    ]
    catchphrase = random.choice(catchphrases)
    text = f'[{keyword}]\\n{catchphrase}'"""
content = content.replace(catchphrase_logic, '    text = full_text')

# 3. Update the generate_post caller to use Gemini for the thumbnail text
old_thumb_call = """    # [1] 최상단 텍스트 썸네일 생성
    thumb_filename = f"thumb_{int(time.time())}"
    thumb_rel_path = create_text_thumbnail(best_keyword, thumb_filename)"""

new_thumb_call = """    # [1] 최상단 텍스트 썸네일 생성
    thumb_prompt = f\"\"\"당신은 클릭을 유도하는 천재 카피라이터입니다.
키워드 '{best_keyword}'에 대한 생활 정보성 블로그 글의 썸네일용 2줄 텍스트를 작성하세요.
첫 줄: 타겟의 공감을 사거나 호기심을 자극하는 짧은 문구
두 번째 줄: 키워드를 포함하거나 해결책을 제시하는 명확한 문구
주의: '추천', '리뷰', '내돈내산' 단어 절대 금지. 총 글자 수 30자 이내로 아주 짧게 작성.
예시:
지긋지긋한 화장실 냄새
1초 만에 싹 없애는 비법
\"\"\"
    try:
        thumb_text = generate_with_retry(thumb_prompt).strip().replace('\"', '').replace(\"'\", '')
    except:
        thumb_text = f"[{best_keyword}]\\n나만 몰랐던 완벽 활용 팁"

    thumb_filename = f"thumb_{int(time.time())}"
    thumb_rel_path = create_text_thumbnail(thumb_text, thumb_filename)"""

content = content.replace(old_thumb_call, new_thumb_call)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print('Updated thumbnail text logic to use Gemini')
