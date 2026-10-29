def patch_shared():
    with open("pages/_shared.js", "r", encoding="utf-8") as f:
        c = f.read()

    target = """async function adminToggleInlineLock(featureId) {
  const realRole = (localStorage.getItem('user_role') || 'FREE').toUpperCase();
  if (realRole !== 'ADMIN') return;

  try {
    const res = await api('admin/toggle_feature_lock', { feature_id: featureId });
    if (res.error) throw new Error(res.error);

    if (!window.__PLATFORM_FEATURE_LOCKS[featureId]) {
      window.__PLATFORM_FEATURE_LOCKS[featureId] = { locked: Boolean(res.is_locked_for_free), min_role: res.min_role || 'PREMIUM' };
    } else {
      window.__PLATFORM_FEATURE_LOCKS[featureId].locked = Boolean(res.is_locked_for_free);
    }

    const stateWord = res.is_locked_for_free ? 'LOCKED for Free tier' : 'UNLOCKED for Free tier';
    showAdminToast(`Feature [${featureId}] is now ${stateWord}.`, res.is_locked_for_free ? 'locked' : 'unlocked');
    
    // Immediately re-apply to DOM
    applyFeatureLocksToDOM();

    // If on admin page, reload table too
    if (typeof loadAdmin === 'function') {
      const adminPage = document.getElementById('page-admin');
      if (adminPage && adminPage.classList.contains('active')) {
        loadAdmin();
      }
    }
  } catch (err) {
    showAdminToast(err.message || 'Failed to toggle feature lock', 'error');
  }
}

function applyFeatureLocksToDOM() {
  const realRole = (localStorage.getItem('user_role') || 'FREE').toUpperCase();
  const eff = getEffectiveRole();
  const locks = window.__PLATFORM_FEATURE_LOCKS || {};

  // Find all elements designated as features
  const elements = document.querySelectorAll('[data-feature-id]');
  elements.forEach(el => {
    const featureId = el.getAttribute('data-feature-id');
    if (!featureId) return;

    const lockData = locks[featureId];
    const isLocked = lockData ? Boolean(lockData.locked) : true;

    // 1. ADMIN IN-TAB TOGGLE PILL
    let pill = el.querySelector('.admin-inline-lock-pill');
    if (realRole === 'ADMIN') {
      if (!pill) {
        pill = document.createElement('div');
        pill.className = 'admin-inline-lock-pill';
        pill.addEventListener('click', (e) => {
          e.stopPropagation();
          e.preventDefault();
          adminToggleInlineLock(featureId);
        });
        const computedPos = window.getComputedStyle(el).position;
        if (computedPos === 'static') {
          el.style.position = 'relative';
        }
        el.insertBefore(pill, el.firstChild);
      }

      if (isLocked) {
        pill.className = 'admin-inline-lock-pill locked';
        pill.title = 'Click to UNLOCK for Free tier';
        pill.innerHTML = '🔒 FREE: LOCKED';
      } else {
        pill.className = 'admin-inline-lock-pill unlocked';
        pill.title = 'Click to LOCK for Free tier';
        pill.innerHTML = '🔓 FREE: UNLOCKED';
      }
    } else if (pill) {
      pill.remove();
    }

    // 2. ENFORCE LOCK VEIL FOR FREE TIER
    let overlay = el.querySelector('.admin-locked-free-overlay');
    if (eff === 'FREE' && isLocked) {
      el.classList.add('admin-feature-locked-for-free');
      if (!overlay) {
        overlay = document.createElement('div');
        overlay.className = 'admin-locked-free-overlay';
        overlay.innerHTML = `
          <div style="font-size:1.8rem; margin-bottom:8px;">🔒</div>
          <div style="font-family:'Orbitron',sans-serif; font-size:0.95rem; font-weight:700; color:var(--gold); margin-bottom:6px; letter-spacing:1px;">INSTITUTIONAL TIER FEATURE</div>
          <p style="font-size:0.75rem; color:var(--text); max-width:320px; margin-bottom:14px; line-height:1.4;">
            This analytical module has been locked for Free tier. Upgrade to Premium or Elite for unlimited real-time access.
          </p>
          <button onclick="openUpgradeModal()" class="btn" style="background:linear-gradient(135deg, var(--gold), #FFB74D); color:#000; font-weight:bold; padding:6px 16px; font-size:0.75rem; cursor:pointer;">
            UPGRADE TO UNLOCK ➔
          </button>
        `;
        el.appendChild(overlay);
      }
    } else {
      el.classList.remove('admin-feature-locked-for-free');
      if (overlay) {
        overlay.remove();
      }
    }
  });
}"""

    target_crlf = target.replace("\n", "\r\n")

    replacement = """async function adminToggleInlineLock(featureId, featureName, pageName) {
  const realRole = (localStorage.getItem('user_role') || 'FREE').toUpperCase();
  if (realRole !== 'ADMIN') return;

  try {
    const payload = { feature_id: featureId };
    if (featureName) payload.feature_name = featureName;
    if (pageName) payload.page = pageName;

    const res = await api('admin/toggle_feature_lock', payload);
    if (res.error) throw new Error(res.error);

    if (!window.__PLATFORM_FEATURE_LOCKS[featureId]) {
      window.__PLATFORM_FEATURE_LOCKS[featureId] = {
        locked: Boolean(res.is_locked_for_free),
        min_role: res.min_role || 'PREMIUM',
        name: featureName || featureId,
        page: pageName || 'general'
      };
    } else {
      window.__PLATFORM_FEATURE_LOCKS[featureId].locked = Boolean(res.is_locked_for_free);
      if (res.min_role) window.__PLATFORM_FEATURE_LOCKS[featureId].min_role = res.min_role;
    }

    const stateWord = res.is_locked_for_free ? 'LOCKED for Free tier' : 'UNLOCKED for Free tier';
    const displayTitle = featureName || featureId;
    showAdminToast(`[${displayTitle}] is now ${stateWord}.`, res.is_locked_for_free ? 'locked' : 'unlocked');
    
    // Immediately re-apply to DOM
    applyFeatureLocksToDOM();

    // If on admin page, reload table too
    if (typeof loadAdmin === 'function') {
      const adminPage = document.getElementById('page-admin');
      if (adminPage && adminPage.classList.contains('active')) {
        loadAdmin();
      }
    }
  } catch (err) {
    showAdminToast(err.message || 'Failed to toggle feature lock', 'error');
  }
}

function applyFeatureLocksToDOM() {
  const realRole = (localStorage.getItem('user_role') || 'FREE').toUpperCase();
  const eff = getEffectiveRole();
  const locks = window.__PLATFORM_FEATURE_LOCKS || {};

  // Find all elements designated as features
  const elements = document.querySelectorAll('[data-feature-id]');
  elements.forEach(el => {
    const featureId = el.getAttribute('data-feature-id');
    const featureName = el.getAttribute('data-feature-name') || featureId;
    const pageName = el.getAttribute('data-feature-page') || '';
    if (!featureId) return;

    const lockData = locks[featureId];
    const isLocked = lockData ? Boolean(lockData.locked) : (el.getAttribute('data-default-locked') === '1');

    // 1. ADMIN IN-TAB TOGGLE PILL
    let pill = el.querySelector(':scope > .admin-inline-lock-pill');
    if (realRole === 'ADMIN') {
      if (!pill) {
        pill = document.createElement('div');
        pill.className = 'admin-inline-lock-pill';
        pill.addEventListener('click', (e) => {
          e.stopPropagation();
          e.preventDefault();
          adminToggleInlineLock(featureId, featureName, pageName);
        });
        const computedPos = window.getComputedStyle(el).position;
        if (computedPos === 'static') {
          el.style.position = 'relative';
        }
        el.insertBefore(pill, el.firstChild);
      }

      if (isLocked) {
        pill.className = 'admin-inline-lock-pill locked';
        pill.title = `Click to UNLOCK [${featureName}] for Free tier`;
        pill.innerHTML = '🔒 FREE: LOCKED';
      } else {
        pill.className = 'admin-inline-lock-pill unlocked';
        pill.title = `Click to LOCK [${featureName}] for Free tier`;
        pill.innerHTML = '🔓 FREE: UNLOCKED';
      }
    } else if (pill) {
      pill.remove();
    }

    // 2. ENFORCE LOCK VEIL FOR FREE TIER
    let overlay = el.querySelector(':scope > .admin-locked-free-overlay');
    if (eff === 'FREE' && isLocked) {
      el.classList.add('admin-feature-locked-for-free');
      if (!overlay) {
        overlay = document.createElement('div');
        const h = el.offsetHeight || 0;
        const isCompact = (h > 0 && h < 125);
        overlay.className = 'admin-locked-free-overlay' + (isCompact ? ' compact' : '');

        if (isCompact) {
          overlay.innerHTML = `
            <span style="font-size:0.95rem;">🔒</span>
            <span style="font-family:'Orbitron',sans-serif; font-size:0.7rem; font-weight:700; color:var(--gold); white-space:nowrap; letter-spacing:0.5px;">
              ${featureName}: LOCKED FOR FREE
            </span>
            <button onclick="openUpgradeModal()" class="btn" style="background:linear-gradient(135deg, var(--gold), #FFB74D); color:#000; font-weight:bold; padding:2px 8px; font-size:0.62rem; cursor:pointer;">
              UNLOCK ➔
            </button>
          `;
        } else {
          overlay.innerHTML = `
            <div style="font-size:1.5rem; margin-bottom:5px;">🔒</div>
            <div style="font-family:'Orbitron',sans-serif; font-size:0.85rem; font-weight:700; color:var(--gold); margin-bottom:4px; letter-spacing:1px;">
              ${featureName.toUpperCase()}
            </div>
            <p style="font-size:0.72rem; color:var(--text); max-width:320px; margin-bottom:10px; line-height:1.4;">
              This institutional module is reserved for Premium & Elite members.
            </p>
            <button onclick="openUpgradeModal()" class="btn" style="background:linear-gradient(135deg, var(--gold), #FFB74D); color:#000; font-weight:bold; padding:5px 14px; font-size:0.72rem; cursor:pointer;">
              UPGRADE TO UNLOCK ➔
            </button>
          `;
        }
        el.appendChild(overlay);
      }
    } else {
      el.classList.remove('admin-feature-locked-for-free');
      if (overlay) {
        overlay.remove();
      }
    }
  });
}"""

    replacement_crlf = replacement.replace("\n", "\r\n")

    if target in c:
        c = c.replace(target, replacement, 1)
    elif target_crlf in c:
        c = c.replace(target_crlf, replacement_crlf, 1)
    else:
        print("Target not found in pages/_shared.js!")
        return False

    with open("pages/_shared.js", "w", encoding="utf-8") as f:
        f.write(c)
    print("Successfully patched pages/_shared.js!")
    return True

if __name__ == "__main__":
    patch_shared()
