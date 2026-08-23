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
    <form id="auth-form" onsubmit="handleAuthSubmit(event)">
      <!-- Name Field (Signup Only) -->
      <div id="auth-name-group" style="margin-bottom:18px; display:none;">
        <label style="display:block; font-size:0.7rem; text-transform:uppercase; color:var(--text); letter-spacing:1px; margin-bottom:6px; font-weight:600;">Display Name</label>
        <input type="text" id="auth-name" placeholder="John Doe" 
          style="width:100%; padding:10px 12px; background:var(--p2); border:1px solid var(--border); border-radius:4px; color:var(--white); font-family:'Inter',sans-serif; font-size:0.85rem; outline:none; transition:border-color 0.2s;">
      </div>

      <!-- Email Field -->
      <div style="margin-bottom:18px;">
        <label style="display:block; font-size:0.7rem; text-transform:uppercase; color:var(--text); letter-spacing:1px; margin-bottom:6px; font-weight:600;">Email Address</label>
        <input type="email" id="auth-email" required placeholder="name@domain.com" 
          style="width:100%; padding:10px 12px; background:var(--p2); border:1px solid var(--border); border-radius:4px; color:var(--white); font-family:'JetBrains Mono',monospace; font-size:0.85rem; outline:none; transition:border-color 0.2s;">
      </div>
      
      <!-- Password Field -->
      <div style="margin-bottom:18px;">
        <label style="display:block; font-size:0.7rem; text-transform:uppercase; color:var(--text); letter-spacing:1px; margin-bottom:6px; font-weight:600;">Password</label>
        <input type="password" id="auth-password" required placeholder="••••••••" 
          style="width:100%; padding:10px 12px; background:var(--p2); border:1px solid var(--border); border-radius:4px; color:var(--white); font-family:'JetBrains Mono',monospace; font-size:0.85rem; outline:none; transition:border-color 0.2s;">
      </div>

      <!-- Confirm Password (Signup Only) -->
      <div id="auth-confirm-group" style="margin-bottom:24px; display:none;">
        <label style="display:block; font-size:0.7rem; text-transform:uppercase; color:var(--text); letter-spacing:1px; margin-bottom:6px; font-weight:600;">Confirm Password</label>
        <input type="password" id="auth-confirm-password" placeholder="••••••••" 
          style="width:100%; padding:10px 12px; background:var(--p2); border:1px solid var(--border); border-radius:4px; color:var(--white); font-family:'JetBrains Mono',monospace; font-size:0.85rem; outline:none; transition:border-color 0.2s;">
      </div>

      <button type="submit" id="auth-submit-btn" class="btn" style="width:100%; padding:12px; font-size:0.85rem; font-weight:700; letter-spacing:1px; margin-bottom:16px; box-shadow:0 0 15px rgba(41,98,255,0.25);">
        LOG IN
      </button>
    </form>

    <!-- Divider -->
    <div style="display:flex; align-items:center; margin:16px 0; color:var(--dim); font-size:0.7rem; letter-spacing:1px;">
      <span style="flex:1; height:1px; background:var(--border);"></span>
      <span style="padding:0 10px; text-transform:uppercase;">OR</span>
      <span style="flex:1; height:1px; background:var(--border);"></span>
    </div>

    <!-- Official Google Auth Container -->
    <div id="google-signin-btn" style="width:100%; display:flex; justify-content:center; margin-bottom:12px;"></div>

    <!-- Developer Mock Google Auth Fallback -->
    <div id="google-signin-mock-container" style="display:none; text-align:center;">
      <button onclick="handleGoogleAuthMock()" class="btn-gold" style="width:100%; padding:12px; font-size:0.85rem; font-weight:700; letter-spacing:1px; display:flex; align-items:center; justify-content:center; gap:8px; border-radius:4px; cursor:pointer; border:none;">
        <span>🌐</span> CONTINUE WITH GOOGLE (DEV MOCK)
      </button>
      <p style="font-size:0.65rem; color:var(--dim); margin-top:6px; font-family:'JetBrains Mono',monospace;">GOOGLE_CLIENT_ID not configured in .env. Using mock mode.</p>
    </div>

  </div>
</div>
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
  const errDiv = document.getElementById('auth-error');
  
  if (errDiv) errDiv.style.display = 'none';

  if (mode === 'login') {
    if (loginTab) { loginTab.style.color = 'var(--white)'; loginTab.style.borderBottom = '2px solid var(--cyan)'; }
    if (signupTab) { signupTab.style.color = 'var(--dim)'; signupTab.style.borderBottom = 'none'; }
    if (nameGroup) nameGroup.style.display = 'none';
    if (confirmGroup) confirmGroup.style.display = 'none';
    if (submitBtn) submitBtn.textContent = 'LOG IN';
  } else {
    if (loginTab) { loginTab.style.color = 'var(--dim)'; loginTab.style.borderBottom = 'none'; }
    if (signupTab) { signupTab.style.color = 'var(--white)'; signupTab.style.borderBottom = '2px solid var(--cyan)'; }
    if (nameGroup) nameGroup.style.display = 'block';
    if (confirmGroup) confirmGroup.style.display = 'block';
    if (submitBtn) submitBtn.textContent = 'CREATE ACCOUNT';
  }
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
  e.preventDefault();
  const email = document.getElementById('auth-email').value;
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
      localStorage.setItem('user_email', email);
      localStorage.setItem('user_role', res.role || 'USER');
      
      // Check onboarding state
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
  const email = prompt("Enter mock Google email address to sign in:", "google_tester@domain.com");
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
      localStorage.setItem('user_email', email);
      localStorage.setItem('user_role', res.role || 'USER');

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
