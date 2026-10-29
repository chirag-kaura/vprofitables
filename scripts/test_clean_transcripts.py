import os
import sys
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.rag_engine import _get_collection, _get_embedder

col = _get_collection()
model = _get_embedder()

query = "capex and business growth guidance"
q_emb = model.encode([query]).tolist()

res = col.query(query_embeddings=q_emb, n_results=10, where={"symbol": "RELIANCE"})

docs = res["documents"][0]
metas = res["metadatas"][0]

boilerplate_regex = re.compile(
    r"(trading\s+symbol|regulation\s+30|securities\s+and\s+exchange|listing\s+obligations|regd\.?\s*office|maker\s+chambers|nariman\s+point|cin\s*[-:]|phone\s*#|telefax|safe\s*harbor|forward-looking|listen-only|moderator|dear\s*sirs?|bse\s*limited|national\s*stock\s*exchange)",
    re.IGNORECASE
)

print(f"Total retrieved chunks: {len(docs)}")
valid_chunks = []
for i, (d, m) in enumerate(zip(docs, metas)):
    is_bp = bool(boilerplate_regex.search(d))
    print(f"[{i+1}] Boilerplate: {is_bp} | Role: {m.get('speaker_role')} | Doc snippet: {d[:100]}...")
    if not is_bp and len(d.strip()) > 80:
        valid_chunks.append((d, m))

print(f"\nRemaining clean business chunks: {len(valid_chunks)}")
for i, (d, m) in enumerate(valid_chunks[:2]):
    print(f"\nClean Chunk {i+1}:")
    print(d[:300])
