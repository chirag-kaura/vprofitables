import os

def create_admin_page():
    content = r'''# pages/page_admin.py
# -*- coding: utf-8 -*-
"""
Administrator Control Console — Complete User Tier Advancement & Feature Gating
"""

HTML = r"""
<!-- ═══════════ PAGE: ADMIN CONSOLE ═══════════ -->
<div class="page" id="page-admin" style="padding:24px; max-width:1400px; margin:0 auto;">
  
  <!-- Header -->
  <div style="margin-bottom:24px; display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid var(--border); padding-bottom:16px; flex-wrap:wrap; gap:12px;">
    <div>
      <div style="display:flex; align-items:center; gap:10px;">
        <h2 style="font-family:'Orbitron',sans-serif; font-size:1.5rem; color:var(--white); font-weight:700; letter-spacing:1px; margin-bottom:4px;">🛡️ ADMINISTRATOR CONSOLE</h2>
        <span style="background:rgba(179,157,219,0.2); color:#B39DDB; border:1px solid #B39DDB; font-size:0.65rem; font-weight:700; padding:2px 8px; border-radius:3px; font-family:'JetBrains Mono',monospace;">SUPERUSER DESK</span>
      </div>
      <p style="font-family:'JetBrains Mono',monospace; font-size:0.75rem; color:var(--dim);">SYSTEM ENVIRONMENT, USER TIER ADVANCEMENTS & IN-TAB FEATURE GATING</p>
    </div>
    <div style="display:flex; gap:10px; align-items:center;">
      <button class="btn" onclick="loadAdmin()" style="padding:6px 14px; font-size:0.75rem; font-family:'JetBrains Mono',monospace; display:flex; align-items:center; gap:6px;">
        🔄 REFRESH TELEMETRY
      </button>
      <div style="background:rgba(8,153,129,0.12); border:1px solid var(--green); border-radius:4px; padding:6px 14px; font-family:'JetBrains Mono',monospace; font-size:0.75rem; color:var(--green); font-weight:bold;">
        ● SECURE ROOT ACTIVE
      </div>
    </div>
  </div>

  <!-- Alert Banner -->
  <div id="adm-alert" style="display:none; margin-bottom:20px; padding:12px 18px; border-radius:4px; font-size:0.82rem; font-family:'Inter',sans-serif;"></div>

  <!-- System Health & Telemetry Grid -->
  <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(190px, 1fr)); gap:14px; margin-bottom:28px;">
    
    <div class="card" style="padding:16px; display:flex; flex-direction:column; justify-content:center; align-items:center; text-align:center;">
      <span style="font-size:0.68rem; color:var(--dim); text-transform:uppercase; letter-spacing:1px; margin-bottom:6px;">Engine & WAL State</span>
      <span id="adm-stat-status" style="font-size:1.3rem; color:var(--green); font-weight:bold; font-family:'Orbitron',sans-serif;">ONLINE</span>
      <span style="font-size:0.65rem; color:var(--dim); margin-top:4px; font-family:'JetBrains Mono',monospace;">WAL MODE CONCURRENT</span>
    </div>

    <div class="card" style="padding:16px; display:flex; flex-direction:column; justify-content:center; align-items:center; text-align:center;">
      <span style="font-size:0.68rem; color:var(--dim); text-transform:uppercase; letter-spacing:1px; margin-bottom:6px;">Active Instruments</span>
      <span id="adm-stat-inst" style="font-size:1.3rem; color:var(--white); font-weight:bold; font-family:'JetBrains Mono',monospace;">--</span>
      <span style="font-size:0.65rem; color:var(--dim); margin-top:4px; font-family:'JetBrains Mono',monospace;">518 MONITORED</span>
    </div>

    <div class="card" style="padding:16px; display:flex; flex-direction:column; justify-content:center; align-items:center; text-align:center;">
      <span style="font-size:0.68rem; color:var(--dim); text-transform:uppercase; letter-spacing:1px; margin-bottom:6px;">Historical Daily Bars</span>
      <span id="adm-stat-prices" style="font-size:1.3rem; color:var(--cyan); font-weight:bold; font-family:'JetBrains Mono',monospace;">--</span>
      <span style="font-size:0.65rem; color:var(--dim); margin-top:4px; font-family:'JetBrains Mono',monospace;">2,782 EQUITIES</span>
    </div>

    <div class="card" style="padding:16px; display:flex; flex-direction:column; justify-content:center; align-items:center; text-align:center;">
      <span style="font-size:0.68rem; color:var(--dim); text-transform:uppercase; letter-spacing:1px; margin-bottom:6px;">Intraday 15m Bars</span>
      <span id="adm-stat-intraday" style="font-size:1.3rem; color:var(--gold); font-weight:bold; font-family:'JetBrains Mono',monospace;">--</span>
      <span style="font-size:0.65rem; color:var(--dim); margin-top:4px; font-family:'JetBrains Mono',monospace;">HIGH FREQ FEED</span>
    </div>

    <div class="card" style="padding:16px; display:flex; flex-direction:column; justify-content:center; align-items:center; text-align:center;">
      <span style="font-size:0.68rem; color:var(--dim); text-transform:uppercase; letter-spacing:1px; margin-bottom:6px;">Database Size</span>
      <span id="adm-stat-dbsize" style="font-size:1.3rem; color:var(--white); font-weight:bold; font-family:'JetBrains Mono',monospace;">-- MB</span>
      <span style="font-size:0.65rem; color:var(--green); margin-top:4px; font-family:'JetBrains Mono',monospace;">VACUUM OPTIMIZED</span>
    </div>

    <div class="card" style="padding:16px; display:flex; flex-direction:column; justify-content:center; align-items:center; text-align:center;">
      <span style="font-size:0.68rem; color:var(--dim); text-transform:uppercase; letter-spacing:1px; margin-bottom:6px;">Total User Accounts</span>
      <span id="adm-stat-users" style="font-size:1.3rem; color:var(--purple); font-weight:bold; font-family:'JetBrains Mono',monospace;">--</span>
      <span id="adm-stat-tier-breakdown" style="font-size:0.65rem; color:var(--dim); margin-top:4px; font-family:'JetBrains Mono',monospace;">Loading tiers...</span>
    </div>

  </div>

  <!-- In-Tab Locking Explanation Callout Banner -->
  <div style="background:linear-gradient(135deg, rgba(41,98,255,0.08), rgba(179,157,219,0.08)); border:1px solid rgba(41,98,255,0.3); border-radius:6px; padding:16px 20px; margin-bottom:28px; display:flex; gap:16px; align-items:center; flex-wrap:wrap;">
    <div style="font-size:2rem; flex-shrink:0;">💡</div>
    <div style="flex:1; min-width:300px;">
      <div style="font-size:0.9rem; font-weight:700; color:var(--white); margin-bottom:4px; font-family:'Orbitron',sans-serif;">
        DYNAMIC IN-TAB FEATURE LOCK CONTROLLER IS ACTIVE
      </div>
      <p style="font-size:0.8rem; color:var(--text); line-height:1.5; margin:0;">
        Whenever you navigate to ANY tab (<b>Home/Overview</b>, <b>Advisor</b>, <b>Scanner</b>, <b>Simons Lab</b>, <b>Trading Desk</b>, etc.), an interactive 
        <span style="background:rgba(242,54,69,0.2); color:#FF5252; padding:2px 8px; border-radius:4px; font-family:'JetBrains Mono',monospace; font-size:0.75rem; border:1px solid rgba(242,54,69,0.5);">🔒 LOCKED FOR FREE</span> or 
        <span style="background:rgba(8,153,129,0.2); color:#00E676; padding:2px 8px; border-radius:4px; font-family:'JetBrains Mono',monospace; font-size:0.75rem; border:1px solid rgba(8,153,129,0.5);">🔓 UNLOCKED FOR FREE</span> 
        badge appears directly on each feature card! <b>Clicking it instantly toggles access for all Free tier users across the entire desk in real time.</b>
      </p>
    </div>
    <button class="btn" onclick="nav('overview')" style="padding:8px 16px; font-size:0.78rem; font-weight:600; white-space:nowrap; background:linear-gradient(135deg, var(--cyan), var(--cyan2));">
      EXPLORE HOME & TEST LOCKS ➔
    </button>
  </div>

  <!-- Two Column Layout: User Access Control & Feature Gating Matrix -->
  <div style="display:grid; grid-template-columns:1fr; gap:28px; margin-bottom:30px;">
    
    <!-- 1. USER ACCESS MANAGEMENT & TIER ADVANCEMENTS -->
    <div class="card" style="padding:22px;">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px; flex-wrap:wrap; gap:10px;">
        <div>
          <div class="card-title" style="margin-bottom:4px;">👥 USER ACCESS & TIER ADVANCEMENT MANAGEMENT</div>
          <p style="font-size:0.75rem; color:var(--dim); margin:0;">Promote or demote users between Free, Premium, Elite, and Super Admin tiers.</p>
        </div>
        <div style="display:flex; gap:10px; align-items:center;">
          <input type="text" id="adm-user-search" placeholder="🔍 Search user name or email..." onkeyup="adminFilterUsers()" 
                 style="background:var(--p2); border:1px solid var(--border); color:var(--white); padding:6px 12px; font-size:0.78rem; border-radius:4px; width:240px; outline:none;">
        </div>
      </div>

      <div style="overflow-x:auto;">
        <table style="width:100%; border-collapse:collapse; text-align:left; font-size:0.8rem; font-family:'Inter',sans-serif;">
          <thead>
            <tr style="border-bottom:1px solid var(--border); color:var(--dim); font-size:0.7rem; text-transform:uppercase; letter-spacing:0.5px;">
              <th style="padding:12px 10px;">User</th>
              <th style="padding:12px 10px;">Email</th>
              <th style="padding:12px 10px;">Auth Type</th>
              <th style="padding:12px 10px;">Created</th>
              <th style="padding:12px 10px;">Current Tier</th>
              <th style="padding:12px 10px; text-align:center;">Tier Selector</th>
              <th style="padding:12px 10px; text-align:right;">Quick Actions</th>
            </tr>
          </thead>
          <tbody id="adm-users-table-body">
            <tr><td colspan="7" style="padding:20px; text-align:center; color:var(--dim);">Loading user registry...</td></tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 2. MASTER FEATURE GATING & TIER MATRIX -->
    <div class="card" style="padding:22px;">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px; flex-wrap:wrap; gap:10px;">
        <div>
          <div class="card-title" style="margin-bottom:4px;">🔐 MASTER FEATURE GATING & ACCESS MATRIX</div>
          <p style="font-size:0.75rem; color:var(--dim); margin:0;">Configure global visibility rules for Free vs Paid subscribers across all platform pages.</p>
        </div>
        <div style="display:flex; gap:10px; align-items:center;">
          <select id="adm-feature-page-filter" onchange="adminFilterFeatures()" style="background:var(--p2); border:1px solid var(--border); color:var(--white); padding:6px 10px; font-size:0.78rem; border-radius:4px; outline:none;">
            <option value="ALL">All Pages / Tabs</option>
            <option value="overview">Home / Overview</option>
            <option value="advisor">Investment Advisor</option>
            <option value="scanner">Market Scanner</option>
            <option value="simons">Simons Lab</option>
            <option value="trading">Trading Desk</option>
            <option value="sq9">Square of Nine</option>
            <option value="dashboard">Planet Dashboard</option>
            <option value="sentiment">Sentiment</option>
          </select>
        </div>
      </div>

      <div style="overflow-x:auto;">
        <table style="width:100%; border-collapse:collapse; text-align:left; font-size:0.8rem; font-family:'Inter',sans-serif;">
          <thead>
            <tr style="border-bottom:1px solid var(--border); color:var(--dim); font-size:0.7rem; text-transform:uppercase; letter-spacing:0.5px;">
              <th style="padding:12px 10px;">Feature Name & ID</th>
              <th style="padding:12px 10px;">Target Tab</th>
              <th style="padding:12px 10px;">Category</th>
              <th style="padding:12px 10px; text-align:center;">Free Tier Access</th>
              <th style="padding:12px 10px; text-align:center;">Required Tier</th>
              <th style="padding:12px 10px; text-align:right;">Quick Lock Toggle</th>
            </tr>
          </thead>
          <tbody id="adm-features-table-body">
            <tr><td colspan="6" style="padding:20px; text-align:center; color:var(--dim);">Loading feature rules...</td></tr>
          </tbody>
        </table>
      </div>
    </div>

  </div>

  <!-- Quick Launcher for Advanced Tools -->
  <div class="card" style="padding:22px; margin-bottom:30px;">
    <div class="card-title">🚀 RAPID ANALYTICAL SUITE SHORTCUTS</div>
    <p style="font-size:0.75rem; color:var(--dim); margin-bottom:16px; line-height:1.4;">
      Direct one-click access into deep quantitative, cyclical, and astro-geocentric modules across the platform.
    </p>
    
    <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(180px, 1fr)); gap:12px;" id="adm-launcher-grid">
       <button class="btn" style="padding:10px 12px; font-size:0.75rem; text-align:left;" onclick="nav('overview')">🏠 Home / Overview</button>
       <button class="btn" style="padding:10px 12px; font-size:0.75rem; text-align:left;" onclick="nav('advisor')">💡 Investment Advisor</button>
       <button class="btn" style="padding:10px 12px; font-size:0.75rem; text-align:left;" onclick="nav('scanner')">📡 Market Scanner</button>
       <button class="btn" style="padding:10px 12px; font-size:0.75rem; text-align:left;" onclick="nav('dashboard')">🪐 Planet Dashboard</button>
       <button class="btn" style="padding:10px 12px; font-size:0.75rem; text-align:left;" onclick="nav('chart')">📈 Chart + S/R</button>
       <button class="btn" style="padding:10px 12px; font-size:0.75rem; text-align:left;" onclick="nav('simons')">🧠 Simons Lab</button>
       <button class="btn" style="padding:10px 12px; font-size:0.75rem; text-align:left;" onclick="nav('analyze')">🔬 Gann Analysis</button>
       <button class="btn" style="padding:10px 12px; font-size:0.75rem; text-align:left;" onclick="nav('sq9')">⬛ Square of Nine</button>
       <button class="btn" style="padding:10px 12px; font-size:0.75rem; text-align:left;" onclick="nav('trading')">⚡ Trading Desk</button>
       <button class="btn" style="padding:10px 12px; font-size:0.75rem; text-align:left;" onclick="nav('instruments')">📋 Instruments DB</button>
    </div>
  </div>

</div>
"""

JS = r"""
let _adminCachedUsers = [];
let _adminCachedFeatures = [];

async function loadAdmin() {
  const alertEl = document.getElementById('adm-alert');
  if (alertEl) alertEl.style.display = 'none';

  try {
    const res = await api('admin/users');
    if (res.error) throw new Error(res.error);

    _adminCachedUsers = res.users || [];
    _adminCachedFeatures = res.features || [];

    // 1. Update Telemetry Stats
    if (res.stats) {
      document.getElementById('adm-stat-status').textContent = res.stats.engine_status || 'ONLINE';
      document.getElementById('adm-stat-inst').textContent = (res.stats.instruments || 0).toLocaleString();
      document.getElementById('adm-stat-prices').textContent = (res.stats.daily_prices || 0).toLocaleString();
      document.getElementById('adm-stat-intraday').textContent = (res.stats.intraday_bars || 0).toLocaleString();
      document.getElementById('adm-stat-dbsize').textContent = (res.stats.db_size_mb || 0) + ' MB';
      document.getElementById('adm-stat-users').textContent = (res.stats.total_users || 0).toLocaleString();

      const rc = res.stats.role_counts || {};
      document.getElementById('adm-stat-tier-breakdown').innerHTML = 
        `<span style="color:#94A3B8;">Free:${rc.FREE||0}</span> · <span style="color:#00E676;">Prem:${rc.PREMIUM||0}</span> · <span style="color:#00D4FF;">Elite:${rc.ELITE||0}</span> · <span style="color:#B39DDB;">Admin:${rc.ADMIN||0}</span>`;
    }

    // 2. Render Users & Features
    adminRenderUsers(_adminCachedUsers);
    adminRenderFeatures(_adminCachedFeatures);

  } catch (err) {
    showAdminAlert(err.message || 'Failed to load administrator dashboard data', 'error');
  }
}

function adminRenderUsers(users) {
  const tbody = document.getElementById('adm-users-table-body');
  if (!tbody) return;
  tbody.innerHTML = '';

  if (!users || users.length === 0) {
    tbody.innerHTML = '<tr><td colspan="7" style="padding:20px; text-align:center; color:var(--dim);">No user accounts found.</td></tr>';
    return;
  }

  const currentUserEmail = (localStorage.getItem('user_email') || '').toLowerCase();

  users.forEach(u => {
    const tr = document.createElement('tr');
    tr.style.borderBottom = '1px solid var(--border)';
    
    const isCurrentUser = (u.email || '').toLowerCase() === currentUserEmail;
    
    // Tier badge styles
    let badgeHtml = '';
    const r = (u.role || 'FREE').toUpperCase();
    if (r === 'ADMIN') {
      badgeHtml = `<span style="background:rgba(179,157,219,0.2); color:#B39DDB; border:1px solid #B39DDB; font-weight:700; font-size:0.68rem; padding:3px 8px; border-radius:3px;">🛡️ ADMIN</span>`;
    } else if (r === 'ELITE') {
      badgeHtml = `<span style="background:rgba(0,212,255,0.2); color:#00D4FF; border:1px solid #00D4FF; font-weight:700; font-size:0.68rem; padding:3px 8px; border-radius:3px;">💎 ELITE</span>`;
    } else if (r === 'PREMIUM') {
      badgeHtml = `<span style="background:rgba(8,153,129,0.2); color:#00E676; border:1px solid #00E676; font-weight:700; font-size:0.68rem; padding:3px 8px; border-radius:3px;">⭐ PREMIUM</span>`;
    } else {
      badgeHtml = `<span style="background:rgba(255,255,255,0.06); color:#94A3B8; border:1px solid #363A45; font-size:0.68rem; padding:3px 8px; border-radius:3px;">🆓 FREE</span>`;
    }

    // Role selector dropdown
    const roleSelectDisabled = isCurrentUser ? 'disabled' : '';
    const selectHtml = `
      <select onchange="adminUpdateUserRole('${u.id}', this.value)" ${roleSelectDisabled}
              style="background:var(--p2); border:1px solid var(--border); color:var(--white); padding:4px 8px; font-size:0.75rem; border-radius:4px; font-family:'JetBrains Mono',monospace; outline:none; cursor:pointer;">
        <option value="FREE" ${r === 'FREE' ? 'selected' : ''}>FREE</option>
        <option value="PREMIUM" ${r === 'PREMIUM' ? 'selected' : ''}>PREMIUM</option>
        <option value="ELITE" ${r === 'ELITE' ? 'selected' : ''}>ELITE</option>
        <option value="ADMIN" ${r === 'ADMIN' ? 'selected' : ''}>ADMIN</option>
      </select>
    `;

    // Quick action buttons
    let actionButtons = '';
    if (isCurrentUser) {
      actionButtons = `<span style="font-size:0.7rem; color:var(--dim); font-family:'JetBrains Mono',monospace;">(CURRENT SESSION)</span>`;
    } else if (r === 'ADMIN') {
      actionButtons = `<span style="font-size:0.7rem; color:#B39DDB; font-weight:600;">SUPERUSER</span>`;
    } else {
      actionButtons = `
        <div style="display:flex; gap:6px; justify-content:flex-end;">
          ${r !== 'PREMIUM' ? `<button onclick="adminUpdateUserRole('${u.id}', 'PREMIUM')" style="background:rgba(8,153,129,0.15); border:1px solid var(--green); color:var(--green); padding:4px 8px; font-size:0.68rem; border-radius:3px; cursor:pointer; font-weight:600;">⭐ PREM</button>` : ''}
          ${r !== 'ELITE' ? `<button onclick="adminUpdateUserRole('${u.id}', 'ELITE')" style="background:rgba(0,212,255,0.15); border:1px solid var(--cyan); color:var(--cyan); padding:4px 8px; font-size:0.68rem; border-radius:3px; cursor:pointer; font-weight:600;">💎 ELITE</button>` : ''}
          ${r !== 'FREE' ? `<button onclick="adminUpdateUserRole('${u.id}', 'FREE')" style="background:rgba(242,54,69,0.15); border:1px solid var(--red); color:var(--red); padding:4px 8px; font-size:0.68rem; border-radius:3px; cursor:pointer; font-weight:600;">⬇ FREE</button>` : ''}
        </div>
      `;
    }

    tr.innerHTML = `
      <td style="padding:12px 10px; font-weight:600; color:var(--white);">
        <div style="display:flex; align-items:center; gap:8px;">
          <div style="width:24px; height:24px; border-radius:50%; background:var(--p2); border:1px solid var(--border); display:flex; align-items:center; justify-content:center; font-size:0.7rem; font-weight:bold; color:var(--cyan);">
            ${(u.display_name || u.email || 'U')[0].toUpperCase()}
          </div>
          ${u.display_name || 'Standard Trader'}
        </div>
      </td>
      <td style="padding:12px 10px; font-family:'JetBrains Mono',monospace; color:var(--text);">${u.email}</td>
      <td style="padding:12px 10px; font-size:0.72rem; text-transform:uppercase; color:var(--dim);">${u.auth_method || 'LOCAL'}</td>
      <td style="padding:12px 10px; font-size:0.72rem; color:var(--dim); font-family:'JetBrains Mono',monospace;">${(u.created_at || '').substring(0,10)}</td>
      <td style="padding:12px 10px;">${badgeHtml}</td>
      <td style="padding:12px 10px; text-align:center;">${selectHtml}</td>
      <td style="padding:12px 10px; text-align:right;">${actionButtons}</td>
    `;
    tbody.appendChild(tr);
  });
}

function adminRenderFeatures(features) {
  const tbody = document.getElementById('adm-features-table-body');
  if (!tbody) return;
  tbody.innerHTML = '';

  if (!features || features.length === 0) {
    tbody.innerHTML = '<tr><td colspan="6" style="padding:20px; text-align:center; color:var(--dim);">No feature rules registered.</td></tr>';
    return;
  }

  features.forEach(f => {
    const tr = document.createElement('tr');
    tr.style.borderBottom = '1px solid var(--border)';

    const isLocked = Boolean(f.is_locked_for_free);
    const lockStatusBadge = isLocked
      ? `<span style="background:rgba(242,54,69,0.15); color:#FF5252; border:1px solid rgba(242,54,69,0.4); padding:3px 8px; border-radius:3px; font-size:0.68rem; font-weight:700; font-family:'JetBrains Mono',monospace;">🔒 LOCKED FOR FREE</span>`
      : `<span style="background:rgba(8,153,129,0.15); color:#00E676; border:1px solid rgba(8,153,129,0.4); padding:3px 8px; border-radius:3px; font-size:0.68rem; font-weight:700; font-family:'JetBrains Mono',monospace;">🔓 UNLOCKED FOR FREE</span>`;

    const toggleBtnHtml = isLocked
      ? `<button onclick="adminToggleFeature('${f.feature_id}', 0)" style="background:rgba(8,153,129,0.15); border:1px solid var(--green); color:var(--green); padding:5px 12px; font-size:0.72rem; border-radius:3px; cursor:pointer; font-weight:600; font-family:'JetBrains Mono',monospace;">🔓 UNLOCK</button>`
      : `<button onclick="adminToggleFeature('${f.feature_id}', 1)" style="background:rgba(242,54,69,0.15); border:1px solid var(--red); color:var(--red); padding:5px 12px; font-size:0.72rem; border-radius:3px; cursor:pointer; font-weight:600; font-family:'JetBrains Mono',monospace;">🔒 LOCK</button>`;

    tr.innerHTML = `
      <td style="padding:12px 10px;">
        <div style="font-weight:600; color:var(--white);">${f.feature_name}</div>
        <div style="font-size:0.68rem; color:var(--dim); font-family:'JetBrains Mono',monospace;">${f.feature_id}</div>
        <div style="font-size:0.72rem; color:var(--t2); margin-top:2px;">${f.description || ''}</div>
      </td>
      <td style="padding:12px 10px;">
        <span style="background:var(--p2); border:1px solid var(--border); padding:2px 8px; border-radius:3px; font-size:0.72rem; font-family:'JetBrains Mono',monospace; color:var(--cyan);">
          /${f.page}
        </span>
      </td>
      <td style="padding:12px 10px;">
        <span style="font-size:0.7rem; color:var(--dim); text-transform:uppercase; font-weight:600;">${f.category || 'ANALYTICS'}</span>
      </td>
      <td style="padding:12px 10px; text-align:center;">${lockStatusBadge}</td>
      <td style="padding:12px 10px; text-align:center;">
        <select onchange="adminUpdateFeatureMinRole('${f.feature_id}', this.value)"
                style="background:var(--p2); border:1px solid var(--border); color:var(--white); padding:3px 6px; font-size:0.72rem; border-radius:3px; font-family:'JetBrains Mono',monospace; outline:none;">
          <option value="FREE" ${f.min_role === 'FREE' ? 'selected' : ''}>FREE</option>
          <option value="PREMIUM" ${f.min_role === 'PREMIUM' ? 'selected' : ''}>PREMIUM</option>
          <option value="ELITE" ${f.min_role === 'ELITE' ? 'selected' : ''}>ELITE</option>
        </select>
      </td>
      <td style="padding:12px 10px; text-align:right;">${toggleBtnHtml}</td>
    `;
    tbody.appendChild(tr);
  });
}

function adminFilterUsers() {
  const query = (document.getElementById('adm-user-search')?.value || '').toLowerCase().trim();
  if (!query) {
    adminRenderUsers(_adminCachedUsers);
    return;
  }
  const filtered = _adminCachedUsers.filter(u => 
    (u.display_name || '').toLowerCase().includes(query) ||
    (u.email || '').toLowerCase().includes(query) ||
    (u.role || '').toLowerCase().includes(query)
  );
  adminRenderUsers(filtered);
}

function adminFilterFeatures() {
  const pageFilter = document.getElementById('adm-feature-page-filter')?.value || 'ALL';
  if (pageFilter === 'ALL') {
    adminRenderFeatures(_adminCachedFeatures);
    return;
  }
  const filtered = _adminCachedFeatures.filter(f => f.page === pageFilter);
  adminRenderFeatures(filtered);
}

async function adminUpdateUserRole(userId, newRole) {
  const alertEl = document.getElementById('adm-alert');
  if (alertEl) alertEl.style.display = 'none';

  try {
    const res = await api('admin/update_role', { user_id: userId, role: newRole });
    if (res.error) throw new Error(res.error);
    
    showAdminAlert(`Successfully updated user tier to ${newRole}.`, 'success');
    loadAdmin();
  } catch (err) {
    showAdminAlert(err.message || 'Failed to update user tier.', 'error');
  }
}

async function adminToggleFeature(featureId, lockState) {
  try {
    const res = await api('admin/toggle_feature_lock', { feature_id: featureId, is_locked_for_free: lockState });
    if (res.error) throw new Error(res.error);
    
    // Update global lock registry cache
    if (window.__PLATFORM_FEATURE_LOCKS && window.__PLATFORM_FEATURE_LOCKS[featureId]) {
      window.__PLATFORM_FEATURE_LOCKS[featureId].locked = Boolean(res.is_locked_for_free);
    }
    
    showAdminAlert(`Feature '${featureId}' is now ${res.is_locked_for_free ? 'LOCKED for Free tier' : 'UNLOCKED for Free tier'}.`, 'success');
    loadAdmin();
    
    if (typeof applyFeatureLocksToDOM === 'function') {
      applyFeatureLocksToDOM();
    }
  } catch (err) {
    showAdminAlert(err.message || 'Failed to toggle feature lock.', 'error');
  }
}

async function adminUpdateFeatureMinRole(featureId, minRole) {
  try {
    const res = await api('admin/toggle_feature_lock', { feature_id: featureId, min_role: minRole });
    if (res.error) throw new Error(res.error);
    
    showAdminAlert(`Feature '${featureId}' minimum required role updated to ${minRole}.`, 'success');
    loadAdmin();
  } catch (err) {
    showAdminAlert(err.message || 'Failed to update feature required role.', 'error');
  }
}

function showAdminAlert(msg, type) {
  const alertEl = document.getElementById('adm-alert');
  if (!alertEl) return;
  alertEl.textContent = msg;
  alertEl.style.display = 'block';
  if (type === 'success') {
    alertEl.style.background = 'rgba(8,153,129,0.15)';
    alertEl.style.border = '1px solid var(--green)';
    alertEl.style.color = 'var(--green)';
  } else {
    alertEl.style.background = 'rgba(242,54,69,0.15)';
    alertEl.style.border = '1px solid var(--red)';
    alertEl.style.color = 'var(--red)';
  }
}
"""
'''
    with open("pages/page_admin.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("Successfully updated pages/page_admin.py!")

if __name__ == "__main__":
    create_admin_page()
