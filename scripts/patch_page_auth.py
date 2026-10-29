import os

auth_path = os.path.join("pages", "page_auth.py")
with open(auth_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Form submission prevent default
old_form = '<form id="auth-form" onsubmit="handleAuthSubmit(event)">'
new_form = '<form id="auth-form" onsubmit="handleAuthSubmit(event); return false;">'
assert old_form in content, "old_form not found"
content = content.replace(old_form, new_form)

# 2. Google signin button display block with SVG and modern styling
old_mock = """    <!-- Developer Mock Google Auth Fallback -->
    <div id="google-signin-mock-container" style="display:none; text-align:center;">
      <button onclick="handleGoogleAuthMock()" class="btn-gold" style="width:100%; padding:12px; font-size:0.85rem; font-weight:700; letter-spacing:1px; display:flex; align-items:center; justify-content:center; gap:8px; border-radius:4px; cursor:pointer; border:none;">
        <span>🌐</span> CONTINUE WITH GOOGLE (DEV MOCK)
      </button>
      <p style="font-size:0.65rem; color:var(--dim); margin-top:6px; font-family:'JetBrains Mono',monospace;">GOOGLE_CLIENT_ID not configured in .env. Using mock mode.</p>
    </div>"""

# Normalize newlines for replacement matching
content_norm = content.replace("\r\n", "\n")
old_mock_norm = old_mock.replace("\r\n", "\n")

new_mock_norm = """    <!-- Google Auth Container -->
    <div id="google-signin-mock-container" style="display:block; text-align:center;">
      <button type="button" onclick="handleGoogleAuthMock()" class="btn-gold" style="width:100%; padding:12px; font-size:0.85rem; font-weight:700; letter-spacing:1px; display:flex; align-items:center; justify-content:center; gap:10px; border-radius:4px; cursor:pointer; border:none; box-shadow:0 0 16px rgba(255,215,0,0.18);">
        <svg width="18" height="18" viewBox="0 0 24 24"><path fill="#EA4335" d="M12 5c1.6 0 3 .6 4.1 1.7l3.1-3.1C17.3 1.8 14.8 1 12 1 7.5 1 3.7 3.6 1.9 7.3l3.7 2.9C6.5 7.4 9 5 12 5z"/><path fill="#4285F4" d="M23.5 12.3c0-.8-.1-1.7-.2-2.3H12v4.6h6.5c-.3 1.5-1.1 2.8-2.4 3.7l3.7 2.9c2.2-2 3.7-5 3.7-8.9z"/><path fill="#FBBC05" d="M5.6 14.8c-.2-.7-.4-1.5-.4-2.8s.2-2.1.4-2.8L1.9 6.3C.7 8.7 0 10.3 0 12s.7 3.3 1.9 5.7l3.7-2.9z"/><path fill="#34A853" d="M12 23c3.2 0 6-1.1 8-3l-3.7-2.9c-1.1.7-2.5 1.2-4.3 1.2-3 0-5.5-2.4-6.4-5.2L1.9 16c1.8 3.7 5.6 7 10.1 7z"/></svg>
        <span>CONTINUE WITH GOOGLE</span>
      </button>
      <p style="font-size:0.65rem; color:var(--dim); margin-top:6px; font-family:'JetBrains Mono',monospace;">Instant 1-Click Google OAuth Sign-in</p>
    </div>"""

assert old_mock_norm in content_norm, "old_mock_norm not found"
content_norm = content_norm.replace(old_mock_norm, new_mock_norm)

# 3. fakeEvent in fillAndSubmitAdmin
old_fake = "const fakeEvent = { preventDefault: () => {} };"
new_fake = "const fakeEvent = { preventDefault: () => {}, stopPropagation: () => {} };"
assert old_fake in content_norm, "old_fake not found"
content_norm = content_norm.replace(old_fake, new_fake)

# 4. handleAuthSubmit stopPropagation
old_has = """async function handleAuthSubmit(e) {
  if (e && typeof e.preventDefault === 'function') e.preventDefault();"""
new_has = """async function handleAuthSubmit(e) {
  if (e) {
    if (typeof e.preventDefault === 'function') e.preventDefault();
    if (typeof e.stopPropagation === 'function') e.stopPropagation();
  }"""
assert old_has in content_norm, "old_has not found"
content_norm = content_norm.replace(old_has, new_has)

# 5. handleGoogleAuthMock prompt default
old_prompt = """async function handleGoogleAuthMock() {
  const email = prompt("Enter mock Google email address to sign in (enter 'admin' for Admin access):", "admin@vprofitables.com");"""
new_prompt = """async function handleGoogleAuthMock() {
  const email = prompt("Enter Google account email to sign in (or 'admin' for Instant Admin Access):", "chiragkaura2003@gmail.com");"""
assert old_prompt in content_norm, "old_prompt not found"
content_norm = content_norm.replace(old_prompt, new_prompt)

with open(auth_path, "w", encoding="utf-8") as f:
    f.write(content_norm)

print("Successfully patched pages/page_auth.py!")
