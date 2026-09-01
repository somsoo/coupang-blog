import re
import os

filepath = r'C:\Users\hsm29\Documents\coupang-blog\auto_poster.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update thumbnail text to be dynamic and engaging
old_text_logic = "text = f'[{keyword}]\\n핵심 정보 & 꿀팁'"
new_text_logic = """catchphrases = [
        "나만 몰랐던 200% 활용 노하우",
        "삶의 질 수직 상승! 완벽 해결 팁",
        "돈 아끼고 시간 버는 진짜 꿀팁",
        "단점은 없애고 장점만 살리는 비법",
        "더 이상 고민 끝! 완벽 가이드"
    ]
    catchphrase = random.choice(catchphrases)
    text = f'[{keyword}]\\n{catchphrase}'"""

content = content.replace(old_text_logic, new_text_logic)

# 2. Update prompt to make the title more engaging
old_prompt = "사람들이 생활 속에서 궁금해할 법한 '순수 정보성 제목'(예: '자취방 화장실 냄새 없애는 가장 빠른 방법', '아침에 일어날 때 목이 아픈 이유와 해결책')으로 작성하세요."
new_prompt = "사람들의 호기심을 강하게 자극하고 당장 클릭해서 읽고 싶게 만드는 매력적인 '이목 집중형 정보성 제목'(예: '10년 차 자취생도 몰랐던 화장실 냄새 1초 만에 없애는 비법', '이거 하나면 원룸 꿉꿉함 끝! 절대 후회 없는 완벽 가이드')으로 작성하세요."

content = content.replace(old_prompt, new_prompt)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated auto_poster.py for engaging catchphrases")
