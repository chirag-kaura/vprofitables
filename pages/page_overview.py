# -*- coding: utf-8 -*-
"""
page_overview.py — Market Overview Home Page (Default Landing Page)
"""

HTML = r"""
<!-- ═══════════ PAGE: MARKET OVERVIEW ═══════════ -->
<div class="page" id="page-overview" style="padding-top:0;">
  
  <!-- Accessible overview navigation -->
  <div class="ov-tabs" role="tablist" aria-label="Overview sections">
    <button class="ov-tab active" role="tab" aria-selected="true" aria-controls="ov-discovery-pane" id="ov-tab-discovery" onclick="ovSwitchMainTab(this, 'discovery')">Discover</button>
    <button class="ov-tab" role="tab" aria-selected="false" aria-controls="ov-index-fno-pane" id="ov-tab-index-fno" onclick="ovSwitchMainTab(this, 'index_fno')">Derivatives</button>
    <button class="ov-tab" role="tab" aria-selected="false" aria-controls="ov-markets-pane" id="ov-tab-markets" onclick="ovSwitchMainTab(this, 'markets')">Markets</button>
    <button class="ov-tab" role="tab" aria-selected="false" aria-controls="ov-news-pane" id="ov-tab-news" onclick="ovSwitchMainTab(this, 'news')">News</button>
  </div>

  <div id="ov-loading" class="loading"><div class="spinner"></div>LOADING MARKET DATA...</div>
  
  <div id="ov-content" style="display:none;padding-bottom:40px;">
      
      <!-- B. STOCK DISCOVERY PANELS -->
    <div id="ov-discovery-pane" role="tabpanel" aria-labelledby="ov-tab-discovery">
      
      <!-- 1. INDEX OVERVIEW (Bug 7) -->
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
        <h3 style="font-size:1.1rem;margin:0;color:var(--white);">Index Overview</h3>
      </div>
      <div id="ov-discovery-asof" class="ov-data-note" style="margin:-5px 0 12px;"></div>
      <div class="card admin-gated-section" data-feature-id="intraday_reversal_matrix" data-feature-name="Index Overview & Day Range" data-feature-page="overview" style="position:relative; padding:0;overflow:hidden;margin-bottom:24px;">
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
               <span id="ov-index-chart-tf-label" style="font-size:0.75rem;color:var(--dim);font-family:'JetBrains Mono',monospace;">1M Trend</span>
            </div>
            <div style="flex:1;position:relative;min-height:160px;margin-bottom:12px;">
               <canvas id="ov-index-chart" style="width:100%;height:100%;position:absolute;inset:0;"></canvas>
            </div>
            <div style="display:flex;gap:8px;justify-content:center;">
               <button class="ov-tf-btn" onclick="ovSetIndexChartTf(this,'1D')">1D</button>
               <button class="ov-tf-btn" onclick="ovSetIndexChartTf(this,'1W')">1W</button>
               <button class="ov-tf-btn active" onclick="ovSetIndexChartTf(this,'1M')">1M</button>
               <button class="ov-tf-btn" onclick="ovSetIndexChartTf(this,'1Y')">1Y</button>
               <button class="ov-tf-btn" onclick="ovSetIndexChartTf(this,'ALL')">All</button>
            </div>
          </div>
        </div>
      </div>

      <!-- 2. MOST BOUGHT STOCKS (Bug 8: Subtitle added, View All removed) -->
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
        <div>
          <h3 style="font-size:1.1rem;color:var(--white);margin:0 0 2px 0;">Most Traded by Volume</h3>
        </div>
      </div>
      <div class="ov-data-note" id="ov-most-bought-asof" style="margin:-10px 0 10px;"></div>
      <div id="ov-most-bought" class="ov-hscroll admin-gated-section" data-feature-id="overview_most_bought" data-feature-name="Most Traded by Volume" data-feature-page="overview" style="position:relative; margin-bottom:30px;"></div>

      <!-- 3. TOP MOVERS & SECTORWISE (Bug 9: Wired Nifty 50/500 & Sector dropdown) -->
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
        <h3 style="font-size:1.1rem;color:var(--white);margin:0;">Top Movers and Sectorwise Movements</h3>
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:30px;">
        <div class="card" style="padding:16px;">
          <div style="display:flex;justify-content:space-between;margin-bottom:16px;align-items:center;">
             <div style="display:flex;gap:0;">
               <button class="ov-pill-btn active" onclick="ovSwitchMoversTab(this,'gainers')" style="border-radius:4px 0 0 4px;">Gainers</button>
               <button class="ov-pill-btn" onclick="ovSwitchMoversTab(this,'losers')" style="border-radius:0 4px 4px 0;">Losers</button>
             </div>
             <select class="ov-select" id="ov-movers-universe" onchange="ovFilterMoversUniverse(this.value)">
               <option value="nifty500">All tracked equities</option>
               <option value="nifty50">Nifty 50 (configured list)</option>
             </select>
          </div>
          <div class="ov-table-hdr" style="display:grid;grid-template-columns:1.5fr 1fr 1fr;padding-bottom:8px;border-bottom:1px solid var(--border);color:var(--dim);font-size:0.75rem;">
            <div>Stock</div><div style="text-align:right;">LTP ↕</div><div style="text-align:right;">%Chng ↕</div>
          </div>
          <div id="ov-movers-list" style="max-height:300px;overflow-y:auto;"></div>
        </div>
        
        <div class="card admin-gated-section" data-feature-id="overview_sector_movements" data-feature-name="Sectorwise Movements Heatmap" data-feature-page="overview" style="position:relative; padding:16px;">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;gap:8px;">
            <span style="font-size:0.8rem;color:var(--dim);font-weight:600;">Sector Filter:</span>
            <select class="ov-select" id="ov-sector-select" onchange="ovSelectSectorDropdown(this.value)" style="flex:1;max-width:240px;font-weight:600;">
              <!-- Populated via JS -->
            </select>
          </div>
          <div class="ov-table-hdr" style="display:grid;grid-template-columns:1.5fr 1fr 1fr;padding-bottom:8px;border-bottom:1px solid var(--border);color:var(--dim);font-size:0.75rem;">
            <div>Stock</div><div style="text-align:right;">LTP ↕</div><div style="text-align:right;">%Chng ↕</div>
          </div>
          <div id="ov-sector-list" style="max-height:280px;overflow-y:auto;"></div>
        </div>
      </div>

      <!-- 4. TOP PERFORMERS (Bug 10: Equities-only, Cap dropdown wired, View All removed) -->
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
        <div>
          <h3 style="font-size:1.1rem;color:var(--white);margin:0 0 2px 0;">Top Performers</h3>
        </div>
      </div>
      <div class="card" style="padding:16px;margin-bottom:30px;">
         <div style="display:flex;justify-content:space-between;margin-bottom:16px;flex-wrap:wrap;gap:12px;">
            <div style="display:flex;gap:0;">
               <button class="ov-pill-btn active" onclick="ovLoadPerformers(this,'1W')" style="border-radius:4px 0 0 4px;">1 Week</button>
               <button class="ov-pill-btn" onclick="ovLoadPerformers(this,'1M')" style="border-radius:0;">1 Month</button>
               <button class="ov-pill-btn" onclick="ovLoadPerformers(this,'1Y')" style="border-radius:0;">1 Year</button>
               <button class="ov-pill-btn" onclick="ovLoadPerformers(this,'5Y')" style="border-radius:0 4px 4px 0;">5 Year</button>
            </div>
            <select class="ov-select" id="ov-perf-cap" onchange="ovFilterPerfCap(this.value)">
              <option value="all">All Equities</option>
              <option value="nifty50">Nifty 50</option>
            </select>
         </div>
         <div id="ov-performers-list" class="ov-hscroll"></div>
      </div>

      <!-- 5. TECHNICAL SCREENERS (Bug 11: RSI renamed, Bullish/Bearish badges, dropdowns & View All removed) -->
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
        <div>
          <h3 style="font-size:1.1rem;color:var(--white);margin:0 0 2px 0;">Technical Screeners</h3>
        </div>
      </div>
      <div class="card" style="padding:16px;margin-bottom:30px;">
         <div style="display:flex;justify-content:space-between;margin-bottom:16px;flex-wrap:wrap;gap:12px;">
            <div style="display:flex;gap:8px;flex-wrap:wrap;">
               <button class="ov-tab-btn" onclick="ovLoadScreeners(this,'pivot')">Simple Pivot</button>
               <button class="ov-tab-btn active" onclick="ovLoadScreeners(this,'rsi')">RSI</button>
               <button class="ov-tab-btn" onclick="ovLoadScreeners(this,'macd')">MACD</button>
               <button class="ov-tab-btn" onclick="ovLoadScreeners(this,'sma')">SMA</button>
               <button class="ov-tab-btn" onclick="ovLoadScreeners(this,'ema')">EMA</button>
            </div>
         </div>
         <div id="ov-screeners-list" class="ov-hscroll"></div>
      </div>

      <!-- 6. TRADING SIGNALS (Bug 12: Trigger logics clarified, View All removed) -->
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
        <div>
          <h3 style="font-size:1.1rem;color:var(--white);margin:0 0 2px 0;">Trading Signals</h3>
        </div>
      </div>
      <div class="card" style="padding:16px;margin-bottom:30px;">
         <div style="display:flex;gap:8px;margin-bottom:16px;">
             <button class="ov-tab-btn active" onclick="ovLoadSignals(this,'candles')">Candlesticks</button>
             <button class="ov-tab-btn" onclick="ovLoadSignals(this,'patterns')">Chart Patterns</button>
             <button class="ov-tab-btn" onclick="ovLoadSignals(this,'priceaction')">Price Action</button>
         </div>
         <div id="ov-signals-list" class="ov-hscroll"></div>
      </div>

      <!-- 7. RESEARCH RECOMMENDATIONS (Bug 13: Horizon dropdown added) -->
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;flex-wrap:wrap;gap:10px;">
        <div>
          <h3 style="font-size:1.1rem;color:var(--white);margin:0 0 2px 0;">Research Recommendations</h3>
        </div>
        <div style="display:flex;gap:12px;align-items:center;">
          <select class="ov-select" id="ov-research-horizon" onchange="ovFilterResearchHorizon(this.value)">
            <option value="all">All Horizons</option>
            <option value="swing">Swing (3-15 Days)</option>
            <option value="short">Short-Term (1-3 Months)</option>
            <option value="long">Long-Term / Positional (6-12 Mo)</option>
            <option value="intraday">Intraday</option>
          </select>
          <a href="#" onclick="event.preventDefault(); nav('trade_simulation');" style="color:var(--cyan);font-size:0.8rem;text-decoration:none;font-weight:600;">TRADE SIMULATION ›</a>
        </div>
      </div>
      <div id="ov-research-list" class="ov-hscroll" style="margin-bottom:30px;"></div>

      <!-- 8. POCKET FRIENDLY STOCKS (Bug 14: Non-overlapping brackets, View All removed) -->
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
        <div>
          <h3 style="font-size:1.1rem;color:var(--white);margin:0 0 2px 0;">Pocket Friendly Stocks</h3>
        </div>
      </div>
      <div class="card" style="padding:16px;margin-bottom:30px;">
         <div style="display:flex;gap:0;margin-bottom:16px;">
             <button class="ov-pill-btn active" onclick="ovLoadPocket(this, 0, 50)" style="border-radius:4px 0 0 4px;">₹0 – ₹50</button>
             <button class="ov-pill-btn" onclick="ovLoadPocket(this, 50, 100)" style="border-radius:0;">₹50 – ₹100</button>
             <button class="ov-pill-btn" onclick="ovLoadPocket(this, 100, 200)" style="border-radius:0;">₹100 – ₹200</button>
             <button class="ov-pill-btn" onclick="ovLoadPocket(this, 200, 500)" style="border-radius:0 4px 4px 0;">₹200 – ₹500</button>
         </div>
         <div id="ov-pocket-list" class="ov-hscroll"></div>
      </div>
    </div>

    <!-- C. OTHER PANELS -->
    <div id="ov-index-fno-pane" role="tabpanel" aria-labelledby="ov-tab-index-fno" style="display:none;">
       <div class="ov-section-heading"><div><span class="ov-overline">OPTIONS MARKET</span><h2>Options chain</h2></div></div>
       <div class="ov-chain-controls card">
         <label>Underlying<input class="ov-select" id="ov-chain-symbol" type="search" list="ov-chain-symbol-list" placeholder="Search symbol or company" autocomplete="off" onchange="ovLoadDerivativeChain()"><datalist id="ov-chain-symbol-list"></datalist></label>
         <label>Expiry<select class="ov-select" id="ov-chain-expiry" onchange="ovLoadDerivativeChain()"><option value="">Select underlying</option></select></label>
         <label>Session<select class="ov-select" id="ov-chain-session" onchange="ovLoadDerivativeChain()"><option value="">Latest available</option></select></label>
       </div>
       <div id="ov-chain-status" class="ov-data-note" style="margin:6px 0 10px;"></div>
       <div id="ov-chain-summary" class="ov-chain-summary"></div>
       <div id="ov-chain-table-wrap" class="card ov-chain-table-wrap"></div>
       <div class="ov-data-note ov-chain-guide"><strong>How to read it:</strong> Open interest (OI) is outstanding contracts; Δ OI is the change recorded by this feed; volume is contracts traded in the captured session. Compare call and put changes with the underlying price and prior snapshots. These values describe positioning and activity, not a standalone bullish or bearish forecast.</div>
    </div>
    <div id="ov-markets-pane" role="tabpanel" aria-labelledby="ov-tab-markets" style="display:none;">
       <div class="ov-section-heading"><div><span class="ov-overline">MARKET BOARD</span><h2>Indices &amp; commodities</h2></div><span class="ov-data-note" id="ov-markets-asof"></span></div>
       <div class="ov-market-subtabs"><button class="ov-pill-btn active" onclick="ovSwitchMarketType(this,'indices')">Indices</button><button class="ov-pill-btn" onclick="ovSwitchMarketType(this,'commodities')">Commodities</button></div>
       <div id="ov-markets-list" class="ov-markets-grid"></div>
    </div>
    
    <div id="ov-news-pane" role="tabpanel" aria-labelledby="ov-tab-news" style="display:none;">
       <h3 style="font-size:1.1rem;margin-bottom:12px;color:var(--white);">Market News and Sentiment</h3>
       <div id="ov-news-list" style="display:flex;flex-direction:column;gap:16px;"></div>
    </div>
  </div> <!-- closes ov-content -->
</div> <!-- closes page-overview -->

<style>
.ov-tabs{display:flex;gap:6px;border-bottom:1px solid var(--border);margin:12px 0 14px;overflow-x:auto;position:sticky;top:0;background:var(--bg);z-index:10;padding:4px 0}
.ov-tab{font:600 .82rem Inter,sans-serif;color:var(--dim);background:transparent;border:0;border-bottom:2px solid transparent;padding:11px 14px;white-space:nowrap;cursor:pointer}
.ov-tab:hover,.ov-tab:focus-visible{color:var(--text)}.ov-tab:focus-visible{outline:2px solid var(--cyan);outline-offset:2px}.ov-tab.active{color:var(--cyan);border-bottom-color:var(--cyan)}
.ov-overline{font-size:.62rem;letter-spacing:.1em;font-weight:700;color:var(--dim)}
.ov-hero-grid,.ov-content-grid{display:grid;grid-template-columns:minmax(0,1.3fr) minmax(280px,1fr);gap:16px;margin-bottom:16px}
.ov-summary-card,.ov-content-card,.ov-action-card,.ov-news-card,.ov-insight-card{padding:18px}
.ov-section-heading{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:15px}.ov-section-heading h2{font-size:1rem;margin:4px 0 0;color:var(--white)}
.ov-metric-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}.ov-metric-grid>div{display:flex;flex-direction:column;gap:5px}.ov-metric-grid span{font-size:.7rem;color:var(--dim)}.ov-metric-grid strong{font:700 1.1rem 'JetBrains Mono',monospace;color:var(--white)}
.ov-data-note{font-size:.68rem;color:var(--dim);line-height:1.5}.ov-market-score{font-size:1.25rem;font-weight:700;color:var(--white);margin:14px 0 6px}.ov-market-bar{height:5px;background:linear-gradient(90deg,var(--red),var(--gold),var(--green));border-radius:5px;margin-top:14px;position:relative}.ov-market-bar span{position:absolute;height:13px;width:3px;background:white;top:-4px;left:50%;transition:left .25s}
.ov-info-button{border:1px solid var(--border);background:transparent;color:var(--dim);border-radius:4px;padding:6px 9px;font-size:.68rem;cursor:help}.ov-action-card{margin-bottom:16px}.ov-action-list,.ov-list{display:flex;flex-direction:column;gap:8px}.ov-action-row{display:flex;gap:10px;align-items:flex-start;padding:10px 12px;border-left:3px solid var(--border);background:var(--p2);border-radius:4px;font-size:.78rem;line-height:1.45}.ov-action-row.danger{border-color:var(--red)}.ov-action-row.warn{border-color:var(--gold)}.ov-action-row.info{border-color:var(--cyan)}
.ov-add-row{display:flex;gap:6px;margin-bottom:10px}.ov-add-row input{flex:1;min-width:0;background:var(--p2);border:1px solid var(--border);border-radius:4px;color:var(--white);padding:8px 10px}.ov-news-toggle{display:flex}.ov-news-toggle button{padding:6px 10px}.ov-empty{padding:12px 0;color:var(--dim);font-size:.8rem}.ov-insight-copy{font-size:.82rem;line-height:1.6;color:var(--text)}
@media(max-width:800px){.ov-hero-grid,.ov-content-grid{grid-template-columns:1fr}.ov-metric-grid{grid-template-columns:1fr 1fr}}
@media(max-width:480px){.ov-summary-card,.ov-content-card,.ov-action-card,.ov-news-card,.ov-insight-card{padding:14px}.ov-metric-grid{grid-template-columns:1fr}.ov-tab{padding:10px 9px}}
.ov-tab-old-marker {display:none}
 font-family:'Inter',sans-serif; font-size:0.9rem; color:var(--dim); cursor:pointer; padding-bottom:8px; border-bottom:2px solid transparent; white-space:nowrap; transition:all 0.2s; }
.ov-tab-old:hover { color:var(--text); }
.ov-tab-old.active { color:var(--cyan); border-bottom-color:var(--cyan); font-weight:600; }

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

.ov-select { background:var(--panel); border:1px solid var(--border); color:var(--text); padding:6px 10px; border-radius:4px; outline:none; font-size:0.8rem; cursor:pointer; }
.ov-select:focus { border-color:var(--cyan); }

.ov-trow { display:grid; grid-template-columns:1.5fr 1fr 1fr; padding:12px 0; border-bottom:1px solid var(--border); align-items:center; }
.ov-trow:hover { background:rgba(255,255,255,0.02); }

.ov-signal-card { display:flex; background:var(--p2); border:1px solid var(--border); border-radius:6px; overflow:hidden; min-width:320px; flex-shrink:0; cursor:pointer; }
.ov-signal-card:hover { border-color:var(--dim); }
.ov-signal-indicator { width:80px; display:flex; flex-direction:column; justify-content:center; align-items:center; padding:12px; font-size:0.75rem; text-align:center; font-weight:600; }
.ov-signal-details { padding:16px; flex:1; display:flex; justify-content:space-between; align-items:center; }

.ov-research-card { background:var(--p2); border:1px solid var(--border); border-radius:6px; padding:16px; min-width:320px; flex-shrink:0; cursor:pointer;}
.ov-research-card:hover { border-color:var(--dim); }

.ov-tab{font-family:Inter,sans-serif;font-size:.82rem;color:var(--dim);background:transparent;border:0;border-bottom:2px solid transparent;padding:11px 14px;white-space:nowrap;cursor:pointer;transition:color .15s,border-color .15s}
.ov-tab.active{color:var(--cyan);border-bottom-color:var(--cyan);font-weight:600}
.ov-derivatives-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:12px}.ov-option-metric{display:flex;justify-content:space-between;gap:12px;margin:10px 0;font-size:.78rem}.ov-option-metric span{color:var(--dim)}
.ov-chain-controls{display:flex;flex-wrap:wrap;gap:12px;padding:14px;margin-bottom:12px}.ov-chain-controls label{display:flex;flex-direction:column;gap:5px;color:var(--dim);font-size:.72rem}.ov-chain-summary{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:12px}.ov-chain-summary .card{padding:12px 16px;min-width:140px}.ov-chain-table-wrap{overflow:auto;padding:0}.ov-chain-table{width:100%;min-width:760px;border-collapse:collapse;font-size:.76rem}.ov-chain-table th,.ov-chain-table td{padding:9px 8px;text-align:right;border-bottom:1px solid var(--border);white-space:nowrap}.ov-chain-table th{color:var(--dim);font-weight:600;position:sticky;top:0;background:var(--panel)}.ov-chain-table td:nth-child(4),.ov-chain-table th:nth-child(4){text-align:center}.ov-chain-table .call-side{color:#72c7aa}.ov-chain-table .put-side{color:#f28b96}.ov-chain-guide{padding:12px 4px;max-width:1000px}.ov-market-subtabs{display:flex;gap:6px;margin-bottom:14px}.ov-markets-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:12px}
</style>
"""

JS = r"""
var _ovData = window._ovData || null;
var _ovCurrentIndexIdx = 0;
var _ovCurrentIndexTf = '1M';
var _ovCurrentMoversType = 'gainers';
var _ovCurrentMoversUniverse = 'nifty500';
var _ovCurrentPerfTf = '1W';
var _ovCurrentPerfCap = 'all';
var _ovCurrentResearchHorizon = 'all';
var _ovLoadedSections = new Set();
var _ovPocketRequest = 0;
function ovEsc(value) { return String(value == null ? '' : value).replace(/[&<>\"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#39;'}[ch])); }
function ovSafeHref(value) {
  try { const u = new URL(String(value || ''), window.location.href); return (u.protocol === 'http:' || u.protocol === 'https:') ? u.href : ''; }
  catch (_) { return ''; }
}

async function loadOverview() {
  if (_ovData) {
    document.getElementById('ov-loading').style.display = 'none';
    document.getElementById('ov-content').style.display = 'block';
    renderOverview();
    return;
  }
  document.getElementById('ov-loading').style.display = 'flex';
  document.getElementById('ov-content').style.display = 'none';
  try {
    const res = await api('overview_data', {section: 'discovery'});
    if (res.error) throw new Error(res.error);
    _ovData = res;
    _ovLoadedSections.add('discovery');
    document.getElementById('ov-loading').style.display = 'none';
    document.getElementById('ov-content').style.display = 'block';
    renderOverview();
  } catch (e) {
    document.getElementById('ov-loading').innerHTML = '<div class="err">Market overview could not load. <button class="btn btn-sm" onclick="loadOverview()">Retry</button></div>';
  }
}

async function ovEnsureTabData(tab) {
  if (tab === 'stocks_fno') tab = 'index_fno';
  if (_ovLoadedSections.has(tab)) return;
  _ovLoadedSections.add(tab);
  const targets = {discovery:'discovery', index_fno:'derivatives', markets:'markets', news:'news'};
  const section = targets[tab];
  if (!section) return;
  try {
    const payload = await api('overview_data', {section});
    if (payload && !payload.error) {
      _ovData = Object.assign({}, _ovData || {}, payload);
      _ovLoadedSections.add(section);
      if (section === 'discovery') renderDiscovery();
      else if (section === 'derivatives') ovInitDerivativeControls();
      else if (section === 'markets') renderMarketsTab('indices');
      else if (section === 'news') renderNewsTab();
    } else {
      _ovLoadedSections.delete(tab);
    }
  } catch (e) {
    _ovLoadedSections.delete(tab);
  }
}

document.addEventListener('keydown', function(e) {
  const tab = e.target.closest && e.target.closest('.ov-tabs [role="tab"]');
  if (!tab || !['ArrowLeft','ArrowRight','Home','End'].includes(e.key)) return;
  const tabs = Array.from(document.querySelectorAll('.ov-tabs [role="tab"]'));
  let i = tabs.indexOf(tab);
  if (e.key === 'ArrowRight') i = (i + 1) % tabs.length;
  else if (e.key === 'ArrowLeft') i = (i - 1 + tabs.length) % tabs.length;
  else if (e.key === 'Home') i = 0; else i = tabs.length - 1;
  e.preventDefault(); tabs[i].focus(); tabs[i].click();
});

function ovSwitchMainTab(el, tab) {
  document.querySelectorAll('.ov-tab').forEach(t => {
    t.classList.remove('active');
    t.setAttribute('aria-selected', 'false');
    t.tabIndex = -1;
  });
  el.classList.add('active');
  el.setAttribute('aria-selected', 'true');
  el.tabIndex = 0;
  const paneMap = {discovery:'ov-discovery-pane', index_fno:'ov-index-fno-pane', markets:'ov-markets-pane', news:'ov-news-pane'};
  Object.values(paneMap).forEach(id => { const node = document.getElementById(id); if (node) node.style.display = 'none'; });
  const pane = document.getElementById(paneMap[tab]);
  if (pane) pane.style.display = 'block';
  if (tab === 'discovery' && _ovData && _ovLoadedSections.has('discovery')) renderDiscovery();
  if (tab === 'index_fno' && _ovData && _ovLoadedSections.has('derivatives')) ovInitDerivativeControls();
  if (tab === 'markets' && _ovData && _ovLoadedSections.has('markets')) renderMarketsTab('indices');
  if (tab === 'news' && _ovData && _ovLoadedSections.has('news')) renderNewsTab();
  ovEnsureTabData(tab);
}

function renderOverview() {
  if (!_ovData) return;
  renderDiscovery();
}

function renderDiscovery() {
  if (!_ovData) return;
  const coverageNote = document.getElementById('ov-discovery-asof');
  if (coverageNote) {
    const meta = _ovData.meta || {};
    coverageNote.textContent = meta.trade_date ? `Market data through ${meta.trade_date}${meta.fallback ? ` · ${meta.latest_coverage_pct}% latest-date coverage; prior comparable snapshot shown` : ''}` : 'Snapshot date unavailable';
    coverageNote.title = meta.selection_note || '';
  }
  renderIndicesList();
  setTimeout(() => selectIndex(_ovCurrentIndexIdx), 0);
  renderMostBought();
  renderMovers(_ovCurrentMoversType);
  renderSectorTabs();
  const perfBtn = document.querySelector('#ov-discovery-pane [onclick*="ovLoadPerformers"].active');
  if (perfBtn) ovLoadPerformers(perfBtn, '1W');
  const screenBtn = document.querySelector('#ov-discovery-pane .ov-tab-btn.active');
  if (screenBtn) ovLoadScreeners(screenBtn, 'rsi');
  const sigBtn = document.querySelectorAll('#ov-signals-list')[0]?.previousElementSibling?.querySelector('.active');
  if (sigBtn) ovLoadSignals(sigBtn, 'candles');
  renderResearch();
  const pktBtn = document.querySelector('#ov-pocket-list')?.previousElementSibling?.querySelector('.active');
  if (pktBtn) ovLoadPocket(pktBtn, 0, 50);
}

// ══════════════════════════════════════════════════════════════════════════════
// STOCK DISCOVERY FUNCTIONS
// ══════════════════════════════════════════════════════════════════════════════


async function ovAddToWatchlist(sym) {
  sym = (sym || '').toUpperCase().trim();
  if (!sym) { alert('Enter a valid symbol (e.g. RELIANCE, TCS)'); return; }
  try {
    const res = await api('watchlist_add', {symbol: sym});
    if (res && res.ok) {
      const inp = document.getElementById('ov-wl-input');
      if (inp) inp.value = '';
      if (typeof mdLoad === 'function') mdLoad();
    } else {
      alert((res && res.error) || 'Failed to add to watchlist');
    }
  } catch(e) {
    alert('Error: ' + e.message);
  }
}

async function ovRemoveFromWatchlist(sym) {
  if (!confirm('Remove ' + sym + ' from watchlist?')) return;
  try {
    const res = await api('watchlist_remove', {symbol: sym});
    if (res && res.ok) {
      if (typeof mdLoad === 'function') mdLoad();
    }
  } catch(e) {}
}

function renderIndicesList() {
  const c = document.getElementById('ov-indices-list');
  let html = '';
  (_ovData.indices || []).forEach((idx, i) => {
     const cls = idx.chg >= 0 ? 'var(--green)' : 'var(--red)';
     const sign = idx.chg >= 0 ? '▲' : '▼';
     html += `<div class="ov-idx-item ${i===_ovCurrentIndexIdx?'active':''}" onclick="selectIndex(${i}, this)">
       <div style="font-size:0.75rem;color:var(--dim);margin-bottom:4px;font-weight:600;">${idx.symbol}</div>
       <div style="font-family:Share Tech Mono,monospace;font-size:0.9rem;color:${cls};font-weight:700;">
         ${idx.ltp.toFixed(2)} <span style="font-size:0.7rem;">${sign} ${Math.abs(idx.chg).toFixed(2)} (${idx.chgPct.toFixed(2)}%)</span>
       </div>
     </div>`;
  });
  c.innerHTML = html;
}

function selectIndex(i, el) {
  _ovCurrentIndexIdx = i;
  if (el) {
    document.querySelectorAll('.ov-idx-item').forEach(x => x.classList.remove('active'));
    el.classList.add('active');
  } else {
    const items = document.querySelectorAll('.ov-idx-item');
    if (items[i]) {
      items.forEach(x => x.classList.remove('active'));
      items[i].classList.add('active');
    }
  }
  const idx = (_ovData && _ovData.indices) ? _ovData.indices[i] : null;
  if (!idx) return;

  document.getElementById('ov-index-low').textContent = idx.low.toFixed(2);
  document.getElementById('ov-index-high').textContent = idx.high.toFixed(2);
  document.getElementById('ov-index-open').textContent = idx.open.toFixed(2);
  document.getElementById('ov-index-oh').textContent = idx.high.toFixed(2);
  document.getElementById('ov-index-ol').textContent = idx.low.toFixed(2);
  document.getElementById('ov-index-close').textContent = idx.prev_close.toFixed(2);
  document.getElementById('ov-index-chart-price').textContent = idx.ltp.toFixed(2);
  document.getElementById('ov-index-chart-price').style.background = idx.chg >= 0 ? 'var(--green)' : 'var(--red)';

  const range = idx.high - idx.low;
  let pct = 50;
  if (range > 0) {
     pct = ((idx.ltp - idx.low) / range) * 100;
  }
  document.getElementById('ov-index-slider-marker').style.left = pct + '%';

  // Draw chart with current timeframe
  const historySeries = (idx.histories && idx.histories[_ovCurrentIndexTf]) ? idx.histories[_ovCurrentIndexTf] : (idx.history || []);
  const tfLabel = document.getElementById('ov-index-chart-tf-label');
  if (tfLabel) tfLabel.textContent = _ovCurrentIndexTf === '1D' && historySeries.length < 2 ? 'No observed intraday candles' : `${_ovCurrentIndexTf} observed history`;
  drawIndexChart(historySeries);
}

function drawIndexChart(history) {
  const canvas = document.getElementById('ov-index-chart');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  
  const rect = canvas.parentElement.getBoundingClientRect();
  if (rect.width <= 0 || rect.height <= 0) return;
  canvas.width = rect.width;
  canvas.height = rect.height;
  
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  if (!history || history.length < 2) return;

  const minP = Math.min(...history.map(d => d.c));
  const maxP = Math.max(...history.map(d => d.c));
  const range = maxP - minP;
  
  const pad = 12;
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
  ctx.lineWidth = 2.5;
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
  _ovCurrentIndexTf = tf;
  document.querySelectorAll('.ov-tf-btn').forEach(b => b.classList.remove('active'));
  if (el) el.classList.add('active');
  const tfLabel = document.getElementById('ov-index-chart-tf-label');
  if (tfLabel) tfLabel.textContent = `${tf} Trend`;
  selectIndex(_ovCurrentIndexIdx);
}

function renderMostBought() {
  const c = document.getElementById('ov-most-bought');
  const asof = document.getElementById('ov-most-bought-asof');
  if (asof) asof.textContent = `Daily share volume · ${(_ovData.meta||{}).trade_date || 'date unavailable'} · local snapshot`;
  let html = '';
  (_ovData.most_bought || []).forEach(s => {
    const cls = s.chg >= 0 ? 'var(--green)' : 'var(--red)';
    const sign = s.chg >= 0 ? '▲' : '▼';
    html += `<div class="ov-stock-card" onclick="openSymbolChart('${ovEsc(s.symbol)}')">
      <div style="display:flex;align-items:center;gap:12px;margin-bottom:12px;">
        <div style="width:36px;height:36px;background:var(--panel);border:1px solid var(--border);border-radius:4px;display:flex;align-items:center;justify-content:center;font-weight:700;color:var(--text);font-size:0.8rem;">
          ${ovEsc(s.symbol.substring(0,2))}
        </div>
        <div>
          <div style="font-weight:700;color:var(--white);font-size:0.9rem;">${ovEsc(s.symbol)}</div>
          <div style="font-size:0.7rem;color:var(--dim);">${ovEsc(s.name||'Equity')}</div>
        </div>
      </div>
      <div style="font-family:Share Tech Mono,monospace;font-size:1rem;color:${cls};font-weight:700;">
        ₹${s.ltp.toFixed(2)} <span style="font-size:0.75rem;">${sign} ${Math.abs(s.chg).toFixed(2)} (${s.chgPct.toFixed(2)}%)</span>
      </div>
      <div class="ov-data-note" style="margin-top:8px;">Reported daily volume: ${Number(s.volume || 0).toLocaleString('en-IN')} shares</div>
    </div>`;
  });
  c.innerHTML = html || '<div class="ov-empty">No equity volume rows are available for the validated session. Check that the daily price feed includes reported volume.</div>';
}

function ovSwitchMoversTab(el, type) {
  _ovCurrentMoversType = type;
  el.parentNode.querySelectorAll('.ov-pill-btn').forEach(b => b.classList.remove('active'));
  if (el) el.classList.add('active');
  renderMovers(type);
}

function ovFilterMoversUniverse(val) {
  _ovCurrentMoversUniverse = val;
  renderMovers(_ovCurrentMoversType);
}

function renderMovers(type) {
  const c = document.getElementById('ov-movers-list');
  let data = [];
  if (type === 'gainers') {
    data = _ovCurrentMoversUniverse === 'nifty50' ? (_ovData.gainers_n50 || []) : (_ovData.gainers_n500 || []);
  } else {
    data = _ovCurrentMoversUniverse === 'nifty50' ? (_ovData.losers_n50 || []) : (_ovData.losers_n500 || []);
  }
  let html = '';
  (data || []).forEach(s => {
    const cls = s.chg >= 0 ? 'var(--green)' : 'var(--red)';
    const sign = s.chg >= 0 ? '▲' : '▼';
    html += `<div class="ov-trow" style="cursor:pointer;" onclick="openSymbolChart('${ovEsc(s.symbol)}')">
       <div>
         <div style="font-weight:600;color:var(--white);font-size:0.85rem;">${ovEsc(s.symbol)}</div>
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
  const meta = _ovData.meta || {};
  c.innerHTML = html || `<div style="padding:14px;color:var(--dim);font-size:.8rem;text-align:center;">No mover rows in the validated snapshot (${ovEsc(meta.trade_date || 'date unavailable')}).</div>`;
}

function renderSectorTabs() {
  const selectEl = document.getElementById('ov-sector-select');
  const sectors = Object.keys(_ovData.sectors || {});
  if (sectors.length === 0) return;
  
  let selectHtml = '';
  sectors.forEach((sec, i) => {
    selectHtml += `<option value="${sec}">${sec}</option>`;
  });
  if (selectEl) selectEl.innerHTML = selectHtml;
  ovSelectSector(null, sectors[0]);
}

function ovSelectSectorDropdown(sec) {
  ovSelectSector(null, sec);
}

function ovSelectSector(el, sec) {
  const selectEl = document.getElementById('ov-sector-select');
  if (selectEl && selectEl.value !== sec) selectEl.value = sec;

  const data = (_ovData.sectors || {})[sec] || [];
  const c = document.getElementById('ov-sector-list');
  let html = '';
  data.forEach(s => {
    const cls = s.chg >= 0 ? 'var(--green)' : 'var(--red)';
    const sign = s.chg >= 0 ? '▲' : '▼';
    html += `<div class="ov-trow" style="cursor:pointer;" onclick="openSymbolChart('${s.symbol}')">
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
  c.innerHTML = html || `<div style="padding:14px;color:var(--dim);font-size:.8rem;text-align:center;">No constituents have valid prices for ${ovEsc(sec)} on ${ovEsc((_ovData.meta||{}).trade_date||'the selected date')}.</div>`;
}

function ovLoadPerformers(el, tf) {
  _ovCurrentPerfTf = tf;
  if(el) {
    el.parentNode.querySelectorAll('.ov-pill-btn').forEach(b => b.classList.remove('active'));
    el.classList.add('active');
  }
  renderPerformersList();
}

function ovFilterPerfCap(cap) {
  _ovCurrentPerfCap = cap;
  renderPerformersList();
}

function renderPerformersList() {
  const c = document.getElementById('ov-performers-list');
  let data = [];
  if (_ovData.performers_by_cap && _ovData.performers_by_cap[_ovCurrentPerfCap]) {
    data = _ovData.performers_by_cap[_ovCurrentPerfCap][_ovCurrentPerfTf] || [];
  } else {
    data = (_ovData.performers || {})[_ovCurrentPerfTf] || [];
  }
  let html = '';
  const meta = (_ovData && _ovData.meta) || {};
  data.forEach(s => {
     html += `<div class="ov-stock-card" onclick="openSymbolChart('${s.symbol}')">
       <div style="display:flex;justify-content:space-between;margin-bottom:12px;">
         <div>
       <div style="font-weight:700;color:var(--white);font-size:0.9rem;">${s.symbol}</div>
           <div style="font-size:0.7rem;color:var(--dim);">${s.name||'Equity'} · ${ovEsc(s.start_date || '')} to ${ovEsc(s.end_date || '')}</div>
         </div>
       <div style="background:${Number(s.returnPct)>=0?'rgba(8,153,129,0.1)':'rgba(242,54,69,0.1)'};color:${Number(s.returnPct)>=0?'var(--green)':'var(--red)'};font-family:Share Tech Mono,monospace;font-size:0.75rem;padding:4px 8px;border-radius:4px;font-weight:700;">
           ${Number(s.returnPct)>=0?'+':''}${Number(s.returnPct).toFixed(2)}%
         </div>
       </div>
       <div style="font-family:Share Tech Mono,monospace;font-size:0.9rem;color:${Number(s.returnPct)>=0?'var(--green)':'var(--red)'};font-weight:700;">
         ₹${Number(s.ltp).toFixed(2)} <span style="font-size:0.7rem;">${Number(s.chg)>=0?'▲':'▼'} ${Math.abs(Number(s.chg)).toFixed(2)}</span>
       </div>
     </div>`;
  });
  c.innerHTML = html || `<div style="padding:14px;color:var(--dim);font-size:.8rem;text-align:center;">No performer records for ${ovEsc(_ovCurrentPerfTf)} in the validated date range ending ${ovEsc(meta.trade_date||'unknown')}.</div>`;
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
    
    // Explicit badge for RSI & screeners (Bug 11)
    let badgeHtml = '';
    if (type === 'rsi') {
      const isBull = s.is_bullish !== undefined ? s.is_bullish : (s.rsi_val >= 50);
      const bColor = isBull ? 'var(--green)' : 'var(--red)';
      badgeHtml = `<div style="margin-top:6px;"><span class="badge" style="background:${bColor}20; color:${bColor}; font-size:0.62rem; padding:2px 6px; font-weight:700;">${isBull ? '🟢 Bullish Momentum' : '🔴 Oversold'} (RSI ${s.rsi_val||55})</span></div>`;
    } else if (type === 'macd') {
      badgeHtml = `<div style="margin-top:6px;"><span class="badge" style="background:rgba(41,98,255,0.15); color:var(--cyan); font-size:0.62rem; padding:2px 6px;">MACD histogram ${Number(s.macd_hist)>=0?'positive':'negative'}</span></div>`;
    } else if (type === 'sma') {
      badgeHtml = `<div style="margin-top:6px;"><span class="badge" style="background:${Number(s.ltp)>=Number(s.sma20)?'rgba(8,153,129,0.15)':'rgba(242,54,69,0.15)'}; color:${Number(s.ltp)>=Number(s.sma20)?'var(--green)':'var(--red)'}; font-size:0.62rem; padding:2px 6px;">${Number(s.ltp)>=Number(s.sma20)?'Above':'Below'} SMA 20 (₹${s.sma20||s.ltp})</span></div>`;
    } else if (type === 'ema') {
      badgeHtml = `<div style="margin-top:6px;"><span class="badge" style="background:${Number(s.ltp)>=Number(s.ema20)?'rgba(8,153,129,0.15)':'rgba(242,54,69,0.15)'}; color:${Number(s.ltp)>=Number(s.ema20)?'var(--green)':'var(--red)'}; font-size:0.62rem; padding:2px 6px;">${Number(s.ltp)>=Number(s.ema20)?'Above':'Below'} EMA 20 (₹${s.ema20||s.ltp})</span></div>`;
    } else if (type === 'pivot') {
      badgeHtml = `<div style="margin-top:6px;"><span class="badge" style="background:rgba(255,152,0,0.15); color:var(--gold); font-size:0.62rem; padding:2px 6px;">Trading Above Pivot P</span></div>`;
    }

    html += `<div class="ov-stock-card" style="min-width:200px;" onclick="openSymbolChart('${s.symbol}')">
      <div style="font-weight:700;color:var(--white);font-size:0.85rem;">${s.symbol}</div>
      <div style="font-size:0.65rem;color:var(--dim);margin-bottom:6px;">${s.name||'Equity'}</div>
      <div style="font-family:Share Tech Mono,monospace;font-size:0.9rem;color:${cls};font-weight:700;">
        ₹${s.ltp.toFixed(2)} <span style="font-size:0.65rem;">${sign} (${s.chgPct.toFixed(2)}%)</span>
      </div>
      ${badgeHtml}
    </div>`;
  });
  c.innerHTML = html || `<div style="padding:14px;color:var(--dim);font-size:.8rem;text-align:center;">No symbols meet this screener in the validated snapshot dated ${ovEsc((_ovData.meta||{}).trade_date||'unknown')}.</div>`;
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
    html += `<div class="ov-signal-card" onclick="openSymbolChart('${s.symbol}')">
       <div class="ov-signal-indicator" style="background:${bg};color:${cls};border-right:1px solid var(--border);">
          <div style="font-size:1.4rem;margin-bottom:4px;">${s.signal==='Bullish'?'↑↑':s.signal==='Bearish'?'↓↓':'−'}</div>
          ${s.pattern}<br>(${s.signal})
       </div>
       <div class="ov-signal-details">
          <div>
            <div style="font-weight:700;color:var(--white);font-size:0.9rem;">${s.symbol}</div>
            <div style="font-size:0.7rem;color:var(--dim);margin-bottom:4px;">${s.desc || s.name || 'Algorithmic trigger'}</div>
            <div style="font-size:0.68rem;color:var(--dim);">Time Frame: ${s.tf || '1D'}</div>
          </div>
          <div style="text-align:right;font-family:Share Tech Mono,monospace;">
            <div style="font-size:0.9rem;color:${s.chg>=0?'var(--green)':'var(--red)'};font-weight:700;">₹${s.ltp.toFixed(2)}</div>
            <div style="font-size:0.7rem;color:${s.chg>=0?'var(--green)':'var(--red)'};">${s.chg>=0?'▲':'▼'} ${Math.abs(s.chg).toFixed(2)} (${s.chgPct.toFixed(2)}%)</div>
          </div>
       </div>
    </div>`;
  });
  c.innerHTML = html || `<div style="padding:14px;color:var(--dim);font-size:.8rem;text-align:center;">No signals matched the validated snapshot dated ${ovEsc((_ovData.meta||{}).trade_date||'unknown')}.</div>`;
}

function ovFilterResearchHorizon(hz) {
  _ovCurrentResearchHorizon = hz;
  renderResearch();
}

function renderResearch() {
  const c = document.getElementById('ov-research-list');
  const allData = _ovData.research || [];
  let data = _ovCurrentResearchHorizon === 'all' 
    ? [...allData] 
    : allData.filter(s => (s.type||'').toLowerCase().includes(_ovCurrentResearchHorizon.toLowerCase()));
  
  // Sort in descending order of % Potential Expected (Bug 7b)
  data.sort((a, b) => (parseFloat(b.potential) || 0) - (parseFloat(a.potential) || 0));

  let html = '';
  data.forEach(s => {
    html += `<div class="ov-research-card" onclick="openAdvisorReport('${ovEsc(s.symbol)}','${ovEsc(s.type)}')">
       <div style="display:flex;justify-content:space-between;margin-bottom:12px;">
         <div>
           <div style="font-weight:700;color:var(--white);font-size:0.95rem;">${s.symbol}</div>
           <div style="font-size:0.7rem;color:var(--dim);">${s.name||'Equity'}</div>
         </div>
         <div style="font-size:0.7rem;color:var(--green);font-weight:700;display:flex;align-items:center;gap:4px;text-transform:uppercase;">
           <div style="width:6px;height:6px;border-radius:50%;background:var(--green);"></div> ${s.type}
         </div>
       </div>
       
       <div style="display:flex;justify-content:space-between;align-items:flex-end;margin-bottom:16px;">
         <div>
           <div style="font-size:0.7rem;color:var(--dim);margin-bottom:2px;">LTP</div>
           <div style="font-family:Share Tech Mono,monospace;font-size:0.95rem;color:var(--green);font-weight:700;">₹${s.ltp.toFixed(2)} <span style="font-size:0.7rem;">▲ ${s.chgPct.toFixed(2)}%</span></div>
         </div>
         <div style="text-align:right;">
           <div style="font-size:0.7rem;color:var(--dim);margin-bottom:2px;">Recommended Price</div>
           <div style="font-family:Share Tech Mono,monospace;font-size:0.85rem;color:var(--white);">₹${s.rec_price.toFixed(2)} - ₹${(s.rec_price_high || s.rec_price*1.01).toFixed(2)}</div>
         </div>
       </div>

       <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;font-family:Share Tech Mono,monospace;font-size:0.8rem;background:rgba(255,255,255,0.02);padding:8px 12px;border-radius:4px;">
         <div style="text-align:center;">
           <div style="color:var(--red);font-size:0.65rem;margin-bottom:2px;font-weight:700;">SL</div>
           <div style="color:var(--text);">${s.sl.toFixed(2)}</div>
         </div>
         <div style="text-align:center;">
           <div style="color:var(--green);font-size:0.65rem;margin-bottom:2px;font-weight:700;">ENTRY</div>
           <div style="color:var(--text);">${s.rec_price.toFixed(2)}</div>
         </div>
         <div style="text-align:center;">
           <div style="color:var(--gold);font-size:0.65rem;margin-bottom:2px;font-weight:700;">TARGET</div>
           <div style="color:var(--text);">${s.target.toFixed(2)}</div>
         </div>
       </div>

       <div style="background:rgba(255,152,0,0.1);color:var(--gold);font-size:0.75rem;padding:6px;text-align:center;border-radius:4px;font-weight:700;margin-bottom:12px;">
         ${s.potential}% POTENTIAL EXPECTED
       </div>

       <div style="display:flex;justify-content:space-between;align-items:center;">
         <div style="font-size:0.65rem;color:var(--dim);">Updated: ${s.updated} · ${ovEsc(s.status||'OPEN')}</div>
         <button class="btn btn-sm" style="padding:6px 18px;font-size:0.78rem;" onclick="event.stopPropagation();openAdvisorReport('${ovEsc(s.symbol)}','${ovEsc(s.type)}');">Open analysis</button>
       </div>
     </div>`;
  });
  c.innerHTML = html || '<div style="padding:14px; color:var(--dim); font-size:0.8rem; text-align:center;">No research recommendations found in this horizon.</div>';
}

async function ovLoadPocket(el, minPrice, maxPrice) {
  if(el) {
    el.parentNode.querySelectorAll('.ov-pill-btn').forEach(b => b.classList.remove('active'));
    el.classList.add('active');
  }
  const c = document.getElementById('ov-pocket-list');
  const requestId = ++_ovPocketRequest;
  c.innerHTML = '<div class="ov-empty">Loading price band…</div>';
  const dataRes = await api('overview_pocket', {min_price:minPrice, max_price:maxPrice});
  if (requestId !== _ovPocketRequest) return;
  const data = dataRes && !dataRes.error ? (dataRes.items || []) : [];
  let html = '';
  data.forEach(s => {
    const cls = s.chg >= 0 ? 'var(--green)' : 'var(--red)';
    const sign = s.chg >= 0 ? '▲' : '▼';
    html += `<div class="ov-stock-card" style="min-width:180px;" onclick="openSymbolChart('${s.symbol}')">
      <div style="font-weight:700;color:var(--white);font-size:0.85rem;">${s.symbol}</div>
      <div style="font-size:0.65rem;color:var(--dim);margin-bottom:8px;">${s.name||'Equity'}</div>
      <div style="font-family:Share Tech Mono,monospace;font-size:0.9rem;color:${cls};font-weight:700;">
        ₹${s.ltp.toFixed(2)} <span style="font-size:0.65rem;">${sign} (${s.chgPct.toFixed(2)}%)</span>
      </div>
      <div class="ov-data-note" style="margin-top:8px;">Daily volume: ${Number(s.volume || 0).toLocaleString('en-IN')}</div>
    </div>`;
  });
  c.innerHTML = html || '<div style="color:var(--dim);font-size:0.8rem;padding:12px;text-align:center;">No equities currently trading within ₹' + minPrice + ' – ₹' + maxPrice + ' on ' + ovEsc(dataRes?.trade_date || 'the selected snapshot') + '.</div>';
}

let _ovChainRequest = 0;
function ovInitDerivativeControls() {
  const catalog = (_ovData && _ovData.derivatives && _ovData.derivatives.catalog) || [];
  const sel = document.getElementById('ov-chain-symbol');
  if (!sel) return;
  const current = sel.value || window._ovSelectedDerivativeSymbol || '';
  const list = document.getElementById('ov-chain-symbol-list');
  const optionsMarkup = catalog.map(x => `<option value="${ovEsc(x.symbol)}">${ovEsc(x.kind==='index'?'Index':'Stock')} · expiry ${ovEsc(x.expiry || 'unavailable')} · ${ovEsc(x.trade_date || 'date unavailable')}</option>`).join('');
  if (list && list.dataset.catalog !== optionsMarkup) { list.innerHTML = optionsMarkup; list.dataset.catalog = optionsMarkup; }
  const chosen = catalog.some(x => x.symbol === current) ? current : (catalog[0]?.symbol || '');
  if (sel.value !== chosen) sel.value = chosen;
  if (chosen) ovLoadDerivativeChain();
  else {
    const table = document.getElementById('ov-chain-table-wrap');
    if (table) table.innerHTML = '<div class="ov-empty" style="padding:16px;">No option underlyings are available in the local option feed.</div>';
    const expiry = document.getElementById('ov-chain-expiry'); if (expiry) expiry.innerHTML = '<option value="">No expiry available</option>';
    const session = document.getElementById('ov-chain-session'); if (session) session.innerHTML = '<option value="">No session available</option>';
  }
}
async function ovLoadDerivativeChain() {
  const symbol = document.getElementById('ov-chain-symbol')?.value || '';
  const expirySel = document.getElementById('ov-chain-expiry');
  const sessionSel = document.getElementById('ov-chain-session');
  const table = document.getElementById('ov-chain-table-wrap');
  const summary = document.getElementById('ov-chain-summary');
  if (!symbol || !table) return;
  window._ovSelectedDerivativeSymbol = symbol;
  const req = ++_ovChainRequest;
  table.innerHTML = '<div class="ov-empty" style="padding:16px;">Loading option chain…</div>';
  const status = document.getElementById('ov-chain-status');
  if (status) status.textContent = `Loading ${symbol} option data…`;
  let result;
  try {
    result = await api('derivatives_chain', {symbol, expiry:expirySel?.value || '', session:sessionSel?.value || ''});
  } catch (error) {
    if (req !== _ovChainRequest) return;
    if (summary) summary.innerHTML = '';
    if (expirySel) expirySel.innerHTML = '<option value="">Unavailable</option>';
    if (sessionSel) sessionSel.innerHTML = '<option value="">Unavailable</option>';
    if (status) status.textContent = `Could not load option data for ${symbol}.`;
    table.innerHTML = `<div class="ov-empty" style="padding:16px;">${ovEsc(error?.message || 'Option data request failed. Retry by selecting the underlying again.')}</div>`;
    return;
  }
  if (req !== _ovChainRequest) return;
  if (!result || result.error || !Array.isArray(result.rows) || result.rows.length === 0) {
    if (summary) summary.innerHTML = '';
    if (expirySel) expirySel.innerHTML = (result?.expiries || []).map(x => `<option value="${ovEsc(x)}">${ovEsc(x)}</option>`).join('') || '<option value="">No expiry available</option>';
    if (sessionSel) sessionSel.innerHTML = (result?.sessions || []).map(x => `<option value="${ovEsc(x)}">${ovEsc(x)}</option>`).join('') || '<option value="">No session available</option>';
    if (status) status.textContent = result?.trade_date ? `${ovEsc(result.symbol || symbol)} · ${ovEsc(result.trade_date)} · no strike rows in this snapshot` : 'No dated option snapshot is available for this underlying.';
    table.innerHTML = `<div class="ov-empty" style="padding:16px;">${ovEsc(result?.message || result?.error || 'No validated option chain is available.')}</div>`;
    return;
  }
  if (expirySel) {
    const oldExpiry = expirySel.value;
    expirySel.innerHTML = (result.expiries || []).map(x => `<option value="${ovEsc(x)}">${ovEsc(x)}</option>`).join('') || '<option value="">No expiry</option>';
    if (result.expiries?.includes(oldExpiry)) expirySel.value = oldExpiry;
    else expirySel.value = result.expiry || '';
    if (!expirySel.dataset.initialized) { expirySel.dataset.initialized='1'; if (result.expiries?.length) { expirySel.value=result.expiries[0]; setTimeout(ovLoadDerivativeChain,0); return; } }
  }
  if (sessionSel) {
    const oldSession = sessionSel.value;
    sessionSel.innerHTML = (result.sessions || []).map(x => `<option value="${ovEsc(x)}">${ovEsc(x)}</option>`).join('') || '<option value="">Session unavailable</option>';
    if (result.sessions?.includes(oldSession)) sessionSel.value = oldSession;
    else sessionSel.value = result.session || '';
  }
  const s = result.summary || {};
  if(status)status.textContent=`${ovEsc(result.symbol)} · ${ovEsc(result.expiry)} expiry · ${ovEsc(result.trade_date)} · session ${ovEsc(result.session)} · ${s.contract_count||0} strike rows`;
  summary.innerHTML = `<div class="card"><div class="ov-data-note">As of</div><strong>${ovEsc(result.trade_date || 'Unknown')} · ${ovEsc(result.session || 'Unknown')}</strong></div><div class="card"><div class="ov-data-note">Call OI</div><strong>${Number(s.call_oi||0).toLocaleString('en-IN')}</strong><div class="ov-data-note">Δ ${Number(s.call_change_oi||0).toLocaleString('en-IN')}</div></div><div class="card"><div class="ov-data-note">Put OI</div><strong>${Number(s.put_oi||0).toLocaleString('en-IN')}</strong><div class="ov-data-note">Δ ${Number(s.put_change_oi||0).toLocaleString('en-IN')}</div></div><div class="card"><div class="ov-data-note">PCR (OI)</div><strong>${s.pcr == null ? 'Unavailable' : Number(s.pcr).toFixed(2)}</strong></div><div class="card"><div class="ov-data-note">Contracts</div><strong>${Number(s.contract_count||0).toLocaleString('en-IN')}</strong></div>`;
  const fmt = v => v == null ? '—' : Number(v).toLocaleString('en-IN', {maximumFractionDigits:2});
  table.innerHTML = `<table class="ov-chain-table"><thead><tr><th>Call OI</th><th>Call Δ OI</th><th>Call Vol</th><th>Strike</th><th>Put Vol</th><th>Put Δ OI</th><th>Put OI</th></tr></thead><tbody>${result.rows.map(r=>`<tr><td class="call-side">${fmt(r.call_oi)}</td><td class="call-side">${fmt(r.call_change_oi)}</td><td>${fmt(r.call_volume)}</td><td><strong>${fmt(r.strike)}</strong></td><td>${fmt(r.put_volume)}</td><td class="put-side">${fmt(r.put_change_oi)}</td><td class="put-side">${fmt(r.put_oi)}</td></tr>`).join('')}</tbody></table><div class="ov-data-note" style="padding:10px 12px;">Source: ${ovEsc(result.source || 'option_chain_data')} · Stored snapshot ${ovEsc(result.fetched_at || '')}</div>`;
}

function renderMarketsTab(kind) {
  const c = document.getElementById('ov-markets-list');
  if (!c) return;
  const meta = (_ovData && _ovData.meta) || {};
  const asof = document.getElementById('ov-markets-asof');
  if (asof) asof.textContent = `Local close data · ${meta.trade_date || 'date unavailable'}`;
  const data = kind === 'commodities' ? (_ovData.commodities || []) : (_ovData.indices || []);
  c.innerHTML = data.map(s => {
    const good = Number(s.chgPct) >= 0;
    const priceLabel = kind === 'indices' ? 'Index value' : 'Exchange quote';
    return `<article class="ov-stock-card" onclick="openSymbolChart('${ovEsc(s.symbol)}')"><div style="font-weight:700;color:var(--white);font-size:.95rem;">${ovEsc(s.symbol)}</div><div class="ov-data-note">${kind==='indices'?'Index':'Commodity'}${kind==='commodities'?` · ${ovEsc(s.exchange||'Exchange unavailable')} · unit not verified`:''}</div><div style="display:flex;justify-content:space-between;margin:12px 0 6px;font-family:Share Tech Mono,monospace;"><span class="ov-data-note">${priceLabel}</span><strong>${Number(s.ltp).toLocaleString('en-IN',{minimumFractionDigits:2})}</strong></div><div style="display:flex;justify-content:space-between;color:${good?'var(--green)':'var(--red)'};font-family:Share Tech Mono,monospace;"><span>Session change</span><strong>${good?'▲':'▼'} ${Number(s.chgPct).toFixed(2)}%</strong></div></article>`;
  }).join('') || '<div class="ov-empty">No validated quotes are available for this market group.</div>';
}
function ovSwitchMarketType(el, kind) {
  el.parentNode.querySelectorAll('.ov-pill-btn').forEach(b=>b.classList.remove('active'));
  el.classList.add('active'); renderMarketsTab(kind);
}
function renderNewsTab() {
  const c = document.getElementById('ov-news-list');
  let html = '';
  (_ovData.news || []).forEach(n => {
     const score = n.score == null || n.score === '' ? NaN : Number(n.score);
     const sourceUrl = ovSafeHref(n.url);
     const badgeColor = !Number.isFinite(score) ? 'var(--dim)' : score > 0.15 ? 'var(--green)' : score < -0.15 ? 'var(--red)' : 'var(--dim)';
     const badgeText = !Number.isFinite(score) ? 'NOT SCORED' : score > 0.15 ? 'BULLISH' : score < -0.15 ? 'BEARISH' : 'NEUTRAL';
     
     html += `<div class="card" style="padding:16px;">
       <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px;gap:12px;">
         <span style="font-weight:700;color:var(--white);font-size:0.95rem;">${ovEsc(n.title)}</span>
         <span class="badge" style="background:${badgeColor}20;color:${badgeColor};font-size:0.6rem;padding:3px 8px;font-weight:700;white-space:nowrap;">
           ${badgeText}${Number.isFinite(score) ? ` (${score.toFixed(2)})` : ''}
         </span>
       </div>
       <p style="font-size:0.8rem;color:var(--text);margin-bottom:12px;line-height:1.4;">${ovEsc(n.snippet || '')}</p>
       <div style="display:flex;justify-content:space-between;font-size:0.7rem;color:var(--dim);">
         <span>${sourceUrl ? `<a href="${ovEsc(sourceUrl)}" target="_blank" rel="noopener noreferrer">${ovEsc(n.source || 'Open source')}</a>` : `Source: ${ovEsc(n.source || 'Market Feed')}`}</span>
         <span>Published: ${n.published_at ? new Date(n.published_at).toLocaleString() : 'Time unavailable'}${n.fetched_at ? ` · fetched ${ovEsc(n.fetched_at)}` : ''}</span>
       </div>
     </div>`;
  });
  c.innerHTML = html || '<div class="ov-empty">No news feed items found.</div>';
}
"""
