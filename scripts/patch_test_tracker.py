def patch_test_tracker():
    with open("tests/test_tracker_lifecycle.py", "r", encoding="utf-8") as f:
        c = f.read()

    target = """@pytest.fixture(autouse=True)
def setup_tables():
    \"\"\"Ensure database schema is up-to-date before running tests.\"\"\"
    init_tracker_tables()"""

    target_crlf = """@pytest.fixture(autouse=True)\r
def setup_tables():\r
    \"\"\"Ensure database schema is up-to-date before running tests.\"\"\"\r
    init_tracker_tables()"""

    replacement = """@pytest.fixture(autouse=True)
def setup_tables():
    \"\"\"Ensure database schema is up-to-date and isolate test records.\"\"\"
    init_tracker_tables()
    conn = get_db_connection()
    try:
        conn.execute("DELETE FROM tracker_bucket WHERE symbol = 'RELIANCE'")
        conn.execute("DELETE FROM forward_signals WHERE symbol = 'RELIANCE'")
        conn.execute("DELETE FROM tracker_events_log WHERE symbol = 'RELIANCE'")
        conn.commit()
    finally:
        conn.close()"""

    replacement_crlf = """@pytest.fixture(autouse=True)\r
def setup_tables():\r
    \"\"\"Ensure database schema is up-to-date and isolate test records.\"\"\"\r
    init_tracker_tables()\r
    conn = get_db_connection()\r
    try:\r
        conn.execute("DELETE FROM tracker_bucket WHERE symbol = 'RELIANCE'")\r
        conn.execute("DELETE FROM forward_signals WHERE symbol = 'RELIANCE'")\r
        conn.execute("DELETE FROM tracker_events_log WHERE symbol = 'RELIANCE'")\r
        conn.commit()\r
    finally:\r
        conn.close()"""

    if target in c:
        c = c.replace(target, replacement, 1)
    elif target_crlf in c:
        c = c.replace(target_crlf, replacement_crlf, 1)

    with open("tests/test_tracker_lifecycle.py", "w", encoding="utf-8") as f:
        f.write(c)
    print("Patched test_tracker_lifecycle.py fixture!")

if __name__ == "__main__":
    patch_test_tracker()
