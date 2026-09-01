import re
import os

filepath = r'C:\Users\hsm29\Documents\coupang-blog\auto_poster.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

old_thumb_prompt = '''    thumb_prompt = f\"\"\"당신은 클릭을 유도하는 천재 카피라이터입니다.
키워드 '{best_keyword}'에 대한 생활 정보성 블로그 글의 썸네일용 2줄 텍스트를 작성하세요.
첫 줄: 타겟의 공감을 사거나 호기심을 자극하는 짧은 문구
두 번째 줄: 키워드를 포함하거나 해결책을 제시하는 명확한 문구
주의: '추천', '리뷰', '내돈내산' 단어 절대 금지. 총 글자 수 30자 이내로 아주 짧게 작성.
예시:
지긋지긋한 화장실 냄새
1초 만에 싹 없애는 비법
\"\"\"'''

new_thumb_prompt = '''    thumb_prompt = f\"\"\"당신은 센스있는 라이프스타일 에디터입니다.
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
\"\"\"'''

content = content.replace(old_thumb_prompt, new_thumb_prompt)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated thumbnail prompt to prevent extreme/unrelated hooks")
