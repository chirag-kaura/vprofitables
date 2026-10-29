# pages/page_auth.py

HTML = r"""
<div id="page-auth" class="page" style="display:flex; justify-content:center; align-items:center; min-height:100vh; padding:20px; background:var(--bg);">
  <div class="card" style="width:100%; max-width:440px; padding:36px; border-radius:8px; border:1px solid var(--border); box-shadow:0 12px 40px rgba(0,0,0,0.6); background:var(--panel);">
    
    <!-- Logo Header -->
    <div style="text-align:center; margin-bottom:28px;">
      <h1 style="font-family:Orbitron,sans-serif; font-size:2rem; font-weight:700; color:var(--white); letter-spacing:2px; margin-bottom:4px;">Vprofitables</h1>
      <p style="font-family:'JetBrains Mono',monospace; font-size:0.75rem; color:var(--dim); letter-spacing:1px;">
        STOCKS & DERIVATIVES TERMINAL <span style="color:var(--gold); font-weight:bold;">v4.0</span>
      </p>
    </div>

    <!-- Toggle Tabs -->
    <div style="display:flex; border-bottom:1px solid var(--border); margin-bottom:24px; cursor:pointer;">
      <div id="auth-tab-login" onclick="toggleAuthMode('login')" style="flex:1; text-align:center; padding:12px; font-family:'Inter',sans-serif; font-size:0.85rem; font-weight:600; color:var(--white); border-bottom:2px solid var(--cyan);">SIGN IN</div>
      <div id="auth-tab-signup" onclick="toggleAuthMode('signup')" style="flex:1; text-align:center; padding:12px; font-family:'Inter',sans-serif; font-size:0.85rem; font-weight:600; color:var(--dim);">CREATE ACCOUNT</div>
    </div>

    <!-- Error Banner -->
    <div id="auth-error" class="err" style="display:none; margin-bottom:20px; font-size:0.75rem; padding:10px 14px; border-color:var(--red);"></div>

    <!-- Form -->
    <form id="auth-form" onsubmit="handleAuthSubmit(event); return false;">
      <!-- Name Field (Signup Only) -->
      <div id="auth-name-group" style="margin-bottom:18px; display:none;">
        <label style="display:block; font-size:0.7rem; text-transform:uppercase; color:var(--text); letter-spacing:1px; margin-bottom:6px; font-weight:600;">Display Name</label>
        <input type="text" id="auth-name" placeholder="John Doe" 
          style="width:100%; padding:10px 12px; background:var(--p2); border:1px solid var(--border); border-radius:4px; color:var(--white); font-family:'Inter',sans-serif; font-size:0.85rem; outline:none; transition:border-color 0.2s;">
      </div>

      <!-- Email / User ID Field -->
      <div style="margin-bottom:18px;">
        <label id="auth-email-label" style="display:block; font-size:0.7rem; text-transform:uppercase; color:var(--text); letter-spacing:1px; margin-bottom:6px; font-weight:600;">Email Address or User ID</label>
        <input type="text" id="auth-email" required placeholder="admin or name@domain.com" autocomplete="username"
          style="width:100%; padding:10px 12px; background:var(--p2); border:1px solid var(--border); border-radius:4px; color:var(--white); font-family:'JetBrains Mono',monospace; font-size:0.85rem; outline:none; transition:border-color 0.2s;">
      </div>
      
      <!-- Password Field -->
      <div style="margin-bottom:18px;">
        <label style="display:block; font-size:0.7rem; text-transform:uppercase; color:var(--text); letter-spacing:1px; margin-bottom:6px; font-weight:600;">Password</label>
        <input type="password" id="auth-password" required placeholder="••••••••" autocomplete="current-password"
          style="width:100%; padding:10px 12px; background:var(--p2); border:1px solid var(--border); border-radius:4px; color:var(--white); font-family:'JetBrains Mono',monospace; font-size:0.85rem; outline:none; transition:border-color 0.2s;">
      </div>

      <!-- Confirm Password (Signup Only) -->
      <div id="auth-confirm-group" style="margin-bottom:24px; display:none;">
        <label style="display:block; font-size:0.7rem; text-transform:uppercase; color:var(--text); letter-spacing:1px; margin-bottom:6px; font-weight:600;">Confirm Password</label>
        <input type="password" id="auth-confirm-password" placeholder="••••••••" 
          style="width:100%; padding:10px 12px; background:var(--p2); border:1px solid var(--border); border-radius:4px; color:var(--white); font-family:'JetBrains Mono',monospace; font-size:0.85rem; outline:none; transition:border-color 0.2s;">
      </div>

      <button type="submit" id="auth-submit-btn" class="btn" style="width:100%; padding:12px; font-size:0.85rem; font-weight:700; letter-spacing:1px; margin-bottom:14px; box-shadow:0 0 15px rgba(41,98,255,0.25);">
        LOG IN
      </button>

      <!-- Instant 1-Click Admin Access Shortcut -->
      <div id="auth-admin-quick-wrap" style="margin-bottom:16px;">
        <button type="button" onclick="fillAndSubmitAdmin()" style="width:100%; padding:10px; background:rgba(179,157,219,0.12); border:1px dashed #B39DDB; border-radius:4px; color:#B39DDB; font-family:'JetBrains Mono',monospace; font-size:0.75rem; font-weight:700; cursor:pointer; display:flex; align-items:center; justify-content:center; gap:8px; transition:all 0.2s;">
          <span>🛡️</span> 1-CLICK INSTANT ADMIN LOGIN
        </button>
        <div style="text-align:center; font-family:'JetBrains Mono',monospace; font-size:0.65rem; color:var(--dim); margin-top:6px;">
          Root Admin: <span style="color:var(--white); font-weight:bold;">admin</span> &nbsp;|&nbsp; Password: <span style="color:var(--white); font-weight:bold;">admin123</span>
        </div>
      </div>
    </form>

    <!-- Divider -->
    <div style="display:flex; align-items:center; margin:16px 0; color:var(--dim); font-size:0.7rem; letter-spacing:1px;">
      <span style="flex:1; height:1px; background:var(--border);"></span>
      <span style="padding:0 10px; text-transform:uppercase;">OR</span>
      <span style="flex:1; height:1px; background:var(--border);"></span>
    </div>

    <!-- Official Google Auth Container -->
    <div id="google-signin-btn" style="width:100%; display:flex; justify-content:center; margin-bottom:12px;"></div>

    <!-- Google Auth Container -->
    <div id="google-signin-mock-container" style="display:block; text-align:center;">
      <button type="button" onclick="handleGoogleAuthMock()" class="btn-gold" style="width:100%; padding:12px; font-size:0.85rem; font-weight:700; letter-spacing:1px; display:flex; align-items:center; justify-content:center; gap:10px; border-radius:4px; cursor:pointer; border:none; box-shadow:0 0 16px rgba(255,215,0,0.18);">
        <svg width="18" height="18" viewBox="0 0 24 24"><path fill="#EA4335" d="M12 5c1.6 0 3 .6 4.1 1.7l3.1-3.1C17.3 1.8 14.8 1 12 1 7.5 1 3.7 3.6 1.9 7.3l3.7 2.9C6.5 7.4 9 5 12 5z"/><path fill="#4285F4" d="M23.5 12.3c0-.8-.1-1.7-.2-2.3H12v4.6h6.5c-.3 1.5-1.1 2.8-2.4 3.7l3.7 2.9c2.2-2 3.7-5 3.7-8.9z"/><path fill="#FBBC05" d="M5.6 14.8c-.2-.7-.4-1.5-.4-2.8s.2-2.1.4-2.8L1.9 6.3C.7 8.7 0 10.3 0 12s.7 3.3 1.9 5.7l3.7-2.9z"/><path fill="#34A853" d="M12 23c3.2 0 6-1.1 8-3l-3.7-2.9c-1.1.7-2.5 1.2-4.3 1.2-3 0-5.5-2.4-6.4-5.2L1.9 16c1.8 3.7 5.6 7 10.1 7z"/></svg>
        <span>CONTINUE WITH GOOGLE</span>
      </button>
      <p style="font-size:0.65rem; color:var(--dim); margin-top:6px; font-family:'JetBrains Mono',monospace;">Instant 1-Click Google OAuth Sign-in</p>
    </div>

  </div>
</div>

<!-- Bulletproof Standalone Auth Fallback (immune to any external script error) -->
<script>
(function() {
  window.fillAndSubmitAdmin = window.fillAndSubmitAdmin || function() {
    var emailInp = document.getElementById('auth-email');
    var passInp = document.getElementById('auth-password');
    if (emailInp) emailInp.value = 'admin';
    if (passInp) passInp.value = 'admin123';
    window.handleAuthSubmit();
  };

  window.handleAuthSubmit = window.handleAuthSubmit || async function(e) {
    if (e && e.preventDefault) e.preventDefault();
    var email = (document.getElementById('auth-email')?.value || 'admin').trim();
    var password = document.getElementById('auth-password')?.value || 'admin123';
    var btn = document.getElementById('auth-submit-btn');
    var errDiv = document.getElementById('auth-error');
    if (btn) { btn.disabled = true; btn.textContent = 'Authenticating...'; }
    if (errDiv) errDiv.style.display = 'none';

    try {
      var res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email, password: password })
      }).then(function(r) { return r.json(); });

      if (res && res.token) {
        localStorage.setItem('token', res.token);
        localStorage.setItem('user_email', res.email || email);
        localStorage.setItem('user_role', res.role || 'ADMIN');
        
        var authEl = document.getElementById('page-auth');
        var layoutEl = document.getElementById('app-layout');
        if (authEl) authEl.style.display = 'none';
        if (layoutEl) layoutEl.style.display = 'flex';
        
        if (typeof showDashboardTerminal === 'function') {
          showDashboardTerminal();
        } else if (typeof nav === 'function') {
          nav('overview');
        } else {
          location.reload();
        }
      } else {
        throw new Error((res && res.error) || 'Invalid credentials');
      }
    } catch(err) {
      if (errDiv) {
        errDiv.textContent = err.message || 'Login failed';
        errDiv.style.display = 'block';
      }
    } finally {
      if (btn) { btn.disabled = false; btn.textContent = 'LOG IN'; }
    }
  };
})();
</script>
"""

JS = r"""
let activeAuthMode = 'login';

function toggleAuthMode(mode) {
  activeAuthMode = mode;
  const loginTab = document.getElementById('auth-tab-login');
  const signupTab = document.getElementById('auth-tab-signup');
  const submitBtn = document.getElementById('auth-submit-btn');
  const nameGroup = document.getElementById('auth-name-group');
  const confirmGroup = document.getElementById('auth-confirm-group');
  const emailLabel = document.getElementById('auth-email-label');
  const adminQuick = document.getElementById('auth-admin-quick-wrap');
  const errDiv = document.getElementById('auth-error');
  
  if (errDiv) errDiv.style.display = 'none';

  if (mode === 'login') {
    if (loginTab) { loginTab.style.color = 'var(--white)'; loginTab.style.borderBottom = '2px solid var(--cyan)'; }
    if (signupTab) { signupTab.style.color = 'var(--dim)'; signupTab.style.borderBottom = 'none'; }
    if (nameGroup) nameGroup.style.display = 'none';
    if (confirmGroup) confirmGroup.style.display = 'none';
    if (emailLabel) emailLabel.textContent = 'EMAIL ADDRESS OR USER ID';
    if (adminQuick) adminQuick.style.display = 'block';
    if (submitBtn) submitBtn.textContent = 'LOG IN';
  } else {
    if (loginTab) { loginTab.style.color = 'var(--dim)'; loginTab.style.borderBottom = 'none'; }
    if (signupTab) { signupTab.style.color = 'var(--white)'; signupTab.style.borderBottom = '2px solid var(--cyan)'; }
    if (nameGroup) nameGroup.style.display = 'block';
    if (confirmGroup) confirmGroup.style.display = 'block';
    if (emailLabel) emailLabel.textContent = 'EMAIL ADDRESS';
    if (adminQuick) adminQuick.style.display = 'none';
    if (submitBtn) submitBtn.textContent = 'CREATE ACCOUNT';
  }
}

function fillAndSubmitAdmin() {
  toggleAuthMode('login');
  const emailInp = document.getElementById('auth-email');
  const passInp = document.getElementById('auth-password');
  if (emailInp) emailInp.value = 'admin';
  if (passInp) passInp.value = 'admin123';
  const fakeEvent = { preventDefault: () => {}, stopPropagation: () => {} };
  handleAuthSubmit(fakeEvent);
}

async function initGoogleSignIn() {
  try {
    const cfg = await api('config');
    const hasClientId = cfg.google_client_id && 
                       cfg.google_client_id !== 'your-google-client-id-here.apps.googleusercontent.com' &&
                       !cfg.google_client_id.startsWith('your-');
    
    if (hasClientId) {
      document.getElementById('google-signin-mock-container').style.display = 'none';
      document.getElementById('google-signin-btn').style.display = 'flex';
      let attempts = 0;
      const interval = setInterval(() => {
        if (window.google && window.google.accounts) {
          clearInterval(interval);
          google.accounts.id.initialize({
            client_id: cfg.google_client_id,
            callback: handleGoogleCredentialResponse
          });
          google.accounts.id.renderButton(
            document.getElementById("google-signin-btn"),
            { theme: "filled_blue", size: "large", width: 368 }
          );
        }
        if (++attempts > 20) clearInterval(interval);
      }, 500);
    } else {
      document.getElementById('google-signin-btn').style.display = 'none';
      document.getElementById('google-signin-mock-container').style.display = 'block';
    }
  } catch (e) {
    console.error("Failed to load Google OAuth config, falling back to mock", e);
    document.getElementById('google-signin-btn').style.display = 'none';
    document.getElementById('google-signin-mock-container').style.display = 'block';
  }
}

async function handleGoogleCredentialResponse(response) {
  const errDiv = document.getElementById('auth-error');
  if (errDiv) errDiv.style.display = 'none';
  
  try {
    const res = await api('auth/google', { id_token: response.credential });
    if (res.token) {
      localStorage.setItem('token', res.token);
      localStorage.setItem('user_email', res.email);
      localStorage.setItem('user_role', res.role || 'USER');
      
      if ((res.role || '').toUpperCase() === 'ADMIN') {
        showDashboardTerminal();
        return;
      }

      const check = await api('onboarding/check');
      if (check.completed) {
        showDashboardTerminal();
      } else {
        showOnboardingTerminal();
      }
    } else {
      throw new Error(res.error || 'Google authentication failed');
    }
  } catch (err) {
    if (errDiv) {
      errDiv.textContent = err.message || 'Verification of Google account failed';
      errDiv.style.display = 'block';
    }
  }
}

async function handleAuthSubmit(e) {
  if (e) {
    if (typeof e.preventDefault === 'function') e.preventDefault();
    if (typeof e.stopPropagation === 'function') e.stopPropagation();
  }
  const email = (document.getElementById('auth-email').value || '').trim();
  const password = document.getElementById('auth-password').value;
  const displayName = document.getElementById('auth-name').value;
  const confirmPassword = document.getElementById('auth-confirm-password').value;
  const errDiv = document.getElementById('auth-error');
  const submitBtn = document.getElementById('auth-submit-btn');

  if (errDiv) errDiv.style.display = 'none';

  if (activeAuthMode === 'signup') {
    if (password !== confirmPassword) {
      if (errDiv) {
        errDiv.textContent = "Passwords do not match.";
        errDiv.style.display = 'block';
      }
      return;
    }
  }

  if (submitBtn) { submitBtn.disabled = true; submitBtn.textContent = 'Processing...'; }

  const endpoint = activeAuthMode === 'login' ? 'auth/login' : 'auth/signup';
  const payload = { email, password };
  if (activeAuthMode === 'signup') {
    payload.display_name = displayName;
    payload.auth_method = 'password';
  }

  try {
    const res = await api(endpoint, payload);
    if (res.token) {
      localStorage.setItem('token', res.token);
      localStorage.setItem('user_email', res.email || email);
      localStorage.setItem('user_role', res.role || 'USER');
      
      // If user is ADMIN, go straight to terminal desk without questionnaire
      if ((res.role || '').toUpperCase() === 'ADMIN') {
        showDashboardTerminal();
        return;
      }

      // Check onboarding state for regular users
      const check = await api('onboarding/check');
      if (check.completed) {
        showDashboardTerminal();
      } else {
        showOnboardingTerminal();
      }
    } else {
      throw new Error(res.error || 'Authentication failed');
    }
  } catch (err) {
    if (errDiv) {
      errDiv.textContent = err.message || 'Server connection failed';
      errDiv.style.display = 'block';
    }
  } finally {
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.textContent = activeAuthMode === 'login' ? 'LOG IN' : 'CREATE ACCOUNT';
    }
  }
}

async function handleGoogleAuthMock() {
  const email = prompt("Enter Google account email to sign in (or 'admin' for Instant Admin Access):", "chiragkaura2003@gmail.com");
  if (!email) return;

  const errDiv = document.getElementById('auth-error');
  if (errDiv) errDiv.style.display = 'none';

  try {
    const googleSub = "google_oauth_sub_" + email.split('@')[0];
    const res = await api('auth/login', { 
      email: email, 
      google_sub: googleSub,
      auth_method: 'google',
      display_name: email.split('@')[0]
    });
    
    if (res.token) {
      localStorage.setItem('token', res.token);
      localStorage.setItem('user_email', res.email || email);
      localStorage.setItem('user_role', res.role || 'USER');

      if ((res.role || '').toUpperCase() === 'ADMIN') {
        showDashboardTerminal();
        return;
      }

      const check = await api('onboarding/check');
      if (check.completed) {
        showDashboardTerminal();
      } else {
        showOnboardingTerminal();
      }
    } else {
      throw new Error(res.error || 'Google login simulation failed');
    }
  } catch (err) {
    if (errDiv) {
      errDiv.textContent = err.message || 'Google Auth simulation failed';
      errDiv.style.display = 'block';
    }
  }
}

// Initialise Google GIS button rendering
document.addEventListener('DOMContentLoaded', () => {
  // If not logged in, trigger Google Init
  const token = localStorage.getItem('token');
  if (!token) {
    setTimeout(initGoogleSignIn, 100);
  }
});

"""
