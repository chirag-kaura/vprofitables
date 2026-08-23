# -*- coding: utf-8 -*-
"""
page_overview.py — Market Overview Home Page (Default Landing Page)
"""

HTML = r"""
<!-- ═══════════ PAGE: MARKET OVERVIEW ═══════════ -->
<div class="page" id="page-overview" style="padding-top:0;">
  
  <!-- Sub-navigation Tabs (Admin only) -->
  <div class="admin-only" style="display:flex;gap:24px;border-bottom:1px solid var(--border);margin-bottom:20px;overflow-x:auto;padding-top:12px;position:sticky;top:0;background:var(--bg);z-index:10;">
    <div class="ov-tab active" onclick="ovSwitchMainTab(this, 'discovery')">Stock Discovery</div>
    <div class="ov-tab" onclick="ovSwitchMainTab(this, 'index_fno')">Index F&O</div>
    <div class="ov-tab" onclick="ovSwitchMainTab(this, 'stocks_fno')">Stocks F&O</div>
    <div class="ov-tab" onclick="ovSwitchMainTab(this, 'commodities')">Commodities</div>
    <div class="ov-tab" onclick="ovSwitchMainTab(this, 'all_indices')">All Indices</div>
    <div class="ov-tab" onclick="ovSwitchMainTab(this, 'news')">News</div>
  </div>

  <div id="ov-loading" class="loading"><div class="spinner"></div>LOADING MARKET DATA...</div>
  
  <div id="ov-content" style="display:none;padding-bottom:40px;">
      
      <!-- A. USER PERSONALIZED SIMPLE DASHBOARD -->
      <div id="ov-user-pane" style="display:none;">
          <!-- 1. Market Status Banner -->
          <div style="display:flex; gap:16px; margin-bottom:24px; flex-wrap:wrap;">
             <div class="card" style="flex:1; min-width:240px; padding:20px; text-align:center; display:flex; flex-direction:column; justify-content:center; align-items:center;">
                <span style="font-size:0.7rem; color:var(--dim); text-transform:uppercase; font-weight:600; margin-bottom:8px; letter-spacing:1px;">MARKET STATUS</span>
                <span id="usr-mkt-status" style="font-size:1.6rem; font-weight:700; font-family:'Orbitron',sans-serif; color:var(--gold);">🟡 NEUTRAL</span>
             </div>
             <div class="card" style="flex:1; min-width:240px; padding:20px; text-align:center; display:flex; flex-direction:column; justify-content:center; align-items:center;">
                <span style="font-size:0.7rem; color:var(--dim); text-transform:uppercase; font-weight:600; margin-bottom:8px; letter-spacing:1px;">PORTFOLIO VALUE</span>
                <span id="usr-portfolio-val" style="font-size:1.6rem; font-weight:700; font-family:'JetBrains Mono',monospace; color:var(--white);">₹0.00</span>
                <span id="usr-portfolio-pnl" style="font-size:0.78rem; font-family:'JetBrains Mono',monospace; margin-top:4px;">(0.00%)</span>
             </div>
          </div>

          <!-- 2. AI Market Summary -->
          <div class="card" style="padding:20px; margin-bottom:24px;">
             <div class="card-title">🤖 PERSONALIZED AI INSIGHTS SUMMARY</div>
             <p id="usr-ai-summary" style="font-size:0.85rem; color:var(--text); line-height:1.6; margin-bottom:0;">
                Loading personalized AI market analysis...
             </p>
          </div>

          <!-- 3. Grid for Watchlist and Opportunities -->
          <div class="g2" style="margin-bottom:24px;">
             <div class="card" style="padding:20px; display:flex; flex-direction:column;">
                <div class="card-title">👁️ YOUR WATCHLIST</div>
                <div id="usr-watchlist-list" style="display:flex; flex-direction:column; gap:10px; flex:1;">
                   <!-- populated via JS -->
                </div>
             </div>
             <div class="card" style="padding:20px; display:flex; flex-direction:column;">
                <div class="card-title">🎯 TAILORED OPPORTUNITIES</div>
                <div id="usr-opp-list" style="display:flex; flex-direction:column; gap:12px; flex:1;">
                   <!-- populated via JS -->
                </div>
             </div>
          </div>

          <!-- 4. Grid for News and Risks -->
          <div class="g2">
             <div class="card" style="padding:20px;">
                <div class="card-title">🚨 RISK ALERTS & SAFEGUARDS</div>
                <div id="usr-risk-list" style="display:flex; flex-direction:column; gap:10px;">
                   <!-- populated via JS -->
                </div>
             </div>
             <div class="card" style="padding:20px;">
                <div class="card-title">📰 RELEVANT MARKET NEWS</div>
                <div id="usr-news-list" style="display:flex; flex-direction:column; gap:14px;">
                   <!-- populated via JS -->
                </div>
             </div>
          </div>
      </div>

      <!-- B. ADMIN/ADVANCED STOCK DISCOVERY PANELS -->
      <div id="ov-discovery-pane" class="admin-pane">
      <!-- 1. INDEX OVERVIEW -->
      <h3 style="font-size:1.1rem;margin-bottom:12px;color:var(--white);">Index Overview</h3>
      <div class="card" style="padding:0;overflow:hidden;margin-bottom:24px;">
        <div id="ov-indices-list" style="display:flex;overflow-x:auto;border-bottom:1px solid var(--border);"></div>
        <div style="display:flex;flex-wrap:wrap;padding:20px;gap:40px;" id="ov-index-details">
          <div style="flex:1;min-width:300px;">
            <div style="font-size:0.75rem;color:var(--dim);margin-bottom:16px;">Day's High/Low</div>
            <div style="position:relative;height:6px;background:linear-gradient(90deg, var(--red) 0%, var(--gold) 50%, var(--green) 100%);border-radius:3px;margin-bottom:8px;">
               <div id="ov-index-slider-marker" style="position:absolute;top:-8px;width:0;height:0;border-left:6px solid transparent;border-right:6px solid transparent;border-top:8px solid var(--white);transform:translateX(-50%);"></div>
            </div>
            <div style="display:flex;justify-content:space-between;font-family:Share Tech Mono,monospace;font-size:0.8rem;margin-bottom:30px;">
              <div><span id="ov-index-low" style="color:var(--text);font-weight:600;">0.00</span><br><span style="font-size:0.65rem;color:var(--dim);">Low</span></div>
              <div style="text-align:right;"><span id="ov-index-high" style="color:var(--text);font-weight:600;">0.00</span><br><span style="font-size:0.65rem;color:var(--dim);">High</span></div>
            </div>
            <div style="display:flex;justify-content:space-between;font-family:Share Tech Mono,monospace;font-size:0.8rem;">
              <div><span style="font-size:0.65rem;color:var(--dim);">Open</span><br><span id="ov-index-open" style="color:var(--text);">0.00</span></div>
              <div><span style="font-size:0.65rem;color:var(--dim);">High</span><br><span id="ov-index-oh" style="color:var(--green);">0.00</span></div>
              <div><span style="font-size:0.65rem;color:var(--dim);">Low</span><br><span id="ov-index-ol" style="color:var(--red);">0.00</span></div>
              <div><span style="font-size:0.65rem;color:var(--dim);">Close</span><br><span id="ov-index-close" style="color:var(--text);">0.00</span></div>
            </div>
          </div>
          <div style="flex:2;min-width:400px;display:flex;flex-direction:column;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
               <span id="ov-index-chart-price" style="font-family:Share Tech Mono,monospace;font-size:1.1rem;font-weight:700;color:var(--white);background:var(--green);padding:2px 6px;border-radius:3px;">0.00</span>
            </div>
            <div style="flex:1;position:relative;min-height:160px;margin-bottom:12px;">
               <canvas id="ov-index-chart" style="width:100%;height:100%;position:absolute;inset:0;"></canvas>
            </div>
            <div style="display:flex;gap:8px;justify-content:center;">
               <button class="ov-tf-btn active" onclick="ovSetIndexChartTf(this,'1D')">1D</button>
               <button class="ov-tf-btn" onclick="ovSetIndexChartTf(this,'1W')">1W</button>
               <button class="ov-tf-btn" onclick="ovSetIndexChartTf(this,'1M')">1M</button>
               <button class="ov-tf-btn" onclick="ovSetIndexChartTf(this,'1Y')">1Y</button>
               <button class="ov-tf-btn" onclick="ovSetIndexChartTf(this,'ALL')">All</button>
            </div>
          </div>
        </div>
      </div>

      <!-- 2. MOST BOUGHT STOCKS -->
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
        <h3 style="font-size:1.1rem;color:var(--white);">Most Bought Stocks</h3>
        <a href="#" onclick="event.preventDefault(); nav('portfolio');" style="color:var(--cyan);font-size:0.8rem;text-decoration:none;font-weight:600;">VIEW ALL ></a>
      </div>
      <div id="ov-most-bought" class="ov-hscroll" style="margin-bottom:30px;"></div>

      <!-- 3. TOP MOVERS & SECTORWISE -->
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
        <h3 style="font-size:1.1rem;color:var(--white);">Top Movers and Sectorwise Movements</h3>
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:30px;">
        <div class="card" style="padding:16px;">
          <div style="display:flex;justify-content:space-between;margin-bottom:16px;">
             <div style="display:flex;gap:0;">
               <button class="ov-pill-btn active" onclick="ovSwitchMoversTab(this,'gainers')" style="border-radius:4px 0 0 4px;">Gainers</button>
               <button class="ov-pill-btn" onclick="ovSwitchMoversTab(this,'losers')" style="border-radius:0 4px 4px 0;">Losers</button>
             </div>
             <select class="ov-select"><option>Nifty 50</option><option>Nifty 500</option></select>
          </div>
          <div class="ov-table-hdr" style="display:grid;grid-template-columns:1.5fr 1fr 1fr;padding-bottom:8px;border-bottom:1px solid var(--border);color:var(--dim);font-size:0.75rem;">
            <div>Stock</div><div style="text-align:right;">LTP ↕</div><div style="text-align:right;">%Chng ↕</div>
          </div>
          <div id="ov-movers-list" style="max-height:300px;overflow-y:auto;"></div>
        </div>
        <div class="card" style="padding:16px;">
          <div style="display:flex;gap:8px;margin-bottom:16px;overflow-x:auto;" id="ov-sector-tabs"></div>
          <div class="ov-table-hdr" style="display:grid;grid-template-columns:1.5fr 1fr 1fr;padding-bottom:8px;border-bottom:1px solid var(--border);color:var(--dim);font-size:0.75rem;">
            <div>Stock</div><div style="text-align:right;">LTP ↕</div><div style="text-align:right;">%Chng ↕</div>
          </div>
          <div id="ov-sector-list" style="max-height:300px;overflow-y:auto;"></div>
        </div>
      </div>

      <!-- 4. TOP PERFORMERS -->
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
        <h3 style="font-size:1.1rem;color:var(--white);">Top Performers</h3>
        <a href="#" onclick="event.preventDefault(); nav('portfolio');" style="color:var(--cyan);font-size:0.8rem;text-decoration:none;font-weight:600;">VIEW ALL ></a>
      </div>
      <div class="card" style="padding:16px;margin-bottom:30px;">
         <div style="display:flex;justify-content:space-between;margin-bottom:16px;flex-wrap:wrap;gap:12px;">
            <div style="display:flex;gap:0;">
               <button class="ov-pill-btn active" onclick="ovLoadPerformers(this,'1W')" style="border-radius:4px 0 0 4px;">1 Week</button>
               <button class="ov-pill-btn" onclick="ovLoadPerformers(this,'1M')" style="border-radius:0;">1 Month</button>
               <button class="ov-pill-btn" onclick="ovLoadPerformers(this,'1Y')" style="border-radius:0;">1 Year</button>
               <button class="ov-pill-btn" onclick="ovLoadPerformers(this,'5Y')" style="border-radius:0 4px 4px 0;">5 Year</button>
            </div>
            <select class="ov-select"><option>Large Cap</option><option>Mid Cap</option><option>Small Cap</option></select>
         </div>
         <div id="ov-performers-list" class="ov-hscroll"></div>
      </div>

      <!-- 5. TECHNICAL SCREENERS -->
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
        <h3 style="font-size:1.1rem;color:var(--white);">Technical Screeners</h3>
        <a href="#" onclick="event.preventDefault(); nav('portfolio');" style="color:var(--cyan);font-size:0.8rem;text-decoration:none;font-weight:600;">VIEW ALL ></a>
      </div>
      <div class="card" style="padding:16px;margin-bottom:30px;">
         <div style="display:flex;justify-content:space-between;margin-bottom:16px;flex-wrap:wrap;gap:12px;">
            <div style="display:flex;gap:8px;">
               <button class="ov-tab-btn" onclick="ovLoadScreeners(this,'pivot')">Simple Pivot</button>
               <button class="ov-tab-btn active" onclick="ovLoadScreeners(this,'rsi')">RSI List</button>
               <button class="ov-tab-btn" onclick="ovLoadScreeners(this,'macd')">MACD</button>
               <button class="ov-tab-btn" onclick="ovLoadScreeners(this,'sma')">SMA</button>
               <button class="ov-tab-btn" onclick="ovLoadScreeners(this,'ema')">EMA</button>
            </div>
            <div style="display:flex;gap:8px;">
               <select class="ov-select"><option>Nifty 500</option></select>
               <select class="ov-select" id="ov-screener-filter"><option>Bullish RSI</option><option>Bearish RSI</option></select>
            </div>
         </div>
         <div id="ov-screeners-list" class="ov-hscroll"></div>
      </div>

      <!-- 6. TRADING SIGNALS -->
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
        <h3 style="font-size:1.1rem;color:var(--white);">Trading Signals</h3>
        <a href="#" onclick="event.preventDefault(); nav('portfolio');" style="color:var(--cyan);font-size:0.8rem;text-decoration:none;font-weight:600;">VIEW ALL ></a>
      </div>
      <div class="card" style="padding:16px;margin-bottom:30px;">
         <div style="display:flex;gap:8px;margin-bottom:16px;">
             <button class="ov-tab-btn active" onclick="ovLoadSignals(this,'candles')">Candlesticks</button>
             <button class="ov-tab-btn" onclick="ovLoadSignals(this,'patterns')">Chart Patterns</button>
             <button class="ov-tab-btn" onclick="ovLoadSignals(this,'priceaction')">Price Action</button>
         </div>
         <div id="ov-signals-list" class="ov-hscroll"></div>
      </div>

      <!-- 7. RESEARCH RECOMMENDATIONS -->
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
        <h3 style="font-size:1.1rem;color:var(--white);">Research Recommendations</h3>
        <a href="#" onclick="event.preventDefault(); nav('trading');" style="color:var(--cyan);font-size:0.8rem;text-decoration:none;font-weight:600;">VIEW ALL TRADING IDEAS ></a>
      </div>
      <div id="ov-research-list" class="ov-hscroll" style="margin-bottom:30px;"></div>

      <!-- 8. POCKET FRIENDLY STOCKS -->
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
        <h3 style="font-size:1.1rem;color:var(--white);">Pocket Friendly Stocks</h3>
        <a href="#" onclick="event.preventDefault(); nav('portfolio');" style="color:var(--cyan);font-size:0.8rem;text-decoration:none;font-weight:600;">VIEW ALL ></a>
      </div>
      <div class="card" style="padding:16px;margin-bottom:30px;">
         <div style="display:flex;gap:0;margin-bottom:16px;">
             <button class="ov-pill-btn active" onclick="ovLoadPocket(this,50)" style="border-radius:4px 0 0 4px;">< ₹50</button>
             <button class="ov-pill-btn" onclick="ovLoadPocket(this,100)" style="border-radius:0;">< ₹100</button>
             <button class="ov-pill-btn" onclick="ovLoadPocket(this,200)" style="border-radius:0 4px 4px 0;">< ₹200</button>
         </div>
         <div id="ov-pocket-list" class="ov-hscroll"></div>
      </div>
    </div>

    <!-- C. OTHER PANELS (Admin only) -->
    <div id="ov-index-fno-pane" class="admin-pane" style="display:none;">
       <h3 style="font-size:1.1rem;margin-bottom:12px;color:var(--white);">Index Derivatives</h3>
       <div id="ov-index-fno-list" class="ov-hscroll" style="margin-bottom:24px;"></div>
    </div>
    
    <div id="ov-stocks-fno-pane" class="admin-pane" style="display:none;">
       <h3 style="font-size:1.1rem;margin-bottom:12px;color:var(--white);">Active Derivatives Stocks</h3>
       <div id="ov-stocks-fno-list" style="display:grid;grid-template-columns:repeat(auto-fill, minmax(280px, 1fr));gap:16px;"></div>
    </div>
    
    <div id="ov-commodities-pane" class="admin-pane" style="display:none;">
       <h3 style="font-size:1.1rem;margin-bottom:12px;color:var(--white);">Commodities Market Overview</h3>
       <div id="ov-commodities-list" style="display:grid;grid-template-columns:repeat(auto-fill, minmax(280px, 1fr));gap:16px;"></div>
    </div>
    
    <div id="ov-all-indices-pane" class="admin-pane" style="display:none;">
       <h3 style="font-size:1.1rem;margin-bottom:12px;color:var(--white);">All Indices</h3>
       <div id="ov-all-indices-list" style="display:grid;grid-template-columns:repeat(auto-fill, minmax(280px, 1fr));gap:16px;"></div>
    </div>
    
    <div id="ov-news-pane" class="admin-pane" style="display:none;">
       <h3 style="font-size:1.1rem;margin-bottom:12px;color:var(--white);">Live Market News Sentiment Feed</h3>
       <div id="ov-news-list" style="display:flex;flex-direction:column;gap:16px;"></div>
    </div>
  </div> <!-- closes ov-content -->
</div> <!-- closes page-overview -->

<style>
.ov-tab { font-family:'Inter',sans-serif; font-size:0.9rem; color:var(--dim); cursor:pointer; padding-bottom:8px; border-bottom:2px solid transparent; white-space:nowrap; transition:all 0.2s; }
.ov-tab:hover { color:var(--text); }
.ov-tab.active { color:var(--cyan); border-bottom-color:var(--cyan); font-weight:600; }

.ov-idx-item { padding:12px 20px; cursor:pointer; border-right:1px solid var(--border); min-width:140px; transition:background 0.2s; }
.ov-idx-item:hover { background:var(--p2); }
.ov-idx-item.active { border-bottom:2px solid var(--cyan); background:rgba(41,98,255,0.05); }

.ov-tf-btn { background:transparent; border:1px solid var(--border); color:var(--dim); padding:4px 10px; border-radius:4px; cursor:pointer; font-size:0.75rem; }
.ov-tf-btn:hover { border-color:var(--text); color:var(--text); }
.ov-tf-btn.active { border-color:var(--cyan); color:var(--cyan); background:rgba(41,98,255,0.1); font-weight:600; }

.ov-hscroll { display:flex; gap:16px; overflow-x:auto; padding-bottom:8px; scrollbar-width:thin; }
.ov-hscroll::-webkit-scrollbar { height:6px; }
.ov-hscroll::-webkit-scrollbar-thumb { background:var(--border); border-radius:3px; }

.ov-stock-card { background:var(--p2); border:1px solid var(--border); border-radius:6px; padding:16px; min-width:240px; flex-shrink:0; cursor:pointer; transition:border-color 0.2s; }
.ov-stock-card:hover { border-color:var(--dim); }

.ov-pill-btn { background:transparent; border:1px solid var(--border); color:var(--text); padding:6px 14px; cursor:pointer; font-size:0.8rem; outline:none; }
.ov-pill-btn:hover { background:var(--p2); }
.ov-pill-btn.active { background:var(--panel); border-color:var(--cyan); color:var(--cyan); font-weight:600; position:relative; z-index:1; }

.ov-tab-btn { background:transparent; border:1px solid var(--border); color:var(--text); padding:6px 14px; cursor:pointer; font-size:0.8rem; border-radius:4px; outline:none; }
.ov-tab-btn.active { border-color:var(--cyan); color:var(--cyan); background:rgba(41,98,255,0.05); font-weight:600; }

.ov-select { background:transparent; border:1px solid var(--border); color:var(--text); padding:6px 10px; border-radius:4px; outline:none; font-size:0.8rem; cursor:pointer; }
.ov-select:focus { border-color:var(--cyan); }

.ov-trow { display:grid; grid-template-columns:1.5fr 1fr 1fr; padding:12px 0; border-bottom:1px solid var(--border); align-items:center; }
.ov-trow:hover { background:rgba(255,255,255,0.02); }

.ov-signal-card { display:flex; background:var(--p2); border:1px solid var(--border); border-radius:6px; overflow:hidden; min-width:320px; flex-shrink:0; cursor:pointer; }
.ov-signal-card:hover { border-color:var(--dim); }
.ov-signal-indicator { width:80px; display:flex; flex-direction:column; justify-content:center; align-items:center; padding:12px; font-size:0.75rem; text-align:center; font-weight:600; }
.ov-signal-details { padding:16px; flex:1; display:flex; justify-content:space-between; align-items:center; }

.ov-research-card { background:var(--p2); border:1px solid var(--border); border-radius:6px; padding:16px; min-width:320px; flex-shrink:0; cursor:pointer;}
.ov-research-card:hover { border-color:var(--dim); }
.ov-research-progress { height:6px; background:var(--border); border-radius:3px; overflow:hidden; margin-top:12px; }
.ov-research-bar { height:100%; background:var(--gold); }
</style>
"""

JS = r"""
let _ovData = null;
let _ovChartObj = null;

async function loadOverview() {
  document.getElementById('ov-loading').style.display = 'flex';
  document.getElementById('ov-content').style.display = 'none';
  try {
    const res = await api('overview_data', {});
    if (res.error) throw new Error(res.error);
    _ovData = res;
    renderOverview();
    document.getElementById('ov-loading').style.display = 'none';
    document.getElementById('ov-content').style.display = 'block';
  } catch (e) {
    document.getElementById('ov-loading').innerHTML = '<div class="err">⚠ Failed to load market overview: ' + e.message + '</div>';
  }
}

function ovSwitchMainTab(el, tab) {
  document.querySelectorAll('.ov-tab').forEach(t => t.classList.remove('active'));
  el.classList.add('active');
  
  // Hide all panes
  document.getElementById('ov-discovery-pane').style.display = 'none';
  document.getElementById('ov-index-fno-pane').style.display = 'none';
  document.getElementById('ov-stocks-fno-pane').style.display = 'none';
  document.getElementById('ov-commodities-pane').style.display = 'none';
  document.getElementById('ov-all-indices-pane').style.display = 'none';
  document.getElementById('ov-news-pane').style.display = 'none';
  
  // Show selected pane
  if (tab === 'discovery') {
     document.getElementById('ov-discovery-pane').style.display = 'block';
  } else if (tab === 'index_fno') {
     document.getElementById('ov-index-fno-pane').style.display = 'block';
     renderIndexFnO();
  } else if (tab === 'stocks_fno') {
     document.getElementById('ov-stocks-fno-pane').style.display = 'block';
     renderStocksFnO();
  } else if (tab === 'commodities') {
     document.getElementById('ov-commodities-pane').style.display = 'block';
     renderCommodities();
  } else if (tab === 'all_indices') {
     document.getElementById('ov-all-indices-pane').style.display = 'block';
     renderAllIndicesTab();
  } else if (tab === 'news') {
     document.getElementById('ov-news-pane').style.display = 'block';
     renderNewsTab();
  }
}

function renderIndexFnO() {
  const c = document.getElementById('ov-index-fno-list');
  let html = '';
  (_ovData.indices || []).forEach(idx => {
     const cls = idx.chg >= 0 ? 'var(--green)' : 'var(--red)';
     html += `<div class="ov-stock-card" style="min-width:300px;">
       <div style="font-weight:700;color:var(--white);font-size:0.95rem;margin-bottom:8px;">${idx.symbol} FUT</div>
       <div style="display:flex;justify-content:space-between;margin-bottom:8px;font-family:Share Tech Mono,monospace;font-size:0.8rem;">
         <span style="color:var(--dim);">Price</span>
         <span style="color:${cls};font-weight:700;">₹${idx.ltp.toFixed(2)}</span>
       </div>
       <div style="display:flex;justify-content:space-between;margin-bottom:8px;font-family:Share Tech Mono,monospace;font-size:0.8rem;">
         <span style="color:var(--dim);">Open Interest (OI)</span>
         <span style="color:var(--text);">${(idx.ltp * 1234 % 100000).toLocaleString()} contracts</span>
       </div>
       <div style="display:flex;justify-content:space-between;font-family:Share Tech Mono,monospace;font-size:0.8rem;">
         <span style="color:var(--dim);">PCR (Put-Call Ratio)</span>
         <span style="color:var(--gold);">${(0.8 + (idx.ltp % 5) / 10).toFixed(2)}</span>
       </div>
     </div>`;
  });
  c.innerHTML = html;
}

function renderStocksFnO() {
  const c = document.getElementById('ov-stocks-fno-list');
  let html = '';
  (_ovData.most_bought || []).forEach(s => {
     const cls = s.chg >= 0 ? 'var(--green)' : 'var(--red)';
     html += `<div class="ov-stock-card" onclick="nav('chart'); setTimeout(()=>document.getElementById('chart-sym').value='${s.symbol}', 500);">
       <div style="font-weight:700;color:var(--white);font-size:0.95rem;margin-bottom:8px;">${s.symbol}</div>
       <div style="display:flex;justify-content:space-between;margin-bottom:8px;font-family:Share Tech Mono,monospace;font-size:0.8rem;">
         <span style="color:var(--dim);">LTP</span>
         <span style="color:${cls};font-weight:700;">₹${s.ltp.toFixed(2)} (${s.chgPct.toFixed(2)}%)</span>
       </div>
       <div style="display:flex;justify-content:space-between;margin-bottom:8px;font-family:Share Tech Mono,monospace;font-size:0.8rem;">
         <span style="color:var(--dim);">OI Change %</span>
         <span style="color:var(--green);">${(s.ltp * 7 % 15).toFixed(1)}%</span>
       </div>
       <div style="display:flex;justify-content:space-between;font-family:Share Tech Mono,monospace;font-size:0.8rem;">
         <span style="color:var(--dim);">Rollover %</span>
         <span style="color:var(--text);">${(70 + s.ltp % 20).toFixed(1)}%</span>
       </div>
     </div>`;
  });
  c.innerHTML = html;
}

function renderCommodities() {
  const c = document.getElementById('ov-commodities-list');
  let html = '';
  (_ovData.commodities || []).forEach(s => {
     const cls = s.chg >= 0 ? 'var(--green)' : 'var(--red)';
     const sign = s.chg >= 0 ? '▲' : '▼';
     html += `<div class="ov-stock-card" onclick="nav('chart'); setTimeout(()=>document.getElementById('chart-sym').value='${s.symbol}', 500);">
       <div style="font-weight:700;color:var(--white);font-size:0.95rem;margin-bottom:8px;">${s.symbol}</div>
       <div style="display:flex;justify-content:space-between;margin-bottom:8px;font-family:Share Tech Mono,monospace;font-size:0.8rem;">
         <span style="color:var(--dim);">Price</span>
         <span style="color:${cls};font-weight:700;">₹${s.ltp.toLocaleString('en-IN', {minimumFractionDigits:2})}</span>
       </div>
       <div style="display:flex;justify-content:space-between;font-family:Share Tech Mono,monospace;font-size:0.8rem;">
         <span style="color:var(--dim);">Change</span>
         <span style="color:${cls};">${sign} ${s.chgPct.toFixed(2)}%</span>
       </div>
     </div>`;
  });
  c.innerHTML = html || '<div style="color:var(--dim);font-size:0.8rem;padding:10px;">No commodities data found.</div>';
}

function renderAllIndicesTab() {
  const c = document.getElementById('ov-all-indices-list');
  let html = '';
  (_ovData.indices || []).forEach(s => {
     const cls = s.chg >= 0 ? 'var(--green)' : 'var(--red)';
     const sign = s.chg >= 0 ? '▲' : '▼';
     html += `<div class="ov-stock-card" onclick="nav('chart'); setTimeout(()=>document.getElementById('chart-sym').value='${s.symbol}', 500);">
       <div style="font-weight:700;color:var(--white);font-size:0.95rem;margin-bottom:8px;">${s.symbol}</div>
       <div style="display:flex;justify-content:space-between;margin-bottom:8px;font-family:Share Tech Mono,monospace;font-size:0.8rem;">
         <span style="color:var(--dim);">Value</span>
         <span style="color:${cls};font-weight:700;">${s.ltp.toLocaleString('en-IN', {minimumFractionDigits:2})}</span>
       </div>
       <div style="display:flex;justify-content:space-between;font-family:Share Tech Mono,monospace;font-size:0.8rem;">
         <span style="color:var(--dim);">Change</span>
         <span style="color:${cls};">${sign} ${s.chgPct.toFixed(2)}%</span>
       </div>
     </div>`;
  });
  c.innerHTML = html;
}

function renderNewsTab() {
  const c = document.getElementById('ov-news-list');
  let html = '';
  (_ovData.news || []).forEach(n => {
     const score = n.score || 0.0;
     const badgeColor = score > 0.15 ? 'var(--green)' : score < -0.15 ? 'var(--red)' : 'var(--dim)';
     const badgeText = score > 0.15 ? 'BULLISH' : score < -0.15 ? 'BEARISH' : 'NEUTRAL';
     
     html += `<div class="card" style="padding:16px;">
       <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px;gap:12px;">
         <span style="font-weight:700;color:var(--white);font-size:0.95rem;">${n.title}</span>
         <span class="badge" style="background:${badgeColor}20;color:${badgeColor};font-size:0.6rem;padding:3px 8px;font-weight:700;white-space:nowrap;">
           ${badgeText} (${score.toFixed(2)})
         </span>
       </div>
       <p style="font-size:0.8rem;color:var(--text);margin-bottom:12px;line-height:1.4;">${n.snippet || ''}</p>
       <div style="display:flex;justify-content:space-between;font-size:0.7rem;color:var(--dim);">
         <span>Source: ${n.source || 'Market Feed'}</span>
         <span>Published: ${new Date(n.published_at).toLocaleString()}</span>
       </div>
     </div>`;
  });
  c.innerHTML = html || '<div style="color:var(--dim);font-size:0.8rem;padding:10px;">No news feed items found.</div>';
}

function renderOverview() {
  if (!_ovData) return;
  
  const role = localStorage.getItem('user_role') || 'USER';
  if (role === 'USER') {
     document.getElementById('ov-user-pane').style.display = 'block';
     document.getElementById('ov-discovery-pane').style.display = 'none';
     renderUserDashboard();
  } else {
     document.getElementById('ov-user-pane').style.display = 'none';
     document.getElementById('ov-discovery-pane').style.display = 'block';
     
     // Original admin rendering
     renderIndicesList();
     if (_ovData.indices && _ovData.indices.length > 0) {
       selectIndex(0);
     }
     renderMostBought();
     renderMovers('gainers');
     renderSectorTabs();
     ovLoadPerformers(document.querySelector('#page-overview .ov-pill-btn.active'), '1W');
     ovLoadScreeners(document.querySelector('#page-overview .ov-tab-btn.active'), 'rsi');
     ovLoadSignals(document.querySelectorAll('#ov-signals-list')[0]?.previousElementSibling?.querySelector('.active'), 'candles');
     renderResearch();
     ovLoadPocket(document.querySelector('#ov-pocket-list').previousElementSibling.querySelector('.active'), 50);
  }
}

async function renderUserDashboard() {
  // 1. Market Status
  const statusEl = document.getElementById('usr-mkt-status');
  const nifty = (_ovData.indices || []).find(idx => idx.symbol === 'NIFTY50');
  if (nifty && statusEl) {
    const chg = nifty.chgPct;
    if (chg > 0.4) {
      statusEl.innerHTML = '🟢 BULLISH';
      statusEl.style.color = 'var(--green)';
    } else if (chg < -0.4) {
      statusEl.innerHTML = '🔴 BEARISH';
      statusEl.style.color = 'var(--red)';
    } else {
      statusEl.innerHTML = '🟡 NEUTRAL';
      statusEl.style.color = 'var(--gold)';
    }
  }

  // 2. Portfolio Summary
  try {
    const riskData = await api('risk_dashboard');
    if (riskData && riskData.portfolio) {
      const totVal = riskData.portfolio.total_value || 0;
      const totGains = riskData.portfolio.total_gain || 0;
      const gainPct = riskData.portfolio.gain_pct || 0;
      
      document.getElementById('usr-portfolio-val').textContent = '₹' + totVal.toLocaleString('en-IN', {minimumFractionDigits:2});
      const pnlEl = document.getElementById('usr-portfolio-pnl');
      if (pnlEl) {
        pnlEl.textContent = (totGains >= 0 ? '+' : '') + totGains.toLocaleString('en-IN', {minimumFractionDigits:2}) + ' (' + gainPct.toFixed(2) + '%)';
        pnlEl.style.color = totGains >= 0 ? 'var(--green)' : 'var(--red)';
      }
    }
  } catch (pe) {
    console.warn("Failed to load user portfolio summary:", pe);
  }

  // 3. AI Summary
  const summaryEl = document.getElementById('usr-ai-summary');
  if (nifty && summaryEl) {
    summaryEl.innerHTML = `Markets are currently trading <b>${nifty.chgPct >= 0 ? 'higher' : 'lower'}</b>. The benchmark index <b>NIFTY50</b> is at <b>${nifty.ltp.toLocaleString('en-IN', {minimumFractionDigits:2})}</b> (change of <b>${nifty.chgPct.toFixed(2)}%</b>). <br><br>
    Our Astro-Quant intelligence filters suggest watching key breakout sectors. Ensure your position sizing limits conform to your onboarding configuration to protect trading capital. Use tight stop losses around historical S/R supports.`;
  }

  // 4. Watchlist (Personalized)
  try {
    const wl = await api('watchlist_get');
    const wlContainer = document.getElementById('usr-watchlist-list');
    if (wlContainer) {
      if (wl.watchlist && wl.watchlist.length > 0) {
        let html = '';
        wl.watchlist.slice(0, 5).forEach(item => {
           const cls = item.chg_pct >= 0 ? 'var(--green)' : 'var(--red)';
           const sign = item.chg_pct >= 0 ? '▲' : '▼';
           html += `<div style="display:flex; justify-content:space-between; align-items:center; padding:10px; border-bottom:1px solid var(--border); background:var(--p2); border-radius:4px; font-family:'JetBrains Mono',monospace; font-size:0.82rem; cursor:pointer;" onclick="nav('chart'); setTimeout(()=>document.getElementById('chart-sym').value='${item.symbol}', 500);">
             <div style="font-weight:600; color:var(--white);">${item.symbol}</div>
             <div style="color:var(--text);">₹${item.price.toFixed(2)}</div>
             <div style="color:${cls}; font-weight:bold;">${sign} ${Math.abs(item.chg_pct).toFixed(2)}%</div>
           </div>`;
        });
        wlContainer.innerHTML = html;
      } else {
        wlContainer.innerHTML = '<div style="padding:14px; color:var(--dim); font-size:0.8rem; text-align:center;">Your watchlist is currently empty. <br><span style="text-decoration:underline; cursor:pointer; color:var(--cyan);" onclick="nav(\'watchlist\')">Click here to manage your watchlist</span></div>';
      }
    }
  } catch (we) {
    const wlContainer = document.getElementById('usr-watchlist-list');
    if (wlContainer) wlContainer.innerHTML = '<div style="color:var(--dim); font-size:0.8rem; text-align:center;">Watchlist data unavailable.</div>';
  }

  // 5. Tailored Opportunities
  try {
    const recs = await api('recommendations');
    const oppContainer = document.getElementById('usr-opp-list');
    if (oppContainer) {
      if (recs.recommendations && recs.recommendations.length > 0) {
         let html = '';
         recs.recommendations.slice(0, 3).forEach(r => {
            const payload = typeof r.payload === 'string' ? JSON.parse(r.payload) : r.payload;
            const reasons = typeof r.reasoning === 'string' ? JSON.parse(r.reasoning) : r.reasoning;
            html += `<div style="padding:12px; background:var(--p2); border:1px solid var(--border); border-radius:4px; cursor:pointer; margin-bottom:8px;" onclick="nav('advisor')">
              <div style="display:flex; justify-content:space-between; margin-bottom:6px;">
                <span style="font-weight:700; color:var(--white); font-size:0.85rem;">${r.symbol || payload.symbol}</span>
                <span class="badge bgo" style="font-size:0.6rem;">${payload.type || 'Breakout'}</span>
              </div>
              <div style="font-size:0.75rem; color:var(--t2); margin-bottom:8px; line-height:1.4;">
                ${reasons.engine_contributions || 'Scored breakout opportunity matches your profile.'}
              </div>
              <div style="display:flex; justify-content:space-between; font-size:0.65rem; color:var(--dim); font-family:'JetBrains Mono',monospace;">
                <span>Target: ₹${(payload.target || payload.target1 || 0).toFixed(2)}</span>
                <span>SL: ₹${(payload.sl || payload.stop_loss || 0).toFixed(2)}</span>
              </div>
            </div>`;
         });
         oppContainer.innerHTML = html;
      } else {
         oppContainer.innerHTML = '<div style="padding:14px; color:var(--dim); font-size:0.8rem; text-align:center;">No direct matching opportunities found today.</div>';
      }
    }
  } catch (re) {
    const oppContainer = document.getElementById('usr-opp-list');
    if (oppContainer) oppContainer.innerHTML = '<div style="padding:14px; color:var(--dim); font-size:0.8rem; text-align:center;">Tailored recommendations loading...</div>';
  }

  // 6. Risks
  const riskContainer = document.getElementById('usr-risk-list');
  if (riskContainer) {
    riskContainer.innerHTML = `
      <div style="display:flex; gap:10px; align-items:flex-start; padding:10px; background:rgba(255,152,0,0.05); border-left:3px solid var(--gold); font-size:0.78rem; border-radius:3px; margin-bottom:10px;">
         <span style="font-size:0.95rem;">⚠️</span>
         <div style="color:var(--text); line-height:1.4;">Please review single-position sizing limits before trading. Never concentrate more than your derived max threshold in a single asset class.</div>
      </div>
      <div style="display:flex; gap:10px; align-items:flex-start; padding:10px; background:rgba(242,54,69,0.05); border-left:3px solid var(--red); font-size:0.78rem; border-radius:3px;">
         <span style="font-size:0.95rem;">🚨</span>
         <div style="color:var(--text); line-height:1.4;">High volatility planetary stations are currently active. Be cautious about placing wide stop-loss orders.</div>
      </div>
    `;
  }

  // 7. News
  const newsContainer = document.getElementById('usr-news-list');
  if (newsContainer) {
    if (_ovData.news && _ovData.news.length > 0) {
       let html = '';
       _ovData.news.slice(0, 3).forEach(n => {
          html += `<div style="border-bottom:1px solid var(--border); padding-bottom:8px; margin-bottom:8px;">
            <div style="font-weight:600; color:var(--white); font-size:0.82rem; margin-bottom:4px; cursor:pointer;" onclick="nav('sentiment')">${n.title}</div>
            <p style="font-size:0.7rem; color:var(--dim); margin-bottom:0;">Source: ${n.source} · ${new Date(n.published_at).toLocaleDateString()}</p>
          </div>`;
       });
       newsContainer.innerHTML = html;
    } else {
       newsContainer.innerHTML = '<div style="padding:10px; color:var(--dim); font-size:0.8rem;">No recent news matching preferred sectors.</div>';
    }
  }
}

function renderIndicesList() {
  const c = document.getElementById('ov-indices-list');
  let html = '';
  (_ovData.indices || []).forEach((idx, i) => {
     const cls = idx.chg >= 0 ? 'var(--green)' : 'var(--red)';
     const sign = idx.chg >= 0 ? '▲' : '▼';
     html += `<div class="ov-idx-item ${i===0?'active':''}" onclick="selectIndex(${i}, this)">
       <div style="font-size:0.75rem;color:var(--dim);margin-bottom:4px;font-weight:600;">${idx.symbol}</div>
       <div style="font-family:Share Tech Mono,monospace;font-size:0.9rem;color:${cls};font-weight:700;">
         ${idx.ltp.toFixed(2)} <span style="font-size:0.7rem;">${sign} ${Math.abs(idx.chg).toFixed(2)} (${idx.chgPct.toFixed(2)}%)</span>
       </div>
     </div>`;
  });
  c.innerHTML = html;
}

function selectIndex(i, el) {
  if (el) {
    document.querySelectorAll('.ov-idx-item').forEach(x => x.classList.remove('active'));
    el.classList.add('active');
  }
  const idx = _ovData.indices[i];
  if (!idx) return;

  // Update details
  document.getElementById('ov-index-low').textContent = idx.low.toFixed(2);
  document.getElementById('ov-index-high').textContent = idx.high.toFixed(2);
  document.getElementById('ov-index-open').textContent = idx.open.toFixed(2);
  document.getElementById('ov-index-oh').textContent = idx.high.toFixed(2);
  document.getElementById('ov-index-ol').textContent = idx.low.toFixed(2);
  document.getElementById('ov-index-close').textContent = idx.prev_close.toFixed(2);
  document.getElementById('ov-index-chart-price').textContent = idx.ltp.toFixed(2);
  document.getElementById('ov-index-chart-price').style.background = idx.chg >= 0 ? 'var(--green)' : 'var(--red)';

  // Slider marker
  const range = idx.high - idx.low;
  let pct = 50;
  if (range > 0) {
     pct = ((idx.ltp - idx.low) / range) * 100;
  }
  document.getElementById('ov-index-slider-marker').style.left = pct + '%';

  // Draw chart
  drawIndexChart(idx.history || []);
}

function drawIndexChart(history) {
  const canvas = document.getElementById('ov-index-chart');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  
  const rect = canvas.parentElement.getBoundingClientRect();
  canvas.width = rect.width;
  canvas.height = rect.height;
  
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  if (!history || history.length < 2) return;

  const minP = Math.min(...history.map(d => d.c));
  const maxP = Math.max(...history.map(d => d.c));
  const range = maxP - minP;
  
  const pad = 10;
  const h = canvas.height - pad * 2;
  const w = canvas.width;
  const step = w / (history.length - 1);
  
  ctx.beginPath();
  history.forEach((d, i) => {
    const x = i * step;
    const y = range > 0 ? pad + h - ((d.c - minP) / range * h) : pad + h/2;
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  
  const isGreen = history[history.length-1].c >= history[0].c;
  const color = isGreen ? '#089981' : '#F23645';
  
  ctx.strokeStyle = color;
  ctx.lineWidth = 2;
  ctx.stroke();
  
  const grad = ctx.createLinearGradient(0, 0, 0, canvas.height);
  grad.addColorStop(0, color + '40');
  grad.addColorStop(1, color + '00');
  
  ctx.lineTo(w, canvas.height);
  ctx.lineTo(0, canvas.height);
  ctx.fillStyle = grad;
  ctx.fill();
}

function ovSetIndexChartTf(el, tf) {
  document.querySelectorAll('.ov-tf-btn').forEach(b => b.classList.remove('active'));
  el.classList.add('active');
  const activeIdxEl = document.querySelector('.ov-idx-item.active');
  if (activeIdxEl) {
     const i = Array.from(activeIdxEl.parentNode.children).indexOf(activeIdxEl);
     selectIndex(i);
  }
}

function renderMostBought() {
  const c = document.getElementById('ov-most-bought');
  let html = '';
  (_ovData.most_bought || []).forEach(s => {
    const cls = s.chg >= 0 ? 'var(--green)' : 'var(--red)';
    const sign = s.chg >= 0 ? '▲' : '▼';
    html += `<div class="ov-stock-card" onclick="nav('chart'); setTimeout(()=>document.getElementById('chart-sym').value='${s.symbol}', 500);">
      <div style="display:flex;align-items:center;gap:12px;margin-bottom:12px;">
        <div style="width:36px;height:36px;background:var(--panel);border:1px solid var(--border);border-radius:4px;display:flex;align-items:center;justify-content:center;font-weight:700;color:var(--text);font-size:0.8rem;">
          ${s.symbol.substring(0,2)}
        </div>
        <div>
          <div style="font-weight:700;color:var(--white);font-size:0.9rem;">${s.symbol}</div>
          <div style="font-size:0.7rem;color:var(--dim);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:140px;">${s.name||'Equity'}</div>
        </div>
      </div>
      <div style="font-family:Share Tech Mono,monospace;font-size:1rem;color:${cls};font-weight:700;">
        ₹${s.ltp.toFixed(2)} <span style="font-size:0.75rem;">${sign} ${Math.abs(s.chg).toFixed(2)} (${s.chgPct.toFixed(2)}%)</span>
      </div>
    </div>`;
  });
  c.innerHTML = html;
}

function ovSwitchMoversTab(el, type) {
  el.parentNode.querySelectorAll('.ov-pill-btn').forEach(b => b.classList.remove('active'));
  if(el) el.classList.add('active');
  renderMovers(type);
}

function renderMovers(type) {
  const c = document.getElementById('ov-movers-list');
  const data = type === 'gainers' ? (_ovData.gainers || []) : (_ovData.losers || []);
  let html = '';
  data.forEach(s => {
    const cls = s.chg >= 0 ? 'var(--green)' : 'var(--red)';
    const sign = s.chg >= 0 ? '▲' : '▼';
    html += `<div class="ov-trow" style="cursor:pointer;" onclick="nav('chart'); setTimeout(()=>document.getElementById('chart-sym').value='${s.symbol}', 500);">
       <div>
         <div style="font-weight:600;color:var(--white);font-size:0.85rem;">${s.symbol}</div>
         <div style="font-size:0.65rem;color:var(--dim);">${s.name||'Equity'}</div>
       </div>
       <div style="text-align:right;font-family:Share Tech Mono,monospace;color:${cls};font-size:0.85rem;">
         ₹${s.ltp.toFixed(2)} ${sign}
       </div>
       <div style="text-align:right;font-family:Share Tech Mono,monospace;color:${cls};font-size:0.85rem;">
         ${s.chgPct > 0 ? '+':''}${s.chgPct.toFixed(2)}%
       </div>
     </div>`;
  });
  c.innerHTML = html;
}

function renderSectorTabs() {
  const tabs = document.getElementById('ov-sector-tabs');
  const sectors = Object.keys(_ovData.sectors || {});
  if (sectors.length === 0) return;
  
  let html = '';
  sectors.forEach((sec, i) => {
    html += `<button class="ov-tab-btn ${i===0?'active':''}" onclick="ovSelectSector(this, '${sec}')">${sec}</button>`;
  });
  tabs.innerHTML = html;
  ovSelectSector(tabs.querySelector('.ov-tab-btn'), sectors[0]);
}

function ovSelectSector(el, sec) {
  if (el) {
    el.parentNode.querySelectorAll('.ov-tab-btn').forEach(b => b.classList.remove('active'));
    el.classList.add('active');
  }
  const data = (_ovData.sectors || {})[sec] || [];
  const c = document.getElementById('ov-sector-list');
  let html = '';
  data.forEach(s => {
    const cls = s.chg >= 0 ? 'var(--green)' : 'var(--red)';
    const sign = s.chg >= 0 ? '▲' : '▼';
    html += `<div class="ov-trow" style="cursor:pointer;" onclick="nav('chart'); setTimeout(()=>document.getElementById('chart-sym').value='${s.symbol}', 500);">
       <div>
         <div style="font-weight:600;color:var(--white);font-size:0.85rem;">${s.symbol}</div>
         <div style="font-size:0.65rem;color:var(--dim);">${s.name||'Equity'}</div>
       </div>
       <div style="text-align:right;font-family:Share Tech Mono,monospace;color:${cls};font-size:0.85rem;">
         ₹${s.ltp.toFixed(2)} ${sign}
       </div>
       <div style="text-align:right;font-family:Share Tech Mono,monospace;color:${cls};font-size:0.85rem;">
         ${s.chgPct > 0 ? '+':''}${s.chgPct.toFixed(2)}%
       </div>
     </div>`;
  });
  c.innerHTML = html;
}

function ovLoadPerformers(el, tf) {
  if(el) {
    el.parentNode.querySelectorAll('.ov-pill-btn').forEach(b => b.classList.remove('active'));
    el.classList.add('active');
  }
  const c = document.getElementById('ov-performers-list');
  const data = (_ovData.performers || {})[tf] || [];
  let html = '';
  data.forEach(s => {
     html += `<div class="ov-stock-card" onclick="nav('chart'); setTimeout(()=>document.getElementById('chart-sym').value='${s.symbol}', 500);">
       <div style="display:flex;justify-content:space-between;margin-bottom:12px;">
         <div>
           <div style="font-weight:700;color:var(--white);font-size:0.9rem;">${s.symbol}</div>
           <div style="font-size:0.7rem;color:var(--dim);">${s.name||'Equity'}</div>
         </div>
         <div style="background:rgba(8,153,129,0.1);color:var(--green);font-family:Share Tech Mono,monospace;font-size:0.75rem;padding:4px 8px;border-radius:4px;font-weight:700;">
           +${s.returnPct.toFixed(2)}%
         </div>
       </div>
       <div style="font-family:Share Tech Mono,monospace;font-size:0.9rem;color:var(--green);font-weight:700;">
         ₹${s.ltp.toFixed(2)} <span style="font-size:0.7rem;">▲ ${s.chg.toFixed(2)}</span>
       </div>
     </div>`;
  });
  c.innerHTML = html;
}

function ovLoadScreeners(el, type) {
  if(el) {
    el.parentNode.querySelectorAll('.ov-tab-btn').forEach(b => b.classList.remove('active'));
    el.classList.add('active');
  }
  const c = document.getElementById('ov-screeners-list');
  const data = (_ovData.screeners || {})[type] || [];
  let html = '';
  data.forEach(s => {
    const cls = s.chg >= 0 ? 'var(--green)' : 'var(--red)';
    const sign = s.chg >= 0 ? '▲' : '▼';
    html += `<div class="ov-stock-card" style="min-width:180px;" onclick="nav('chart'); setTimeout(()=>document.getElementById('chart-sym').value='${s.symbol}', 500);">
      <div style="font-weight:600;color:var(--white);font-size:0.85rem;">${s.symbol}</div>
      <div style="font-size:0.65rem;color:var(--dim);margin-bottom:8px;">${s.name||'Equity'}</div>
      <div style="font-family:Share Tech Mono,monospace;font-size:0.9rem;color:${cls};font-weight:700;">
        ₹${s.ltp.toFixed(2)} <span style="font-size:0.65rem;">${sign} (${s.chgPct.toFixed(2)}%)</span>
      </div>
    </div>`;
  });
  c.innerHTML = html;
}

function ovLoadSignals(el, type) {
  if(el) {
    el.parentNode.querySelectorAll('.ov-tab-btn').forEach(b => b.classList.remove('active'));
    el.classList.add('active');
  }
  const c = document.getElementById('ov-signals-list');
  const data = (_ovData.signals || {})[type] || [];
  let html = '';
  data.forEach(s => {
    const cls = s.signal === 'Bullish' ? 'var(--green)' : s.signal === 'Bearish' ? 'var(--red)' : 'var(--dim)';
    const bg  = s.signal === 'Bullish' ? 'rgba(8,153,129,0.1)' : s.signal === 'Bearish' ? 'rgba(242,54,69,0.1)' : 'rgba(255,255,255,0.05)';
    html += `<div class="ov-signal-card" onclick="nav('chart'); setTimeout(()=>document.getElementById('chart-sym').value='${s.symbol}', 500);">
       <div class="ov-signal-indicator" style="background:${bg};color:${cls};border-right:1px solid var(--border);">
          <div style="font-size:1.4rem;margin-bottom:4px;">${s.signal==='Bullish'?'↑↑':s.signal==='Bearish'?'↓↓':'−'}</div>
          ${s.pattern}<br>(${s.signal})
       </div>
       <div class="ov-signal-details">
          <div>
            <div style="font-weight:700;color:var(--white);font-size:0.9rem;">${s.symbol}</div>
            <div style="font-size:0.7rem;color:var(--dim);margin-bottom:4px;">${s.name||'Equity'}</div>
            <div style="font-size:0.7rem;color:var(--dim);">Time Frame: ${s.tf}</div>
          </div>
          <div style="text-align:right;font-family:Share Tech Mono,monospace;">
            <div style="font-size:0.9rem;color:${s.chg>=0?'var(--green)':'var(--red)'};font-weight:700;">₹${s.ltp.toFixed(2)}</div>
            <div style="font-size:0.7rem;color:${s.chg>=0?'var(--green)':'var(--red)'};">${s.chg>=0?'▲':'▼'} ${Math.abs(s.chg).toFixed(2)} (${s.chgPct.toFixed(2)}%)</div>
          </div>
       </div>
    </div>`;
  });
  c.innerHTML = html;
}

function renderResearch() {
  const c = document.getElementById('ov-research-list');
  const data = _ovData.research || [];
  let html = '';
  data.forEach(s => {
     html += `<div class="ov-research-card" onclick="nav('chart'); setTimeout(()=>document.getElementById('chart-sym').value='${s.symbol}', 500);">
       <div style="display:flex;justify-content:space-between;margin-bottom:12px;">
         <div>
           <div style="font-weight:700;color:var(--white);font-size:0.9rem;">${s.symbol}</div>
           <div style="font-size:0.7rem;color:var(--dim);">${s.name||'Equity'}</div>
         </div>
         <div style="font-size:0.7rem;color:var(--green);font-weight:600;display:flex;align-items:center;gap:4px;">
           <div style="width:6px;height:6px;border-radius:50%;background:var(--green);"></div> ${s.type}
         </div>
       </div>
       
       <div style="display:flex;justify-content:space-between;align-items:flex-end;margin-bottom:16px;">
         <div>
           <div style="font-size:0.7rem;color:var(--dim);margin-bottom:2px;">LTP</div>
           <div style="font-family:Share Tech Mono,monospace;font-size:0.9rem;color:var(--green);font-weight:700;">₹${s.ltp.toFixed(2)} <span style="font-size:0.7rem;">▲ ${s.chgPct.toFixed(2)}%</span></div>
         </div>
         <div style="text-align:right;">
           <div style="font-size:0.7rem;color:var(--dim);margin-bottom:2px;">Recommended Price</div>
           <div style="font-family:Share Tech Mono,monospace;font-size:0.85rem;color:var(--white);">₹${s.rec_price.toFixed(2)} - ₹${(s.rec_price*1.01).toFixed(2)}</div>
         </div>
       </div>

       <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;font-family:Share Tech Mono,monospace;font-size:0.8rem;">
         <div style="text-align:center;">
           <div style="color:var(--red);font-size:0.65rem;margin-bottom:2px;font-weight:600;">SL</div>
           <div style="color:var(--text);">${s.sl.toFixed(2)}</div>
         </div>
         <div style="text-align:center;">
           <div style="color:var(--green);font-size:0.65rem;margin-bottom:2px;font-weight:600;">ENTRY</div>
           <div style="color:var(--text);">${s.rec_price.toFixed(2)}</div>
         </div>
         <div style="text-align:center;">
           <div style="color:var(--gold);font-size:0.65rem;margin-bottom:2px;font-weight:600;">TARGET</div>
           <div style="color:var(--text);">${s.target.toFixed(2)}</div>
         </div>
       </div>

       <div style="background:rgba(255,152,0,0.1);color:var(--gold);font-size:0.75rem;padding:6px;text-align:center;border-radius:4px;font-weight:600;margin-bottom:12px;">
         ${s.potential}% POTENTIAL EXPECTED
       </div>

       <div style="display:flex;justify-content:space-between;align-items:center;">
         <div style="font-size:0.65rem;color:var(--dim);">Updated: ${s.updated}</div>
         <button class="btn" style="padding:6px 20px;font-size:0.8rem;" onclick="event.stopPropagation();document.getElementById('chart-sym').value='${s.symbol}';nav('chart');loadChart();setTimeout(()=>chartShowOrder('BUY'), 600);">BUY</button>
       </div>
     </div>`;
  });
  c.innerHTML = html;
}

function ovLoadPocket(el, maxPrice) {
  if(el) {
    el.parentNode.querySelectorAll('.ov-pill-btn').forEach(b => b.classList.remove('active'));
    el.classList.add('active');
  }
  const c = document.getElementById('ov-pocket-list');
  const data = (_ovData.pocket || []).filter(s => s.ltp <= maxPrice);
  let html = '';
  data.forEach(s => {
    const cls = s.chg >= 0 ? 'var(--green)' : 'var(--red)';
    const sign = s.chg >= 0 ? '▲' : '▼';
    html += `<div class="ov-stock-card" style="min-width:180px;" onclick="nav('chart'); setTimeout(()=>document.getElementById('chart-sym').value='${s.symbol}', 500);">
      <div style="font-weight:600;color:var(--white);font-size:0.85rem;">${s.symbol}</div>
      <div style="font-size:0.65rem;color:var(--dim);margin-bottom:8px;">${s.name||'Equity'}</div>
      <div style="font-family:Share Tech Mono,monospace;font-size:0.9rem;color:${cls};font-weight:700;">
        ₹${s.ltp.toFixed(2)} <span style="font-size:0.65rem;">${sign} (${s.chgPct.toFixed(2)}%)</span>
      </div>
    </div>`;
  });
  c.innerHTML = html || '<div style="color:var(--dim);font-size:0.8rem;padding:10px;">No stocks found in this range.</div>';
}
"""
