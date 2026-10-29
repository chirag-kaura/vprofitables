def patch_admin():
    with open("pages/page_admin.py", "r", encoding="utf-8") as f:
        c = f.read()

    # Add search input next to page filter
    t_hdr = """        <div style="display:flex; gap:10px; align-items:center;">
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
        </div>"""

    r_hdr = """        <div style="display:flex; gap:10px; align-items:center; flex-wrap:wrap;">
          <input type="text" id="adm-feature-search" placeholder="🔍 Search feature name/ID..." onkeyup="adminFilterFeatures()" 
                 style="background:var(--p2); border:1px solid var(--border); color:var(--white); padding:6px 12px; font-size:0.78rem; border-radius:4px; width:220px; outline:none;">
          <select id="adm-feature-page-filter" onchange="adminFilterFeatures()" style="background:var(--p2); border:1px solid var(--border); color:var(--white); padding:6px 10px; font-size:0.78rem; border-radius:4px; outline:none;">
            <option value="ALL">All Pages / Tabs (31)</option>
            <option value="advisor">💡 Investment Advisor (15)</option>
            <option value="overview">🏠 Home / Overview (8)</option>
            <option value="scanner">📡 Market Scanner</option>
            <option value="simons">🧠 Simons Lab</option>
            <option value="trading">⚡ Trading Desk</option>
            <option value="sq9">⬛ Square of Nine & Tools</option>
            <option value="dashboard">🪐 Planet Dashboard</option>
            <option value="sentiment">📊 Sentiment & F&O</option>
          </select>
        </div>"""

    c = c.replace(t_hdr, r_hdr).replace(t_hdr.replace('\n', '\r\n'), r_hdr.replace('\n', '\r\n'))

    # Update adminFilterFeatures
    t_func = """function adminFilterFeatures() {
  const pageFilter = document.getElementById('adm-feature-page-filter')?.value || 'ALL';
  if (pageFilter === 'ALL') {
    adminRenderFeatures(_adminCachedFeatures);
    return;
  }
  const filtered = _adminCachedFeatures.filter(f => f.page === pageFilter);
  adminRenderFeatures(filtered);
}"""

    r_func = """function adminFilterFeatures() {
  const pageFilter = document.getElementById('adm-feature-page-filter')?.value || 'ALL';
  const query = (document.getElementById('adm-feature-search')?.value || '').toLowerCase().trim();

  let filtered = _adminCachedFeatures;
  if (pageFilter !== 'ALL') {
    filtered = filtered.filter(f => f.page === pageFilter);
  }
  if (query) {
    filtered = filtered.filter(f => 
      (f.feature_name || '').toLowerCase().includes(query) ||
      (f.feature_id || '').toLowerCase().includes(query) ||
      (f.description || '').toLowerCase().includes(query) ||
      (f.category || '').toLowerCase().includes(query)
    );
  }
  adminRenderFeatures(filtered);
}"""

    c = c.replace(t_func, r_func).replace(t_func.replace('\n', '\r\n'), r_func.replace('\n', '\r\n'))

    with open("pages/page_admin.py", "w", encoding="utf-8") as f:
        f.write(c)
    print("Successfully patched pages/page_admin.py!")
    return True

if __name__ == "__main__":
    patch_admin()
