"""
tests/test_tracker_lifecycle.py
================================
Autonomous "Radar-to-Sniper" Trade Tracker Lifecycle Test Suite.
Validates the complete end-to-end lifecycle:
  1. Database state machine & schema migration (WAL, tables, columns)
  2. Bespoke Equity Research Dossier generation (all 7 modules + HTML + MD)
  3. Staging setup into Tracker Bucket (Tracker Induction Notice)
  4. Event-driven Drip intelligence hooks (Bulk deal, Delivery spike, FII OI, FinBERT news)
  5. 4-Checkpoint Verification Gate evaluation (Gate 1 to Gate 4)
  6. Execution Green Light transition (CONFIRMED_TRIGGER)
  7. Invalidation / Noise Pruning transition (INVALIDATED)
  8. SQLite WAL mode concurrency and non-blocking reads/writes
"""

import os
import sqlite3
import pytest
from datetime import date, datetime, timedelta

from core.paths import DB_PATH
from core.tracker import (
    get_db_connection,
    init_tracker_tables,
    stage_tracker_signal,
    get_active_trackers,
    handle_bulk_deals_drip,
    handle_delivery_spike_drip,
    handle_participant_oi_drip,
    handle_finbert_news_drip,
    advance_tracked_signals,
    run_autonomous_radar_scan,
    sync_and_dispatch_tracker_desk
)
from core.report_engine import generate_symbol_dossier
from models.unified_logic import evaluate_tracker_checkpoints
from core.notifier import (
    send_tracker_staged_alert,
    send_drip_event_alert,
    send_execution_trigger_alert,
    send_invalidation_alert
)


@pytest.fixture(autouse=True)
def setup_tables():
    """Ensure database schema is up-to-date and isolate test records."""
    init_tracker_tables()
    conn = get_db_connection()
    try:
        conn.execute("DELETE FROM tracker_bucket WHERE symbol = 'RELIANCE'")
        conn.execute("DELETE FROM forward_signals WHERE symbol = 'RELIANCE'")
        conn.execute("DELETE FROM tracker_events_log WHERE symbol = 'RELIANCE'")
        conn.commit()
    finally:
        conn.close()


@pytest.fixture(autouse=True)
def mock_notifier_dispatch(monkeypatch):
    """Prevent automated unit tests from dispatching real emails or WhatsApp messages."""
    monkeypatch.setattr(
        "core.notifier._dispatch_alert",
        lambda subject, html_body, wa_text: {
            "ok": True,
            "subject": subject,
            "wa_text": wa_text,
            "channels": {
                "email": {"ok": True, "method": "mock_email", "to": "mock@test.com"},
                "whatsapp": {"ok": True, "method": "mock_wa"}
            }
        }
    )


def test_schema_initialization_and_wal():
    """Verify that forward_signals, tracker_bucket, and tracker_events_log exist and WAL mode is active."""
    conn = get_db_connection()
    try:
        # Check WAL mode
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        assert str(mode).lower() == "wal", f"Expected WAL mode, got {mode}"

        # Verify forward_signals columns
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(forward_signals)").fetchall()}
        required_cols = {
            "id", "symbol", "status", "scout_source", "projected_date",
            "projected_entry_min", "projected_entry_max", "stop_loss",
            "target1", "target2", "rr_ratio", "checkpoints_passed",
            "checkpoints_detail", "research_dossier_sent", "last_drip_update_at"
        }
        for col in required_cols:
            assert col in cols, f"Missing column {col} in forward_signals"

        # Verify tracker_bucket table
        tb_cols = {r["name"] for r in conn.execute("PRAGMA table_info(tracker_bucket)").fetchall()}
        assert "symbol" in tb_cols
        assert "projected_date" in tb_cols
        assert "checkpoints_passed" in tb_cols

        # Verify tracker_events_log table
        log_cols = {r["name"] for r in conn.execute("PRAGMA table_info(tracker_events_log)").fetchall()}
        assert "event_type" in log_cols
        assert "headline" in log_cols
        assert "payload_json" in log_cols
        assert "dispatched_at" in log_cols
    finally:
        conn.close()


def test_bespoke_equity_research_dossier():
    """Verify synthesis of the 7-section Bespoke Equity Research Dossier for RELIANCE."""
    target_window = (date.today() + timedelta(days=14)).isoformat()
    dossier = generate_symbol_dossier("RELIANCE", target_date=target_window, inv_type="swing")

    assert dossier["symbol"] == "RELIANCE"
    assert dossier["target_date"] == target_window
    assert dossier["current_price"] > 0

    # 1. Executive Conviction Brief
    exec_b = dossier["executive_conviction"]
    assert 0 <= exec_b["master_confluence_score"] <= 100
    assert "strategy_type" in exec_b
    assert "allocation_limit" in exec_b
    assert len(exec_b["narrative"]) > 20

    # 2. Time & Price Geometry
    geo = dossier["geometry"]
    assert 0.0 <= geo["gann_sq9_angle"] <= 360.0
    assert geo["sq9_support"] > 0
    assert geo["dominant_cwt_period_days"] > 0
    assert len(geo["planetary_aspects"]) > 0

    # 3. Microstructure & Volume Profile
    micro = dossier["microstructure"]
    assert micro["vpoc"] > 0
    assert micro["vah"] >= micro["val"]
    assert "delivery_5d_avg" in micro
    assert "wyckoff_status" in micro

    # 4. Institutional Footprint
    foot = dossier["institutional_footprint"]
    assert "fii_index_long_pct" in foot
    assert "options_pcr" in foot
    assert "options_max_pain" in foot

    # 5. Fundamental Health
    fund = dossier["fundamental_health"]
    assert fund["pe_ratio"] > 0
    assert fund["grade"] in ("A", "A+", "B", "C")

    # 6. NLP News & Risks
    nlp = dossier["nlp_news_risks"]
    assert 0.0 <= nlp["finbert_avg_bullish_prob"] <= 1.0
    assert "management_tone" in nlp

    # 7. Actionable Playbook
    play = dossier["actionable_playbook"]
    assert len(play["entry_corridor"]) == 2
    assert play["entry_corridor"][0] <= play["entry_corridor"][1]
    assert play["stop_loss"] < play["entry_corridor"][0]
    assert play["target1"] > play["entry_corridor"][1]
    assert play["target2"] > play["target1"]
    assert play["rr_ratio"] >= 1.0

    # 8. Renderers
    assert "<!DOCTYPE html>" in dossier["html"]
    assert "VPROFITABLES BESPOKE EQUITY DOSSIER" in dossier["html"]
    assert len(dossier["markdown"]) > 500


def test_stage_forward_signal_induction():
    """Verify staging a forward signal into the tracker bucket with dossier induction dispatch."""
    target_dt = (date.today() + timedelta(days=10)).isoformat()
    signal_res = stage_tracker_signal(
        symbol="RELIANCE",
        projected_date=target_dt,
        projected_entry_min=2700.0,
        projected_entry_max=2740.0,
        stop_loss=2620.0,
        target1=2900.0,
        target2=3050.0,
        rr_ratio=2.2,
        scout_source="GANN_SQ9 + CWT_WAVELET + ASTRO_ASPECT",
        inv_type="swing",
        send_induction_notice=True
    )

    assert signal_res["id"] > 0
    assert signal_res["symbol"] == "RELIANCE"
    assert signal_res["status"] == "STAGED_TRACKER"
    assert signal_res["research_dossier_sent"] == 1

    # Verify database persistence
    conn = get_db_connection()
    try:
        row = conn.execute("SELECT * FROM forward_signals WHERE id = ?", (signal_res["id"],)).fetchone()
        assert row is not None
        assert row["status"] == "STAGED_TRACKER"
        assert row["research_dossier_sent"] == 1

        tb_row = conn.execute("SELECT * FROM tracker_bucket WHERE id = ?", (signal_res["id"],)).fetchone()
        assert tb_row is not None
        assert tb_row["status"] == "STAGED_TRACKER"

        # Verify audit log entry
        log_row = conn.execute(
            "SELECT * FROM tracker_events_log WHERE signal_id = ? AND event_type = 'CHECKPOINT_CHANGE'",
            (signal_res["id"],)
        ).fetchone()
        assert log_row is not None
    finally:
        conn.close()


def test_drip_hook_block_deal():
    """Verify that a newly processed block deal triggers the event drip hook and updates audit logs."""
    conn = get_db_connection()
    try:
        sig = stage_tracker_signal(
            symbol="RELIANCE",
            projected_date=(date.today() + timedelta(days=12)).isoformat(),
            projected_entry_min=2700.0,
            projected_entry_max=2740.0,
            stop_loss=2620.0,
            target1=2900.0,
            target2=3050.0,
            send_induction_notice=False,
            conn=conn
        )
        sig_id = sig["id"]

        test_deals = [{
            "symbol": "RELIANCE",
            "deal_date": date.today().isoformat(),
            "deal_type": "BUY",
            "quantity": 500000,
            "price": 2725.50,
            "deal_kind": "BLOCK",
            "client_name": "MORGAN STANLEY ASIA (SINGAPORE) PTE."
        }]

        dispatched = handle_bulk_deals_drip(test_deals, conn=conn)
        assert len(dispatched) >= 1
        assert dispatched[0]["symbol"] == "RELIANCE"
        assert dispatched[0]["event_type"] == "BULK_DEAL"

        # Verify tracker_events_log
        log_row = conn.execute(
            "SELECT * FROM tracker_events_log WHERE signal_id = ? AND event_type = 'BULK_DEAL' ORDER BY id DESC LIMIT 1",
            (sig_id,)
        ).fetchone()
        assert log_row is not None
        assert "MORGAN STANLEY" in log_row["headline"]

        # Verify last_drip_update_at is populated
        sig_row = conn.execute("SELECT last_drip_update_at FROM forward_signals WHERE id = ?", (sig_id,)).fetchone()
        assert sig_row["last_drip_update_at"] is not None
    finally:
        conn.close()


def test_drip_hook_delivery_spike():
    """Verify that an abnormal Bhavcopy delivery % or volume surge dispatches a Drip update."""
    conn = get_db_connection()
    try:
        sig = stage_tracker_signal(
            symbol="RELIANCE",
            projected_date=(date.today() + timedelta(days=12)).isoformat(),
            projected_entry_min=2700.0,
            projected_entry_max=2740.0,
            stop_loss=2620.0,
            target1=2900.0,
            target2=3050.0,
            send_induction_notice=False,
            conn=conn
        )
        sig_id = sig["id"]

        today_str = date.today().isoformat()
        res = handle_delivery_spike_drip(
            symbol="RELIANCE",
            trade_date=today_str,
            deliverable_pct=64.2,  # > 55% threshold
            deliverable_qty=3200000,
            conn=conn
        )
        assert res is not None
        assert res["symbol"] == "RELIANCE"
        assert res["event_type"] == "DELIVERY_SPIKE"
        assert res["details"]["deliverable_pct"] == 64.2

        # Verify audit log
        log_row = conn.execute(
            "SELECT * FROM tracker_events_log WHERE signal_id = ? AND event_type = 'DELIVERY_SPIKE' ORDER BY id DESC LIMIT 1",
            (sig_id,)
        ).fetchone()
        assert log_row is not None
        assert "64.2%" in log_row["headline"]
    finally:
        conn.close()


def test_drip_hook_participant_oi_swing():
    """Verify that a >10% FII index future long swing dispatches an OI_SHIFT event."""
    conn = get_db_connection()
    try:
        stage_tracker_signal(
            symbol="RELIANCE",
            projected_date=(date.today() + timedelta(days=12)).isoformat(),
            projected_entry_min=2700.0,
            projected_entry_max=2740.0,
            stop_loss=2620.0,
            target1=2900.0,
            target2=3050.0,
            send_induction_notice=False,
            conn=conn
        )

        today_str = date.today().isoformat()
        dispatched = handle_participant_oi_drip(
            trade_date=today_str,
            fii_long_pct=65.5,
            prev_fii_long_pct=52.0,  # Swing of +13.5%
            conn=conn
        )
        assert len(dispatched) >= 1
        assert any(d["symbol"] == "RELIANCE" for d in dispatched)

        # Check log
        log_rows = conn.execute(
            "SELECT * FROM tracker_events_log WHERE symbol = 'RELIANCE' AND event_type = 'OI_SHIFT' ORDER BY id DESC LIMIT 1"
        ).fetchall()
        assert len(log_rows) >= 1
        assert "+13.5%" in log_rows[0]["headline"]
    finally:
        conn.close()


def test_drip_hook_finbert_news():
    """Verify that a high-impact (>90% confidence) FinBERT headline dispatches a flash update."""
    conn = get_db_connection()
    try:
        stage_tracker_signal(
            symbol="RELIANCE",
            projected_date=(date.today() + timedelta(days=12)).isoformat(),
            projected_entry_min=2700.0,
            projected_entry_max=2740.0,
            stop_loss=2620.0,
            target1=2900.0,
            target2=3050.0,
            send_induction_notice=False,
            conn=conn
        )

        headlines = [{
            "symbol": "RELIANCE",
            "title": "Reliance Industries signs mega renewable energy partnership with global institutional sovereign fund",
            "source": "Bloomberg India",
            "raw_score": 0.88,
            "finbert_prob_bullish": 0.94,  # > 90% confidence
            "url": "https://example.com/ril-news"
        }]

        dispatched = handle_finbert_news_drip(headlines, conn=conn)
        assert len(dispatched) >= 1
        assert dispatched[0]["symbol"] == "RELIANCE"
        assert dispatched[0]["event_type"] == "NEWS_ALERT"

        log_row = conn.execute(
            "SELECT * FROM tracker_events_log WHERE symbol = 'RELIANCE' AND event_type = 'NEWS_ALERT' ORDER BY id DESC LIMIT 1"
        ).fetchone()
        assert log_row is not None
        assert "mega renewable energy" in log_row["headline"]
    finally:
        conn.close()


def test_checkpoint_evaluation_gates():
    """Verify that evaluate_tracker_checkpoints correctly computes all 4 gates."""
    eval_res = evaluate_tracker_checkpoints("RELIANCE")

    assert eval_res["symbol"] == "RELIANCE"
    assert "gates" in eval_res
    gates = eval_res["gates"]

    # Gate 1: Price elasticity
    assert "gate1_price_elasticity" in gates
    assert isinstance(gates["gate1_price_elasticity"]["passed"], bool)

    # Gate 2: Delivery absorption
    assert "gate2_delivery_absorption" in gates
    assert isinstance(gates["gate2_delivery_absorption"]["passed"], bool)

    # Gate 3: Microstructure rejection
    assert "gate3_microstructure_rejection" in gates
    assert isinstance(gates["gate3_microstructure_rejection"]["passed"], bool)

    # Gate 4: Derivatives Smart Money
    assert "gate4_derivatives_smart_money" in gates
    assert isinstance(gates["gate4_derivatives_smart_money"]["passed"], bool)

    assert 0 <= eval_res["checkpoints_passed"] <= 4
    assert eval_res["status"] in ("STAGED_TRACKER", "VERIFICATION_PENDING", "CONFIRMED_TRIGGER", "INVALIDATED")


def test_execution_green_light_transition():
    """Verify that a staged signal transitions to CONFIRMED_TRIGGER when verification gates pass."""
    conn = get_db_connection()
    try:
        # Get latest price of RELIANCE
        latest_px = conn.execute("SELECT close FROM daily_prices WHERE symbol = 'RELIANCE' ORDER BY trade_date DESC LIMIT 1").fetchone()
        cur_price = float(latest_px["close"]) if latest_px else 2700.0

        today_str = date.today().isoformat()
        # Stage setup where current price sits precisely at projected entry
        sig = stage_tracker_signal(
            symbol="RELIANCE",
            projected_date=today_str,
            projected_entry_min=round(cur_price * 0.998, 2),
            projected_entry_max=round(cur_price * 1.002, 2),
            stop_loss=round(cur_price * 0.950, 2),
            target1=round(cur_price * 1.060, 2),
            target2=round(cur_price * 1.120, 2),
            rr_ratio=2.5,
            send_induction_notice=False,
            conn=conn
        )
        sig_id = sig["id"]

        # Run advancement coordinator
        results = advance_tracked_signals(as_of_date=date.today(), conn=conn)
        assert len(results) > 0

        # Verify state in database
        updated_sig = conn.execute("SELECT * FROM forward_signals WHERE id = ?", (sig_id,)).fetchone()
        assert updated_sig["status"] in ("CONFIRMED_TRIGGER", "VERIFICATION_PENDING")
        assert updated_sig["checkpoints_passed"] >= 2
    finally:
        conn.close()


def test_invalidation_noise_pruning():
    """Verify that a staged setup transitions to INVALIDATED if price breaches Stop Loss without absorption."""
    conn = get_db_connection()
    try:
        # Get current price
        latest_px = conn.execute("SELECT close FROM daily_prices WHERE symbol = 'RELIANCE' ORDER BY trade_date DESC LIMIT 1").fetchone()
        cur_price = float(latest_px["close"]) if latest_px else 2700.0

        # Stage setup with a Stop Loss set ABOVE current price (simulating breakdown)
        stop_loss_above = round(cur_price * 1.05, 2)
        today_str = date.today().isoformat()

        sig = stage_tracker_signal(
            symbol="RELIANCE",
            projected_date=today_str,
            projected_entry_min=round(cur_price * 1.08, 2),
            projected_entry_max=round(cur_price * 1.10, 2),
            stop_loss=stop_loss_above,
            target1=round(cur_price * 1.20, 2),
            target2=round(cur_price * 1.30, 2),
            send_induction_notice=False,
            conn=conn
        )
        sig_id = sig["id"]

        # Direct evaluation of checkpoints
        eval_res = evaluate_tracker_checkpoints("RELIANCE", as_of_date=date.today(), conn=conn)
        # Verify status is INVALIDATED
        assert eval_res["status"] == "INVALIDATED"
        assert eval_res["action"] == "INVALIDATE"
        assert "breached Stop Loss" in eval_res["invalidation_reason"]

        # Run advancement coordinator and verify state transition in database
        advance_tracked_signals(as_of_date=date.today(), conn=conn)
        row = conn.execute("SELECT status FROM forward_signals WHERE id = ?", (sig_id,)).fetchone()
        assert row["status"] == "INVALIDATED"
    finally:
        conn.close()


def test_notifier_templates_and_dispatch():
    """Verify that all 4 alert dispatcher functions construct and dispatch formatted templates."""
    dummy_signal = {
        "id": 999,
        "symbol": "RELIANCE",
        "projected_date": "2026-11-15",
        "projected_entry_min": 2700.0,
        "projected_entry_max": 2740.0,
        "entry": 2720.0,
        "stop_loss": 2620.0,
        "target1": 2920.0,
        "target2": 3100.0,
        "rr_ratio": 2.0,
        "confidence": 82
    }

    # 1. Tracker staged induction alert
    res1 = send_tracker_staged_alert("RELIANCE", dummy_signal, dossier_html="<html><body>Dossier</body></html>")
    assert res1["ok"] is True
    assert "TRACKER INDUCTION" in res1["subject"]
    assert "RELIANCE" in res1["wa_text"]

    # 2. Drip event alert
    res2 = send_drip_event_alert("RELIANCE", "BULK_DEAL", {
        "deal_type": "BUY", "quantity": 100000, "price": 2715.0, "client_name": "Test Inst"
    })
    assert res2["ok"] is True
    assert "EVENT DRIP" in res2["subject"]

    # 3. Execution Green Light alert
    gates_detail = {
        "gate1_price_elasticity": {"passed": True, "detail": "Price in support zone"},
        "gate2_delivery_absorption": {"passed": True, "detail": "Delivery 58%"},
        "gate3_microstructure_rejection": {"passed": True, "detail": "Shadow 0.52"},
        "gate4_derivatives_smart_money": {"passed": True, "detail": "Put writing active"}
    }
    res3 = send_execution_trigger_alert("RELIANCE", dummy_signal, gates_detail)
    assert res3["ok"] is True
    assert "EXECUTION GREEN LIGHT" in res3["subject"]
    assert "4/4" in res3["subject"] or "Passed" in res3["subject"]

    # 4. Invalidation alert
    res4 = send_invalidation_alert("RELIANCE", dummy_signal, "Stop Loss breached without absorption")
    assert res4["ok"] is True
    assert "TRADE INVALIDATION" in res4["subject"]
    assert "Capital preserved" in res4["wa_text"]


def test_sqlite_wal_concurrency():
    """Verify that multiple simultaneous SQLite connections operate under WAL mode without locks."""
    conn1 = get_db_connection()
    conn2 = get_db_connection()
    try:
        # Reader on conn1
        r1 = conn1.execute("SELECT COUNT(*) FROM forward_signals").fetchone()[0]

        # Writer on conn2
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn2.execute("""
            INSERT INTO tracker_events_log (signal_id, symbol, event_type, headline, payload_json, dispatched_at)
            VALUES (0, 'TEST_CONCURRENCY', 'TEST', 'WAL Concurrency Test', '{}', ?)
        """, (now_str,))
        conn2.commit()

        # Reader on conn1 immediately reads new data
        r2 = conn1.execute("SELECT COUNT(*) FROM tracker_events_log WHERE symbol = 'TEST_CONCURRENCY'").fetchone()[0]
        assert r2 >= 1

        # Clean up test event
        conn2.execute("DELETE FROM tracker_events_log WHERE symbol = 'TEST_CONCURRENCY'")
        conn2.commit()
    finally:
        conn1.close()
        conn2.close()


def test_tracker_deduplication_and_in_place_update():
    """Verify that calling stage_tracker_signal with allow_duplicate=False updates active setup in place."""
    target_dt1 = (date.today() + timedelta(days=7)).isoformat()
    target_dt2 = (date.today() + timedelta(days=12)).isoformat()

    sig1 = stage_tracker_signal(
        symbol="TCS",
        projected_date=target_dt1,
        projected_entry_min=2400.0,
        projected_entry_max=2450.0,
        stop_loss=2350.0,
        target1=2550.0,
        target2=2650.0,
        send_induction_notice=False,
        allow_duplicate=False
    )
    initial_id = sig1["id"]

    # Re-stage with updated parameters
    sig2 = stage_tracker_signal(
        symbol="TCS",
        projected_date=target_dt2,
        projected_entry_min=2420.0,
        projected_entry_max=2460.0,
        stop_loss=2370.0,
        target1=2580.0,
        target2=2680.0,
        send_induction_notice=False,
        allow_duplicate=False
    )
    assert sig2["id"] == initial_id
    assert sig2["is_update"] is True
    assert sig2["projected_date"] == target_dt2
    assert sig2["stop_loss"] == 2370.0

    conn = get_db_connection()
    try:
        active_count = conn.execute(
            "SELECT COUNT(*) FROM forward_signals WHERE symbol = 'TCS' AND status IN ('STAGED_TRACKER', 'VERIFICATION_PENDING')"
        ).fetchone()[0]
        assert active_count == 1, f"Expected exactly 1 active record for TCS, found {active_count}"
    finally:
        conn.close()


def test_autonomous_radar_scan_multi_symbol():
    """Verify autonomous radar scan ranks and stages diverse symbols across sectors."""
    res = run_autonomous_radar_scan(
        symbols=["TCS", "INFY", "ICICIBANK", "SBIN"],
        min_confluence=70,
        max_stage_count=3,
        target_days_ahead=10,
        send_notifications=False
    )
    assert res["symbols_scanned"] == 4
    assert res["candidates_found"] >= 1
    assert 1 <= res["staged_count"] <= 3
    assert len(res["staged_signals"]) == res["staged_count"]

    # Verify staged symbols are unique
    staged_syms = [s["symbol"] for s in res["staged_signals"]]
    assert len(staged_syms) == len(set(staged_syms))
    for s in res["staged_signals"]:
        assert s["confluence_score"] >= 70
        assert s["rr_ratio"] > 0
        assert s["status"] == "STAGED_TRACKER"


def test_sync_and_dispatch_tracker_desk():
    """Verify production orchestrator audits active trackers, executes radar, and transitions gates."""
    res = sync_and_dispatch_tracker_desk(
        min_confluence=70,
        max_stage_count=2,
        send_notifications=False,
        run_scan=False
    )
    assert res["status"] == "SUCCESS"
    assert "active_trackers_count" in res
    assert "pending_dossiers_sent" in res
    assert "gate_transitions" in res
    assert isinstance(res["gate_transitions"], list)


