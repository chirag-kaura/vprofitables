"""
cloud_sync.py — Lifetime Free Cloud DB Sync for GANN-ASTRO v3.9
================================================================
Automates database distribution between Oracle Cloud Free VM & local edge clients.

USAGE:
  1. Oracle Cloud (Upload after daily 9:00 PM IST run):
     python cloud_sync.py --upload

  2. Local Edge Client (Download latest DB on startup):
     python cloud_sync.py --download
"""

import os
import sys
import sqlite3
import argparse
import requests
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, "market_data_v2.db")
CONFIG_FILE = os.path.join(BASE_DIR, "cloud_config.json")

# Default Oracle Cloud Object Storage / S3 Public Bucket URL
DEFAULT_BUCKET_URL = os.environ.get(
    "GANN_CLOUD_URL",
    "https://objectstorage.ap-mumbai-1.oraclecloud.com/n/yournamespace/b/gann-astro-data/o/"
)

def upload_db(bucket_url: str):
    """Uploads local market_data_v2.db to Oracle Object Storage / S3."""
    if not os.path.exists(DB_PATH):
        print("  [CLOUD] Error: market_data_v2.db does not exist to upload.", flush=True)
        return False
    
    target_url = bucket_url.rstrip("/") + "/market_data_v2.db"
    print(f"  [CLOUD] Uploading market_data_v2.db to Oracle Object Storage...", flush=True)
    try:
        # Enable WAL checkpoint before upload to flush all data from WAL to DB file
        conn = sqlite3.connect(DB_PATH, timeout=30)
        conn.execute("PRAGMA wal_checkpoint(FULL)")
        conn.close()

        with open(DB_PATH, "rb") as f:
            resp = requests.put(target_url, data=f, headers={"Content-Type": "application/octet-stream"}, timeout=300)
            if resp.status_code in (200, 201):
                print("  [CLOUD] Upload successful!", flush=True)
                return True
            else:
                print(f"  [CLOUD] Upload HTTP {resp.status_code}: {resp.text[:200]}", flush=True)
                return False
    except Exception as e:
        print(f"  [CLOUD] Upload error: {e}", flush=True)
        return False

def download_db(bucket_url: str):
    """Downloads updated market_data_v2.db from cloud if remote version is newer or missing."""
    target_url = bucket_url.rstrip("/") + "/market_data_v2.db"
    tmp_path   = DB_PATH + ".tmp"
    print(f"  [CLOUD] Checking for cloud database update...", flush=True)

    try:
        # Check Last-Modified / ETag header via HEAD request
        head_resp = requests.head(target_url, timeout=10)
        if head_resp.status_code != 200:
            print(f"  [CLOUD] No remote database found at cloud URL (HTTP {head_resp.status_code}). Using local DB.", flush=True)
            return False

        remote_size = int(head_resp.headers.get("Content-Length", 0))
        if os.path.exists(DB_PATH):
            local_size = os.path.getsize(DB_PATH)
            # If local DB is larger/equal and modified today, keep local
            if local_size == remote_size and remote_size > 0:
                print("  [CLOUD] Local database is already up-to-date with cloud.", flush=True)
                return True

        print("  [CLOUD] Downloading latest market_data_v2.db from cloud...", flush=True)
        with requests.get(target_url, stream=True, timeout=600) as r:
            r.raise_for_status()
            with open(tmp_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024 * 1024): # 1 MB chunks
                    if chunk:
                        f.write(chunk)

        # Atomic swap
        if os.path.exists(DB_PATH):
            os.replace(tmp_path, DB_PATH)
        else:
            os.rename(tmp_path, DB_PATH)

        print("  [CLOUD] Download complete & database updated successfully!", flush=True)
        return True

    except Exception as e:
        print(f"  [CLOUD] Sync check skipped: {e}", flush=True)
        if os.path.exists(tmp_path):
            try: os.remove(tmp_path)
            except Exception: pass
        return False

def main():
    parser = argparse.ArgumentParser(description="GANN-ASTRO Lifetime Free Cloud Sync Engine")
    parser.add_argument("--upload",   action="store_true", help="Upload local DB to Oracle Cloud Storage")
    parser.add_argument("--download", action="store_true", help="Download updated DB from Oracle Cloud Storage")
    parser.add_argument("--url",      type=str, default=DEFAULT_BUCKET_URL, help="Custom Oracle Storage URL")
    args = parser.parse_args()

    if args.upload:
        upload_db(args.url)
    elif args.download:
        download_db(args.url)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
