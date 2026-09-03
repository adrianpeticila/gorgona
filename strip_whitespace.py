import os

dirs = ["gorgona", "tools", "tests"]
files_to_check = ["README.md"]

for d in dirs:
    if os.path.exists(d):
        for root, _, files in os.walk(d):
            for file in files:
                if file.endswith((".py", ".md")):
                    files_to_check.append(os.path.join(root, file))

for filepath in files_to_check:
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
            
        lines = content.split('\n')
        # strip trailing spaces from each line
        lines = [line.rstrip(' \t') for line in lines]
        # remove trailing empty lines at EOF
        while len(lines) > 1 and lines[-1] == '':
            lines.pop()
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write('\n'.join(lines) + '\n')
