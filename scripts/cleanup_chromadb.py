import os
import sys
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.rag_engine import _get_collection, RAG_AVAILABLE

def purge_corrupt_chunks():
    if not RAG_AVAILABLE:
        print("RAG not available.")
        return
    col = _get_collection()
    count = col.count()
    print(f"Total chunks in ChromaDB: {count}")
    
    # ChromaDB get all
    batch_size = 500
    corrupt_ids = []
    
    # Read in batches
    res = col.get(include=["documents"])
    ids = res.get("ids", [])
    docs = res.get("documents", [])
    
    for doc_id, text in zip(ids, docs):
        if not text:
            corrupt_ids.append(doc_id)
            continue
        if "%PDF-" in text or "/Filter/FlateDecode" in text or "endobj" in text or "xref" in text:
            corrupt_ids.append(doc_id)
            continue
        printable = sum(1 for c in text if 32 <= ord(c) <= 126 or c in "\n\r\t")
        ratio = printable / max(1, len(text))
        if ratio < 0.85:
            corrupt_ids.append(doc_id)

    print(f"Found {len(corrupt_ids)} corrupt/binary chunks out of {len(ids)}.")
    if corrupt_ids:
        # Delete in chunks
        chunk_size = 200
        for i in range(0, len(corrupt_ids), chunk_size):
            batch = corrupt_ids[i:i+chunk_size]
            col.delete(ids=batch)
        print(f"Successfully deleted {len(corrupt_ids)} corrupt chunks from ChromaDB.")
    else:
        print("No corrupt chunks found.")

if __name__ == "__main__":
    purge_corrupt_chunks()
