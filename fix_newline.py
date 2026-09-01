import re

with open(r'C:\Users\hsm29\Documents\coupang-blog\auto_poster.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix literal \n\n in image_markdown
content = content.replace("})\\n\\n\"", "})\\n\\n\"")
# Actually, the best way to do this is to replace the whole line cleanly:
search_thumb = r"image_markdown = f\"!\[\{product_name\}\]\(\{\{\{\{ \'/\' \| append: \'\{thumb_rel_path\}\' \| relative_url \}\}\}\}\).*?\""
replace_thumb = "image_markdown = f\"![{product_name}]({{{{ '/' | append: '{thumb_rel_path}' | relative_url }}}})\\n\\n\""
content = re.sub(search_thumb, replace_thumb, content)

# But wait, python interprets \n in code as a newline. If I wrote `\\n\\n` it writes literal \n.
# Let's just use regular newline in the code.
replace_thumb_real = "image_markdown = f\"![{product_name}]({{{{ '/' | append: '{thumb_rel_path}' | relative_url }}}})\\n\\n\""

content = re.sub(r'image_markdown = f"!\\[\{product_name\}\]\(\{\{\{\{.*?relative_url \}\}\}\}\).*?"', replace_thumb_real, content)

# Aggressively filter out '추천', '리뷰', '내돈내산' from the generated title
title_fix_logic = '''
    if lines and lines[0].lower().startswith("title:"):
        title = lines[0][6:].strip().replace('"', "'")
        # 강제 필터링
        title = title.replace('추천', '').replace('리뷰', '').replace('내돈내산', '').replace('[', '').replace(']', '')
        # 공백 정리
        title = " ".join(title.split())
        body_content = '\\n'.join(lines[1:]).strip()
'''
content = re.sub(r'    if lines and lines\[0\]\.lower\(\)\.startswith\("title:"\):.*?body_content = \'\\n\'\.join\(lines\[1:\]\)\.strip\(\)', title_fix_logic, content, flags=re.DOTALL)

with open(r'C:\Users\hsm29\Documents\coupang-blog\auto_poster.py', 'w', encoding='utf-8') as f:
    f.write(content)
