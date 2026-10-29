with open('start.bat', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    # 1. Add delay to background update so it doesn't fight app.py startup
    if 'python update_all.py' in line and 'timeout' not in line:
        line = line.replace('cmd /c "python update_all.py', 'cmd /c "timeout 20 & python update_all.py')
    
    # 2. Wait for server before opening browser
    if 'Start-Sleep 6; Start-Process' in line:
        line = 'start "" powershell -WindowStyle Hidden -Command "for ($i=0; $i -lt 30; $i++) { try { $r = (Invoke-WebRequest -Uri http://localhost:5050 -UseBasicParsing -TimeoutSec 1); if ($r.StatusCode -eq 200) { Start-Process http://localhost:5050; break; } } catch { Start-Sleep 1 } }"\n'
    
    # 3. Use python -X utf8
    if line.strip() == 'python app.py':
        line = 'python -X utf8 app.py\n'
        
    new_lines.append(line)

with open('start.bat', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("start.bat successfully patched!")
