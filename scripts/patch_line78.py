with open('start.bat', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace(
    'cmd /c "python update_all.py',
    'cmd /c "timeout 20 & python update_all.py'
)

with open('start.bat', 'w', encoding='utf-8') as f:
    f.write(text)

print("start.bat line 78 patched successfully!")
