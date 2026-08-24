import os
import random
from datetime import datetime
from google import genai

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment variables.")

client = genai.Client(api_key=GEMINI_API_KEY)

def generate_post():
    topics = [
        "Everyday life hacks and time-saving tips",
        "Top 5 cost-effective household items you must have",
        "Kitchen organization and cleaning hacks",
        "Smart shopping: How to spot the best deals online",
        "Home interior and DIY improvements for small spaces"
    ]
    topic = random.choice(topics)
    
        prompt = f"""당신은 친근한 한국인 라이프스타일/생활꿀팁 전문 SEO 마케터이자 블로거입니다.

다음 주제에 대해 SEO/AEO/GEO 최적화된 매력적인 블로그 포스팅을 한글로 작성해주세요: {topic}

작성 지침:
1. 분량: 1000자 이상, 상세하고 유용한 정보 제공.
2. 구조: H2, H3 태그를 활용한 소제목 분할, 가독성 높은 문단 구조, 핵심 요약(Bullet points), 결론.
3. SEO/AEO/GEO: 독자의 검색 의도와 질문에 직접적으로 답변하는 형태(AEO)를 취하고, 자연스럽게 키워드를 배치하세요.
4. 어조: 친구에게 꿀팁을 전수하듯 자연스럽고 친근한 인간적인 말투 (로봇 같은 딱딱한 말투 절대 금지). 공감과 경험을 바탕으로 한 스토리텔링 기법 적용.
5. 중간중간 상품 추천이나 클릭 유도를 위한 자연스러운 맥락(CTA)을 반드시 포함하세요.

Important: The very first line of your response MUST be the exact title of the post, starting with 'Title: '. Do not use markdown formatting for the title line.
The rest of the response should be the body of the post in standard Markdown format."""

    models_to_try = ['gemini-3.5-flash-lite', 'gemini-3.1-flash-lite']
    response = None
    for model_name in models_to_try:
        try:
            response = client.models.generate_content(model=model_name, contents=prompt)
            print(f'Successfully generated content using model: {model_name}')
            break
        except Exception as e:
            if '429' in str(e) or 'quota' in str(e).lower():
                print(f'Quota exceeded for model {model_name}. Trying next model...')
                continue
            else:
                print(f'Error with {model_name}: {e}')
                continue
                
    if not response:
        raise Exception('All models failed.')
    

    text = response.text.strip()
    
    # --- 2nd Pass: Review and Revise ---
    print("Evaluating draft...")
    eval_prompt = f"""You are a master Editor and SEO/AEO/GEO Specialist.
Review the following blog post draft:

Draft:
{text}

Evaluate the draft on three criteria (0-100 score each):
1. SEO (Search Engine Optimization): Keyword usage, headers, readability.
2. GEO (Generative Engine Optimization): Clear structured data, bullet points, concise facts for AI to parse.
3. AEO (Answer Engine Optimization): Direct answers to the user's implicit question.

If the total score is below 285/300, or if it can be significantly improved, completely REWRITE the draft to be perfectly optimized. 
CRITICAL: The very first line of your response MUST still be the exact title of the post, starting with 'Title: '. Do not use markdown formatting for the title line.
The rest of the response should be the heavily revised and optimized body of the post in standard Markdown format."""

    revised_response = None
    for model_name in models_to_try:
        try:
            revised_response = client.models.generate_content(model=model_name, contents=eval_prompt)
            print(f'Successfully revised content using model: {model_name}')
            break
        except Exception as e:
            continue
            
    if revised_response and revised_response.text.strip():
        text = revised_response.text.strip()

    lines = text.split('\n')
    title = "Life Tips Update"
    body = text
    
    if lines and lines[0].lower().startswith("title:"):
        title = lines[0][6:].strip().replace('"', "'")
        body = '\n'.join(lines[1:]).strip()
        
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
    
    frontmatter = f"""---
layout: post
title: "{title}"
date: {time_str}
categories: [Life]
---

{body}
"""
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(frontmatter)

if __name__ == "__main__":
    title, body = generate_post()
    save_post(title, body)
