"""
core/tracker.py — Autonomous "Radar-to-Sniper" Trade Tracker Engine
===================================================================
Manages the end-to-end lifecycle of forward trading setups:
  1. STAGED_TRACKER       — Advance scouted setups placed in tracker bucket
  2. VERIFICATION_PENDING — Approaching window (T-3d to T-0d)
  3. CONFIRMED_TRIGGER    — 4-checkpoint verification passed -> Execution Green Light
  4. INVALIDATED          — Stop-loss breached or structural breakdown -> Noise pruned
  5. ACTIVE_POSITION      — Trade executed and actively managed
  6. COMPLETED            — Targets achieved or position closed

Includes:
  - Database state machine & schema migration (forward_signals, tracker_bucket, tracker_events_log)
  - Event-driven Drip intelligence listeners (Bulk deals, Delivery spikes, FII OI swings, FinBERT news)
  - Checkpoint verification coordinator
"""

import os
import json
import sqlite3
import logging
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple

from core.paths import DB_PATH

logger = logging.getLogger("tracker_engine")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# Expose checkpoint verification gate evaluator
from core.unified_logic import evaluate_tracker_checkpoints
evaluate_symbol_checkpoints = evaluate_tracker_checkpoints


# ─────────────────────────────────────────────────────────────────────────────
# 1. DATABASE SCHEMA INITIALIZATION & STATE MACHINE MIGRATIONS
# ─────────────────────────────────────────────────────────────────────────────

def get_db_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Returns a WAL-enabled SQLite connection with generous busy timeout."""
    target_path = db_path or DB_PATH
    conn = sqlite3.connect(target_path, timeout=30.0)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA busy_timeout=10000")
    conn.row_factory = sqlite3.Row
    return conn


def init_tracker_tables(conn: Optional[sqlite3.Connection] = None) -> None:
    """
    Ensures all required columns and tables exist for the Autonomous Tracker:
      - forward_signals (with updated tracker lifecycle columns)
      - tracker_bucket (dedicated tracker table/view)
      - tracker_events_log (audit log for event drips and checkpoint changes)
    """
    should_close = False
    if conn is None:
        conn = get_db_connection()
        should_close = True

    try:
        # 1. Master forward_signals table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS forward_signals (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                signal_date         TEXT NOT NULL,
                symbol              TEXT NOT NULL,
                inv_type            TEXT DEFAULT 'swing',
                entry               REAL DEFAULT 0.0,
                stop_loss           REAL DEFAULT 0.0,
                target1             REAL DEFAULT 0.0,
                target2             REAL DEFAULT 0.0,
                rr_ratio            REAL DEFAULT 0.0,
                confidence          INTEGER DEFAULT 50,
                regime              TEXT DEFAULT 'UNKNOWN',
                wyckoff_phase       TEXT DEFAULT '',
                news_sentiment      TEXT DEFAULT '',
                bulk_signal         TEXT DEFAULT '',
                hold_days           INTEGER DEFAULT 10,
                buy_date            TEXT,
                sell_date           TEXT,
                reasons             TEXT DEFAULT '[]',
                status              TEXT DEFAULT 'STAGED_TRACKER',
                exit_date           TEXT DEFAULT NULL,
                exit_price          REAL DEFAULT NULL,
                exit_reason         TEXT DEFAULT NULL,
                max_high            REAL DEFAULT NULL,
                trailing_sl         REAL DEFAULT NULL,
                pnl_pct             REAL DEFAULT NULL,
                notified            INTEGER DEFAULT 0,
                scout_source        TEXT DEFAULT 'GANN_SQ9 + CWT_WAVELET + ASTRO_ASPECT',
                projected_date      TEXT DEFAULT NULL,
                projected_entry_min REAL DEFAULT 0.0,
                projected_entry_max REAL DEFAULT 0.0,
                checkpoints_passed  INTEGER DEFAULT 0,
                checkpoints_detail  TEXT DEFAULT '{}',
                research_dossier_sent INTEGER DEFAULT 0,
                last_drip_update_at TEXT DEFAULT NULL,
                created_at          TEXT NOT NULL,
                updated_at          TEXT
            )
        """)

        # Dynamically add missing columns to forward_signals if table was created in earlier versions
        cols_needed = [
            ("scout_source", "TEXT DEFAULT 'GANN_SQ9 + CWT_WAVELET + ASTRO_ASPECT'"),
            ("projected_date", "TEXT DEFAULT NULL"),
            ("projected_entry_min", "REAL DEFAULT 0.0"),
            ("projected_entry_max", "REAL DEFAULT 0.0"),
            ("checkpoints_passed", "INTEGER DEFAULT 0"),
            ("checkpoints_detail", "TEXT DEFAULT '{}'"),
            ("research_dossier_sent", "INTEGER DEFAULT 0"),
            ("last_drip_update_at", "TEXT DEFAULT NULL"),
        ]
        cur_cols = {r["name"] for r in conn.execute("PRAGMA table_info(forward_signals)").fetchall()}
        for col_name, col_def in cols_needed:
            if col_name not in cur_cols:
                try:
                    conn.execute(f"ALTER TABLE forward_signals ADD COLUMN {col_name} {col_def}")
                except Exception as e:
                    logger.warning(f"Error altering forward_signals for {col_name}: {e}")

        # 2. Dedicated tracker_bucket table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tracker_bucket (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol              TEXT NOT NULL,
                status              TEXT DEFAULT 'STAGED_TRACKER',
                scout_source        TEXT DEFAULT 'GANN_SQ9 + CWT_WAVELET + ASTRO_ASPECT',
                projected_date      TEXT NOT NULL,
                projected_entry_min REAL NOT NULL,
                projected_entry_max REAL NOT NULL,
                stop_loss           REAL NOT NULL,
                target1             REAL NOT NULL,
                target2             REAL NOT NULL,
                rr_ratio            REAL NOT NULL,
                checkpoints_passed  INTEGER DEFAULT 0,
                checkpoints_detail  TEXT DEFAULT '{}',
                research_dossier_sent INTEGER DEFAULT 0,
                last_drip_update_at TEXT DEFAULT NULL,
                created_at          TEXT NOT NULL,
                updated_at          TEXT NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tb_sym_status ON tracker_bucket(symbol, status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tb_proj_date ON tracker_bucket(projected_date)")

        # 3. Audit trail: tracker_events_log
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tracker_events_log (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                signal_id      INTEGER,
                symbol         TEXT NOT NULL,
                event_type     TEXT NOT NULL, -- 'BULK_DEAL', 'DELIVERY_SPIKE', 'OI_SHIFT', 'NEWS_ALERT', 'CHECKPOINT_CHANGE'
                headline       TEXT,
                payload_json   TEXT,
                dispatched_at  TEXT DEFAULT (datetime('now','localtime'))
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tel_symbol ON tracker_events_log(symbol)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tel_sig_id ON tracker_events_log(signal_id)")

        conn.commit()
    finally:
        if should_close:
            conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# 2. STAGING & LIFECYCLE MANAGEMENT
# ─────────────────────────────────────────────────────────────────────────────

def stage_tracker_signal(
    symbol: str,
    projected_date: str,
    projected_entry_min: float,
    projected_entry_max: float,
    stop_loss: float,
    target1: float,
    target2: float,
    rr_ratio: Optional[float] = None,
    scout_source: str = "GANN_SQ9 + CWT_WAVELET + ASTRO_ASPECT",
    inv_type: str = "swing",
    confidence: int = 78,
    reasons: Optional[List[str]] = None,
    send_induction_notice: bool = True,
    allow_duplicate: bool = False,
    conn: Optional[sqlite3.Connection] = None,
) -> Dict[str, Any]:
    """
    Stages a new setup into the Tracker Bucket.
    Generates the Bespoke Equity Research Dossier immediately and dispatches the
    Tracker Induction Notice to the user.
    If allow_duplicate is False and an active tracker exists for the symbol,
    updates the existing record in-place to avoid wasting DB storage and avoid spam.
    """
    should_close = False
    if conn is None:
        conn = get_db_connection()
        should_close = True

    try:
        init_tracker_tables(conn)
        now_iso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        today_iso = date.today().isoformat()

        mid_entry = round((projected_entry_min + projected_entry_max) / 2.0, 2)
        risk = abs(mid_entry - stop_loss)
        reward = abs(target1 - mid_entry)
        computed_rr = round(reward / risk, 2) if risk > 0 else (rr_ratio or 2.0)
        final_rr = rr_ratio if (rr_ratio is not None and rr_ratio > 0) else computed_rr

        reasons_list = reasons or [
            f"Gann Sq9 Harmonic Support identified at ₹{projected_entry_min:,.2f}–₹{projected_entry_max:,.2f}",
            f"Dominant CWT Wavelet cycle resonance projected for {projected_date}",
            f"Planetary aspect confluence window active around {projected_date}"
        ]
        reasons_json = json.dumps(reasons_list)

        cur = conn.cursor()
        existing = None
        if not allow_duplicate:
            cur.execute("""
                SELECT id, research_dossier_sent, status
                FROM forward_signals
                WHERE symbol = ? AND status IN ('STAGED_TRACKER', 'VERIFICATION_PENDING', 'CONFIRMED_TRIGGER')
                ORDER BY id DESC LIMIT 1
            """, (symbol.upper(),))
            existing = cur.fetchone()

        if existing:
            # Update existing active record
            signal_id = existing[0] if isinstance(existing, tuple) else existing["id"]
            already_sent = bool(existing[1] if isinstance(existing, tuple) else existing["research_dossier_sent"])
            current_status = existing[2] if isinstance(existing, tuple) else existing["status"]

            # Check if induction dossier was already logged in audit table
            if not already_sent:
                chk_doss = conn.execute(
                    "SELECT id FROM tracker_events_log WHERE symbol = ? AND headline LIKE '%Dossier%'",
                    (symbol.upper(),)
                ).fetchone()
                if chk_doss:
                    already_sent = True

            cur.execute("""
                UPDATE forward_signals
                SET projected_date = ?,
                    projected_entry_min = ?,
                    projected_entry_max = ?,
                    entry = ?,
                    stop_loss = ?,
                    target1 = ?,
                    target2 = ?,
                    rr_ratio = ?,
                    confidence = ?,
                    reasons = ?,
                    scout_source = ?,
                    inv_type = ?,
                    updated_at = ?
                WHERE id = ?
            """, (
                projected_date, projected_entry_min, projected_entry_max,
                mid_entry, stop_loss, target1, target2, final_rr,
                confidence, reasons_json, scout_source, inv_type,
                now_iso, signal_id
            ))

            cur.execute("""
                UPDATE tracker_bucket
                SET projected_date = ?,
                    projected_entry_min = ?,
                    projected_entry_max = ?,
                    stop_loss = ?,
                    target1 = ?,
                    target2 = ?,
                    rr_ratio = ?,
                    scout_source = ?,
                    updated_at = ?
                WHERE id = ?
            """, (
                projected_date, projected_entry_min, projected_entry_max,
                stop_loss, target1, target2, final_rr, scout_source,
                now_iso, signal_id
            ))
            conn.commit()
            is_update = True
        else:
            # Insert into forward_signals
            cur.execute("""
                INSERT INTO forward_signals (
                    signal_date, symbol, inv_type, entry, stop_loss, target1, target2,
                    rr_ratio, confidence, reasons, status, scout_source,
                    projected_date, projected_entry_min, projected_entry_max,
                    checkpoints_passed, checkpoints_detail, research_dossier_sent,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'STAGED_TRACKER', ?, ?, ?, ?, 0, '{}', 0, ?, ?)
            """, (
                today_iso, symbol.upper(), inv_type, mid_entry, stop_loss, target1, target2,
                final_rr, confidence, reasons_json, scout_source,
                projected_date, projected_entry_min, projected_entry_max,
                now_iso, now_iso
            ))
            signal_id = cur.lastrowid

            # Insert into tracker_bucket for dedicated tracker querying
            cur.execute("""
                INSERT INTO tracker_bucket (
                    id, symbol, status, scout_source, projected_date,
                    projected_entry_min, projected_entry_max, stop_loss,
                    target1, target2, rr_ratio, checkpoints_passed,
                    checkpoints_detail, research_dossier_sent, created_at, updated_at
                ) VALUES (?, ?, 'STAGED_TRACKER', ?, ?, ?, ?, ?, ?, ?, ?, 0, '{}', 0, ?, ?)
            """, (
                signal_id, symbol.upper(), scout_source, projected_date,
                projected_entry_min, projected_entry_max, stop_loss,
                target1, target2, final_rr, now_iso, now_iso
            ))
            conn.commit()
            already_sent = False
            current_status = "STAGED_TRACKER"
            is_update = False

        signal_data = {
            "id": signal_id,
            "symbol": symbol.upper(),
            "status": current_status,
            "scout_source": scout_source,
            "projected_date": projected_date,
            "projected_entry_min": projected_entry_min,
            "projected_entry_max": projected_entry_max,
            "entry": mid_entry,
            "stop_loss": stop_loss,
            "target1": target1,
            "target2": target2,
            "rr_ratio": final_rr,
            "confidence": confidence,
            "reasons": reasons_list,
            "inv_type": inv_type,
            "created_at": now_iso,
            "is_update": is_update,
            "research_dossier_sent": 1 if already_sent else 0
        }

        # 3. Generate Bespoke Equity Research Dossier
        dossier = {}
        dossier_html = ""
        try:
            from core.report_engine import generate_symbol_dossier
            dossier = generate_symbol_dossier(symbol.upper(), target_date=projected_date, inv_type=inv_type)
            dossier_html = dossier.get("html", "")
        except Exception as e:
            logger.warning(f"Could not generate dossier for {symbol}: {e}")

        # 4. Dispatch Tracker Induction Notice + Dossier (only if not already sent, or forced)
        if send_induction_notice and not already_sent:
            try:
                from core.notifier import send_tracker_staged_alert
                send_tracker_staged_alert(symbol.upper(), signal_data, dossier_html=dossier_html)
                conn.execute("""
                    UPDATE forward_signals SET research_dossier_sent = 1, updated_at = ? WHERE id = ?
                """, (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), signal_id))
                conn.execute("""
                    UPDATE tracker_bucket SET research_dossier_sent = 1, updated_at = ? WHERE id = ?
                """, (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), signal_id))
                conn.commit()
                signal_data["research_dossier_sent"] = 1
            except Exception as e:
                logger.warning(f"Could not send tracker induction alert for {symbol}: {e}")

        # Log event
        log_tracker_event(
            signal_id=signal_id,
            symbol=symbol.upper(),
            event_type="CHECKPOINT_CHANGE",
            headline=f"Setup {'Updated in' if is_update else 'Staged into'} Tracker Bucket for {projected_date}",
            payload={"status": current_status, "projected_date": projected_date, "entry_zone": [projected_entry_min, projected_entry_max]},
            conn=conn
        )

        signal_data["dossier"] = dossier
        return signal_data
    finally:
        if should_close:
            conn.close()


def log_tracker_event(
    signal_id: Optional[int],
    symbol: str,
    event_type: str,
    headline: str,
    payload: Optional[Dict[str, Any]] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> int:
    """Logs an audit record into tracker_events_log and updates last_drip_update_at."""
    should_close = False
    if conn is None:
        conn = get_db_connection()
        should_close = True

    try:
        init_tracker_tables(conn)
        now_iso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        payload_str = json.dumps(payload or {})

        cur = conn.cursor()
        cur.execute("""
            INSERT INTO tracker_events_log (signal_id, symbol, event_type, headline, payload_json, dispatched_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (signal_id, symbol.upper(), event_type, headline, payload_str, now_iso))
        event_id = cur.lastrowid

        # Update last_drip_update_at on forward_signals and tracker_bucket
        if signal_id:
            conn.execute("UPDATE forward_signals SET last_drip_update_at = ?, updated_at = ? WHERE id = ?", (now_iso, now_iso, signal_id))
            conn.execute("UPDATE tracker_bucket SET last_drip_update_at = ?, updated_at = ? WHERE id = ?", (now_iso, now_iso, signal_id))
        else:
            conn.execute("UPDATE forward_signals SET last_drip_update_at = ?, updated_at = ? WHERE symbol = ? AND status IN ('STAGED_TRACKER', 'VERIFICATION_PENDING')", (now_iso, now_iso, symbol.upper()))
            conn.execute("UPDATE tracker_bucket SET last_drip_update_at = ?, updated_at = ? WHERE symbol = ? AND status IN ('STAGED_TRACKER', 'VERIFICATION_PENDING')", (now_iso, now_iso, symbol.upper()))

        conn.commit()
        return event_id
    finally:
        if should_close:
            conn.close()


def get_active_trackers(symbol: Optional[str] = None, conn: Optional[sqlite3.Connection] = None) -> List[Dict[str, Any]]:
    """Retrieves all setups currently in STAGED_TRACKER or VERIFICATION_PENDING status."""
    should_close = False
    if conn is None:
        conn = get_db_connection()
        should_close = True

    try:
        init_tracker_tables(conn)
        query = """
            SELECT * FROM forward_signals
            WHERE status IN ('STAGED_TRACKER', 'VERIFICATION_PENDING')
        """
        params = []
        if symbol:
            query += " AND symbol = ?"
            params.append(symbol.upper())
        query += " ORDER BY id DESC"

        rows = conn.execute(query, params).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            if isinstance(d.get("checkpoints_detail"), str):
                try:
                    d["checkpoints_detail"] = json.loads(d["checkpoints_detail"])
                except Exception:
                    pass
            if isinstance(d.get("reasons"), str):
                try:
                    d["reasons"] = json.loads(d["reasons"])
                except Exception:
                    pass
            result.append(d)
        return result
    finally:
        if should_close:
            conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# 3. EVENT-DRIVEN DRIP INTELLIGENCE HOOKS
# ─────────────────────────────────────────────────────────────────────────────

def handle_bulk_deals_drip(deals: List[Dict[str, Any]], conn: Optional[sqlite3.Connection] = None) -> List[Dict[str, Any]]:
    """
    Evaluates newly scraped/processed bulk or block deals.
    If any deal matches a symbol currently staged in the Tracker Bucket,
    logs the event and dispatches an automated Drip notification.
    """
    if not deals:
        return []

    should_close = False
    if conn is None:
        conn = get_db_connection()
        should_close = True

    dispatched = []
    try:
        init_tracker_tables(conn)
        active_list = get_active_trackers(conn=conn)
        if not active_list:
            return []
        active_trackers = {}
        for r in active_list:
            sym_k = r["symbol"]
            if sym_k not in active_trackers:
                active_trackers[sym_k] = r

        from core.notifier import send_drip_event_alert

        for deal in deals:
            sym = str(deal.get("symbol", "")).upper().strip()
            if sym in active_trackers:
                sig = active_trackers[sym]
                deal_type = deal.get("deal_type", "BUY")
                qty = int(deal.get("quantity", 0) or 0)
                price = float(deal.get("price", 0.0) or 0.0)
                client = deal.get("client_name", "Institutional Participant")
                kind = deal.get("deal_kind", "BLOCK")

                headline = f"Institutional {kind} Deal: {client} executed {deal_type} of {qty:,} shares at ₹{price:,.2f}"
                details = {
                    "deal_type": deal_type,
                    "deal_kind": kind,
                    "quantity": qty,
                    "price": price,
                    "value_cr": round(qty * price / 1e7, 2),
                    "client_name": client,
                    "deal_date": deal.get("deal_date", date.today().isoformat()),
                    "projected_date": sig.get("projected_date"),
                    "projected_entry_corridor": [sig.get("projected_entry_min"), sig.get("projected_entry_max")]
                }

                # Log to tracker_events_log
                log_tracker_event(
                    signal_id=sig["id"],
                    symbol=sym,
                    event_type="BULK_DEAL",
                    headline=headline,
                    payload=details,
                    conn=conn
                )

                # Send drip alert only if not already sent today
                chk_drip = conn.execute("""
                    SELECT id FROM tracker_events_log
                    WHERE symbol = ? AND event_type = 'BULK_DEAL'
                    AND date(dispatched_at) = date('now', 'localtime')
                    AND id < (SELECT MAX(id) FROM tracker_events_log)
                """, (sym,)).fetchone()
                if not chk_drip:
                    send_drip_event_alert(sym, "BULK_DEAL", details)
                dispatched.append({"symbol": sym, "event_type": "BULK_DEAL", "details": details})

        return dispatched
    finally:
        if should_close:
            conn.close()


def handle_delivery_spike_drip(
    symbol: str,
    trade_date: str,
    deliverable_pct: Optional[float],
    deliverable_qty: Optional[int],
    conn: Optional[sqlite3.Connection] = None
) -> Optional[Dict[str, Any]]:
    """
    Checks if a newly recorded Bhavcopy delivery row shows an institutional absorption spike:
    condition: deliverable_pct > 55% or delivery volume > 2.0x 20-day mean.
    If matched on a tracked symbol, dispatches a Drip notification.
    """
    if deliverable_pct is None and deliverable_qty is None:
        return None

    should_close = False
    if conn is None:
        conn = get_db_connection()
        should_close = True

    try:
        init_tracker_tables(conn)
        sym = symbol.upper().strip()
        active_list = get_active_trackers(symbol=sym, conn=conn)
        if not active_list:
            return None
        sig = active_list[0]

        # Calculate 20-day delivery volume average
        avg_20d_row = conn.execute("""
            SELECT AVG(deliverable_qty) as avg_qty, AVG(deliverable_pct) as avg_pct
            FROM (
                SELECT deliverable_qty, deliverable_pct
                FROM daily_prices
                WHERE symbol = ? AND trade_date < ? AND deliverable_qty IS NOT NULL
                ORDER BY trade_date DESC LIMIT 20
            )
        """, (sym, trade_date)).fetchone()

        avg_qty = float(avg_20d_row["avg_qty"] or 0.0) if avg_20d_row else 0.0
        pct_val = float(deliverable_pct or 0.0)
        qty_val = int(deliverable_qty or 0)

        is_pct_spike = pct_val > 55.0
        is_qty_surge = (avg_qty > 0 and qty_val > 2.0 * avg_qty)

        if is_pct_spike or is_qty_surge:
            mult = round(qty_val / avg_qty, 2) if avg_qty > 0 else 1.0
            headline = f"Delivery Absorption Spike: {pct_val:.1f}% Deliverable ({mult:.1f}x 20-day avg)"
            details = {
                "symbol": sym,
                "trade_date": trade_date,
                "deliverable_pct": pct_val,
                "deliverable_qty": qty_val,
                "avg_20d_qty": round(avg_qty, 0),
                "volume_surge_multiple": mult,
                "projected_date": sig.get("projected_date"),
                "entry_corridor": [sig.get("projected_entry_min"), sig.get("projected_entry_max")]
            }

            log_tracker_event(
                signal_id=sig["id"],
                symbol=sym,
                event_type="DELIVERY_SPIKE",
                headline=headline,
                payload=details,
                conn=conn
            )

            from core.notifier import send_drip_event_alert
            chk_drip = conn.execute("""
                SELECT id FROM tracker_events_log
                WHERE symbol = ? AND event_type = 'DELIVERY_SPIKE'
                AND date(dispatched_at) = date('now', 'localtime')
                AND id < (SELECT MAX(id) FROM tracker_events_log)
            """, (sym,)).fetchone()
            if not chk_drip:
                send_drip_event_alert(sym, "DELIVERY_SPIKE", details)
            return {"symbol": sym, "event_type": "DELIVERY_SPIKE", "details": details}

        return None
    finally:
        if should_close:
            conn.close()


def handle_participant_oi_drip(
    trade_date: str,
    fii_long_pct: float,
    prev_fii_long_pct: Optional[float] = None,
    conn: Optional[sqlite3.Connection] = None
) -> List[Dict[str, Any]]:
    """
    Checks if FII Index Future Long % shifted by > 10% in the direction of the setup.
    Dispatches a Drip intelligence flash to all active staged trackers.
    """
    should_close = False
    if conn is None:
        conn = get_db_connection()
        should_close = True

    try:
        init_tracker_tables(conn)
        if prev_fii_long_pct is None:
            # Query prior trade date from participant_sentiment_summary
            prior_row = conn.execute("""
                SELECT fii_index_long_pct FROM participant_sentiment_summary
                WHERE trade_date < ? ORDER BY trade_date DESC LIMIT 1
            """, (trade_date,)).fetchone()
            if prior_row:
                prev_fii_long_pct = float(prior_row["fii_index_long_pct"] or 50.0)
            else:
                prev_fii_long_pct = 50.0

        swing = round(fii_long_pct - prev_fii_long_pct, 2)
        if abs(swing) < 10.0:
            return []

        active_trackers = get_active_trackers(conn=conn)
        if not active_trackers:
            return []

        from core.notifier import send_drip_event_alert
        dispatched = []

        direction = "BULLISH EXPANSION" if swing > 0 else "BEARISH UNWINDING"
        headline = f"FII Participant OI Swing: Long ratio shifted {swing:+.1f}% to {fii_long_pct:.1f}% ({direction})"

        seen_symbols = set()
        for sig in active_trackers:
            sym = sig["symbol"]
            if sym in seen_symbols:
                continue
            seen_symbols.add(sym)
            details = {
                "symbol": sym,
                "trade_date": trade_date,
                "fii_long_pct": fii_long_pct,
                "prev_fii_long_pct": prev_fii_long_pct,
                "swing_pct": swing,
                "smart_money_bias": direction,
                "projected_date": sig.get("projected_date")
            }

            log_tracker_event(
                signal_id=sig["id"],
                symbol=sym,
                event_type="OI_SHIFT",
                headline=headline,
                payload=details,
                conn=conn
            )

            send_drip_event_alert(sym, "OI_SHIFT", details)
            dispatched.append({"symbol": sym, "event_type": "OI_SHIFT", "details": details})

        return dispatched
    finally:
        if should_close:
            conn.close()


def handle_finbert_news_drip(
    headlines: List[Dict[str, Any]],
    conn: Optional[sqlite3.Connection] = None
) -> List[Dict[str, Any]]:
    """
    Checks if newly fetched/scored news headlines have high-impact sentiment (> 90% confidence).
    Dispatches a Drip flash alert for active tracked symbols.
    """
    if not headlines:
        return []

    should_close = False
    if conn is None:
        conn = get_db_connection()
        should_close = True

    dispatched = []
    try:
        init_tracker_tables(conn)
        active_list = get_active_trackers(conn=conn)
        if not active_list:
            return []
        active_trackers = {}
        for r in active_list:
            sym_k = r["symbol"]
            if sym_k not in active_trackers:
                active_trackers[sym_k] = r

        from core.notifier import send_drip_event_alert

        for h in headlines:
            sym = str(h.get("symbol", "")).upper().strip()
            if sym not in active_trackers:
                continue

            fb_prob = h.get("finbert_prob_bullish")
            score = float(h.get("raw_score", 0.0) or h.get("score", 0.0) or 0.0)
            title = h.get("title", "") or h.get("headline", "")

            # Check > 90% confidence condition:
            is_high_confidence = False
            sentiment_tag = "NEUTRAL"
            if fb_prob is not None:
                if fb_prob >= 0.90:
                    is_high_confidence = True
                    sentiment_tag = f"STRONG BULLISH ({fb_prob*100:.0f}%)"
                elif fb_prob <= 0.10:
                    is_high_confidence = True
                    sentiment_tag = f"STRONG BEARISH ({(1.0-fb_prob)*100:.0f}%)"
            elif abs(score) >= 0.90:
                is_high_confidence = True
                sentiment_tag = f"HIGH CONVICTION ({score:+.2f})"

            if is_high_confidence and title:
                sig = active_trackers[sym]
                headline_text = f"FinBERT Breaking Intelligence: {title[:90]}... [{sentiment_tag}]"
                details = {
                    "symbol": sym,
                    "title": title,
                    "source": h.get("source", "Financial News Wire"),
                    "finbert_prob_bullish": fb_prob,
                    "sentiment_score": score,
                    "sentiment_label": sentiment_tag,
                    "url": h.get("url", ""),
                    "projected_date": sig.get("projected_date")
                }

                log_tracker_event(
                    signal_id=sig["id"],
                    symbol=sym,
                    event_type="NEWS_ALERT",
                    headline=headline_text,
                    payload=details,
                    conn=conn
                )

                chk_drip = conn.execute("""
                    SELECT id FROM tracker_events_log
                    WHERE symbol = ? AND event_type = 'NEWS_ALERT'
                    AND date(dispatched_at) = date('now', 'localtime')
                    AND id < (SELECT MAX(id) FROM tracker_events_log)
                """, (sym,)).fetchone()
                if not chk_drip:
                    send_drip_event_alert(sym, "NEWS_ALERT", details)
                dispatched.append({"symbol": sym, "event_type": "NEWS_ALERT", "details": details})

        return dispatched
    finally:
        if should_close:
            conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# 4. LIFECYCLE ADVANCEMENT: CHECKPOINT EVALUATOR & GREEN LIGHT DISPATCHER
# ─────────────────────────────────────────────────────────────────────────────

def advance_tracked_signals(
    as_of_date: Optional[str] = None,
    send_notifications: bool = True,
    conn: Optional[sqlite3.Connection] = None
) -> List[Dict[str, Any]]:
    """
    Evaluates all active tracker setups (STAGED_TRACKER, VERIFICATION_PENDING)
    against the 4-Checkpoint Verification Gate using evaluate_tracker_checkpoints.
    Updates the database state:
      - 3 or 4 gates pass on/near window -> CONFIRMED_TRIGGER -> Execution Green Light alert
      - Stop loss breached -> INVALIDATED -> Invalidation alert
      - T-3d to T-0d approaching window -> VERIFICATION_PENDING
    """
    should_close = False
    if conn is None:
        conn = get_db_connection()
        should_close = True

    results = []
    try:
        init_tracker_tables(conn)
        active_list = get_active_trackers(conn=conn)
        if not active_list:
            return []

        from core.unified_logic import evaluate_tracker_checkpoints
        from core.notifier import send_execution_trigger_alert, send_invalidation_alert

        now_iso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for sig in active_list:
            sig_id = sig["id"]
            sym = sig["symbol"]
            eval_res = evaluate_tracker_checkpoints(sym, as_of_date=as_of_date, conn=conn)

            passed_count = eval_res.get("checkpoints_passed", 0)
            gates_detail = eval_res.get("gates", {})
            new_status = eval_res.get("status", sig["status"])
            action = eval_res.get("action", "MONITOR")
            detail_json = json.dumps(gates_detail)

            # Check if state transitioned
            if new_status != sig["status"] or passed_count != sig.get("checkpoints_passed", 0):
                conn.execute("""
                    UPDATE forward_signals
                    SET status = ?, checkpoints_passed = ?, checkpoints_detail = ?, updated_at = ?
                    WHERE id = ?
                """, (new_status, passed_count, detail_json, now_iso, sig_id))
                conn.execute("""
                    UPDATE tracker_bucket
                    SET status = ?, checkpoints_passed = ?, checkpoints_detail = ?, updated_at = ?
                    WHERE id = ?
                """, (new_status, passed_count, detail_json, now_iso, sig_id))
                conn.commit()

                # Log event
                log_tracker_event(
                    signal_id=sig_id,
                    symbol=sym,
                    event_type="CHECKPOINT_CHANGE",
                    headline=f"Verification status transitioned to {new_status} ({passed_count}/4 gates passed)",
                    payload={"old_status": sig["status"], "new_status": new_status, "gates": gates_detail},
                    conn=conn
                )

                # Dispatch Actionable Alerts if notifications are enabled with deduplication guards
                if send_notifications:
                    if new_status == "CONFIRMED_TRIGGER":
                        chk_trig = conn.execute("""
                            SELECT id FROM tracker_events_log
                            WHERE signal_id = ? AND headline LIKE '%CONFIRMED_TRIGGER%'
                            AND id < (SELECT MAX(id) FROM tracker_events_log)
                        """, (sig_id,)).fetchone()
                        if not chk_trig:
                            send_execution_trigger_alert(sym, sig, gates_detail)
                        else:
                            logger.info(f"[VERIFY DEDUP] Execution Green Light already sent for {sym} (Signal #{sig_id}) — alert suppressed.")
                    elif new_status == "INVALIDATED":
                        chk_inv = conn.execute("""
                            SELECT id FROM tracker_events_log
                            WHERE signal_id = ? AND headline LIKE '%INVALIDATED%'
                            AND id < (SELECT MAX(id) FROM tracker_events_log)
                        """, (sig_id,)).fetchone()
                        if not chk_inv:
                            reason = eval_res.get("invalidation_reason", "Stop Loss violated without microstructure absorption")
                            send_invalidation_alert(sym, sig, reason)
                        else:
                            logger.info(f"[VERIFY DEDUP] Invalidation alert already sent for {sym} (Signal #{sig_id}) — alert suppressed.")

            results.append({
                "signal_id": sig_id,
                "symbol": sym,
                "old_status": sig["status"],
                "new_status": new_status,
                "checkpoints_passed": passed_count,
                "action": action,
                "gates": gates_detail
            })

        return results
    finally:
        if should_close:
            conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# 6. AUTONOMOUS RADAR SCAN & ADVANCE SCOUTING
# ─────────────────────────────────────────────────────────────────────────────

def run_autonomous_radar_scan(
    symbols: Optional[List[str]] = None,
    min_confluence: int = 70,
    max_stage_count: int = 5,
    target_days_ahead: int = 10,
    send_notifications: bool = False,
    inv_type: str = "swing",
    conn: Optional[sqlite3.Connection] = None,
) -> Dict[str, Any]:
    """
    Autonomous Radar Scanner for Advance Scouting across the liquid universe.
    Scans symbols using multi-engine confluence (Gann Sq9, Morlet CWT Wavelets,
    Planetary Aspects, Volume Profile, Fundamentals, FinBERT sentiment).
    Ranks setups by Confluence Score and stages top diverse symbols into Tracker Bucket.
    Prevents duplicate database records and avoids spamming notifications.
    """
    should_close = False
    if conn is None:
        conn = get_db_connection()
        should_close = True

    try:
        from core.report_engine import generate_symbol_dossier

        # Determine target window date
        target_date = (date.today() + timedelta(days=target_days_ahead)).isoformat()

        # Build candidate symbol pool
        if symbols:
            candidate_pool = [s.upper().strip() for s in symbols if s.strip()]
        else:
            # 1. Fetch recent high-conviction picks from advisor recommendations / signals
            advisor_picks = []
            try:
                rec_rows = conn.execute(
                    "SELECT DISTINCT symbol FROM recommendations WHERE symbol IS NOT NULL ORDER BY id DESC LIMIT 15"
                ).fetchall()
                advisor_picks = [r[0] for r in rec_rows if r[0]]
            except Exception:
                advisor_picks = []

            # 2. Fetch from instruments table
            try:
                db_syms = [
                    r[0] for r in conn.execute(
                        "SELECT symbol FROM instruments WHERE instrument_type = 'EQUITY' OR instrument_type IS NULL ORDER BY symbol"
                    ).fetchall()
                    if r[0] not in ('BANKNIFTY', 'NIFTY50', 'NIFTYAUTO', 'NIFTYIT', 'NIFTYPHARMA', 'GOLD', 'SILVER', 'COPPER', 'CRUDEOIL', 'NATURALGAS')
                ]
            except Exception:
                db_syms = []

            # 3. Fetch top volume active equities from daily_prices
            recent_active = []
            try:
                act_rows = conn.execute("""
                    SELECT symbol FROM daily_prices 
                    WHERE trade_date = (SELECT MAX(trade_date) FROM daily_prices)
                    AND symbol NOT IN ('BANKNIFTY', 'NIFTY50', 'NIFTYAUTO', 'NIFTYIT', 'NIFTYPHARMA', 'GOLD', 'SILVER', 'COPPER', 'CRUDEOIL', 'NATURALGAS')
                    ORDER BY volume DESC LIMIT 30
                """).fetchall()
                recent_active = [r[0] for r in act_rows if r[0]]
            except Exception:
                recent_active = []

            default_liquid = [
                "ADANIPORTS", "RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "SBIN",
                "TATAMOTORS", "ITC", "MARUTI", "LT", "AXISBANK", "KOTAKBANK",
                "BAJFINANCE", "HINDUNILVR", "SUNPHARMA", "TATASTEEL", "WIPRO",
                "HCLTECH", "TECHM", "NTPC", "POWERGRID", "COALINDIA", "BAJAJ-AUTO",
                "BHARTIARTL", "ASIANPAINT", "TITAN", "ULTRACEMCO", "JSWSTEEL", "CIPLA"
            ]
            seen = set()
            candidate_pool = []
            for s in (advisor_picks + default_liquid + db_syms + recent_active):
                if s and s not in seen:
                    seen.add(s)
                    candidate_pool.append(s)

        candidates = []
        for sym in candidate_pool:
            try:
                dossier = generate_symbol_dossier(sym, target_date=target_date, inv_type=inv_type)
                score = dossier.get("executive_conviction", {}).get("master_confluence_score", 0)
                playbook = dossier.get("actionable_playbook", {})
                corridor = playbook.get("entry_corridor", [dossier["current_price"] * 0.99, dossier["current_price"] * 1.01])
                sl = playbook.get("stop_loss", round(dossier["current_price"] * 0.96, 2))
                t1 = playbook.get("target1", round(dossier["current_price"] * 1.05, 2))
                t2 = playbook.get("target2", round(dossier["current_price"] * 1.10, 2))
                rr = playbook.get("rr_ratio", 2.2)

                if score >= min_confluence:
                    candidates.append({
                        "symbol": sym,
                        "confluence_score": score,
                        "current_price": dossier["current_price"],
                        "entry_min": corridor[0],
                        "entry_max": corridor[1],
                        "stop_loss": sl,
                        "target1": t1,
                        "target2": t2,
                        "rr_ratio": rr,
                        "dossier": dossier,
                    })
            except Exception as e:
                logger.warning(f"Error evaluating candidate {sym} for radar scan: {e}")

        # Sort candidates by confluence score descending
        candidates.sort(key=lambda c: c["confluence_score"], reverse=True)

        # Select top candidates up to max_stage_count (in-place update or fresh staging)
        top_candidates = candidates[:max_stage_count]
        staged_signals = []

        for cand in top_candidates:
            sym = cand["symbol"]
            staged = stage_tracker_signal(
                symbol=sym,
                projected_date=target_date,
                projected_entry_min=cand["entry_min"],
                projected_entry_max=cand["entry_max"],
                stop_loss=cand["stop_loss"],
                target1=cand["target1"],
                target2=cand["target2"],
                rr_ratio=cand["rr_ratio"],
                confidence=cand["confluence_score"],
                send_induction_notice=send_notifications,
                allow_duplicate=False,
                conn=conn
            )
            staged_signals.append({
                "symbol": sym,
                "id": staged["id"],
                "status": staged["status"],
                "confluence_score": cand["confluence_score"],
                "entry_zone": [cand["entry_min"], cand["entry_max"]],
                "stop_loss": cand["stop_loss"],
                "target1": cand["target1"],
                "target2": cand["target2"],
                "rr_ratio": cand["rr_ratio"],
                "projected_date": target_date,
                "is_update": staged.get("is_update", False)
            })

        return {
            "as_of_date": date.today().isoformat(),
            "projected_date": target_date,
            "symbols_scanned": len(candidate_pool),
            "candidates_found": len(candidates),
            "staged_count": len(staged_signals),
            "staged_signals": staged_signals
        }
    finally:
        if should_close:
            conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# 7. PRODUCTION DESK ORCHESTRATOR (DAILY 9:00 PM LOCAL & ON-DEMAND)
# ─────────────────────────────────────────────────────────────────────────────

def sync_and_dispatch_tracker_desk(
    min_confluence: int = 70,
    max_stage_count: int = 5,
    send_notifications: bool = True,
    force_resend_dossiers: bool = False,
    run_scan: bool = True,
    as_of_date: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> Dict[str, Any]:
    """
    Production Orchestrator for the Autonomous "Radar-to-Sniper" Trade Tracker Desk.
    Designed for daily 9:00 PM local scheduling and on-demand execution:
      1. Evaluates liquid universe and scouts candidate setups (if run_scan=True).
      2. Audits active tracked symbols: if not already added/sent, sends Bespoke Dossier.
      3. Evaluates 4-Checkpoint Verification Gates on all active tracked setups.
         Transitions state to CONFIRMED_TRIGGER (green light) or INVALIDATED (noise pruning)
         and automatically dispatches corresponding email + WhatsApp notifications.
      4. Audits recent event drips (bulk deals, delivery spikes, participant OI shifts).
    """
    should_close = False
    if conn is None:
        conn = get_db_connection()
        should_close = True

    try:
        init_tracker_tables(conn)
        as_of = as_of_date or date.today().isoformat()
        now_iso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 1. Advance Radar Scan across liquid universe
        scan_result = {}
        if run_scan:
            try:
                scan_result = run_autonomous_radar_scan(
                    min_confluence=min_confluence,
                    max_stage_count=max_stage_count,
                    send_notifications=send_notifications,
                    conn=conn
                )
            except Exception as e:
                logger.error(f"Error during autonomous radar scan in tracker desk: {e}")
                scan_result = {"error": str(e)}

        # 2. Audit active setups: Ensure pending dossiers are sent
        dispatched_dossiers = []
        cur = conn.cursor()
        cur.execute("""
            SELECT id, symbol, status, projected_date, projected_entry_min, projected_entry_max,
                   entry, stop_loss, target1, target2, rr_ratio, confidence, reasons, inv_type,
                   research_dossier_sent
            FROM forward_signals
            WHERE status IN ('STAGED_TRACKER', 'VERIFICATION_PENDING')
            ORDER BY id ASC
        """)
        active_rows = cur.fetchall()

        from core.report_engine import generate_symbol_dossier
        from core.notifier import send_tracker_staged_alert

        for r in active_rows:
            sig_id = r["id"]
            sym = r["symbol"]
            dossier_sent = bool(r["research_dossier_sent"])

            # Check if dossier was already logged as dispatched in tracker_events_log
            if not dossier_sent and not force_resend_dossiers:
                chk = conn.execute(
                    "SELECT id FROM tracker_events_log WHERE symbol = ? AND headline LIKE '%Dossier%'",
                    (sym,)
                ).fetchone()
                if chk:
                    conn.execute("UPDATE forward_signals SET research_dossier_sent = 1, updated_at = ? WHERE id = ?", (now_iso, sig_id))
                    conn.execute("UPDATE tracker_bucket SET research_dossier_sent = 1, updated_at = ? WHERE id = ?", (now_iso, sig_id))
                    conn.commit()
                    dossier_sent = True

            if (not dossier_sent or force_resend_dossiers) and send_notifications:
                try:
                    reasons_val = []
                    try:
                        reasons_val = json.loads(r["reasons"]) if r["reasons"] else []
                    except Exception:
                        pass

                    sig_data = {
                        "id": sig_id,
                        "symbol": sym,
                        "status": r["status"],
                        "projected_date": r["projected_date"],
                        "projected_entry_min": float(r["projected_entry_min"] or 0),
                        "projected_entry_max": float(r["projected_entry_max"] or 0),
                        "entry": float(r["entry"] or 0),
                        "stop_loss": float(r["stop_loss"] or 0),
                        "target1": float(r["target1"] or 0),
                        "target2": float(r["target2"] or 0),
                        "rr_ratio": float(r["rr_ratio"] or 2.0),
                        "confidence": int(r["confidence"] or 75),
                        "reasons": reasons_val,
                        "inv_type": r["inv_type"] or "swing",
                    }

                    dossier = generate_symbol_dossier(sym, target_date=r["projected_date"], inv_type=sig_data["inv_type"])
                    dossier_html = dossier.get("html", "")

                    alert_res = send_tracker_staged_alert(sym, sig_data, dossier_html=dossier_html)

                    conn.execute("""
                        UPDATE forward_signals SET research_dossier_sent = 1, updated_at = ? WHERE id = ?
                    """, (now_iso, sig_id))
                    conn.execute("""
                        UPDATE tracker_bucket SET research_dossier_sent = 1, updated_at = ? WHERE id = ?
                    """, (now_iso, sig_id))
                    conn.commit()

                    log_tracker_event(
                        signal_id=sig_id,
                        symbol=sym,
                        event_type="CHECKPOINT_CHANGE",
                        headline=f"Bespoke Equity Research Dossier Dispatched for {sym}",
                        payload={"status": r["status"], "projected_date": r["projected_date"]},
                        conn=conn
                    )
                    dispatched_dossiers.append({"id": sig_id, "symbol": sym, "alert_result": alert_res})
                except Exception as e:
                    logger.error(f"Error dispatching pending dossier for {sym} (ID: {sig_id}): {e}")

        # 3. Advance Tracked Signals through the 4-Checkpoint Verification Gates
        gate_transitions = []
        try:
            gate_transitions = advance_tracked_signals(as_of_date=as_of, send_notifications=send_notifications, conn=conn)
        except Exception as e:
            logger.error(f"Error advancing tracked signals through verification gates: {e}")

        # 4. Check & log summary
        summary = {
            "status": "SUCCESS",
            "executed_at": now_iso,
            "as_of_date": as_of,
            "radar_scan": scan_result,
            "active_trackers_count": len(active_rows),
            "pending_dossiers_sent": len(dispatched_dossiers),
            "dossiers_dispatched": dispatched_dossiers,
            "gate_transitions": gate_transitions,
            "transition_count": len(gate_transitions),
        }
        return summary
    finally:
        if should_close:
            conn.close()


