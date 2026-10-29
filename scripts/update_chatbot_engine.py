with open('core/chatbot_engine.py', 'r', encoding='utf-8') as f:
    content = f.read()

target = '''    if transcripts:
        lines.append("#### 🎙️ Key Management Guidance & Transcript Excerpts")
        for t in transcripts[:2]:
            role = t.get("speaker_role", "EXECUTIVE")
            period = t.get("fiscal_period", "")
            excerpt = t.get("excerpt", "").strip()
            if len(excerpt) > 280:
                excerpt = excerpt[:277] + "..."
            lines.append(f"> **[{role}] ({period}):** \\"{excerpt}\\"")
        lines.append("")'''

replacement = '''    valid_transcripts = [t for t in transcripts if t.get("excerpt", "").strip()]
    if valid_transcripts:
        lines.append("#### 🎙️ Key Management Guidance & Transcript Excerpts")
        for t in valid_transcripts[:2]:
            role = t.get("speaker_role", "EXECUTIVE")
            period = t.get("fiscal_period", "")
            excerpt = t.get("excerpt", "").strip()
            if len(excerpt) > 280:
                excerpt = excerpt[:277] + "..."
            lines.append(f"> **[{role}] ({period}):** \\"{excerpt}\\"")
        lines.append("")'''

# Normalise newlines for replacement
c_norm = content.replace('\r\n', '\n')
t_norm = target.replace('\r\n', '\n')
r_norm = replacement.replace('\r\n', '\n')

if t_norm in c_norm:
    c_norm = c_norm.replace(t_norm, r_norm, 1)
    with open('core/chatbot_engine.py', 'w', encoding='utf-8') as f:
        f.write(c_norm)
    print("Updated core/chatbot_engine.py successfully.")
else:
    print("Target not found in core/chatbot_engine.py")
