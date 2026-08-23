// ════════════════════════════════════════════════════════════════════
// Global fetch interceptor to inject Authorization headers for all /api/ calls
(function() {
  const originalFetch = window.fetch;
  window.fetch = function(input, init) {
    let url = '';
    if (typeof input === 'string') {
      url = input;
    } else if (input && input.url) {
      url = input.url;
    }
    const token = localStorage.getItem('token');
    if (token && (url.startsWith('/api/') || url.includes('/api/'))) {
      init = init || {};
      init.headers = init.headers || {};
      if (typeof init.headers.set === 'function') {
        if (!init.headers.has('Authorization')) {
          init.headers.set('Authorization', 'Bearer ' + token);
        }
      } else if (Array.isArray(init.headers)) {
        const hasAuth = init.headers.some(h => h[0].toLowerCase() === 'authorization');
        if (!hasAuth) {
          init.headers.push(['Authorization', 'Bearer ' + token]);
        }
      } else {
        const hasAuth = Object.keys(init.headers).some(k => k.toLowerCase() === 'authorization');
        if (!hasAuth) {
          init.headers['Authorization'] = 'Bearer ' + token;
        }
      }
    }
    return originalFetch.call(this, input, init);
  };
})();

const _now  = Date.now() + (5.5 * 3600000);
const _ist  = new Date(_now);
const today = _ist.getFullYear()+'-'+String(_ist.getMonth()+1).padStart(2,'0')+'-'+String(_ist.getDate()).padStart(2,'0');
let allSymbols = [];
let GANN_DATE = today;
function getDate() { return GANN_DATE; }
function setGlobalDate(d) {
  GANN_DATE = d;
  const inp=document.getElementById('global-date'), badge=document.getElementById('backtest-badge');
  const todayBtn=document.getElementById('today-btn'), hint=document.getElementById('datebar-hint');
  const datebar=document.getElementById('global-datebar'); const isBack=d!==today;
  if(inp) inp.value=d;
  if(isBack){
    if(badge) badge.style.display='inline-block';
    if(todayBtn){todayBtn.style.color='var(--orange)';todayBtn.style.borderColor='var(--orange)';todayBtn.textContent='\u21A9 TODAY';}
    if(hint) hint.style.display='none';
    if(datebar){datebar.style.borderBottomColor='var(--orange)';datebar.style.background='rgba(255,136,0,0.05)';}
  } else {
    if(badge) badge.style.display='none';
    if(todayBtn){todayBtn.style.color='var(--dim)';todayBtn.style.borderColor='var(--b2)';todayBtn.textContent='TODAY';}
    if(hint) hint.style.display='';
    if(datebar){datebar.style.borderBottomColor='';datebar.style.background='';}
  }
  const lbl=document.getElementById('dash-date-label'); if(lbl) lbl.textContent=d;
  const tag=document.getElementById('dash-live-tag'); if(tag){tag.textContent=isBack?'BACKTEST':'LIVE';tag.style.color=isBack?'var(--orange)':'';}
  const sd=document.getElementById('sideDate'); if(sd) sd.textContent=d+(isBack?'  \u23EA':'');
}
function onGlobalDateChange(d){if(!d)return;setGlobalDate(d);reloadActivePage();}
function setGlobalDateToday(){setGlobalDate(today);reloadActivePage();}
function stepDate(dir){
  const dt=new Date(GANN_DATE+'T00:00:00'); dt.setDate(dt.getDate()+dir);
  const nd=dt.getFullYear()+'-'+String(dt.getMonth()+1).padStart(2,'0')+'-'+String(dt.getDate()).padStart(2,'0');
  setGlobalDate(nd); reloadActivePage();
}
function reloadActivePage(){
  const ap=document.querySelector('.page.active'); if(!ap) return;
  const pid=ap.id.replace('page-',''); syncDateFields();
  if(pid==='dashboard') loadDashboard();
  else if(pid==='scanner') loadScanner();
  else if(pid==='chart'){const s=document.getElementById('chart-sym')?.value;if(s)loadChart();}
  else if(pid==='simons'){const s=document.getElementById('simons-sym')?.value;if(s)loadSimons();}
  else if(pid==='analyze') fillPriceFromDB('az-sym','az-price');
  else if(pid==='natal'){const s=document.getElementById('natal-sym')?.value;if(s)loadNatal();}
}
function syncDateFields(){
  ['dash-date','az-date','natal-date','chart-date','simons-date'].forEach(id=>{const el=document.getElementById(id);if(el)el.value=GANN_DATE;});
}
async function fillPriceFromDB(symId,priceId){
  const token = localStorage.getItem('token');
  if (!token) return;
  const sym=document.getElementById(symId)?.value; if(!sym) return;
  try{const d=await api('price',{symbol:sym,date:GANN_DATE});const el=document.getElementById(priceId);if(el&&d.close)el.value=d.close;}catch(e){}
}
function backtestBanner(){
  if(GANN_DATE===today) return '';
  return '<div style="display:flex;align-items:center;gap:10px;padding:8px 14px;margin-bottom:14px;background:rgba(255,136,0,0.08);border:1px solid var(--orange);border-radius:3px;font-family:\'Share Tech Mono\',monospace;font-size:0.72rem;">'+
    '<span style="color:var(--orange);font-size:1rem;">&#9194;</span>'+
    '<span style="color:var(--orange);letter-spacing:1px;font-weight:600;">BACKTEST MODE</span>'+
    '<span style="color:var(--dim);">&#8212;</span>'+
    '<span style="color:var(--gold);">Viewing data as of <b>'+GANN_DATE+'</b></span>'+
    '<span style="color:var(--dim);margin-left:auto;font-size:0.65rem;">All prices, signals and analysis reflect this historical date</span>'+
    '<button onclick="setGlobalDateToday()" style="background:var(--orange);border:none;color:#000;padding:2px 10px;font-family:\'Share Tech Mono\',monospace;font-size:0.65rem;cursor:pointer;font-weight:700;letter-spacing:1px;">RETURN TO LIVE</button></div>';
}

// ── DB Coverage badge ────────────────────────────────────────────────────
// Shows how many rows we have for the current symbol, and a download button
async function refreshDbBadge(sym, badgeId) {
  const token = localStorage.getItem('token');
  if (!token) return;
  if (!sym || !badgeId) return;
  const el = document.getElementById(badgeId);
  if (!el) return;
  try {
    const d = await api('history_status');
    const found = (d.symbols || []).find(s => s.symbol === sym);
    if (found && found.rows > 30) {
      const yrs = ((new Date(found.to) - new Date(found.from)) / 86400000 / 365).toFixed(1);
      el.innerHTML = `<span style="color:#00e5ff;font-size:0.75rem;">📊 ${found.rows.toLocaleString()} rows · ${yrs}yr · ${found.from} → ${found.to}</span>`;
    } else {
      const noData = found ? `only ${found.rows} rows` : 'no data';
      el.innerHTML = `<span style="color:#ff9800;font-size:0.75rem;cursor:pointer;" onclick="triggerDownload('${sym}',this)">⬇ ${noData} — click to download full history</span>`;
    }
  } catch(e) { el.innerHTML = ''; }
}

async function triggerDownload(sym, el) {
  if (el) { el.style.opacity='0.5'; el.textContent = `⬇ Downloading ${sym}...`; }
  try {
    const r = await api('download_trigger', {symbol: sym});
    if (el) { el.style.opacity='1'; el.textContent = `⬇ ${r.message || 'Download started'} — refresh in 30s`; }
  } catch(e) {
    if (el) { el.textContent = '⬇ Download error: ' + e; }
  }
}

async function api(endpoint, params={}) {
  const NO_DATE=['all_symbols','save_pivot','scheduler_status','scheduler_trigger','history_status','download_trigger',
    'portfolio_get','portfolio_add','portfolio_close','portfolio_modify','portfolio_partial_exit','portfolio_csv',
    'watchlist_get','watchlist_add','watchlist_remove','market_depth','price_history',
    'alert_get','alert_set','alert_delete','alert_check',
    'risk_dashboard','risk_settings_get','risk_settings_save','correlation_matrix',
    'analytics_data','analytics_whatsapp_report', 'onboarding/check', 'onboarding/submit', 'auth/login', 'auth/signup',
    'recommendations', 'recommendations/feedback', 'gann_track_record'];
  if(!NO_DATE.includes(endpoint)&&!params.date) params={...params,date:GANN_DATE};

  const token = localStorage.getItem('token');
  const publicEndpoints = ['all_symbols', 'ticker', 'auth/login', 'auth/signup', 'auth/google', 'config'];
  if (!token && !publicEndpoints.includes(endpoint)) {
    throw new Error('Authentication required (no token present)');
  }

  const headers = {};
  if (token) {
    headers['Authorization'] = 'Bearer ' + token;
  }

  const isPost = endpoint.startsWith('auth/') || endpoint === 'onboarding/submit' || endpoint === 'recommendations/feedback';
  let url = `/api/${endpoint}`;
  let options = { headers };

  if (isPost) {
    options.method = 'POST';
    options.headers['Content-Type'] = 'application/json';
    options.body = JSON.stringify(params);
  } else {
    const qs=new URLSearchParams(params).toString();
    url += qs ? '?' + qs : '';
    options.method = 'GET';
  }

  try {
    const r = await fetch(url, options);
    if (!r.ok) throw new Error('HTTP ' + r.status);
    const d = await r.json();
    if (d.error) throw new Error(d.error);
    return d;
  } catch(e) {
    console.error('API [' + endpoint + ']:', e.message);
    throw e;
  }
}

function toggleSidebar() {
  const sb = document.getElementById('app-sidebar');
  const ov = document.querySelector('.sidebar-overlay');
  if(sb) sb.classList.toggle('open');
  if(ov) ov.classList.toggle('show');
  // Freeze main scroll so it can't steal touch events from the open sidebar
  document.body.classList.toggle('sidebar-open', sb ? sb.classList.contains('open') : false);
}

function nav(page, skipHistory = false) {
  const role = localStorage.getItem('user_role') || 'USER';
  const adminPages = ['admin', 'scanner', 'dashboard', 'simons', 'analyze', 'natal', 'sq9', 'cycles', 'confluence', 'instruments', 'risk', 'analytics', 'research'];
  if (adminPages.includes(page) && role !== 'ADMIN') {
    console.warn("RBAC Intercept: Access to page '" + page + "' denied.");
    if (page === 'overview') return;
    nav('overview', true);
    return;
  }

  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  const pg = document.getElementById('page-' + page);
  if (!pg) { console.warn('No page element: page-' + page); return; }
  pg.classList.add('active');
  // Scroll .main to top so page content always shows at top of viewport
  const mainEl = document.querySelector('.main');
  if (mainEl) mainEl.scrollTop = 0;
  document.querySelectorAll('.nav-item').forEach(n => {
    if (n.getAttribute('onclick') && n.getAttribute('onclick').includes(`'${page}'`))
      n.classList.add('active');
  });
  
  // Close sidebar if on mobile
  if (window.innerWidth <= 900) {
    const sb = document.getElementById('app-sidebar');
    const ov = document.querySelector('.sidebar-overlay');
    if(sb) sb.classList.remove('open');
    if(ov) ov.classList.remove('show');
    document.body.classList.remove('sidebar-open');
  }

  // Update URL history & Page Title
  const titleMap = {
    'overview': 'Market Overview',
    'advisor': 'Investment Advisor',
    'scanner': 'Market Scanner',
    'dashboard': 'Planet Dashboard',
    'chart': 'Chart + S/R',
    'simons': 'Simons Lab',
    'analyze': 'Gann Analysis',
    'natal': 'Natal Charts',
    'fundamentals': 'Fundamentals',
    'sentiment': 'Sentiment',
    'sq9': 'Square of Nine',
    'cycles': 'Time Cycles',
    'confluence': 'Confluence',
    'instruments': 'Instruments DB',
    'trading': 'Trading Desk',
    'risk': 'Risk Management',
    'watchlist': 'Watchlist',
    'analytics': 'Analytics',
    'research': 'Equity Research',
    'admin': 'Admin Dashboard',
  };
  if (titleMap[page]) {
    document.title = `Vprofitables — ${titleMap[page]}`;
  } else {
    document.title = `Vprofitables`;
  }

  if (!skipHistory) {
    window.history.pushState({ page: page }, document.title, `#${page}`);
  }
  
  if (typeof trackPageHistory === 'function') {
    trackPageHistory(page, titleMap[page] || page);
  }

  // Load triggers — every page that needs data

  if (page === 'overview')    loadOverview();
  if (page === 'admin')       loadAdmin();
  if (page === 'dashboard')   loadDashboard();
  if (page === 'scanner')     loadScanner();
  if (page === 'scheduler')   loadScheduler();
  if (page === 'instruments') loadInstrumentsPage();
  if (page === 'fundamentals') initFundamentalsPage();
  if (page === 'trading') { tradingTab('backtest'); initTradingPage(); }
  if (page === 'risk')    { initRiskPage(); }
  if (page === 'watchlist') { if(typeof initWatchlist==='function') initWatchlist(); }
  if (page === 'analytics') { if(typeof initAnalytics==='function') initAnalytics(); }
  if (page === 'sentiment') initSentimentPage();
  if(['chart','analyze','natal','simons','sq9','cycles','confluence','advisor'].includes(page)){
    if(page==='confluence') setTimeout(function(){if(typeof initConfluence==='function')initConfluence();},200);
    syncDateFields();
    if(typeof initSymbols==='function'&&allSymbols.length===0) initSymbols();
    if(page==='natal')   setTimeout(function(){if(typeof loadNatal==='function')loadNatal();},400);
    if(page==='analyze') setTimeout(function(){onAzSymChange();},400);
    if(page==='chart')   setTimeout(function(){const s=document.getElementById('chart-sym')?.value;if(s)loadChart();},400);
    if(page==='simons')  setTimeout(function(){const s=document.getElementById('simons-sym')?.value;if(s)loadSimons();},400);
    if(page==='advisor') setTimeout(function(){if(typeof runAdvisor==='function'){const btn=document.getElementById('advisor-scan-btn');if(btn&&!document.getElementById('advisor-results')?.innerHTML?.trim())btn.click();}},500);
  }
}

let appPageHistory = [];
try {
  const st = sessionStorage.getItem('appPageHistory');
  if (st) appPageHistory = JSON.parse(st);
} catch(e) {}

function trackPageHistory(pageId, pageTitle) {
  appPageHistory = appPageHistory.filter(p => p.id !== pageId);
  appPageHistory.push({ id: pageId, title: pageTitle });
  if (appPageHistory.length > 8) {
    appPageHistory.shift();
  }
  try { sessionStorage.setItem('appPageHistory', JSON.stringify(appPageHistory)); } catch(e){}
  renderBreadcrumbs();
}

function renderBreadcrumbs() {
  const bc = document.getElementById('global-breadcrumbs');
  if (!bc) return;
  if (appPageHistory.length <= 1) {
    bc.style.display = 'none';
    return;
  }
  bc.style.display = 'flex';
  
  let html = '';
  appPageHistory.forEach((p, idx) => {
    const isLast = (idx === appPageHistory.length - 1);
    if (idx > 0) {
      html += `<span class="bc-sep">/</span>`;
    }
    const cls = isLast ? 'bc-item active' : 'bc-item';
    const click = isLast ? '' : `onclick="nav('${p.id}')"`;
    html += `<span class="${cls}" ${click}>${p.title}</span>`;
  });
  bc.innerHTML = html;
  setTimeout(() => { bc.scrollLeft = bc.scrollWidth; }, 50);
}


function setDate(id, d) {
  const el = document.getElementById(id);
  if (el) el.value = d || today;
}

function loading(id, show) {
  var _e=document.getElementById(id); if(_e) _e.style.display=show?'flex':'none';
}

function show(id, visible) {
  var _e=document.getElementById(id); if(_e) _e.style.display=(visible!==false)?'block':'none';
}

const PC = {Sun:'#FFD700',Moon:'#C0C0C0',Mercury:'#B5B5FF',Venus:'#FFB6C1',
  Mars:'#FF6B6B',Jupiter:'#FFA500',Saturn:'#DEB887',Uranus:'#7FFFD4',
  Neptune:'#6495ED',Pluto:'#9370DB',Rahu:'#888',Ketu:'#8B4513'};

function pcolor(name) { return PC[name] || 'var(--t2)'; }
function natureClass(n) { return n==='BULLISH'?'bull':n==='BEARISH'?'bear':'neut'; }

// Populate all symbol selectors
async function initSymbols() {
  try {
    const d = await api('all_symbols');
    // Normalise: each item may be {symbol,name} or plain string
    const _sym = x => typeof x === 'object' ? x.symbol : x;
    const _lbl = x => typeof x === 'object' ? (x.symbol + (x.name ? ' — ' + x.name : '')) : x;
    allSymbols = [...d.indices, ...d.equities, ...d.commodities].map(_sym);
    try{sessionStorage.setItem('allSymbols',JSON.stringify(allSymbols));}catch(e){}

    // Map each select to its {priceInputId, badgeId}
    const selMap = {
      'chart-sym':  { price:'chart-price',   badge:'chart-price-badge'  },
      'simons-sym': { price:'simons-price',  badge:'simons-price-badge' },
      'az-sym':     { price:'az-price',      badge:'az-price-badge'     },
      'natal-sym':  { price: null,           badge: null                },
    };
    Object.entries(selMap).forEach(([id, {price, badge}]) => {
      const sel = document.getElementById(id);
      if (!sel) return;
      sel.innerHTML = '';
      [['Indices', d.indices], ['Equities', d.equities], ['Commodities', d.commodities]].forEach(([grp, syms]) => {
        const og = document.createElement('optgroup');
        og.label = grp;
        syms.forEach(s => { const o = document.createElement('option'); o.value = _sym(s); o.textContent = _lbl(s); og.appendChild(o); });
        sel.appendChild(og);
      });
    });

    // Build chips — each chip auto-fetches price then optionally fires a callback
    buildChips('simons-chips',
      [...d.indices.slice(0,6), ...d.equities.slice(0,10), ...d.commodities.slice(0,3)].map(_sym),
      'simons-sym',
      () => autoFetchPrice('simons-sym','simons-price','simons-price-badge'));

    // analyze-chips intentionally empty — symbol dropdown has all 257 instruments

    // natal-chips intentionally empty — symbol dropdown has all 257 instruments

    // Check if token exists before calling authenticated endpoints on startup
    const token = localStorage.getItem('token');
    if (!token) return;

    // Auto-fetch price for the default selected symbol on each page
    autoFetchPrice('chart-sym',  'chart-price',  'chart-price-badge');
    // Refresh DB coverage badges for default symbols on startup
    const _defChartSym = document.getElementById('chart-sym')?.value;
    const _defSimSym   = document.getElementById('simons-sym')?.value;
    const _defAzSym    = document.getElementById('az-symbol')?.value;
    if (_defChartSym) refreshDbBadge(_defChartSym, 'chart-db-badge');
    // simons-db-badge hidden (not needed)
    if (_defAzSym)    refreshDbBadge(_defAzSym,    'az-db-badge');
    autoFetchPrice('simons-sym', 'simons-price', 'simons-price-badge');
    onAzSymChange(); // load pivot dropdown on startup
  } catch(e) { console.error('initSymbols', e); }
}

function buildChips(containerId, symbols, selectId, callback) {
  const el = document.getElementById(containerId);
  if (!el) return;
  el.innerHTML = '';
  symbols.forEach(s => {
    const chip = document.createElement('div');
    chip.className = 'chip';
    chip.textContent = s;
    chip.onclick = () => {
      el.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      const sel = document.getElementById(selectId);
      if (sel) sel.value = s;
      if (callback) callback();
    };
    el.appendChild(chip);
  });
}

// ── Auto-fetch price when symbol changes ──────────────────────────────────
// ── Pivot dropdown state ──────────────────────────────────────────
let _azPivots = [];   // [{label, price, date, source, description}]

async function onAzSymChange() {
  const token = localStorage.getItem('token');
  if (!token) return;
  const _azEl = document.getElementById('az-sym');
  if (!_azEl) return; // not on this page
  const sym = _azEl.value;
  if (!sym) return;

  // 1. Fetch price (async, non-blocking)
  autoFetchPrice('az-sym','az-price','az-price-badge');

  // Load instrument info to get the auto-detected swing pivot or static fallback (Fix 1)
  let infoPivot = null;
  try {
    const info = await api('instrument_info', { symbol: sym });
    if (info && info.pivot_price) {
      infoPivot = {
        label: info.pivot_label || 'SWING_LOW',
        price: info.pivot_price,
        date: info.pivot_date,
        source: info.pivot_source,
        description: `Auto-fill: ${info.pivot_label} (${info.pivot_source})`
      };
      
      // Update fields
      document.getElementById('az-pivot').value = info.pivot_price;
      document.getElementById('az-pdate').value  = info.pivot_date || '';
      
      const descEl = document.getElementById('az-pivot-desc');
      if (descEl) {
        const SOURCE_ICON = { static_fallback:'📌', auto_detected:'🤖', user_defined:'⭐' };
        descEl.textContent = `${SOURCE_ICON[info.pivot_source] || '🤖'} Source: ${info.pivot_source.toUpperCase()} (${info.pivot_label})`;
      }
    }
  } catch(e) {
    console.error("Error fetching instrument info", e);
  }

  // 2. Load all pivot levels for this symbol
  try {
    const d = await api('pivots_for_symbol', { symbol: sym });
    _azPivots = d.pivots || [];
    
    // If we have an auto-detected pivot, merge it if not already present
    if (infoPivot && !_azPivots.some(p => p.label === infoPivot.label)) {
      _azPivots.unshift(infoPivot);
    }
    
    buildPivotDropdown(_azPivots);
    
    // Auto-select preference
    const preferred = ['RECENT_SWING_LOW','LAST_SWING_LOW','MAJOR_BOTTOM_LOW','ATL', infoPivot ? infoPivot.label : ''];
    const best = preferred.find(l => l && _azPivots.some(p => p.label === l));
    if (best) {
      document.getElementById('az-pivot-select').value = best;
      applyPivot(best);
    }
  } catch(e) {
    // If pivots_for_symbol fails, we already have infoPivot loaded!
  }
}

function buildPivotDropdown(pivots) {
  const sel = document.getElementById('az-pivot-select');
  if (!sel) return;

  // ── Label config: display name + emoji + group (LOW / HIGH / OTHER) ──
  const META = {
    // LOWS
    ATL:                 { icon:'📌', name:'All-Time Low (ATL)',         group:'LOW',   groupLabel:'── LOWS ──' },
    MAJOR_BOTTOM_LOW:    { icon:'🔻', name:'Major Bottom',               group:'LOW' },
    RECENT_SWING_LOW:    { icon:'📉', name:'Recent Swing Low (12m)',      group:'LOW' },
    LAST_SWING_LOW:      { icon:'↩', name:'Last Swing Low (6m)',         group:'LOW' },
    // HIGHS
    ATH:                 { icon:'📌', name:'All-Time High (ATH)',         group:'HIGH',  groupLabel:'── HIGHS ──' },
    MAJOR_TOP:           { icon:'🔺', name:'Major Top',                   group:'HIGH' },
    RECENT_SWING_HIGH:   { icon:'📈', name:'Recent Swing High (12m)',     group:'HIGH' },
    LAST_SWING_HIGH:     { icon:'↪', name:'Last Swing High (6m)',        group:'HIGH' },
  };
  const LOW_ORDER  = ['ATL','MAJOR_BOTTOM_LOW','RECENT_SWING_LOW','LAST_SWING_LOW'];
  const HIGH_ORDER = ['ATH','MAJOR_TOP','RECENT_SWING_HIGH','LAST_SWING_HIGH'];
  const SOURCE_TAG = { STATIC:'', STATIC_VERIFIED:' ·VERIFIED', AUTO_VERIFIED:' ·DB-VERIFIED', AUTO:' ·AUTO', USER:' ·SAVED' };

  sel.innerHTML = '<option value="">— select pivot view —</option>';

  // helper: add an <optgroup>-style disabled separator
  function addSep(txt) {
    const o = document.createElement('option');
    o.disabled = true;
    o.textContent = txt;
    o.style.color = '#3a6a8a';
    o.style.fontSize = '0.6rem';
    sel.appendChild(o);
  }

  function addPivotOpt(p) {
    const m   = META[p.label] || { icon:'⭐', name: p.label, group:'OTHER' };
    const opt = document.createElement('option');
    opt.value = p.label;
    opt.textContent =
      m.icon + ' ' + m.name +
      '   ' + Number(p.price).toLocaleString('en-IN', {maximumFractionDigits:2}) +
      '  (' + p.date + ')' + (SOURCE_TAG[p.source] || '');
    sel.appendChild(opt);
  }

  // ── LOW group ──
  const lowPivots = LOW_ORDER.map(l => pivots.find(p => p.label === l)).filter(Boolean);
  if (lowPivots.length) {
    addSep('─── SUPPORT PIVOTS (LOWS) ───');
    lowPivots.forEach(addPivotOpt);
  }

  // ── HIGH group ──
  const highPivots = HIGH_ORDER.map(l => pivots.find(p => p.label === l)).filter(Boolean);
  if (highPivots.length) {
    addSep('─── RESISTANCE PIVOTS (HIGHS) ───');
    highPivots.forEach(addPivotOpt);
  }

  // ── User custom pivots not in standard lists ──
  const knownLabels = [...LOW_ORDER, ...HIGH_ORDER];
  const customPivots = pivots.filter(p => !knownLabels.includes(p.label));
  if (customPivots.length) {
    addSep('─── YOUR SAVED PIVOTS ───');
    customPivots.forEach(addPivotOpt);
  }

  // ── Manual entry option ──
  addSep('');
  const manOpt = document.createElement('option');
  manOpt.value = '__CUSTOM__';
  manOpt.textContent = '✏  Enter custom pivot manually...';
  sel.appendChild(manOpt);
}

function onPivotSelectChange() {
  const sel   = document.getElementById('az-pivot-select');
  const label = sel.value;
  if (!label) return;

  if (label === '__CUSTOM__') {
    // Show save row, clear fields for manual entry
    document.getElementById('az-save-pivot-row').style.display = 'flex';
    document.getElementById('az-pivot').value = '';
    document.getElementById('az-pdate').value  = '';
    return;
  }
  document.getElementById('az-save-pivot-row').style.display = 'none';
  applyPivot(label);
}

function applyPivot(label) {
  const pv = _azPivots.find(p => p.label === label);
  if (!pv) return;

  const priceEl = document.getElementById('az-pivot');
  const dateEl  = document.getElementById('az-pdate');

  priceEl.value = pv.price;
  dateEl.value  = pv.date;

  // Flash gold
  [priceEl, dateEl].forEach(el => {
    el.style.borderColor = 'var(--gold)';
    el.style.boxShadow   = '0 0 8px rgba(255,204,0,0.25)';
    setTimeout(() => { el.style.borderColor=''; el.style.boxShadow=''; }, 1200);
  });

  // Show description
  const SOURCE_ICON = { STATIC:'📌', AUTO:'🤖', USER:'⭐' };
  const descEl = document.getElementById('az-pivot-desc');
  if (descEl) descEl.textContent = (SOURCE_ICON[pv.source]||'') + ' ' + (pv.description || label);
}

function onManualPivotEdit() {
  // If user manually edits pivot fields, switch dropdown to custom
  const sel = document.getElementById('az-pivot-select');
  if (sel) sel.value = '__CUSTOM__';
  document.getElementById('az-save-pivot-row').style.display = 'flex';
}

async function saveCustomPivot() {
  const sym    = document.getElementById('az-sym').value;
  const price  = parseFloat(document.getElementById('az-pivot').value);
  const dt     = document.getElementById('az-pdate').value;
  const label  = (document.getElementById('az-custom-label').value || 'CUSTOM').toUpperCase().replace(/\s+/g,'_');
  if (!sym || !price || !dt) return;

  try {
    await api('save_pivot', { symbol: sym, label, price, date: dt,
      description: label + ' — User defined pivot' });
    // Refresh pivot list
    const d = await api('pivots_for_symbol', { symbol: sym });
    _azPivots = d.pivots || [];
    buildPivotDropdown(_azPivots);
    document.getElementById('az-pivot-select').value = label;
    applyPivot(label);
    // Show confirm
    const confirm = document.getElementById('az-save-confirm');
    confirm.style.display = 'inline';
    setTimeout(() => { confirm.style.display='none'; }, 2500);
  } catch(e) { console.error('save pivot', e); }
}

async function autoFetchPrice(selectId, priceInputId, badgeId) {
  const token = localStorage.getItem('token');
  if (!token) return;
  const selEl = document.getElementById(selectId);
  if (!selEl) return; // element doesn't exist (e.g. called from CW tab)
  const sym   = selEl.value;
  const input = document.getElementById(priceInputId);
  const badge = document.getElementById(badgeId);
  if (!sym || !input) return;

  input.style.opacity = '0.5';
  if (badge) {
    badge.style.display='inline'; badge.textContent='...';
    badge.style.background='rgba(58,90,112,0.3)'; badge.style.color='var(--dim)';
    badge.style.border='1px solid var(--border)';
  }
  try {
    const d = await api('price', { symbol: sym });
    input.style.opacity = '1';

    const src = d.source || '';

    if (src === 'EOD_CACHE' || src === 'LIVE') {
      // ── REAL price from market_data.db ──────────────────────────
      input.value = d.price;
      input.placeholder = '';

      // Gold flash to signal fresh data
      input.style.borderColor = 'var(--gold)';
      input.style.boxShadow   = '0 0 12px rgba(255,204,0,0.35)';
      setTimeout(() => { input.style.borderColor=''; input.style.boxShadow=''; }, 1600);

      if (badge) {
        const chg     = d.change_pct != null ? d.change_pct : 0;
        const isPos   = chg > 0;
        const isNeg   = chg < 0;
        const arrow   = isPos ? '▲' : isNeg ? '▼' : '';
        const chgStr  = chg !== 0 ? (' ' + arrow + Math.abs(chg).toFixed(2) + '%') : '';
        // Color: green if positive, red if negative, cyan if flat
        const col     = isPos ? '#00ff88' : isNeg ? '#ff3355' : 'var(--cyan)';
        const bg      = isPos ? 'rgba(0,255,136,0.08)' : isNeg ? 'rgba(255,51,85,0.08)' : 'rgba(0,212,255,0.08)';
        const bdr     = isPos ? 'rgba(0,255,136,0.25)'  : isNeg ? 'rgba(255,51,85,0.25)'  : 'rgba(0,212,255,0.2)';
        if (src === 'LIVE') {
          badge.style.background='rgba(0,255,136,0.12)'; badge.style.color='#00ff88';
          badge.style.border='1px solid rgba(0,255,136,0.3)';
          badge.textContent = '● LIVE' + chgStr;
        } else {
          // EOD_CACHE — date + colored change
          const dt = d.date ? d.date.slice(5).replace('-','/') : '';
          badge.style.background = bg;
          badge.style.border     = '1px solid ' + bdr;
          // Badge base color is cyan for label, but change part gets colored inline
          badge.style.color = 'var(--cyan)';
          badge.innerHTML = '● EOD ' + dt +
            (chg !== 0
              ? ' <span style="color:' + col + ';font-weight:600;">' + arrow + Math.abs(chg).toFixed(2) + '%</span>'
              : '');
        }
        badge.style.display = 'inline';
      }

    } else {
      // ── NO DB PRICE yet (FALLBACK / NO_YF) ─────────────────────
      // Leave input EMPTY — never fill with a fake value
      input.value = '';
      input.placeholder = 'enter price';
      input.style.borderColor = 'rgba(255,51,85,0.4)';
      setTimeout(() => { input.style.borderColor=''; }, 2000);

      if (badge) {
        badge.style.background='rgba(255,51,85,0.08)';
        badge.style.color='var(--red)';
        badge.style.border='1px solid rgba(255,51,85,0.25)';
        badge.textContent = src === 'NO_YF' ? '○ NO YF' : '⚠ RUN app.py';
        badge.style.display = 'inline';
      }
    }
  } catch(e) {
    input.style.opacity = '1';
    if (badge) { badge.textContent='ERR'; badge.style.color='var(--red)'; badge.style.display='inline'; }
  }
}

function onChartSymChange() {
  autoFetchPrice('chart-sym','chart-price','chart-price-badge');
  const sym = document.getElementById('chart-sym').value;
  if (sym) refreshDbBadge(sym, 'chart-db-badge');
}

// ── Chart window auto-restore ─────────────────────────────────────────────
// Called on DOMContentLoaded when page is opened with ?chartWindow=1
function _maybeRestoreChartWindow() {
  if (!window._chartWindowMode) return;
  const raw = sessionStorage.getItem('tvChartState');
  nav('chart');
  if (!raw) return;
  setTimeout(function() {
    try {
      const state = JSON.parse(raw);
      if (state.chartType)  TV.chartType = state.chartType;
      if (state.indicators) Object.assign(TV.indicators, state.indicators);
      if (state.params) {
        Object.assign(TV.params, state.params);
        if (state.params.smaP) TV.params.smaP = [...state.params.smaP];
      }
      if (state.view) Object.assign(TV.view, state.view);
      if (state.data) {
        TV.data = state.data;
        const symEl = document.getElementById('tv-summary-sym');
        if (symEl && state.sym) symEl.textContent = state.sym;
        loading('chart-loading', false);
        show('chart-content');
        const total = (TV.data.closes || []).length;
        TV.mainH = 460; TV._eventsAttached = false;
        TV.yRange = {min:null, max:null};
        const wrap = document.getElementById('tv-chart-card');
        if (wrap) {
          const W = Math.floor(wrap.getBoundingClientRect().width) || 1100;
          const cvs = document.getElementById('price-canvas');
          if (cvs) {
            cvs.width = W; cvs.style.width = W + 'px';
            cvs.height = TV.mainH; cvs.style.height = TV.mainH + 'px';
          }
        }
        if (TV.view.start == null) TV.view.start = Math.max(0, total - 252);
        if (TV.view.end   == null) TV.view.end   = total;
        requestAnimationFrame(function() {
          tvDrawSummaryChart();
          tvBuildPeriodCards();
          tvRedraw();
          tvSetupInteraction();
        });
      }
    } catch(e) { console.error('chartWindow restore error:', e); }
  }, 800);
}

// ── Sliding Ticker Tape ───────────────────────────────────────────────────
async function initTicker() {
  try {
    let d = await api('ticker');
    if (d && d.prices && d.prices.length > 0) {
      let html = '';
      d.prices.forEach(p => {
        let cls = p.chg >= 0 ? 'up' : 'down';
        let sign = p.chg >= 0 ? '▲' : '▼';
        html += `<div class="ticker-item"><span class="ticker-symbol">${p.sym}</span><span class="ticker-price">${Number(p.price).toLocaleString('en-IN', {minimumFractionDigits:2, maximumFractionDigits:2})}</span><span class="ticker-chg ${cls}">${sign} ${Math.abs(p.chg).toFixed(2)}%</span></div>`;
      });
      // Double the content for smooth infinite CSS scrolling
      document.getElementById('ticker-content').innerHTML = html + html;
      document.getElementById('top-ticker').style.display = 'block';
    }
  } catch(e) { console.warn("Ticker load error", e); }
}
document.addEventListener('DOMContentLoaded', initTicker);

// ── Routing & History Management ──────────────────────────────────────────
window.addEventListener('popstate', (e) => {
  if (e.state && e.state.page) {
    nav(e.state.page, true);
  } else {
    const hash = window.location.hash.substring(1);
    if (hash && document.getElementById('page-' + hash)) {
      nav(hash, true);
    } else {
      nav('advisor', true);
    }
  }
});

// Authentication and Onboarding Layout Toggles
function showAuthTerminal() {
  const layout = document.getElementById('app-layout');
  const auth = document.getElementById('page-auth');
  const onboarding = document.getElementById('page-onboarding');
  if (layout) layout.style.display = 'none';
  if (onboarding) onboarding.style.display = 'none';
  if (auth) {
    auth.style.display = 'flex';
    toggleAuthMode('login');
  }
}

function showOnboardingTerminal() {
  const layout = document.getElementById('app-layout');
  const auth = document.getElementById('page-auth');
  const onboarding = document.getElementById('page-onboarding');
  if (layout) layout.style.display = 'none';
  if (auth) auth.style.display = 'none';
  if (onboarding) {
    onboarding.style.display = 'flex';
    showOnbStep(1);
  }
}

function showDashboardTerminal() {
  const role = localStorage.getItem('user_role') || 'USER';
  if (role === 'ADMIN') {
    document.body.classList.remove('user-role-user');
    document.body.classList.add('user-role-admin');
  } else {
    document.body.classList.remove('user-role-admin');
    document.body.classList.add('user-role-user');
  }

  const layout = document.getElementById('app-layout');
  const auth = document.getElementById('page-auth');
  const onboarding = document.getElementById('page-onboarding');
  if (auth) auth.style.display = 'none';
  if (onboarding) onboarding.style.display = 'none';
  if (layout) layout.style.display = 'flex';
  
  // Route to saved hash or overview
  const hash = window.location.hash.substring(1);
  if (hash && document.getElementById('page-' + hash)) {
    nav(hash, true);
  } else {
    nav('overview', true);
  }

  // Trigger any dynamic components reload
  if (typeof initTicker === 'function') initTicker();
}

function logoutAuth() {
  localStorage.removeItem('token');
  localStorage.removeItem('user_email');
  localStorage.removeItem('user_role');
  showAuthTerminal();
  if (typeof initGoogleSignIn === 'function') {
    initGoogleSignIn();
  }
}

// Initial load routing checking auth and onboarding status
document.addEventListener('DOMContentLoaded', async () => {
  const token = localStorage.getItem('token');
  if (!token) {
    showAuthTerminal();
    return;
  }
  
  try {
    const check = await api('onboarding/check');
    if (check.completed) {
      showDashboardTerminal();
    } else {
      showOnboardingTerminal();
    }
  } catch (err) {
    // If auth token expired, show auth page
    console.error('Session validation failed, logging out...', err);
    logoutAuth();
  }
});



// ── FORWARD SIGNAL DEPLOY HELPERS ───────────────────────────────────────────
// Builds the Auto-Pilot banner HTML shown after Forward Signal results.
// Matches the exact style of the Advisor Auto-Pilot banner.
function _buildFwdDeployBanner(sigs) {
  if (!sigs || sigs.length === 0) return '';
  const n = sigs.length;
  const sectors = [...new Set(sigs.map(s => s.sector || '').filter(Boolean))];
  const sectorNote = sectors.length > 1
    ? `across ${sectors.length} different sectors`
    : sigs.length === 1
      ? `for ${sigs[0].name || sigs[0].symbol}`
      : 'from the live scan';

  return `
  <div class="easy-only" style="background:rgba(41,98,255,0.10);border:1px solid var(--cyan);
    border-radius:4px;padding:14px 16px;margin-top:4px;margin-bottom:4px;">
    <div style="color:var(--cyan);font-weight:bold;margin-bottom:6px;
      font-family:Share Tech Mono,monospace;font-size:0.8rem;letter-spacing:1px;">
      ✨ AUTO-PILOT PORTFOLIO GENERATED
    </div>
    <div style="font-family:Inter,sans-serif;font-size:0.8rem;color:var(--text);line-height:1.5;margin-bottom:10px;">
      We have automatically selected the <b>${n} best stock${n > 1 ? 's' : ''}</b> ${sectorNote}.
      Your risk is spread out, and every trade has a predefined Safety Net (Stop Loss).
      Deploy this portfolio with a single click.
    </div>
    <button onclick="deployFwdSignals()"
      style="width:100%;padding:10px;background:var(--cyan);color:var(--bg);border:none;
      border-radius:4px;font-family:Share Tech Mono,monospace;font-size:0.78rem;
      font-weight:bold;letter-spacing:2px;cursor:pointer;">
      🚀 DEPLOY PORTFOLIO TO DEMAT
    </button>
  </div>`;
}

// Deploys signals currently in window._fwdSignals (set by generateForwardSignal).
async function deployFwdSignals() {
  const sigs = window._fwdSignals;
  if (!sigs || sigs.length === 0) {
    alert('No signals to deploy. Generate signals first using ⚡ GENERATE + SEND or 👁 PREVIEW ONLY.');
    return;
  }

  const n = sigs.length;
  if (!confirm(
    `Deploy ${n} stock${n > 1 ? 's' : ''} to your Paper Portfolio?\n\n` +
    sigs.map(s =>
      `• ${s.symbol}  Entry ₹${Number(s.entry || s.price || 0).toLocaleString('en-IN', {maximumFractionDigits: 2})}` +
      `  SL ₹${Number(s.stop_loss || 0).toLocaleString('en-IN', {maximumFractionDigits: 2})}` +
      `  T1 ₹${Number(s.target1 || 0).toLocaleString('en-IN', {maximumFractionDigits: 2})}`
    ).join('\n')
  )) return;

  let successCount = 0;
  const failures = [];

  for (const s of sigs) {
    const entryPrice = Number(s.entry || s.price || 0);
    const shares     = Number(s.shares || 1);
    const stopLoss   = Number(s.stop_loss || 0);
    const target1    = Number(s.target1 || 0);
    const target2    = Number(s.target2 || 0);

    if (!s.symbol || entryPrice <= 0) {
      failures.push(`${s.symbol || '?'} — skipped (no entry price)`);
      continue;
    }

    try {
      const res = await api('portfolio_add', {
        symbol:      s.symbol,
        inv_type:    s.inv_type || 'swing',
        entry_price: entryPrice,
        shares:      shares,
        stop_loss:   stopLoss,
        target1:     target1,
        target2:     target2,
      });
      if (res && res.ok) {
        successCount++;
      } else {
        failures.push(`${s.symbol} — ${(res && res.error) || 'server error'}`);
      }
    } catch(e) {
      failures.push(`${s.symbol} — ${e.message || 'network error'}`);
    }
  }

  let msg = `✅ Auto-Pilot Complete!\nDeployed ${successCount} / ${n} trades to Paper Portfolio.`;
  if (failures.length) msg += `\n\n⚠ Skipped:\n${failures.join('\n')}`;
  alert(msg);

  if (successCount > 0) {
    nav('trading');
    setTimeout(() => { if (window.tradingTab) window.tradingTab('ptf'); }, 150);
  }
}

async function deployAutoPilot() {
  const d = window.currentAdvisorData;
  if(!d || !d.recommendations || d.recommendations.length === 0) {
    alert('No recommendations to deploy. Run the Advisor scan first.');
    return;
  }

  const totalAlloc = d.amount || d.total_allocation || 0;
  const nStocks    = d.recommendations.length;

  if(!confirm(
    `Deploy ${nStocks} stock${nStocks > 1 ? 's' : ''} to your Paper Portfolio?\n` +
    `Total Capital: ₹${Number(totalAlloc).toLocaleString('en-IN', {maximumFractionDigits: 0})}\n\n` +
    d.recommendations.map(r =>
      `• ${r.symbol}  ₹${Number(r.allocation || 0).toLocaleString('en-IN', {maximumFractionDigits: 0})}  (${r.shares || 0} shares @ ₹${Number(r.entry || r.cmp || 0).toLocaleString('en-IN', {maximumFractionDigits: 2})})`
    ).join('\n')
  )) return;

  let successCount = 0;
  const failures   = [];

  for (const r of d.recommendations) {
    const entryPrice = Number(r.entry || r.cmp || 0);
    const shares     = Number(r.shares || 0);
    const stopLoss   = Number(r.stop_loss || 0);
    const target1    = Number(r.target1 || 0);
    const target2    = Number(r.target2 || 0);

    if (!r.symbol || entryPrice <= 0 || shares <= 0) {
      failures.push(`${r.symbol || '?'} — skipped (invalid price/qty)`);
      continue;
    }

    try {
      const res = await api('portfolio_add', {
        symbol:      r.symbol,
        inv_type:    r.inv_type || d.inv_type || 'swing',
        entry_price: entryPrice,
        shares:      shares,
        stop_loss:   stopLoss,
        target1:     target1,
        target2:     target2,
        source_signal_id: r.id || r.signal_id,
      });
      if (res && res.ok) {
        successCount++;
      } else {
        failures.push(`${r.symbol} — ${(res && res.error) || 'server error'}`);
      }
    } catch(e) {
      console.error('AutoPilot Error for', r.symbol, e);
      failures.push(`${r.symbol} — ${e.message || 'network error'}`);
    }
  }

  let msg = `✅ Auto-Pilot Complete!\nDeployed ${successCount} / ${nStocks} trades to Paper Portfolio.`;
  if (failures.length) msg += `\n\n⚠ Skipped:\n${failures.join('\n')}`;
  alert(msg);

  nav('trading');
  setTimeout(() => { if (window.tradingTab) window.tradingTab('ptf'); }, 150);
}

// ── SINGLE STOCK DEPLOY ──────────────────────────────────────────────────────
// Called from the deploy banner inside the Single Stock Report.
async function deploySingleStock() {
  const r = window._singleRec;
  if (!r || !r.symbol) {
    alert('No single-stock signal loaded. Run a Single Stock Report first.');
    return;
  }

  const entryPrice = Number(r.entry || r.cmp || 0);
  const shares     = Number(r.shares || 0);
  const stopLoss   = Number(r.stop_loss || 0);
  const target1    = Number(r.target1 || 0);
  const target2    = Number(r.target2 || 0);

  if (entryPrice <= 0 || shares <= 0) {
    alert(`Cannot deploy ${r.symbol} — entry price or share qty is zero.\nRun the analysis first so the system can compute position sizing.`);
    return;
  }

  if (!confirm(
    `Deploy ${r.symbol} to Paper Portfolio?\n\n` +
    `• Entry:  ₹${entryPrice.toLocaleString('en-IN', {maximumFractionDigits: 2})}\n` +
    `• Shares: ${shares}\n` +
    `• SL:     ₹${stopLoss.toLocaleString('en-IN', {maximumFractionDigits: 2})}\n` +
    `• T1:     ₹${target1.toLocaleString('en-IN', {maximumFractionDigits: 2})}\n` +
    `• T2:     ₹${target2.toLocaleString('en-IN', {maximumFractionDigits: 2})}\n` +
    `• Type:   ${r.inv_type || 'swing'}`
  )) return;

  try {
    const res = await api('portfolio_add', {
      symbol:      r.symbol,
      inv_type:    r.inv_type || 'swing',
      entry_price: entryPrice,
      shares:      shares,
      stop_loss:   stopLoss,
      target1:     target1,
      target2:     target2,
      source_signal_id: r.id || r.signal_id,
    });

    if (res && res.ok) {
      alert(`✅ ${r.symbol} successfully deployed to Paper Portfolio!`);
      nav('trading');
      setTimeout(() => { if (window.tradingTab) window.tradingTab('ptf'); }, 150);
    } else {
      alert(`⚠ Deploy failed: ${(res && res.error) || 'server error'}`);
    }
  } catch(e) {
    alert(`⚠ Network error: ${e.message || String(e)}`);
  }
}

// ── SINGLE RECOMMENDATION DEPLOY (Phase 3 Fix 11) ───────────────────────────
// Called from Take Trade button on individual advisor cards.
async function deploySingleRecommendation(idx) {
  const d = window.currentAdvisorData;
  if (!d || !d.recommendations || !d.recommendations[idx]) {
    alert('No recommendation found at index ' + idx);
    return;
  }

  const r = d.recommendations[idx];
  const entryPrice = Number(r.entry || r.cmp || 0);
  const shares     = Number(r.shares || 0);
  const stopLoss   = Number(r.stop_loss || 0);
  const target1    = Number(r.target1 || 0);
  const target2    = Number(r.target2 || 0);

  if (entryPrice <= 0 || shares <= 0) {
    alert(`Cannot deploy ${r.symbol} — entry price or share qty is zero.\nRun the analysis first so the system can compute position sizing.`);
    return;
  }

  if (!confirm(
    `Deploy ${r.symbol} to Paper Portfolio?\n\n` +
    `• Entry:  ₹${entryPrice.toLocaleString('en-IN', {maximumFractionDigits: 2})}\n` +
    `• Shares: ${shares}\n` +
    `• SL:     ₹${stopLoss.toLocaleString('en-IN', {maximumFractionDigits: 2})}\n` +
    `• T1:     ₹${target1.toLocaleString('en-IN', {maximumFractionDigits: 2})}\n` +
    `• T2:     ₹${target2.toLocaleString('en-IN', {maximumFractionDigits: 2})}\n` +
    `• Type:   ${r.inv_type || d.inv_type || 'swing'}`
  )) return;

  try {
    const res = await api('portfolio_add', {
      symbol:      r.symbol,
      inv_type:    r.inv_type || d.inv_type || 'swing',
      entry_price: entryPrice,
      shares:      shares,
      stop_loss:   stopLoss,
      target1:     target1,
      target2:     target2,
      source_signal_id: r.id || r.signal_id,
    });

    if (res && res.ok) {
      alert(`✅ ${r.symbol} successfully deployed to Paper Portfolio!`);
      nav('trading');
      setTimeout(() => { if (window.tradingTab) window.tradingTab('ptf'); }, 150);
    } else {
      alert(`⚠ Deploy failed: ${(res && res.error) || 'server error'}`);
    }
  } catch(e) {
    alert(`⚠ Network error: ${e.message || String(e)}`);
  }
}

// ── FORWARD TEST SIGNALS DEPLOY ──────────────────────────────────────────────
// Called from the deploy banner in the Forward Testing Report tab.
async function deployForwardSignals() {
  const signals = window._ftrOpenSignals;
  if (!signals || signals.length === 0) {
    alert('No open signals to deploy. Refresh the Forward Testing report first.');
    return;
  }

  if (!confirm(
    `Deploy ${signals.length} open forward-test signal${signals.length > 1 ? 's' : ''} to Paper Portfolio?\n\n` +
    signals.map(s =>
      `• ${s.symbol}  Entry ₹${Number(s.entry || 0).toLocaleString('en-IN', {maximumFractionDigits: 2})}  SL ₹${Number(s.stop_loss || 0).toLocaleString('en-IN', {maximumFractionDigits: 2})}  T1 ₹${Number(s.target1 || 0).toLocaleString('en-IN', {maximumFractionDigits: 2})}`
    ).join('\n')
  )) return;

  let successCount = 0;
  const failures   = [];

  for (const s of signals) {
    const entryPrice = Number(s.entry || 0);
    const shares     = Number(s.shares || 1);
    const stopLoss   = Number(s.stop_loss || 0);
    const target1    = Number(s.target1 || 0);
    const target2    = Number(s.target2 || 0);

    if (!s.symbol || entryPrice <= 0) {
      failures.push(`${s.symbol || '?'} — skipped (no entry price)`);
      continue;
    }

    try {
      const res = await api('portfolio_add', {
        symbol:      s.symbol,
        inv_type:    s.inv_type || 'swing',
        entry_price: entryPrice,
        shares:      shares,
        stop_loss:   stopLoss,
        target1:     target1,
        target2:     target2,
        source_signal_id: s.id,
      });
      if (res && res.ok) {
        successCount++;
      } else {
        failures.push(`${s.symbol} — ${(res && res.error) || 'server error'}`);
      }
    } catch(e) {
      failures.push(`${s.symbol} — ${e.message || 'network error'}`);
    }
  }

  let msg = `✅ Deployed ${successCount} / ${signals.length} forward signals to Paper Portfolio.`;
  if (failures.length) msg += `\n\n⚠ Skipped:\n${failures.join('\n')}`;
  alert(msg);

  if (successCount > 0) {
    nav('trading');
    setTimeout(() => { if (window.tradingTab) window.tradingTab('ptf'); }, 150);
  }
}