
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

