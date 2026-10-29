"""
run_daily_tracker_desk.py
=========================
Production Autonomous "Radar-to-Sniper" Trade Tracker & Equity Research Desk.
Scheduled to run automatically at 9:00 PM IST daily (and on-demand).

Lifecycle Workflow:
  1. Advance Radar Scan:
     - Scans liquid equities across sectors for high-confluence setups (Gann Sq9 + Morlet CWT + Aspects + Volume Profile).
     - Ranks setups by confluence (>= 70) and stages into Tracker Bucket with in-place deduplication.
  2. Induction Notice & Dossier Verification:
     - Audits all active tracked symbols (STAGED_TRACKER / VERIFICATION_PENDING).
     - Checks if Bespoke Equity Research Dossier has been sent. If not sent, generates dossier & sends email notice.
  3. 4-Checkpoint Verification Gate Evaluation:
     - Evaluates Gate 1 (Price Elasticity to Gann level), Gate 2 (Delivery Absorption),
       Gate 3 (Microstructure Rejection Wick), Gate 4 (Smart Money Options OI / FII bias).
     - State transitions:
       - CONFIRMED_TRIGGER: Dispatches "Execution Green Light" Alert.
       - INVALIDATED: Dispatches "Trade Invalidation / Noise Pruning" Notice.
  4. Event-Driven Drip Auditor:
     - Audits recent bulk deals, delivery spikes, participant OI shifts, and news sentiment for tracked symbols.
     - Dispatches flash drip alerts for any unnotified events.
  5. Structured Audit Logging:
     - Outputs execution metrics to stdout and logs/tracker_desk.log.
"""

import os
import sys
import time
import json
import logging
import argparse
from datetime import date, datetime

# Force UTF-8 encoding on Windows console streams to prevent charmap crashes
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Setup logging directory and file handler
LOGS_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOGS_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOGS_DIR, "tracker_desk.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("TrackerDesk")


def parse_arguments():
    parser = argparse.ArgumentParser(description="Autonomous Radar-to-Sniper Trade Tracker Desk Orchestrator")
    parser.add_argument("--quick-check", action="store_true", help="Quick audit: check pending dossiers and verification gates without full universe scan")
    parser.add_argument("--scan-only", action="store_true", help="Only scan liquid universe and stage top candidates")
    parser.add_argument("--verify-only", action="store_true", help="Only evaluate 4-checkpoint gates and transitions")
    parser.add_argument("--force-dossier", action="store_true", help="Force regenerate and resend dossiers even if already sent")
    parser.add_argument("--no-notify", action="store_true", help="Disable email and WhatsApp notifications (dry run)")
    parser.add_argument("--min-confluence", type=int, default=70, help="Minimum confluence score for staging (default: 70)")
    parser.add_argument("--max-stage", type=int, default=5, help="Maximum setups to stage in one run (default: 5)")
    parser.add_argument("--date", type=str, default=None, help="Evaluation as-of date (YYYY-MM-DD, default: today)")
    return parser.parse_args()


def main():
    args = parse_arguments()
    start_time = time.time()

    print("\n" + "=" * 65)
    print("  AUTONOMOUS 'RADAR-TO-SNIPER' TRADE TRACKER & RESEARCH DESK")
    print("  Institutional Confluence & 4-Checkpoint Verification Gate")
    print("=" * 65)
    print(f"  Execution Time   : {datetime.now().strftime('%Y-%m-%d %H:%M:%S IST')}")
    print(f"  Mode             : {'QUICK AUDIT' if args.quick_check else 'FULL 9:00 PM ORCHESTRATION'}")
    print(f"  Notifications    : {'DISABLED (Dry Run)' if args.no_notify else 'ACTIVE (Email + WhatsApp)'}")
    print(f"  Min Confluence   : {args.min_confluence}")
    print(f"  Max Stage Limit  : {args.max_stage}")
    print("=" * 65 + "\n")

    from core.tracker import (
        init_tracker_tables,
        sync_and_dispatch_tracker_desk,
        run_autonomous_radar_scan,
        advance_tracked_signals,
        get_active_trackers
    )

    init_tracker_tables()

    send_notifications = not args.no_notify
    as_of = args.date or date.today().isoformat()

    try:
        if args.scan_only:
            logger.info("[RADAR] Running Advance Radar Scan across liquid equities...")
            scan_res = run_autonomous_radar_scan(
                min_confluence=args.min_confluence,
                max_stage_count=args.max_stage,
                send_notifications=send_notifications,
            )
            print(f"\n  [OK] Advance Scan Complete: {scan_res['staged_count']} candidates staged.")
            for s in scan_res.get("staged_signals", []):
                print(f"       -> {s['symbol']}: Confluence={s['confluence_score']} | Zone={s['entry_zone']} | SL={s['stop_loss']} | T1={s['target1']}")

        elif args.verify_only:
            logger.info("[VERIFY] Evaluating 4-Checkpoint Verification Gates on active tracked setups...")
            transitions = advance_tracked_signals(as_of_date=as_of)
            print(f"\n  [OK] Verification Gates Complete: {len(transitions)} signals evaluated.")
            for t in transitions:
                print(f"       -> {t['symbol']}: Status={t['new_status']} | Gates Passed={t['checkpoints_passed']}/4 | Action={t['action']}")

        elif args.quick_check:
            logger.info("[QUICK-CHECK] Auditing pending dossiers and 4-checkpoint gates...")
            desk_res = sync_and_dispatch_tracker_desk(
                min_confluence=args.min_confluence,
                max_stage_count=args.max_stage,
                send_notifications=send_notifications,
                force_resend_dossiers=args.force_dossier,
                run_scan=False,
                as_of_date=as_of
            )
            print("\n  [OK] Quick Audit Complete:")
            print(f"       Active Tracked Symbols : {desk_res.get('active_trackers_count', 0)}")
            print(f"       Pending Dossiers Sent  : {desk_res.get('pending_dossiers_sent', 0)}")
            print(f"       Gate State Transitions : {desk_res.get('transition_count', 0)}")
            for t in desk_res.get("gate_transitions", []):
                print(f"         * {t['symbol']} -> {t['new_status']} ({t['checkpoints_passed']}/4 gates)")

        else:
            # Full 9:00 PM Orchestration Workflow
            logger.info("[DESK] Executing Full 9:00 PM Tracker Desk Orchestration Pipeline...")
            desk_res = sync_and_dispatch_tracker_desk(
                min_confluence=args.min_confluence,
                max_stage_count=args.max_stage,
                send_notifications=send_notifications,
                force_resend_dossiers=args.force_dossier,
                run_scan=True,
                as_of_date=as_of
            )

            radar = desk_res.get("radar_scan", {})
            staged = radar.get("staged_signals", [])

            print("\n" + "-" * 65)
            print("  DESK ORCHESTRATION SUMMARY")
            print("-" * 65)
            print(f"  Equities Scanned       : {radar.get('symbols_scanned', 0)}")
            print(f"  Candidates Found       : {radar.get('candidates_found', 0)}")
            print(f"  Tracked Bucket Staged  : {len(staged)}")
            for s in staged:
                print(f"    * {s['symbol']:<10} | Confluence: {s['confluence_score']}/100 | Zone: Rs.{s['entry_zone'][0]:,.2f} - Rs.{s['entry_zone'][1]:,.2f} | R:R {s['rr_ratio']}:1 | Update: {s['is_update']}")

            print(f"\n  Active Trackers Count  : {desk_res.get('active_trackers_count', 0)}")
            print(f"  Pending Dossiers Sent  : {desk_res.get('pending_dossiers_sent', 0)}")
            for d in desk_res.get("dossiers_dispatched", []):
                print(f"    * Dossier Delivered  : {d['symbol']} (Signal ID #{d['id']})")

            transitions = desk_res.get("gate_transitions", [])
            print(f"  Verification Transitions : {len(transitions)}")
            for t in transitions:
                status_icon = "[TRIGGER]" if t["new_status"] == "CONFIRMED_TRIGGER" else "[INVALIDATED]" if t["new_status"] == "INVALIDATED" else "[MONITOR]"
                print(f"    * {status_icon:<13} {t['symbol']:<10} | {t['old_status']} -> {t['new_status']} | Gates: {t['checkpoints_passed']}/4 passed | Action: {t['action']}")
            print("-" * 65)

        elapsed = round(time.time() - start_time, 2)
        print(f"\n[DONE] Autonomous Tracker Desk successfully finished in {elapsed}s.")
        print(f"       Log written to {LOG_FILE}\n")

    except Exception as e:
        logger.exception(f"Unhandled error in Tracker Desk execution: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
