def patch_shared_js():
    with open("pages/_shared.js", "r", encoding="utf-8") as f:
        content = f.read()

    target = "function applyTierMode(mode) {\n  const realRole = (localStorage.getItem('user_role') || 'FREE').toUpperCase();"
    if target not in content:
        # try CRLF
        target = "function applyTierMode(mode) {\r\n  const realRole = (localStorage.getItem('user_role') || 'FREE').toUpperCase();"
        if target not in content:
            print("Target not found in pages/_shared.js!")
            return False

    controller_code = r'''// ════════════════════════════════════════════════════════════════════
// Dynamic Admin In-Tab Feature Gating & Lock Controller
window.__PLATFORM_FEATURE_LOCKS = {};

async function loadFeatureLocks() {
  try {
    const res = await api('features/locks');
    if (res && res.locks) {
      window.__PLATFORM_FEATURE_LOCKS = res.locks;
      applyFeatureLocksToDOM();
    }
  } catch (err) {
    console.warn("Feature locks load deferred:", err);
  }
}

function showAdminToast(msg, type = 'info') {
  let container = document.getElementById('admin-toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'admin-toast-container';
    document.body.appendChild(container);
  }

  const toast = document.createElement('div');
  toast.className = 'admin-toast';
  
  let icon = 'ℹ️';
  let borderStyle = 'border-color: var(--border);';
  if (type === 'success' || type === 'unlocked') {
    icon = '🔓';
    borderStyle = 'border-color: var(--green);';
  } else if (type === 'locked') {
    icon = '🔒';
    borderStyle = 'border-color: var(--red);';
  } else if (type === 'error') {
    icon = '⚠️';
    borderStyle = 'border-color: var(--red);';
  }

  toast.style.cssText = borderStyle;
  toast.innerHTML = `<span style="font-size:1.1rem;">${icon}</span><span style="flex:1;">${msg}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    toast.style.transition = 'all 0.3s ease';
    setTimeout(() => {
      if (toast.parentElement) toast.parentElement.removeChild(toast);
    }, 300);
  }, 3500);
}

async function adminToggleInlineLock(featureId) {
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
}

// Auto-observe DOM mutations to apply lock pills dynamically
let _lockMutationDebounce = null;
const _lockObserver = new MutationObserver(() => {
  if (_lockMutationDebounce) clearTimeout(_lockMutationDebounce);
  _lockMutationDebounce = setTimeout(applyFeatureLocksToDOM, 150);
});
document.addEventListener('DOMContentLoaded', () => {
  loadFeatureLocks();
  const mainEl = document.querySelector('.main') || document.body;
  _lockObserver.observe(mainEl, { childList: true, subtree: true });
});

'''
    updated = content.replace(target, controller_code + target)

    # In applyTierMode, add applyFeatureLocksToDOM()
    target_tier_end = "    } else {\n      notice.style.display = 'none';\n    }\n  }\n}"
    target_tier_end_crlf = "    } else {\r\n      notice.style.display = 'none';\r\n    }\r\n  }\r\n}"
    if target_tier_end in updated:
        updated = updated.replace(target_tier_end, target_tier_end[:-1] + "  applyFeatureLocksToDOM();\n}")
    elif target_tier_end_crlf in updated:
        updated = updated.replace(target_tier_end_crlf, target_tier_end_crlf[:-2] + "  applyFeatureLocksToDOM();\r\n}")

    # In nav(page), add applyFeatureLocksToDOM() calls
    target_nav_end = "if(page==='advisor') setTimeout(function(){if(typeof runAdvisor==='function'){const btn=document.getElementById('advisor-scan-btn');if(btn&&!document.getElementById('advisor-results')?.innerHTML?.trim())btn.click();}},500);\n  }"
    target_nav_end_crlf = "if(page==='advisor') setTimeout(function(){if(typeof runAdvisor==='function'){const btn=document.getElementById('advisor-scan-btn');if(btn&&!document.getElementById('advisor-results')?.innerHTML?.trim())btn.click();}},500);\r\n  }"
    
    extra_nav = "\n    setTimeout(applyFeatureLocksToDOM, 250);\n    setTimeout(applyFeatureLocksToDOM, 750);"
    extra_nav_crlf = "\r\n    setTimeout(applyFeatureLocksToDOM, 250);\r\n    setTimeout(applyFeatureLocksToDOM, 750);"
    
    if target_nav_end in updated:
        updated = updated.replace(target_nav_end, target_nav_end + extra_nav)
    elif target_nav_end_crlf in updated:
        updated = updated.replace(target_nav_end_crlf, target_nav_end_crlf + extra_nav_crlf)

    with open("pages/_shared.js", "w", encoding="utf-8") as f:
        f.write(updated)
    print("Successfully patched pages/_shared.js!")
    return True

if __name__ == "__main__":
    patch_shared_js()
