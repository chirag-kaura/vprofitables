# pages/page_admin.py

HTML = r"""
<!-- ═══════════ PAGE: ADMIN CONSOLE ═══════════ -->
<div class="page" id="page-admin" style="padding:20px; display:none;">
  
  <!-- Header -->
  <div style="margin-bottom:24px; display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid var(--border); padding-bottom:16px;">
    <div>
      <h2 style="font-family:'Orbitron',sans-serif; font-size:1.4rem; color:var(--white); font-weight:700; letter-spacing:1px; margin-bottom:4px;">🛡️ ADMINISTRATOR CONSOLE</h2>
      <p style="font-family:'JetBrains Mono',monospace; font-size:0.75rem; color:var(--dim);">SYSTEM ENVIRONMENT & ROLE-BASED ACCESS CONTROL</p>
    </div>
    <div style="background:rgba(8,153,129,0.1); border:1px solid var(--green); border-radius:4px; padding:6px 12px; font-family:'JetBrains Mono',monospace; font-size:0.75rem; color:var(--green); font-weight:bold;">
      SECURE SESSION
    </div>
  </div>

  <!-- Error / Success Alert -->
  <div id="adm-alert" style="display:none; margin-bottom:20px; padding:12px 16px; border-radius:4px; font-size:0.8rem; font-family:'Inter',sans-serif;"></div>

  <!-- System Health & Stats -->
  <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(200px, 1fr)); gap:16px; margin-bottom:30px;">
    
    <div class="card" style="padding:16px; display:flex; flex-direction:column; justify-content:center; align-items:center; text-align:center;">
      <span style="font-size:0.7rem; color:var(--dim); text-transform:uppercase; letter-spacing:1px; margin-bottom:6px;">Engine Status</span>
      <span id="adm-stat-status" style="font-size:1.4rem; color:var(--green); font-weight:bold; font-family:'Orbitron',sans-serif;">ONLINE</span>
    </div>

    <div class="card" style="padding:16px; display:flex; flex-direction:column; justify-content:center; align-items:center; text-align:center;">
      <span style="font-size:0.7rem; color:var(--dim); text-transform:uppercase; letter-spacing:1px; margin-bottom:6px;">Static Instruments</span>
      <span id="adm-stat-inst" style="font-size:1.4rem; color:var(--white); font-weight:bold; font-family:'JetBrains Mono',monospace;">--</span>
    </div>

    <div class="card" style="padding:16px; display:flex; flex-direction:column; justify-content:center; align-items:center; text-align:center;">
      <span style="font-size:0.7rem; color:var(--dim); text-transform:uppercase; letter-spacing:1px; margin-bottom:6px;">Historical Prices</span>
      <span id="adm-stat-prices" style="font-size:1.4rem; color:var(--white); font-weight:bold; font-family:'JetBrains Mono',monospace;">--</span>
    </div>

    <div class="card" style="padding:16px; display:flex; flex-direction:column; justify-content:center; align-items:center; text-align:center;">
      <span style="font-size:0.7rem; color:var(--dim); text-transform:uppercase; letter-spacing:1px; margin-bottom:6px;">Stored Recommendations</span>
      <span id="adm-stat-recs" style="font-size:1.4rem; color:var(--white); font-weight:bold; font-family:'JetBrains Mono',monospace;">--</span>
    </div>
  </div>

  <div style="display:grid; grid-template-columns:3fr 2fr; gap:24px; align-items:start; margin-bottom:30px;">
    
    <!-- User Management Table -->
    <div class="card" style="padding:20px;">
      <div class="card-title">👥 USER ACCESS MANAGEMENT</div>
      <div style="overflow-x:auto;">
        <table style="width:100%; border-collapse:collapse; text-align:left; font-size:0.8rem; font-family:'Inter',sans-serif;">
          <thead>
            <tr style="border-bottom:1px solid var(--border); color:var(--dim); font-size:0.7rem; text-transform:uppercase; letter-spacing:0.5px;">
              <th style="padding:10px;">Display Name</th>
              <th style="padding:10px;">Email</th>
              <th style="padding:10px;">Auth Method</th>
              <th style="padding:10px;">Role</th>
              <th style="padding:10px; text-align:right;">Actions</th>
            </tr>
          </thead>
          <tbody id="adm-users-table-body">
            <!-- populated via JS -->
          </tbody>
        </table>
      </div>
    </div>

    <!-- Quick Launcher for Advanced Tools -->
    <div class="card" style="padding:20px;">
      <div class="card-title">🚀 ADVANCED ANALYTICAL SUITE LAUNCHER</div>
      <p style="font-size:0.75rem; color:var(--dim); margin-bottom:16px; line-height:1.4;">
        Direct access to quantitative, cyclical, and astro-geocentric modules hidden from normal users.
      </p>
      
      <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px;" id="adm-launcher-grid">
         <button class="btn" style="padding:10px 8px; font-size:0.75rem; text-align:left;" onclick="nav('scanner')">📡 Market Scanner</button>
         <button class="btn" style="padding:10px 8px; font-size:0.75rem; text-align:left;" onclick="nav('dashboard')">🪐 Planet Dashboard</button>
         <button class="btn" style="padding:10px 8px; font-size:0.75rem; text-align:left;" onclick="nav('chart')">📈 Chart + S/R</button>
         <button class="btn" style="padding:10px 8px; font-size:0.75rem; text-align:left;" onclick="nav('simons')">🧠 Simons Lab</button>
         <button class="btn" style="padding:10px 8px; font-size:0.75rem; text-align:left;" onclick="nav('analyze')">🔬 Gann Analysis</button>
         <button class="btn" style="padding:10px 8px; font-size:0.75rem; text-align:left;" onclick="nav('natal')">🔭 Natal Charts</button>
         <button class="btn" style="padding:10px 8px; font-size:0.75rem; text-align:left;" onclick="nav('sq9')">⬛ Square of Nine</button>
         <button class="btn" style="padding:10px 8px; font-size:0.75rem; text-align:left;" onclick="nav('cycles')">⏰ Time Cycles</button>
         <button class="btn" style="padding:10px 8px; font-size:0.75rem; text-align:left;" onclick="nav('confluence')">⚡ Confluence</button>
         <button class="btn" style="padding:10px 8px; font-size:0.75rem; text-align:left;" onclick="nav('instruments')">📋 Instruments DB</button>
      </div>
    </div>
  </div>

</div>
"""

JS = r"""
async function loadAdmin() {
  const alertEl = document.getElementById('adm-alert');
  if (alertEl) alertEl.style.display = 'none';

  try {
    const res = await api('admin/users');
    if (res.error) throw new Error(res.error);

    // Update stats
    document.getElementById('adm-stat-status').textContent = res.stats.engine_status;
    document.getElementById('adm-stat-inst').textContent = res.stats.instruments.toLocaleString();
    document.getElementById('adm-stat-prices').textContent = res.stats.prices.toLocaleString();
    document.getElementById('adm-stat-recs').textContent = res.stats.recommendations.toLocaleString();

    // Render User Table
    const tbody = document.getElementById('adm-users-table-body');
    tbody.innerHTML = '';

    res.users.forEach(u => {
      const tr = document.createElement('tr');
      tr.style.borderBottom = '1px solid var(--border)';
      
      const isCurrentUser = u.email === localStorage.getItem('user_email');
      const badgeStyle = u.role === 'ADMIN' ? 'background:rgba(255,152,0,0.15); color:var(--gold);' : 'background:rgba(255,255,255,0.05); color:var(--text);';
      
      let actionBtnHtml = '';
      if (!isCurrentUser) {
         if (u.role === 'ADMIN') {
           actionBtnHtml = `<button onclick="adminToggleRole('${u.id}', 'USER')" class="btn-red" style="padding:4px 8px; font-size:0.65rem; border-radius:3px; cursor:pointer;">DEMOTE</button>`;
         } else {
           actionBtnHtml = `<button onclick="adminToggleRole('${u.id}', 'ADMIN')" class="btn-gold" style="padding:4px 8px; font-size:0.65rem; border-radius:3px; cursor:pointer;">PROMOTE</button>`;
         }
      } else {
         actionBtnHtml = `<span style="font-size:0.65rem; color:var(--dim); font-family:'JetBrains Mono',monospace;">YOU</span>`;
      }

      tr.innerHTML = `
        <td style="padding:10px; font-weight:bold; color:var(--white);">${u.display_name || 'No Name'}</td>
        <td style="padding:10px; font-family:'JetBrains Mono',monospace;">${u.email}</td>
        <td style="padding:10px; font-size:0.75rem; text-transform:uppercase;">${u.auth_method}</td>
        <td style="padding:10px;"><span class="badge" style="font-size:0.65rem; padding:2px 6px; border-radius:3px; ${badgeStyle}">${u.role}</span></td>
        <td style="padding:10px; text-align:right;">${actionBtnHtml}</td>
      `;
      tbody.appendChild(tr);
    });

  } catch (err) {
    showAdminAlert(err.message || 'Failed to load administrator dashboard data', 'error');
  }
}

async function adminToggleRole(userId, newRole) {
  const alertEl = document.getElementById('adm-alert');
  if (alertEl) alertEl.style.display = 'none';

  try {
    const res = await api('admin/update_role', { user_id: userId, role: newRole });
    if (res.error) throw new Error(res.error);
    
    showAdminAlert(`Successfully updated user role to ${newRole}.`, 'success');
    loadAdmin();
  } catch (err) {
    showAdminAlert(err.message || 'Failed to update user role.', 'error');
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
