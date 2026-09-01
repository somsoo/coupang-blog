import os

filepath = r'C:\Users\hsm29\Documents\coupang-blog\auto_poster.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix newline issue
content = content.replace("relative_url }}}}}}\n\n\"", "relative_url }}}})\\n\\n\"")

# Fix title issue
old_title_logic = """    if lines and lines[0].lower().startswith("title:"):
        title = lines[0][6:].strip().replace('"', "'")
        body_content = '\\n'.join(lines[1:]).strip()"""

new_title_logic = """    if lines and lines[0].lower().startswith("title:"):
        title = lines[0][6:].strip().replace('"', "'")
        title = title.replace('추천', '').replace('리뷰', '').replace('내돈내산', '').replace('[', '').replace(']', '')
        title = " ".join(title.split())
        body_content = '\\n'.join(lines[1:]).strip()"""

content = content.replace(old_title_logic, new_title_logic)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
