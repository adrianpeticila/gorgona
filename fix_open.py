import re

with open('tests/test_cli.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = re.sub(r'open\(([^,]+(?:,[^,]+)*),\s*("[wr]")\)', r'open(\1, \2, encoding="utf-8")', content)
content = content.replace('open(os.path.join(td, "clean.txt"), "w")', 'open(os.path.join(td, "clean.txt"), "w", encoding="utf-8")')
content = content.replace('open(os.path.join(td, ".env"), "w")', 'open(os.path.join(td, ".env"), "w", encoding="utf-8")')
content = content.replace('open(os.path.join(td, "secret.txt"), "w")', 'open(os.path.join(td, "secret.txt"), "w", encoding="utf-8")')
content = content.replace('open(os.path.join(mem_dir, "MEMORY.md"), "w")', 'open(os.path.join(mem_dir, "MEMORY.md"), "w", encoding="utf-8")')
content = content.replace('open(os.path.join(mem_dir, "test.md"), "w")', 'open(os.path.join(mem_dir, "test.md"), "w", encoding="utf-8")')

with open('tests/test_cli.py', 'w', encoding='utf-8') as f:
    f.write(content)
