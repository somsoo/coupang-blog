import re

filepath = r'C:\Users\hsm29\Documents\coupang-blog\auto_poster.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix literal backslash-n
content = content.replace("relative_url }}}})\\\\n\\\\n\"", "relative_url }}}})\\n\\n\"")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print('Fixed literal newline bug')
