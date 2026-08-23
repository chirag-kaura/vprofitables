# tests/test_personalization.py
import subprocess
import time
import urllib.request
import json
import os
import sys

PORT = 8080
BASE_URL = f"http://localhost:{PORT}/api"

def make_request(endpoint, method="GET", payload=None, token=None):
    url = f"{BASE_URL}/{endpoint}"
    req_data = None
    headers = {}
    
    if token:
        headers["Authorization"] = f"Bearer {token}"
        
    if method == "POST":
        headers["Content-Type"] = "application/json"
        req_data = json.dumps(payload).encode('utf-8')
    elif payload:
        # GET query params
        from urllib.parse import urlencode
        url = f"{url}?{urlencode(payload)}"
        
    req = urllib.request.Request(url, data=req_data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as res:
            body = res.read().decode('utf-8')
            return json.loads(body)
    except urllib.error.HTTPError as e:
        print(f"HTTP ERROR {e.code}: {e.read().decode('utf-8')}")
        raise e

def run_tests():
    print("[TEST] Launching server app.py...")
    # Change env port to PORT
    my_env = os.environ.copy()
    my_env["GANN_PORT"] = str(PORT)
    server_process = subprocess.Popen(["python", "app.py"], env=my_env)
    
    # Wait for caching/booting
    time.sleep(8)
    
    try:
        # Step 1: Sign up
        print("\n[TEST] 1. Creating user...")
        email = f"tester_{int(time.time())}@domain.com"
        signup_res = make_request("auth/signup", method="POST", payload={
            "email": email,
            "password": "secure_password_123"
        })
        assert "token" in signup_res, "Signup failed: no token returned"
        token = signup_res["token"]
        print(f"Token acquired for {email}.")
        
        # Step 2: Log in
        print("\n[TEST] 2. Logging in...")
        login_res = make_request("auth/login", method="POST", payload={
            "email": email,
            "password": "secure_password_123"
        })
        assert "token" in login_res, "Login failed"
        assert len(login_res["token"]) > 10, "Invalid login token returned"
        print("Login verified.")

        # Step 3: Check onboarding (expect False)
        print("\n[TEST] 3. Checking onboarding status (expect False)...")
        check_res = make_request("onboarding/check", token=token)
        assert check_res["completed"] is False, "Onboarding should be incomplete"
        print("Status is incomplete as expected.")

        # Step 4: Submit onboarding profile
        print("\n[TEST] 4. Submitting onboarding profile...")
        onb_payload = {
            "primary_goal": "growth",
            "horizon_weights": json.dumps({"swing": 30, "short": 40, "long": 30}),
            "drawdown_reaction": "sell_some",
            "experience_level": "some",
            "starting_capital": 100000.0,
            "excluded_sectors": json.dumps(["IT"]),
            "max_position_pct": 15.0,
            "max_sector_pct": 30.0,
            "onboarding_version": 1
        }
        submit_res = make_request("onboarding/submit", method="POST", payload=onb_payload, token=token)
        assert submit_res.get("ok") is True, "Onboarding submission failed"
        print("Onboarding profile saved.")

        # Step 5: Check onboarding again (expect True)
        print("\n[TEST] 5. Checking onboarding status (expect True)...")
        check_res2 = make_request("onboarding/check", token=token)
        assert check_res2["completed"] is True, "Onboarding should be complete now"
        print("Status is complete.")

        # Step 6: Test portfolio scoping
        print("\n[TEST] 6. Testing user-scoped portfolio operations...")
        
        # Add Trade
        print("Adding position...")
        add_res = make_request("portfolio_add", method="GET", payload={
            "symbol": "WIPRO",
            "inv_type": "swing",
            "entry_price": 400.0,
            "shares": 10,
            "stop_loss": 380.0,
            "target1": 420.0,
            "target2": 440.0
        }, token=token)
        assert add_res.get("ok") is True, "portfolio_add failed"
        
        # Get Trade
        get_res = make_request("portfolio_get", token=token)
        assert get_res.get("ok") is True, "portfolio_get failed"
        trades = get_res["trades"]
        assert len(trades) == 1, f"Expected 1 position, got {len(trades)}"
        trade = trades[0]
        trade_id = trade["id"]
        assert trade["symbol"] == "WIPRO", "Symbol mismatch"
        print("Position successfully added and retrieved.")

        # Modify Trade
        print("Modifying position...")
        mod_res = make_request("portfolio_modify", method="GET", payload={
            "id": trade_id,
            "stop_loss": 390.0,
            "target1": 425.0,
            "target2": 445.0
        }, token=token)
        assert mod_res.get("ok") is True, "portfolio_modify failed"
        
        # Verify Modify
        get_res = make_request("portfolio_get", token=token)
        modified_trade = get_res["trades"][0]
        assert modified_trade["stop_loss"] == 390.0, "Modify SL failed"
        print("Position modified successfully.")

        # Partial Exit
        print("Partial exiting position (5 shares)...")
        part_res = make_request("portfolio_partial_exit", method="GET", payload={
            "id": trade_id,
            "shares": 5,
            "exit_price": 410.0
        }, token=token)
        assert part_res.get("ok") is True, "portfolio_partial_exit failed"
        assert part_res["remaining_shares"] == 5, "Remaining shares count mismatch"
        print("Partial exit succeeded.")

        # Close position
        print("Closing remaining position...")
        close_res = make_request("portfolio_close", method="GET", payload={
            "id": trade_id,
            "exit_price": 415.0
        }, token=token)
        assert close_res.get("ok") is True, "portfolio_close failed"
        print("Position closed successfully.")

        # Step 7: Recommendations and Risk Audits
        print("\n[TEST] 7. Testing recommendations constraints & risk audits...")
        
        # Fetch recommendations
        rec_res = make_request("recommendations", token=token)
        assert rec_res.get("ok") is True, "recommendations failed"
        recs = rec_res["recommendations"]
        print(f"Generated {len(recs)} recommendation(s) for user.")
        
        # Test sector exclusions: confirm that no IT stock is recommended
        for r in recs:
            sym = r.get("symbol")
            if sym == "WIPRO":
                # WIPRO is IT, should be excluded
                raise AssertionError("WIPRO recommended despite IT sector exclusion!")
        print("Sector exclusion verified (no IT sector stock recommended).")

        # Save settings with Kill Switch active
        print("Activating Kill Switch...")
        save_settings_res = make_request("risk_settings_save", method="GET", payload={
            "capital": 100000.0,
            "max_risk_pct": 2.0,
            "max_positions": 5,
            "daily_loss_limit": 50000.0,
            "max_sector_pct": 30.0,
            "max_position_pct": 15.0,
            "max_correlation_exposure": 0.7,
            "kill_switch": 1
        }, token=token)
        assert save_settings_res.get("ok") is True, "risk_settings_save failed"
        
        # Fetch recommendations again
        rec_res2 = make_request("recommendations", token=token)
        assert rec_res2.get("ok") is True, "recommendations failed"
        assert len(rec_res2["recommendations"]) == 0, "Recommendations should be empty when Kill Switch is active"
        assert rec_res2.get("blocked") is True, "Should return blocked status"
        print("Kill Switch blocker verified.")

        # Deactivate Kill Switch
        print("Deactivating Kill Switch...")
        make_request("risk_settings_save", method="GET", payload={
            "capital": 100000.0,
            "max_risk_pct": 2.0,
            "max_positions": 5,
            "daily_loss_limit": 50000.0,
            "max_sector_pct": 30.0,
            "max_position_pct": 15.0,
            "max_correlation_exposure": 0.7,
            "kill_switch": 0
        }, token=token)

        # Step 8: Feedback Capture
        print("\n[TEST] 8. Testing recommendation feedback...")
        rec_res3 = make_request("recommendations", token=token)
        if rec_res3["recommendations"]:
            rec_item = rec_res3["recommendations"][0]
            rec_id = rec_item["recommendation_id"]
            
            feedback_res = make_request("recommendations/feedback", method="POST", payload={
                "recommendation_id": rec_id,
                "action": "accepted"
            }, token=token)
            assert feedback_res.get("ok") is True, "recommendations/feedback failed"
            print("Feedback capture verified.")
        else:
            print("Skipping feedback test (no recommendations returned).")
            
        print("\n=== ALL INTEGRATION TESTS PASSED SUCCESSFULLY! ===")
        
    finally:
        print("\n[TEST] Terminating server...")
        server_process.terminate()
        server_process.wait()

if __name__ == "__main__":
    run_tests()
