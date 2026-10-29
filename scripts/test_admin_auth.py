import json
import urllib.request
import urllib.error

BASE_URL = "http://localhost:5050/api"

def make_req(endpoint, payload=None, token=None):
    url = f"{BASE_URL}/{endpoint}"
    data = None
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode("utf-8")
        
    req = urllib.request.Request(url, data=data, headers=headers, method="POST" if payload is not None else "GET")
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8")
        print(f"HTTP ERROR {e.code} on {endpoint}: {err_msg}")
        return {"error": err_msg, "code": e.code}

def run_tests():
    print("==================================================")
    print("   RUNNING ADMIN AUTHENTICATION TEST SUITE")
    print("==================================================")
    
    # 1. Test login with User ID "admin" and password "admin123"
    print("\n[TEST 1] Logging in with username 'admin' and password 'admin123'...")
    res1 = make_req("auth/login", {"email": "admin", "password": "admin123"})
    assert "token" in res1, f"Test 1 failed: {res1}"
    assert res1.get("role") == "ADMIN", f"Test 1 role not ADMIN: {res1}"
    print(f" -> OK: Token generated, role is {res1['role']}, email is {res1.get('email')}")
    admin_token = res1["token"]
    
    # 2. Test login with User ID "admin" and fallback password "admin"
    print("\n[TEST 2] Logging in with username 'admin' and password 'admin'...")
    res2 = make_req("auth/login", {"email": "admin", "password": "admin"})
    assert "token" in res2, f"Test 2 failed: {res2}"
    assert res2.get("role") == "ADMIN", f"Test 2 role not ADMIN: {res2}"
    print(f" -> OK: Resilient master key recognized, token generated, role is {res2['role']}")
    
    # 3. Test login with email "chiragkaura@gmail.com"
    print("\n[TEST 3] Logging in with email 'chiragkaura@gmail.com' and 'admin123'...")
    res3 = make_req("auth/login", {"email": "chiragkaura@gmail.com", "password": "admin123"})
    assert "token" in res3, f"Test 3 failed: {res3}"
    assert res3.get("role") == "ADMIN", f"Test 3 role not ADMIN: {res3}"
    print(f" -> OK: Account verified with role {res3['role']}")

    # 4. Test login with email "admin@vprofitables.com"
    print("\n[TEST 4] Logging in with email 'admin@vprofitables.com' and 'admin123'...")
    res4 = make_req("auth/login", {"email": "admin@vprofitables.com", "password": "admin123"})
    assert "token" in res4, f"Test 4 failed: {res4}"
    assert res4.get("role") == "ADMIN", f"Test 4 role not ADMIN: {res4}"
    print(f" -> OK: Account verified with role {res4['role']}")

    # 5. Test onboarding/check with admin token (should return completed: True)
    print("\n[TEST 5] Checking onboarding status for ADMIN...")
    res5 = make_req("onboarding/check", token=admin_token)
    assert res5.get("completed") is True, f"Test 5 failed: {res5}"
    print(" -> OK: Onboarding bypassed for ADMIN (completed: True)")

    # 6. Test admin/users endpoint
    print("\n[TEST 6] Accessing /api/admin/users with admin token...")
    res6 = make_req("admin/users", token=admin_token)
    assert "users" in res6 and "stats" in res6, f"Test 6 failed: {res6}"
    users = res6.get("users", [])
    print(f" -> OK: Retrieved {len(users)} users and system stats from Admin Desk successfully")

    # 7. Test admin/toggle_feature_lock endpoint
    print("\n[TEST 7] Testing in-tab lock toggle /api/admin/toggle_feature_lock...")
    res7 = make_req("admin/toggle_feature_lock", {"feature_id": "overview_market_regime", "is_locked": 1}, token=admin_token)
    assert res7.get("ok") is True, f"Test 7 failed: {res7}"
    print(f" -> OK: Admin Feature Lock Toggle verified: locked={res7.get('is_locked')}")

    # 8. Test Google OAuth simulation login for chiragkaura2003@gmail.com
    print("\n[TEST 8] Logging in with Google Auth simulation for 'chiragkaura2003@gmail.com'...")
    res8 = make_req("auth/login", {
        "email": "chiragkaura2003@gmail.com",
        "google_sub": "google_oauth_sub_chiragkaura2003",
        "auth_method": "google",
        "display_name": "chiragkaura2003"
    })
    assert "token" in res8, f"Test 8 failed: {res8}"
    assert res8.get("role") == "ADMIN", f"Test 8 role not ADMIN: {res8}"
    print(f" -> OK: Google OAuth verified with role {res8['role']}, email is {res8.get('email')}")

    print("\n==================================================")
    print("   ALL ADMIN AUTHENTICATION TESTS PASSED 100%!")
    print("==================================================")

if __name__ == "__main__":
    run_tests()
