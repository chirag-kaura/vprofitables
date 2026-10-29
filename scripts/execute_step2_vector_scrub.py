import os
import sys
import re
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.rag_engine import _get_collection

BOILERPLATE_REGEXES = [
    re.compile(r"safe\s*harbor", re.I),
    re.compile(r"forward-looking\s*statement", re.I),
    re.compile(r"listen-only\s*mode", re.I),
    re.compile(r"touch-?tone\s*telephone", re.I),
    re.compile(r"does\s*not\s*constitute\s*an\s*offer\s*to\s*(?:buy|sell)", re.I),
    re.compile(r"undertakes\s*no\s*obligation\s*to\s*(?:publicly\s*)?update", re.I),
    re.compile(r"ladies\s*and\s*gentlemen\s*,\s*good\s*day\s*and\s*welcome", re.I),
    re.compile(r"please\s*press\s*\*?\s*(?:then|and)?\s*1", re.I),
    re.compile(r"give\s*your\s*name\s*and\s*company\s*name", re.I),
    re.compile(r"i\s*now\s*hand\s*the\s*conference\s*over\s*to", re.I),
]

def is_chunk_boilerplate(text: str) -> bool:
    t_clean = text.strip()
    if len(t_clean) < 80:
        return True
    
    matches = sum(1 for rgx in BOILERPLATE_REGEXES if rgx.search(t_clean))
    if matches >= 1:
        # Check if it has actual operational/financial guidance
        # If it's heavily operator/legal logistics, purge it
        if "forward-looking" in t_clean.lower() or "listen-only" in t_clean.lower() or matches >= 2:
            return True
        if len(t_clean) < 400 and ("welcome" in t_clean.lower() or "moderator" in t_clean.lower()):
            return True
            
    return False

def scrub_chroma_boilerplate():
    print("=" * 65)
    print("STEP 2: VECTOR STORE BOILERPLATE PURGE & SCRUBBING")
    print("=" * 65)

    col = _get_collection()
    total_chunks = col.count()
    print(f"Initial Vector Store Chunks: {total_chunks}")

    batch_size = 500
    ids_to_delete = []
    
    # Iterate through collection using limit and offset
    offset = 0
    scanned = 0
    t0 = time.time()

    while offset < total_chunks:
        try:
            res = col.get(limit=batch_size, offset=offset, include=['documents'])
            docs = res.get('documents', [])
            ids = res.get('ids', [])
            
            if not ids:
                break

            for doc_id, doc_text in zip(ids, docs):
                scanned += 1
                if is_chunk_boilerplate(doc_text):
                    ids_to_delete.append(doc_id)

            offset += len(ids)
            if scanned % 5000 == 0 or offset >= total_chunks:
                print(f"    Scanned: {scanned}/{total_chunks} | Boilerplate identified: {len(ids_to_delete)}")
        except Exception as e:
            print(f"    Error reading offset {offset}: {e}")
            break

    print(f"\nScan complete in {time.time() - t0:.1f}s.")
    print(f"Total Boilerplate Chunks Identified for Purge: {len(ids_to_delete)} ({len(ids_to_delete)/total_chunks*100:.1f}%)")

    # Delete in batches of 200
    if ids_to_delete:
        del_t0 = time.time()
        print(f"Purging {len(ids_to_delete)} boilerplate chunks from ChromaDB...")
        del_batch_size = 200
        for i in range(0, len(ids_to_delete), del_batch_size):
            del_batch = ids_to_delete[i:i+del_batch_size]
            try:
                col.delete(ids=del_batch)
            except Exception as e:
                print(f"    Error deleting batch {i}: {e}")
        print(f"Purge complete in {time.time() - del_t0:.1f}s.")

    remaining_chunks = col.count()
    print(f"\nFinal High-Quality Vector Chunks: {remaining_chunks}")
    print(f"Purged: {total_chunks - remaining_chunks} legal/operator boilerplate chunks.")
    print("=" * 65)
    print("STEP 2 CHROMA PURGE COMPLETE!")
    print("=" * 65)

if __name__ == "__main__":
    scrub_chroma_boilerplate()
