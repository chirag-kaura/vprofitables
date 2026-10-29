import os
import sys
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.rag_engine import _get_collection

col = _get_collection()

# Sample 20 chunks from ChromaDB
res = col.get(limit=25, include=['documents', 'metadatas'])
docs = res['documents']
metas = res['metadatas']

boilerplate_patterns = [
    r"safe\s*harbor",
    r"forward-looking\s*statements",
    r"ladies\s*and\s*gentlemen",
    r"welcome\s*to\s*the\s*conference\s*call",
    r"listen-only\s*mode",
    r"moderator",
    r"operator",
    r"thank\s*you\s*for\s*joining",
    r"roll\s*call",
    r"disclaimer",
    r"does\s*not\s*constitute\s*an\s*offer"
]

boilerplate_count = 0
for i, (d, m) in enumerate(zip(docs, metas)):
    is_bp = any(re.search(pat, d, re.IGNORECASE) for pat in boilerplate_patterns)
    if is_bp:
        boilerplate_count += 1
    print(f"--- Chunk {i+1} [{m.get('symbol')}] (Role: {m.get('speaker_role')}) ---")
    print(f"Boilerplate detected: {is_bp}")
    print(f"Snippet: {d[:180].strip()}...\n")

print(f"\nBoilerplate sample ratio: {boilerplate_count} / {len(docs)} ({boilerplate_count/len(docs)*100:.1f}%)")
