with open('core/agent_orchestrator.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
for idx, l in enumerate(lines):
    if 'Clean Management Guidance' in l:
        print(f"Line {idx+1}: {l.strip()}")
        for j in range(max(0, idx-2), min(len(lines), idx+12)):
            print(f"{j+1}: {lines[j]}", end='')
