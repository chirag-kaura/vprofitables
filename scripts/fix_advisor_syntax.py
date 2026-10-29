import os

advisor_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pages", "page_advisor.py")

with open(advisor_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = []
found_first = False
for line in lines:
    if 'let _wrapStart = \'<div class="admin-gated-section"' in line:
        if not found_first:
            new_lines.append(line)
            found_first = True
        else:
            print("Skipping duplicate let _wrapStart line!")
            continue
    else:
        new_lines.append(line)

with open(advisor_path, "w", encoding="utf-8", newline="\r\n") as f:
    f.writelines(new_lines)

print("SUCCESS: Fixed page_advisor.py")
