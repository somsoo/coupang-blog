import os
import re
import time
import urllib.parse
from google import genai

posts_dir = "_posts"

api_keys_str = os.environ.get("GEMINI_API_KEY", "")
if not api_keys_str:
    print("GEMINI_API_KEY가 없습니다.")
    exit(1)

API_KEYS = [k.strip() for k in api_keys_str.split(",") if k.strip()]
MODELS = ["gemini-2.0-flash-lite", "gemini-2.0-flash"]

def generate_with_retry(prompt):
    for key in API_KEYS:
        client = genai.Client(api_key=key)
        for model_name in MODELS:
            try:
                response = client.models.generate_content(model=model_name, contents=prompt)
                return response.text
            except Exception as e:
                print(f"  Fallback: {model_name} -> {e}")
                time.sleep(3)
    raise Exception("All API keys exhausted")

def add_color_boxes(content):
    prompt = f"""아래는 쿠팡 제품 리뷰 블로그 글입니다.
독자에게 가장 중요한 꿀팁 1곳 뒤에 노란 박스를, 핵심 스펙/수치 정보 1곳 뒤에 파란 박스를 삽입해서 원문 전체를 반환하세요.

[노란 박스 형식]:
<div style="background:#fffbe6; border-left:4px solid #f5c518; padding:14px 18px; margin:20px 0; border-radius:6px; font-size:0.97em;">
💡 <strong>해당 단락 핵심 내용 1~2문장 요약</strong>
</div>

[파란 박스 형식]:
<div style="background:#e8f4fd; border-left:4px solid #2196F3; padding:14px 18px; margin:20px 0; border-radius:6px; font-size:0.97em;">
📌 <strong>해당 단락 핵심 내용 1~2문장 요약</strong>
</div>

규칙:
- 노란 박스 1개, 파란 박스 1개 총 2개만 삽입
- 기존 글의 내용, 링크, HTML 태그를 절대 수정하지 마세요
- 프론트매터(--- 구간)와 adsbygoogle 블록은 건드리지 마세요
- 출력은 수정된 전체 글만 반환하세요. 부연설명 없이.

[원문]
{content}
"""
    return generate_with_retry(prompt)

def add_pollinations_image(keyword, content):
    obj_prompt = urllib.parse.quote(
        f"A realistic photograph of {keyword} on a clean desk, bright natural lighting, simple and clear"
    )
    img_url = f"https://image.pollinations.ai/prompt/{obj_prompt}?width=800&height=800&nologo=true&private=true&model=flux"
    img_md = f"![{keyword}]({img_url})\n\n"
    parts = content.split("---", 2)
    if len(parts) >= 3:
        return parts[0] + "---" + parts[1] + "---\n\n" + img_md + parts[2].lstrip("\n")
    return img_md + content

files = sorted([f for f in os.listdir(posts_dir) if f.endswith(".md")])
total = len(files)
fixed_image = 0
fixed_box = 0
print(f"총 {total}개 파일 처리 시작\n")

for i, fname in enumerate(files):
    fpath = os.path.join(posts_dir, fname)
    print(f"[{i+1}/{total}] {fname}")
    with open(fpath, "r", encoding="utf-8") as f:
        content = f.read()
    modified = False

    has_image = bool(re.search(r"!\[.*?\]\(https?://", content)) or "<img" in content
    if not has_image:
        title_match = re.search(r'^title:\s*["\']?(.+?)["\']?\s*$', content, re.MULTILINE)
        keyword = title_match.group(1)[:40].strip('"\'') if title_match else "product"
        content = add_pollinations_image(keyword, content)
        print(f"  ✅ Pollinations 이미지 추가")
        fixed_image += 1
        modified = True
    else:
        print(f"  ⏭️  이미지 존재, 스킵")

    has_box = "background:#fffbe6" in content or "background:#e8f4fd" in content
    if not has_box:
        try:
            new_content = add_color_boxes(content)
            if "background:#fffbe6" in new_content or "background:#e8f4fd" in new_content:
                content = new_content
                print(f"  ✅ 색상 박스 삽입 완료")
                fixed_box += 1
                modified = True
            else:
                print(f"  ⚠️  색상 박스 미반영, 스킵")
        except Exception as e:
            print(f"  ❌ 오류: {e}")
    else:
        print(f"  ⏭️  색상 박스 존재, 스킵")

    if modified:
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(content)
    time.sleep(2)

print(f"\n===== 완료 =====")
print(f"이미지 추가: {fixed_image}개")
print(f"색상 박스 삽입: {fixed_box}개")
