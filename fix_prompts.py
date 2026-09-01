import re
with open(r'C:\Users\hsm29\Documents\coupang-blog\auto_poster.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update draft_prompt
draft_search = r"당신은 '내돈내산' 리뷰 전문가입니다.*?생생한 리뷰 포스팅 초안을 1000자 이상 작성하세요\."
draft_replace = "당신은 생활 꿀팁과 유용한 정보를 전달하는 전문 에디터입니다.\n다음 트렌드 키워드와 상품 정보를 바탕으로, 광고 느낌이 전혀 나지 않는 '문제 해결형 순수 정보글' 초안을 1000자 이상 작성하세요."
content = re.sub(draft_search, draft_replace, content, flags=re.DOTALL)

draft_search2 = r"- 실제 사용해본 것처럼 솔직한 장단점을 적어주세요\."
draft_replace2 = "- 상품 추천글이 아니라, 독자의 일상적인 문제를 해결해주는 유익한 정보글(팁 공유) 형태로 작성하세요."
content = re.sub(draft_search2, draft_replace2, content, flags=re.DOTALL)

# 2. Update rewrite_prompt title rule
title_rule_search = r"글의 첫 번째 줄은 반드시 'Title: 제목' 형식이어야 합니다\."
title_rule_replace = "글의 첫 번째 줄은 반드시 'Title: 제목' 형식이어야 합니다.\n[제목 작성 규칙]: 제목에 절대로 '추천', '리뷰', '내돈내산' 같은 상업적 단어를 쓰지 마세요. 사람들이 생활 속에서 궁금해할 법한 '순수 정보성 제목'(예: '자취방 화장실 냄새 없애는 가장 빠른 방법', '아침에 일어날 때 목이 아픈 이유와 해결책')으로 작성하세요."
content = re.sub(title_rule_search, title_rule_replace, content, flags=re.DOTALL)

# 3. Update rewrite_prompt persona
rewrite_search = r"당신은 상위 1% 리뷰 인플루언서입니다\."
rewrite_replace = "당신은 상위 1% 라이프스타일 정보 매거진 에디터입니다."
content = re.sub(rewrite_search, rewrite_replace, content, flags=re.DOTALL)

rewrite_search2 = r"진짜 내돈내산 한 것 같은 찰진 말투로 윤문하세요\."
rewrite_replace2 = "진짜 나만의 살림 노하우나 유용한 정보를 공유하는 정보성 글처럼 윤문하세요."
content = re.sub(rewrite_search2, rewrite_replace2, content, flags=re.DOTALL)

# 4. Fallback title fix
content = content.replace('title = f"{best_keyword} 추천"', 'title = f"{best_keyword} 똑똑하게 활용하는 방법"')

with open(r'C:\Users\hsm29\Documents\coupang-blog\auto_poster.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated auto_poster.py for informational tone")
