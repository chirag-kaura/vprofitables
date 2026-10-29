with open("core/financial_query.py", "r", encoding="utf-8") as f:
    code = f.read()

# 1. executive_only default True
code = code.replace("executive_only: bool = False", "executive_only: bool = True", 1)

# 2. Add strict entity check and drop analyst/operator
old_loop = """        for doc, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
            if not is_clean_transcript_chunk(doc):
                continue
            role, speaker = sanitize_speaker_label(meta.get("speaker_role", ""), meta.get("speaker_name", ""))"""

new_loop = """        for doc, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
            chunk_sym = (meta.get("symbol") or "").strip().upper()
            if chunk_sym and chunk_sym != symbol:
                continue  # STRICT ENTITY MATCH: Reject cross-entity chunks

            raw_role = (meta.get("speaker_role") or "").strip().upper()
            if raw_role in ("OPERATOR", "ANALYST"):
                continue  # NEVER quote external analysts or conference call operators as company guidance

            if not is_clean_transcript_chunk(doc):
                continue
            role, speaker = sanitize_speaker_label(meta.get("speaker_role", ""), meta.get("speaker_name", ""))"""

if old_loop in code:
    code = code.replace(old_loop, new_loop, 1)

with open("core/financial_query.py", "w", encoding="utf-8") as f:
    f.write(code)

print("Successfully patched core/financial_query.py with strict entity verification & executive-only guidance!")
