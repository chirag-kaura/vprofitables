import urllib.request

url = "http://localhost:5050/"
with urllib.request.urlopen(url) as resp:
    html = resp.read().decode("utf-8")
    print(f"HTML length: {len(html):,} bytes")
    print("Check 1 - Form prevent navigation:", "handleAuthSubmit(event); return false;" in html)
    print("Check 2 - Google button text:", "CONTINUE WITH GOOGLE" in html)
    print("Check 3 - Google container display block:", 'id="google-signin-mock-container" style="display:block;' in html)
    print("Check 4 - 1-Click admin button:", "1-CLICK INSTANT ADMIN LOGIN" in html)
    print("Check 5 - Create Account tab:", "CREATE ACCOUNT" in html)
