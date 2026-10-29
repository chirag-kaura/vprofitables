# core/personalization_db.py

import sqlite3

import os

import json

from datetime import datetime



from core.paths import DB_PATH



def get_db_connection(timeout: float = 30.0):

    conn = sqlite3.connect(DB_PATH, timeout=timeout)

    conn.row_factory = sqlite3.Row

    try:

        conn.execute("PRAGMA journal_mode = WAL")

        conn.execute("PRAGMA busy_timeout = 30000")

        conn.execute("PRAGMA foreign_keys = ON")

    except Exception:

        pass

    return conn



def init_personalization_db():

    conn = get_db_connection()

    c = conn.cursor()



    # 1. users

    c.execute("""

        CREATE TABLE IF NOT EXISTS users (

            id TEXT PRIMARY KEY,

            email TEXT UNIQUE NOT NULL,

            password_hash TEXT,

            google_sub TEXT UNIQUE,

            display_name TEXT,

            auth_method TEXT NOT NULL, -- password, google, both

            created_at TEXT NOT NULL

        )

    """)



    # 2. risk_profiles

    c.execute("""

        CREATE TABLE IF NOT EXISTS risk_profiles (

            id TEXT PRIMARY KEY,

            user_id TEXT UNIQUE NOT NULL,

            primary_goal TEXT NOT NULL, -- growth, income, preservation, learning

            horizon_weights TEXT NOT NULL, -- JSON object mapping swing/short/long to pct

            drawdown_reaction TEXT NOT NULL, -- sell_all, sell_some, hold, buy_more

            experience_level TEXT NOT NULL, -- new, some, experienced

            starting_capital REAL NOT NULL,

            excluded_sectors TEXT, -- JSON array

            max_position_pct REAL NOT NULL,

            max_sector_pct REAL NOT NULL,

            onboarding_version INTEGER NOT NULL,

            created_at TEXT NOT NULL,

            updated_at TEXT NOT NULL,

            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE

        )

    """)



    # 3. portfolios

    c.execute("""

        CREATE TABLE IF NOT EXISTS portfolios (

            id TEXT PRIMARY KEY,

            user_id TEXT NOT NULL,

            name TEXT NOT NULL DEFAULT 'Primary',

            created_at TEXT NOT NULL,

            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE

        )

    """)



    # 4. instruments

    c.execute("""

        CREATE TABLE IF NOT EXISTS instruments (

            symbol TEXT PRIMARY KEY,

            name TEXT NOT NULL,

            sector TEXT NOT NULL,

            instrument_type TEXT NOT NULL,

            exchange TEXT NOT NULL

        )

    """)



    # 5. positions

    c.execute("""

        CREATE TABLE IF NOT EXISTS positions (

            id TEXT PRIMARY KEY,

            portfolio_id TEXT NOT NULL,

            symbol TEXT NOT NULL,

            inv_type TEXT NOT NULL, -- swing, short, long

            entry_price REAL NOT NULL,

            shares INTEGER NOT NULL,

            stop_loss REAL,

            target1 REAL,

            target2 REAL,

            status TEXT NOT NULL, -- open, closed

            entry_date TEXT NOT NULL,

            exit_date TEXT,

            exit_price REAL,

            realized_pnl REAL,

            created_at TEXT NOT NULL,

            FOREIGN KEY (portfolio_id) REFERENCES portfolios (id) ON DELETE CASCADE,

            FOREIGN KEY (symbol) REFERENCES instruments (symbol)

        )

    """)

    c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_positions_sym_entry_open ON positions(symbol, entry_date) WHERE status='OPEN'")



    # 6. signals

    c.execute("""

        CREATE TABLE IF NOT EXISTS signals (

            id TEXT PRIMARY KEY,

            symbol TEXT NOT NULL,

            engine_name TEXT NOT NULL,

            engine_version TEXT NOT NULL,

            analysis_date TEXT NOT NULL,

            score REAL NOT NULL,

            confidence REAL NOT NULL,

            raw_output TEXT NOT NULL, -- JSON object

            computed_at TEXT NOT NULL,

            FOREIGN KEY (symbol) REFERENCES instruments (symbol)

        )

    """)



    # 7. recommendations

    c.execute("""

        CREATE TABLE IF NOT EXISTS recommendations (

            id TEXT PRIMARY KEY,

            user_id TEXT NOT NULL,

            portfolio_id TEXT NOT NULL,

            rec_type TEXT NOT NULL, -- new_capital, rebalance, alert

            payload TEXT NOT NULL, -- JSON payload

            reasoning TEXT NOT NULL, -- JSON payload

            constraints_checked TEXT NOT NULL, -- JSON payload

            passed INTEGER NOT NULL, -- 0 or 1

            created_at TEXT NOT NULL,

            applied INTEGER NOT NULL DEFAULT 0, -- 0 or 1

            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,

            FOREIGN KEY (portfolio_id) REFERENCES portfolios (id) ON DELETE CASCADE

        )

    """)



    # 8. user_feedback

    c.execute("""

        CREATE TABLE IF NOT EXISTS user_feedback (

            id TEXT PRIMARY KEY,

            recommendation_id TEXT NOT NULL,

            user_id TEXT NOT NULL,

            action TEXT NOT NULL, -- accepted, rejected, modified

            created_at TEXT NOT NULL,

            FOREIGN KEY (recommendation_id) REFERENCES recommendations (id) ON DELETE CASCADE,

            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE

        )

    """)



    # 9. position_audit_log (Phase 3 Fix 13)

    c.execute("""

        CREATE TABLE IF NOT EXISTS position_audit_log (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            position_id TEXT NOT NULL,

            field TEXT NOT NULL,

            old_value TEXT,

            new_value TEXT,

            changed_at TEXT NOT NULL,

            change_reason TEXT,

            FOREIGN KEY (position_id) REFERENCES positions (id) ON DELETE CASCADE

        )

    """)



    # ── Migration: Add columns to positions table if not present ──

    for col_name, col_type in [

        ("exit_reason",      "TEXT DEFAULT NULL"),

        ("updated_at",       "TEXT DEFAULT NULL"),

        ("source_signal_id", "INTEGER DEFAULT NULL"),

        ("lifecycle_state",  "TEXT DEFAULT 'OPEN'"),

        ("atr_multiplier",   "REAL DEFAULT NULL")

    ]:

        try:

            c.execute(f"ALTER TABLE positions ADD COLUMN {col_name} {col_type}")

        except sqlite3.OperationalError:

            pass  # Column already exists



    # ── Migration: Add columns to signals table if not present ──

    for col_name, col_type in [

        ("signal_subtype", "TEXT"),

        ("fired_at", "TEXT"),

        ("price_at_signal", "REAL"),

        ("outcome_price_5d", "REAL"),

        ("outcome_price_10d", "REAL"),

        ("outcome_price_20d", "REAL"),

        ("planet_name", "TEXT"),

        ("aspect_type", "TEXT"),

        ("direction", "TEXT")

    ]:

        try:

            c.execute(f"ALTER TABLE signals ADD COLUMN {col_name} {col_type}")

        except sqlite3.OperationalError:

            pass  # Column already exists



    # ── Table: gann_calibrated_weights ──

    c.execute("""

        CREATE TABLE IF NOT EXISTS gann_calibrated_weights (

            weight_key TEXT PRIMARY KEY,

            weight_value REAL NOT NULL

        )

    """)



    # ── Table: gann_instrument_scales ──

    c.execute("""

        CREATE TABLE IF NOT EXISTS gann_instrument_scales (

            symbol TEXT PRIMARY KEY,

            scale REAL NOT NULL,

            updated_at TEXT NOT NULL

        )

    """)



    # ── Table: watchlists ──

    c.execute("""

        CREATE TABLE IF NOT EXISTS watchlists (

            id TEXT PRIMARY KEY,

            user_id TEXT NOT NULL,

            name TEXT NOT NULL,

            created_at TEXT NOT NULL,

            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE

        )

    """)



    # ── Table: watchlist_stocks ──

    c.execute("""

        CREATE TABLE IF NOT EXISTS watchlist_stocks (

            id TEXT PRIMARY KEY,

            watchlist_id TEXT NOT NULL,

            symbol TEXT NOT NULL,

            added_at TEXT NOT NULL,

            FOREIGN KEY (watchlist_id) REFERENCES watchlists (id) ON DELETE CASCADE

        )

    """)



    conn.commit()



    # ── Table: feature_access_rules (Admin Feature Gating & Tier Matrix) ──

    c.execute("""

        CREATE TABLE IF NOT EXISTS feature_access_rules (

            feature_id TEXT PRIMARY KEY,

            feature_name TEXT NOT NULL,

            page TEXT NOT NULL,

            category TEXT DEFAULT 'ANALYTICS',

            min_role TEXT DEFAULT 'PREMIUM',

            is_locked_for_free INTEGER DEFAULT 1,

            description TEXT,

            updated_at TEXT NOT NULL

        )

    """)

    conn.commit()



    # Pre-populate default core features if table is empty

    c.execute("SELECT COUNT(*) FROM feature_access_rules")

    if c.fetchone()[0] == 0:

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        defaults = [

            ("overview_market_regime", "Market Regime & Simons FFT", "overview", "REGIME", "PREMIUM", 1, "Simons Fourier regime state and trend cycles"),

            ("overview_sentiment", "FinBERT NLP Sentiment & Flow", "overview", "SENTIMENT", "FREE", 0, "Real-time institutional news sentiment"),

            ("advisor_trade_corridor", "Actionable Entry & Stop Loss Corridor", "advisor", "ADVISORY", "PREMIUM", 1, "Exact numeric price corridors and risk-reward levels"),

            ("advisor_track_dossier", "Autonomous Radar Track & Equity Dossier", "advisor", "AUTOMATION", "PREMIUM", 1, "1-Click induction into trade tracker desk with email dossier"),

            ("scanner_full_pool", "Full 518 Instrument Multi-Confluence Scanner", "scanner", "SCANNER", "PREMIUM", 1, "518-instrument screener with Gann, Astro & Quant confluence"),

            ("simons_fourier_lab", "Simons Cycle Lab & Dominant Harmonics", "simons", "QUANT", "PREMIUM", 1, "Spectral energy decomposition and cycle projections"),

            ("trading_desk_execution", "Order Book & Demat Execution", "trading", "EXECUTION", "PREMIUM", 1, "Live paper & broker trade deployment and tracking"),

            ("gann_sq9_spiral", "Gann Square of 9 Spiral Levels", "sq9", "GANN", "PREMIUM", 1, "Cardinal and diagonal price vibration angles"),

            ("ephemeris_aspects", "Planetary Ephemeris & Geocentric Aspects", "dashboard", "ASTRO", "PREMIUM", 1, "Planetary longitude calculations and aspect windows"),

            ("options_smart_money", "Participant Open Interest & Smart Money", "sentiment", "DERIVATIVES", "PREMIUM", 1, "FII vs DII vs Retail futures & options positioning"),

            ("continuation_deep_engine", "20-EMA Dip & Rip Pullback Engine", "advisor", "MACHINE_LEARNING", "PREMIUM", 1, "XGBoost + PyTorch deep financial utility continuation predictions"),

            ("intraday_reversal_matrix", "Intraday 5m/15m Reversal Heatmap", "overview", "INTRADAY", "PREMIUM", 1, "Exact intraday turning times based on harmonic cycles")

        ]

        c.executemany("""

            INSERT OR REPLACE INTO feature_access_rules

            (feature_id, feature_name, page, category, min_role, is_locked_for_free, description, updated_at)

            VALUES (?, ?, ?, ?, ?, ?, ?, ?)

        """, [(d[0], d[1], d[2], d[3], d[4], d[5], d[6], now_str) for d in defaults])

        conn.commit()



    # ── Migration: Add role column to users table ──

    try:

        c.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'USER'")

        conn.commit()

    except sqlite3.OperationalError:

        pass  # Column already exists



    # ── Migration: Add onboarding preferences columns to risk_profiles ──

    for col_name, col_type in [

        ("age_range", "TEXT DEFAULT NULL"),

        ("occupation", "TEXT DEFAULT NULL"),

        ("location", "TEXT DEFAULT NULL"),

        ("experience_duration", "TEXT DEFAULT NULL"),

        ("primary_goals", "TEXT DEFAULT '[]'"),

        ("risk_comfort", "TEXT DEFAULT NULL"),

        ("risk_scenario_answer", "TEXT DEFAULT NULL"),

        ("preferred_markets", "TEXT DEFAULT '[]'"),

        ("trading_styles", "TEXT DEFAULT '[]'"),

        ("preferred_sectors", "TEXT DEFAULT '[]'"),

        ("investment_horizon", "TEXT DEFAULT NULL")

    ]:

        try:

            c.execute(f"ALTER TABLE risk_profiles ADD COLUMN {col_name} {col_type}")

            conn.commit()

        except sqlite3.OperationalError:

            pass  # Column already exists



    # Migration: Add telemetry columns to watchlist_stocks

    for col_name, col_type in [

        ("view_count", "INTEGER DEFAULT 0"),

        ("last_viewed_at", "TEXT DEFAULT NULL")

    ]:

        try:

            c.execute(f"ALTER TABLE watchlist_stocks ADD COLUMN {col_name} {col_type}")

            conn.commit()

        except Exception:

            pass



    # ── Seed Admin User ──

    import os

    admin_email = os.environ.get("ADMIN_EMAIL", "admin@vprofitables.com").strip().lower()

    admin_pass = os.environ.get("ADMIN_PASSWORD", "admin123")

    

    # Check if admin already exists

    row = c.execute("SELECT id, role FROM users WHERE email=?", (admin_email,)).fetchone()

    

    # Lazy import to avoid circular dependency

    from core.auth import hash_password

    import uuid

    

    if not row:

        print(f"[DB SETUP] Seeding admin user: {admin_email}...")

        admin_id = str(uuid.uuid4())

        pwd_hash = hash_password(admin_pass)

        created_at = datetime.utcnow().isoformat()

        c.execute("""

            INSERT INTO users (id, email, password_hash, display_name, auth_method, role, created_at)

            VALUES (?, ?, ?, ?, 'password', 'ADMIN', ?)

        """, (admin_id, admin_email, pwd_hash, "Administrator", created_at))

        conn.commit()

    else:

        # If admin exists, ensure their role is set to ADMIN

        if row["role"] != "ADMIN":

            print(f"[DB SETUP] Updating user {admin_email} role to ADMIN...")

            c.execute("UPDATE users SET role='ADMIN' WHERE id=?", (row["id"],))

            conn.commit()



    # Ensure chiragkaura@gmail.com and chiragkaura2003@gmail.com also maintain ADMIN role

    c.execute("UPDATE users SET role='ADMIN' WHERE email IN ('chiragkaura@gmail.com', 'chiragkaura2003@gmail.com', 'vprofitables@gmail.com')")

    conn.commit()



    # 9. Seed static instruments from data.instruments if empty

    cnt = c.execute("SELECT COUNT(*) FROM instruments").fetchone()[0]

    if cnt == 0:

        print("[DB SETUP] Seeding instruments table from data.instruments...")

        from data.instruments import ALL_INSTRUMENTS

        for sym, inst in ALL_INSTRUMENTS.items():

            c.execute("""

                INSERT INTO instruments (symbol, name, sector, instrument_type, exchange)

                VALUES (?, ?, ?, ?, ?)

            """, (sym, inst.name, inst.sector, inst.instrument_type, inst.exchange))

        conn.commit()

        print(f"[DB SETUP] Seeded {len(ALL_INSTRUMENTS)} instruments.")



    conn.close()



if __name__ == "__main__":

    init_personalization_db()

    print("[DB SETUP] Database personalization schema initialized successfully.")

