# -*- coding: utf-8 -*-
"""
page_analytics.py — Performance Analytics (Phase 5) — v4.0
Zerodha Console-inspired dark analytics dashboard.

Tabs:
  1. P&L CALENDAR   — GitHub-style contribution heatmap (12 months × ~52 weeks)
  2. EQUITY CURVE   — Portfolio vs Nifty50 line/area chart with time range selector
  3. STATISTICS     — Win/Loss, R:R, Period Breakdown in 3-column layout
  4. BEST/WORST     — Top 10 / Bottom 10 trades table with mini price chart
  5. SECTOR P&L     — Donut chart + bar chart + table with CSV export

Backend endpoints:
  GET /api/analytics_data?type=calendar
  GET /api/analytics_data?type=equity_curve
  GET /api/analytics_data?type=statistics
  GET /api/analytics_data?type=best_worst
  GET /api/analytics_data?type=sector_pnl
  GET /api/portfolio_csv
  POST /api/analytics_whatsapp_report

Exports:
    HTML : Page HTML template (injected into SPA)
    JS   : Page JavaScript (injected into <script> block)
"""

HTML = r"""
<!-- ═══════════ PAGE: PERFORMANCE ANALYTICS ═══════════ -->
<div class="page" id="page-analytics">

  <!-- ── TOPBAR ────────────────────────────────────────────── -->
  <div class="topbar" style="background:var(--panel);border-bottom:1px solid var(--border);padding:12px 20px;display:flex;justify-content:space-between;align-items:center;">
    <div style="display:flex;align-items:center;gap:12px;">
      <span style="font-family:Orbitron,sans-serif;font-size:1.1rem;color:var(--gold);font-weight:700;letter-spacing:2px;">📊 PERFORMANCE ANALYTICS</span>
      <span class="page-tag" style="font-family:'Share Tech Mono',monospace;font-size:0.6rem;color:var(--dim);letter-spacing:1.5px;border:1px solid var(--border);padding:2px 8px;border-radius:3px;">ZERODHA CONSOLE STYLE</span>
    </div>
    <div style="font-family:'Share Tech Mono',monospace;font-size:0.58rem;color:var(--dim);letter-spacing:1px;">
      Vprofitables · PHASE 5 · LIVE P&amp;L INTELLIGENCE
    </div>
  </div>

  <!-- ── TAB NAV ─────────────────────────────────────────────── -->
  <div style="display:flex;gap:0;border-bottom:2px solid var(--border);background:var(--panel);padding:0 20px;overflow-x:auto;" id="analytics-tab-nav">
    <button id="atab-calendar" onclick="analyticsTab('calendar')"
      style="padding:10px 18px;background:rgba(41,98,255,0.15);border:none;border-bottom:2px solid var(--cyan);
             color:var(--cyan);font-family:'Share Tech Mono',monospace;font-size:0.7rem;letter-spacing:1px;cursor:pointer;white-space:nowrap;transition:all 0.2s;">
      📅 P&amp;L CALENDAR
    </button>
    <button id="atab-curve" onclick="analyticsTab('curve')"
      style="padding:10px 18px;background:transparent;border:none;border-bottom:2px solid transparent;
             color:var(--dim);font-family:'Share Tech Mono',monospace;font-size:0.7rem;letter-spacing:1px;cursor:pointer;white-space:nowrap;transition:all 0.2s;">
      📈 EQUITY CURVE
    </button>
    <button id="atab-stats" onclick="analyticsTab('stats')"
      style="padding:10px 18px;background:transparent;border:none;border-bottom:2px solid transparent;
             color:var(--dim);font-family:'Share Tech Mono',monospace;font-size:0.7rem;letter-spacing:1px;cursor:pointer;white-space:nowrap;transition:all 0.2s;">
      📊 STATISTICS
    </button>
    <button id="atab-best" onclick="analyticsTab('best')"
      style="padding:10px 18px;background:transparent;border:none;border-bottom:2px solid transparent;
             color:var(--dim);font-family:'Share Tech Mono',monospace;font-size:0.7rem;letter-spacing:1px;cursor:pointer;white-space:nowrap;transition:all 0.2s;">
      🏆 BEST/WORST
    </button>
    <button id="atab-sector" onclick="analyticsTab('sector')"
      style="padding:10px 18px;background:transparent;border:none;border-bottom:2px solid transparent;
             color:var(--dim);font-family:'Share Tech Mono',monospace;font-size:0.7rem;letter-spacing:1px;cursor:pointer;white-space:nowrap;transition:all 0.2s;">
      🥧 SECTOR P&amp;L
    </button>
  </div>

  <!-- ── TAB PANELS ──────────────────────────────────────────── -->
  <div style="padding:20px;min-height:calc(100vh - 200px);padding-bottom:80px;">

    <!-- ════════════════ TAB 1: P&L CALENDAR ════════════════ -->
    <div id="analytics-calendar">

      <!-- Top Stats Row -->
      <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:20px;" id="cal-top-stats">
        <div class="an-stat-tile" style="background:var(--panel);border:1px solid var(--border);border-radius:8px;padding:16px;position:relative;overflow:hidden;">
          <div style="font-family:'Share Tech Mono',monospace;font-size:0.6rem;color:var(--dim);letter-spacing:1px;margin-bottom:6px;">TOTAL P&amp;L</div>
          <div id="cal-total-pnl" style="font-family:'JetBrains Mono',monospace;font-size:1.4rem;font-weight:700;color:var(--green);">—</div>
          <div style="position:absolute;right:14px;top:14px;font-size:1.4rem;opacity:0.1;">₹</div>
        </div>
        <div class="an-stat-tile" style="background:var(--panel);border:1px solid var(--border);border-radius:8px;padding:16px;position:relative;overflow:hidden;">
          <div style="font-family:'Share Tech Mono',monospace;font-size:0.6rem;color:var(--dim);letter-spacing:1px;margin-bottom:6px;">BEST DAY</div>
          <div id="cal-best-day" style="font-family:'JetBrains Mono',monospace;font-size:1.4rem;font-weight:700;color:var(--green);">—</div>
          <div style="position:absolute;right:14px;top:14px;font-size:1.4rem;opacity:0.1;">🏅</div>
        </div>
        <div class="an-stat-tile" style="background:var(--panel);border:1px solid var(--border);border-radius:8px;padding:16px;position:relative;overflow:hidden;">
          <div style="font-family:'Share Tech Mono',monospace;font-size:0.6rem;color:var(--dim);letter-spacing:1px;margin-bottom:6px;">WORST DAY</div>
          <div id="cal-worst-day" style="font-family:'JetBrains Mono',monospace;font-size:1.4rem;font-weight:700;color:var(--red);">—</div>
          <div style="position:absolute;right:14px;top:14px;font-size:1.4rem;opacity:0.1;">💀</div>
        </div>
        <div class="an-stat-tile" style="background:var(--panel);border:1px solid var(--border);border-radius:8px;padding:16px;position:relative;overflow:hidden;">
          <div style="font-family:'Share Tech Mono',monospace;font-size:0.6rem;color:var(--dim);letter-spacing:1px;margin-bottom:6px;">PROFITABLE DAYS</div>
          <div id="cal-profit-pct" style="font-family:'JetBrains Mono',monospace;font-size:1.4rem;font-weight:700;color:var(--cyan);">—</div>
          <div style="position:absolute;right:14px;top:14px;font-size:1.4rem;opacity:0.1;">%</div>
        </div>
      </div>

      <!-- Calendar Heatmap -->
      <div style="background:var(--panel);border:1px solid var(--border);border-radius:10px;padding:20px;margin-bottom:16px;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;">
          <div style="font-family:'Share Tech Mono',monospace;font-size:0.75rem;color:var(--text);letter-spacing:1px;">📅 DAILY P&amp;L HEATMAP</div>
          <div style="display:flex;align-items:center;gap:8px;font-family:'Share Tech Mono',monospace;font-size:0.6rem;color:var(--dim);">
            <span>LOSS</span>
            <div style="width:12px;height:12px;background:#4a0a0a;border-radius:2px;"></div>
            <div style="width:12px;height:12px;background:#8b1a1a;border-radius:2px;"></div>
            <div style="width:12px;height:12px;background:#1e1e1e;border-radius:2px;border:1px solid var(--border);"></div>
            <div style="width:12px;height:12px;background:#1a4a1a;border-radius:2px;"></div>
            <div style="width:12px;height:12px;background:#0a6e0a;border-radius:2px;"></div>
            <div style="width:12px;height:12px;background:#089981;border-radius:2px;"></div>
            <span>GAIN</span>
          </div>
        </div>
        <div id="cal-heatmap-wrap" style="overflow-x:auto;">
          <canvas id="cal-heatmap-canvas" style="display:block;"></canvas>
        </div>
        <!-- Tooltip -->
        <div id="cal-tooltip" style="position:fixed;background:var(--p2);border:1px solid var(--border);border-radius:6px;padding:10px 14px;font-family:'Share Tech Mono',monospace;font-size:0.65rem;color:var(--text);pointer-events:none;display:none;z-index:9999;box-shadow:0 8px 24px rgba(0,0,0,0.5);">
          <div id="cal-tt-date" style="color:var(--dim);margin-bottom:4px;"></div>
          <div id="cal-tt-pnl" style="font-size:0.8rem;font-weight:700;"></div>
          <div id="cal-tt-trades" style="color:var(--dim);margin-top:3px;"></div>
        </div>
      </div>

      <!-- Monthly Bar Chart -->
      <div style="background:var(--panel);border:1px solid var(--border);border-radius:10px;padding:20px;">
        <div style="font-family:'Share Tech Mono',monospace;font-size:0.75rem;color:var(--text);letter-spacing:1px;margin-bottom:14px;">📊 MONTHLY SUMMARY</div>
        <canvas id="cal-monthly-canvas" style="width:100%;height:150px;display:block;"></canvas>
      </div>
    </div>

    <!-- ════════════════ TAB 2: EQUITY CURVE ════════════════ -->
    <div id="analytics-curve" style="display:none;">

      <!-- Key Metric Tiles -->
      <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:20px;">
        <div style="background:var(--panel);border:1px solid var(--border);border-radius:8px;padding:16px;">
          <div style="font-family:'Share Tech Mono',monospace;font-size:0.6rem;color:var(--dim);letter-spacing:1px;margin-bottom:6px;">TOTAL RETURN</div>
          <div id="eq-total-ret" style="font-family:'JetBrains Mono',monospace;font-size:1.4rem;font-weight:700;color:var(--green);">—</div>
        </div>
        <div style="background:var(--panel);border:1px solid var(--border);border-radius:8px;padding:16px;">
          <div style="font-family:'Share Tech Mono',monospace;font-size:0.6rem;color:var(--dim);letter-spacing:1px;margin-bottom:6px;">VS NIFTY50</div>
          <div id="eq-vs-nifty" style="font-family:'JetBrains Mono',monospace;font-size:1.4rem;font-weight:700;color:var(--cyan);">—</div>
        </div>
        <div style="background:var(--panel);border:1px solid var(--border);border-radius:8px;padding:16px;">
          <div style="font-family:'Share Tech Mono',monospace;font-size:0.6rem;color:var(--dim);letter-spacing:1px;margin-bottom:6px;">SHARPE RATIO</div>
          <div id="eq-sharpe" style="font-family:'JetBrains Mono',monospace;font-size:1.4rem;font-weight:700;color:var(--gold);">—</div>
        </div>
        <div style="background:var(--panel);border:1px solid var(--border);border-radius:8px;padding:16px;">
          <div style="font-family:'Share Tech Mono',monospace;font-size:0.6rem;color:var(--dim);letter-spacing:1px;margin-bottom:6px;">MAX DRAWDOWN</div>
          <div id="eq-drawdown" style="font-family:'JetBrains Mono',monospace;font-size:1.4rem;font-weight:700;color:var(--red);">—</div>
        </div>
      </div>

      <!-- Time Range Buttons -->
      <div style="display:flex;gap:6px;margin-bottom:16px;" id="eq-range-btns">
        <button onclick="setEqRange('1M')" data-range="1M"
          style="padding:5px 14px;background:transparent;border:1px solid var(--border);color:var(--dim);
                 font-family:'Share Tech Mono',monospace;font-size:0.65rem;letter-spacing:1px;cursor:pointer;border-radius:4px;transition:all 0.2s;">1M</button>
        <button onclick="setEqRange('3M')" data-range="3M"
          style="padding:5px 14px;background:transparent;border:1px solid var(--border);color:var(--dim);
                 font-family:'Share Tech Mono',monospace;font-size:0.65rem;letter-spacing:1px;cursor:pointer;border-radius:4px;transition:all 0.2s;">3M</button>
        <button onclick="setEqRange('6M')" data-range="6M"
          style="padding:5px 14px;background:transparent;border:1px solid var(--border);color:var(--dim);
                 font-family:'Share Tech Mono',monospace;font-size:0.65rem;letter-spacing:1px;cursor:pointer;border-radius:4px;transition:all 0.2s;">6M</button>
        <button onclick="setEqRange('1Y')" data-range="1Y"
          style="padding:5px 14px;background:rgba(41,98,255,0.2);border:1px solid var(--cyan);color:var(--cyan);
                 font-family:'Share Tech Mono',monospace;font-size:0.65rem;letter-spacing:1px;cursor:pointer;border-radius:4px;transition:all 0.2s;">1Y</button>
        <button onclick="setEqRange('ALL')" data-range="ALL"
          style="padding:5px 14px;background:transparent;border:1px solid var(--border);color:var(--dim);
                 font-family:'Share Tech Mono',monospace;font-size:0.65rem;letter-spacing:1px;cursor:pointer;border-radius:4px;transition:all 0.2s;">ALL</button>
      </div>

      <!-- Chart -->
      <div style="background:var(--panel);border:1px solid var(--border);border-radius:10px;padding:20px;">
        <div style="display:flex;gap:20px;align-items:center;margin-bottom:14px;">
          <div style="font-family:'Share Tech Mono',monospace;font-size:0.75rem;color:var(--text);letter-spacing:1px;">📈 EQUITY CURVE</div>
          <div style="display:flex;gap:16px;font-family:'Share Tech Mono',monospace;font-size:0.62rem;">
            <span><span style="display:inline-block;width:16px;height:2px;background:var(--cyan);vertical-align:middle;margin-right:5px;"></span>Portfolio</span>
            <span><span style="display:inline-block;width:16px;height:2px;background:#555;vertical-align:middle;margin-right:5px;"></span>Nifty50 (normalized)</span>
          </div>
        </div>
        <div style="position:relative;">
          <canvas id="eq-curve-canvas" style="width:100%;height:320px;display:block;"></canvas>
          <div id="eq-crosshair-info" style="position:absolute;top:8px;right:8px;background:rgba(21,25,36,0.9);border:1px solid var(--border);border-radius:6px;padding:8px 12px;font-family:'Share Tech Mono',monospace;font-size:0.62rem;display:none;"></div>
        </div>
        <div style="display:flex;justify-content:space-between;font-family:'Share Tech Mono',monospace;font-size:0.6rem;color:var(--dim);margin-top:8px;">
          <span id="eq-x-start"></span>
          <span id="eq-x-end"></span>
        </div>
      </div>
    </div>

    <!-- ════════════════ TAB 3: STATISTICS ════════════════ -->
    <div id="analytics-stats" style="display:none;">
      <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px;">

        <!-- Column 1: Win/Loss Stats -->
        <div style="background:var(--panel);border:1px solid var(--border);border-radius:10px;padding:18px;">
          <div style="font-family:'Share Tech Mono',monospace;font-size:0.72rem;color:var(--cyan);letter-spacing:1px;border-bottom:1px solid var(--border);padding-bottom:10px;margin-bottom:14px;">🎯 WIN / LOSS STATS</div>
          <div id="stats-winloss-body">
            <div class="stat-row-an" style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid rgba(43,49,57,0.5);">
              <span style="font-family:Inter,sans-serif;font-size:0.7rem;color:var(--dim);">Total Trades</span>
              <span id="s-total-trades" style="font-family:'JetBrains Mono',monospace;font-size:0.75rem;color:var(--text);">—</span>
            </div>
            <div class="stat-row-an" style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid rgba(43,49,57,0.5);">
              <span style="font-family:Inter,sans-serif;font-size:0.7rem;color:var(--dim);">Win Rate</span>
              <span id="s-win-rate" style="font-family:'JetBrains Mono',monospace;font-size:0.75rem;color:var(--green);">—</span>
            </div>
            <div class="stat-row-an" style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid rgba(43,49,57,0.5);">
              <span style="font-family:Inter,sans-serif;font-size:0.7rem;color:var(--dim);">Loss Rate</span>
              <span id="s-loss-rate" style="font-family:'JetBrains Mono',monospace;font-size:0.75rem;color:var(--red);">—</span>
            </div>
            <div class="stat-row-an" style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid rgba(43,49,57,0.5);">
              <span style="font-family:Inter,sans-serif;font-size:0.7rem;color:var(--dim);">Avg Win</span>
              <span id="s-avg-win" style="font-family:'JetBrains Mono',monospace;font-size:0.75rem;color:var(--green);">—</span>
            </div>
            <div class="stat-row-an" style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid rgba(43,49,57,0.5);">
              <span style="font-family:Inter,sans-serif;font-size:0.7rem;color:var(--dim);">Avg Loss</span>
              <span id="s-avg-loss" style="font-family:'JetBrains Mono',monospace;font-size:0.75rem;color:var(--red);">—</span>
            </div>
            <div class="stat-row-an" style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid rgba(43,49,57,0.5);">
              <span style="font-family:Inter,sans-serif;font-size:0.7rem;color:var(--dim);">Profit Factor</span>
              <span id="s-profit-factor" style="font-family:'JetBrains Mono',monospace;font-size:0.75rem;color:var(--gold);">—</span>
            </div>
            <div class="stat-row-an" style="display:flex;justify-content:space-between;padding:8px 0;">
              <span style="font-family:Inter,sans-serif;font-size:0.7rem;color:var(--dim);">Expectancy / Trade</span>
              <span id="s-expectancy" style="font-family:'JetBrains Mono',monospace;font-size:0.75rem;color:var(--cyan);">—</span>
            </div>
            <!-- Win/Loss mini donut -->
            <div style="margin-top:16px;text-align:center;">
              <canvas id="stats-donut-canvas" width="120" height="120" style="display:inline-block;"></canvas>
            </div>
          </div>
        </div>

        <!-- Column 2: R:R Stats -->
        <div style="background:var(--panel);border:1px solid var(--border);border-radius:10px;padding:18px;">
          <div style="font-family:'Share Tech Mono',monospace;font-size:0.72rem;color:var(--gold);letter-spacing:1px;border-bottom:1px solid var(--border);padding-bottom:10px;margin-bottom:14px;">⚖️ R:R &amp; HOLDING STATS</div>
          <div class="stat-row-an" style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid rgba(43,49,57,0.5);">
            <span style="font-family:Inter,sans-serif;font-size:0.7rem;color:var(--dim);">Avg R:R Ratio</span>
            <span id="s-avg-rr" style="font-family:'JetBrains Mono',monospace;font-size:0.75rem;color:var(--gold);">—</span>
          </div>
          <div class="stat-row-an" style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid rgba(43,49,57,0.5);">
            <span style="font-family:Inter,sans-serif;font-size:0.7rem;color:var(--dim);">Avg Holding (days)</span>
            <span id="s-avg-hold" style="font-family:'JetBrains Mono',monospace;font-size:0.75rem;color:var(--text);">—</span>
          </div>
          <div class="stat-row-an" style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid rgba(43,49,57,0.5);">
            <span style="font-family:Inter,sans-serif;font-size:0.7rem;color:var(--dim);">Best Trade R:R</span>
            <span id="s-best-rr" style="font-family:'JetBrains Mono',monospace;font-size:0.75rem;color:var(--green);">—</span>
          </div>
          <div class="stat-row-an" style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid rgba(43,49,57,0.5);">
            <span style="font-family:Inter,sans-serif;font-size:0.7rem;color:var(--dim);">Worst Trade R:R</span>
            <span id="s-worst-rr" style="font-family:'JetBrains Mono',monospace;font-size:0.75rem;color:var(--red);">—</span>
          </div>
          <div class="stat-row-an" style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid rgba(43,49,57,0.5);">
            <span style="font-family:Inter,sans-serif;font-size:0.7rem;color:var(--dim);">Max Consec. Wins</span>
            <span id="s-consec-wins" style="font-family:'JetBrains Mono',monospace;font-size:0.75rem;color:var(--green);">—</span>
          </div>
          <div class="stat-row-an" style="display:flex;justify-content:space-between;padding:8px 0;">
            <span style="font-family:Inter,sans-serif;font-size:0.7rem;color:var(--dim);">Max Consec. Losses</span>
            <span id="s-consec-losses" style="font-family:'JetBrains Mono',monospace;font-size:0.75rem;color:var(--red);">—</span>
          </div>
          <!-- Streak visual -->
          <div style="margin-top:16px;">
            <div style="font-family:'Share Tech Mono',monospace;font-size:0.6rem;color:var(--dim);margin-bottom:6px;letter-spacing:1px;">RECENT TRADE STREAK</div>
            <div id="s-streak-dots" style="display:flex;gap:4px;flex-wrap:wrap;"></div>
          </div>
        </div>

        <!-- Column 3: Period Breakdown -->
        <div style="background:var(--panel);border:1px solid var(--border);border-radius:10px;padding:18px;">
          <div style="font-family:'Share Tech Mono',monospace;font-size:0.72rem;color:var(--green);letter-spacing:1px;border-bottom:1px solid var(--border);padding-bottom:10px;margin-bottom:14px;">📅 PERIOD BREAKDOWN</div>

          <!-- Monthly mini bars -->
          <div style="font-family:'Share Tech Mono',monospace;font-size:0.62rem;color:var(--dim);letter-spacing:1px;margin-bottom:8px;">LAST 6 MONTHS P&amp;L</div>
          <canvas id="stats-monthly-canvas" style="width:100%;height:90px;display:block;margin-bottom:16px;"></canvas>

          <!-- Weekday performance -->
          <div style="font-family:'Share Tech Mono',monospace;font-size:0.62rem;color:var(--dim);letter-spacing:1px;margin-bottom:8px;">WEEKDAY WIN RATE</div>
          <div id="stats-weekday-body" style="display:flex;flex-direction:column;gap:5px;"></div>
        </div>

      </div>
    </div>

    <!-- ════════════════ TAB 4: BEST/WORST ════════════════ -->
    <div id="analytics-best" style="display:none;">

      <!-- Toggle Buttons -->
      <div style="display:flex;gap:0;margin-bottom:20px;border:1px solid var(--border);border-radius:8px;overflow:hidden;width:fit-content;">
        <button id="bw-btn-best" onclick="loadBestWorst('best')"
          style="padding:8px 28px;background:rgba(8,153,129,0.2);border:none;border-right:1px solid var(--border);
                 color:var(--green);font-family:'Share Tech Mono',monospace;font-size:0.7rem;letter-spacing:1px;cursor:pointer;">
          🏆 BEST 10 TRADES
        </button>
        <button id="bw-btn-worst" onclick="loadBestWorst('worst')"
          style="padding:8px 28px;background:transparent;border:none;
                 color:var(--dim);font-family:'Share Tech Mono',monospace;font-size:0.7rem;letter-spacing:1px;cursor:pointer;">
          💀 WORST 10 TRADES
        </button>
      </div>

      <!-- Table -->
      <div style="background:var(--panel);border:1px solid var(--border);border-radius:10px;overflow:hidden;">
        <div style="display:grid;grid-template-columns:40px 90px 80px 80px 100px 100px 100px 80px 70px 70px;
                    padding:10px 14px;background:rgba(43,49,57,0.6);gap:8px;
                    font-family:'Share Tech Mono',monospace;font-size:0.6rem;color:var(--dim);letter-spacing:1px;">
          <div>#</div><div>SYMBOL</div><div>ENTRY</div><div>EXIT</div>
          <div>ENTRY DATE</div><div>EXIT DATE</div><div>P&amp;L ₹</div><div>P&amp;L %</div><div>R:R</div><div>TYPE</div>
        </div>
        <div id="bw-table-body"></div>
      </div>

      <!-- Mini price chart for selected trade -->
      <div id="bw-mini-chart-wrap" style="display:none;background:var(--panel);border:1px solid var(--border);border-radius:10px;padding:16px;margin-top:16px;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
          <div id="bw-mini-title" style="font-family:'Share Tech Mono',monospace;font-size:0.72rem;color:var(--text);"></div>
          <button onclick="document.getElementById('bw-mini-chart-wrap').style.display='none'"
            style="background:transparent;border:1px solid var(--border);color:var(--dim);padding:3px 10px;cursor:pointer;font-family:'Share Tech Mono',monospace;font-size:0.6rem;border-radius:4px;">✕ CLOSE</button>
        </div>
        <canvas id="bw-mini-canvas" style="width:100%;height:180px;display:block;"></canvas>
      </div>
    </div>

    <!-- ════════════════ TAB 5: SECTOR P&L ════════════════ -->
    <div id="analytics-sector" style="display:none;">

      <div style="display:grid;grid-template-columns:320px 1fr;gap:16px;margin-bottom:16px;">

        <!-- Donut Chart -->
        <div style="background:var(--panel);border:1px solid var(--border);border-radius:10px;padding:18px;">
          <div style="font-family:'Share Tech Mono',monospace;font-size:0.72rem;color:var(--text);letter-spacing:1px;margin-bottom:14px;">🥧 P&amp;L BY SECTOR</div>
          <canvas id="sector-donut-canvas" width="280" height="280" style="display:block;margin:0 auto;"></canvas>
          <div id="sector-donut-legend" style="margin-top:12px;display:flex;flex-direction:column;gap:5px;"></div>
        </div>

        <!-- Sector Bar Chart -->
        <div style="background:var(--panel);border:1px solid var(--border);border-radius:10px;padding:18px;">
          <div style="font-family:'Share Tech Mono',monospace;font-size:0.72rem;color:var(--text);letter-spacing:1px;margin-bottom:14px;">📊 SECTOR WIN / LOSS / NET P&amp;L</div>
          <canvas id="sector-bar-canvas" style="width:100%;height:240px;display:block;"></canvas>
        </div>
      </div>

      <!-- Sector Table -->
      <div style="background:var(--panel);border:1px solid var(--border);border-radius:10px;overflow:hidden;margin-bottom:16px;">
        <div style="display:flex;justify-content:space-between;align-items:center;padding:12px 16px;background:rgba(43,49,57,0.4);">
          <div style="font-family:'Share Tech Mono',monospace;font-size:0.72rem;color:var(--text);">SECTOR BREAKDOWN TABLE</div>
          <button id="sector-export-csv-btn" onclick="exportSectorCSV()"
            style="padding:5px 16px;background:rgba(8,153,129,0.2);border:1px solid var(--green);color:var(--green);
                   font-family:'Share Tech Mono',monospace;font-size:0.65rem;letter-spacing:1px;cursor:pointer;border-radius:4px;">
            ⬇ EXPORT CSV
          </button>
        </div>
        <div style="display:grid;grid-template-columns:1fr 80px 80px 120px 120px;
                    padding:8px 16px;background:rgba(43,49,57,0.6);gap:8px;
                    font-family:'Share Tech Mono',monospace;font-size:0.6rem;color:var(--dim);letter-spacing:1px;">
          <div>SECTOR</div><div>TRADES</div><div>WIN %</div><div>NET P&amp;L</div><div>AVG / TRADE</div>
        </div>
        <div id="sector-table-body"></div>
      </div>
    </div>

  </div><!-- /padding wrapper -->

  <!-- ══════════════════════════════════════════════════════════ -->
  <!-- FIXED FOOTER: EXPORT BAR                                   -->
  <!-- ══════════════════════════════════════════════════════════ -->
  <div id="analytics-export-bar"
    style="position:fixed;bottom:0;left:0;right:0;z-index:800;
           background:rgba(11,14,20,0.97);border-top:1px solid var(--border);
           display:none;justify-content:center;align-items:center;gap:12px;padding:10px 20px;
           backdrop-filter:blur(10px);">
    <span style="font-family:'Share Tech Mono',monospace;font-size:0.6rem;color:var(--dim);letter-spacing:1px;margin-right:8px;">EXPORT:</span>
    <button onclick="exportPDF()"
      style="padding:7px 22px;background:rgba(41,98,255,0.2);border:1px solid var(--cyan);color:var(--cyan);
             font-family:'Share Tech Mono',monospace;font-size:0.7rem;letter-spacing:1px;cursor:pointer;border-radius:5px;
             transition:all 0.2s;" onmouseover="this.style.background='rgba(41,98,255,0.4)'" onmouseout="this.style.background='rgba(41,98,255,0.2)'">
      🖨 EXPORT PDF
    </button>
    <button onclick="exportAnalyticsCSV()"
      style="padding:7px 22px;background:rgba(8,153,129,0.2);border:1px solid var(--green);color:var(--green);
             font-family:'Share Tech Mono',monospace;font-size:0.7rem;letter-spacing:1px;cursor:pointer;border-radius:5px;
             transition:all 0.2s;" onmouseover="this.style.background='rgba(8,153,129,0.4)'" onmouseout="this.style.background='rgba(8,153,129,0.2)'">
      ⬇ EXPORT CSV
    </button>
    <button onclick="sendAnalyticsWhatsApp()"
      style="padding:7px 22px;background:rgba(37,211,102,0.15);border:1px solid #25d366;color:#25d366;
             font-family:'Share Tech Mono',monospace;font-size:0.7rem;letter-spacing:1px;cursor:pointer;border-radius:5px;
             transition:all 0.2s;" onmouseover="this.style.background='rgba(37,211,102,0.3)'" onmouseout="this.style.background='rgba(37,211,102,0.15)'">
      📱 SEND TO WHATSAPP
    </button>
  </div>

</div>
<!-- ═══════════ END PAGE: ANALYTICS ═══════════ -->

<!-- PRINT CSS for PDF export -->
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Inter:wght@400;500;600&display=swap');

:root {
  --bg:     #0B0E14;
  --panel:  #151924;
  --p2:     #1E222D;
  --border: #2B3139;
  --cyan:   #2962FF;
  --green:  #089981;
  --red:    #F23645;
  --gold:   #FF9800;
  --text:   #D1D4DC;
  --dim:    #6C7284;
}

/* Animate stat tiles on load */
.an-stat-tile {
  transition: transform 0.2s, box-shadow 0.2s;
}
.an-stat-tile:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0,0,0,0.4);
}

/* Stat rows hover */
.stat-row-an:hover {
  background: rgba(41,98,255,0.05);
  border-radius: 4px;
}

/* Heatmap cell hover (done via canvas events) */

/* Best/Worst table row hover handled in JS */

/* Analytics tab button active state */
.atab-active {
  background: rgba(41,98,255,0.15) !important;
  border-bottom: 2px solid var(--cyan) !important;
  color: var(--cyan) !important;
}

@media print {
  #analytics-export-bar  { display: none !important; }
  #analytics-tab-nav     { display: none !important; }
  .page                  { display: block !important; }
  #analytics-calendar,
  #analytics-curve,
  #analytics-stats,
  #analytics-best,
  #analytics-sector {
    display: block !important;
    page-break-inside: avoid;
    margin-bottom: 40px;
  }
  body {
    background: #fff !important;
    color: #000 !important;
  }
  canvas {
    max-width: 100%;
  }
}
</style>
"""

JS = r"""
// ═══════════════════════════════════════════════════
//  ANALYTICS PAGE — JavaScript
//  Vprofitables · Phase 5 · Performance Analytics
// ═══════════════════════════════════════════════════

// ── State ────────────────────────────────────────────
let _analyticsTab = 'calendar';
let _eqRange      = '1Y';
let _eqData       = null;
let _calData      = null;
let _sectorData   = null;
let _bwMode       = 'best';
let _bwData       = null;

// ── Tab Switcher ─────────────────────────────────────
function analyticsTab(tab) {
  _analyticsTab = tab;
  const panels = ['calendar','curve','stats','best','sector'];
  const btns   = ['calendar','curve','stats','best','sector'];

  panels.forEach(p => {
    const el = document.getElementById('analytics-' + p);
    if (el) el.style.display = (p === tab) ? '' : 'none';
  });
  btns.forEach(b => {
    const btn = document.getElementById('atab-' + b);
    if (!btn) return;
    if (b === tab) {
      btn.style.background    = 'rgba(41,98,255,0.15)';
      btn.style.borderBottom  = '2px solid #2962FF';
      btn.style.color         = '#2962FF';
    } else {
      btn.style.background    = 'transparent';
      btn.style.borderBottom  = '2px solid transparent';
      btn.style.color         = '#6C7284';
    }
  });

  // Show export bar on all tabs
  const bar = document.getElementById('analytics-export-bar');
  if (bar) bar.style.display = 'flex';

  // Lazy-load tab data
  if (tab === 'calendar'  && !_calData)    loadCalendar();
  if (tab === 'curve'     && !_eqData)     loadEquityCurve();
  if (tab === 'stats')                     loadStatistics();
  if (tab === 'best'      && !_bwData)     loadBestWorst('best');
  if (tab === 'sector'    && !_sectorData) loadSectorPnl();
}

// ── Init ─────────────────────────────────────────────
function initAnalytics() {
  analyticsTab('calendar');
}

// ════════════════════════════════════════════════════
//  TAB 1: P&L CALENDAR HEATMAP
// ════════════════════════════════════════════════════
async function loadCalendar() {
  try {
    let url = '/api/analytics_data?type=calendar';
    const resp = await fetch(url);
    const data = resp.ok ? await resp.json() : null;
    _calData = data || _mockCalendarData();
    drawCalendarHeatmap(_calData);
  } catch(e) {
    _calData = _mockCalendarData();
    drawCalendarHeatmap(_calData);
  }
}

function _mockCalendarData() {
  // Generate a year of mock P&L data
  const days = {};
  const now  = new Date();
  const start = new Date(now.getFullYear(), 0, 1);
  for (let d = new Date(start); d <= now; d.setDate(d.getDate() + 1)) {
    const dow = d.getDay();
    if (dow === 0 || dow === 6) continue; // skip weekends
    const key = d.toISOString().slice(0, 10);
    if (Math.random() < 0.65) { // 65% of trading days have trades
      const pnl = (Math.random() - 0.38) * 25000;
      days[key] = { pnl: Math.round(pnl), trades: Math.ceil(Math.random() * 6) };
    }
  }
  // Compute stats
  const vals = Object.values(days).map(d => d.pnl);
  const total = vals.reduce((a,b) => a+b, 0);
  const bestDay  = Math.max(...vals);
  const worstDay = Math.min(...vals);
  const profitableDays = vals.filter(v => v > 0).length;
  return { days, total, best_day: bestDay, worst_day: worstDay, profitable_pct: Math.round(profitableDays/vals.length*100) };
}

function drawCalendarHeatmap(data) {
  // Update top stats
  const fmt = v => (v >= 0 ? '+' : '') + '₹' + Math.abs(v).toLocaleString('en-IN');
  const setEl = (id, val, col) => { const e = document.getElementById(id); if(e){ e.textContent=val; if(col) e.style.color=col; } };
  setEl('cal-total-pnl',   fmt(data.total || 0),      (data.total||0) >= 0 ? '#089981' : '#F23645');
  setEl('cal-best-day',    fmt(data.best_day || 0),   '#089981');
  setEl('cal-worst-day',   fmt(data.worst_day || 0),  '#F23645');
  setEl('cal-profit-pct',  (data.profitable_pct || 0) + '%', '#2962FF');

  const days = data.days || {};
  const canvas = document.getElementById('cal-heatmap-canvas');
  if (!canvas) return;

  const CELL  = 14;
  const GAP   = 3;
  const STEP  = CELL + GAP;
  const MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  const DAYS_L = ['S','M','T','W','T','F','S'];

  const year  = new Date().getFullYear();
  const jan1  = new Date(year, 0, 1);
  const startDow = jan1.getDay(); // 0=Sun

  // Figure out max weeks needed
  const totalDays = 366;
  const weeks = Math.ceil((totalDays + startDow) / 7) + 1;

  const LEFT_PAD = 26;
  const TOP_PAD  = 32;
  const W = LEFT_PAD + weeks * STEP + 10;
  const H = TOP_PAD  + 7 * STEP + 20;

  canvas.width  = W;
  canvas.height = H;
  const ctx = canvas.getContext('2d');
  ctx.clearRect(0, 0, W, H);

  // Color scale
  const allPnl = Object.values(days).map(d => d.pnl).filter(Boolean);
  const maxGain = allPnl.length ? Math.max(...allPnl.filter(v=>v>0), 1) : 1;
  const maxLoss = allPnl.length ? Math.abs(Math.min(...allPnl.filter(v=>v<0), -1)) : 1;

  function pnlColor(pnl) {
    if (pnl === 0 || pnl === undefined) return '#1a1e27';
    if (pnl > 0) {
      const t = Math.min(pnl / maxGain, 1);
      if (t < 0.33) return '#1a4a1a';
      if (t < 0.66) return '#0a6e0a';
      return '#089981';
    } else {
      const t = Math.min(Math.abs(pnl) / maxLoss, 1);
      if (t < 0.33) return '#4a0a0a';
      if (t < 0.66) return '#8b1a1a';
      return '#F23645';
    }
  }

  // Draw day labels
  ctx.font = '10px JetBrains Mono, monospace';
  ctx.fillStyle = '#6C7284';
  ['M','W','F'].forEach((l, i) => {
    const row = [1,3,5][i];
    ctx.fillText(l, 2, TOP_PAD + row * STEP + CELL - 2);
  });

  // Store cell positions for tooltip
  canvas._cells = [];

  // Draw cells
  let curDate = new Date(year, 0, 1);
  const today = new Date();

  for (let d = 0; d < 365 + (year % 4 === 0 ? 1 : 0); d++) {
    const dow  = curDate.getDay();
    const wnum = Math.floor((d + startDow) / 7);
    const x    = LEFT_PAD + wnum * STEP;
    const y    = TOP_PAD  + dow * STEP;
    const key  = curDate.toISOString().slice(0, 10);
    const cell = days[key];
    const pnl  = cell ? cell.pnl : 0;

    ctx.fillStyle = pnlColor(pnl);
    ctx.beginPath();
    ctx.roundRect(x, y, CELL, CELL, 2);
    ctx.fill();

    // Today highlight
    if (curDate.toDateString() === today.toDateString()) {
      ctx.strokeStyle = '#2962FF';
      ctx.lineWidth   = 1.5;
      ctx.beginPath();
      ctx.roundRect(x, y, CELL, CELL, 2);
      ctx.stroke();
    }

    canvas._cells.push({ x, y, key, pnl, trades: cell ? cell.trades : 0 });
    curDate.setDate(curDate.getDate() + 1);
  }

  // Draw month labels
  ctx.font = '10px Share Tech Mono, monospace';
  ctx.fillStyle = '#6C7284';
  let prevMonth = -1;
  canvas._cells.forEach(c => {
    const dt = new Date(c.key);
    const mo = dt.getMonth();
    if (mo !== prevMonth) {
      const wnum = Math.floor((canvas._cells.indexOf(c) + startDow) / 7);
      ctx.fillText(MONTHS[mo], LEFT_PAD + wnum * STEP, TOP_PAD - 8);
      prevMonth = mo;
    }
  });

  // Tooltip logic
  canvas.onmousemove = (e) => {
    const rect = canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;
    const tt = document.getElementById('cal-tooltip');
    let found = false;
    for (const c of canvas._cells) {
      if (mx >= c.x && mx <= c.x + CELL && my >= c.y && my <= c.y + CELL) {
        if (!c.key) break;
        const fmt2 = v => (v >= 0 ? '+' : '-') + '₹' + Math.abs(v).toLocaleString('en-IN');
        document.getElementById('cal-tt-date').textContent   = c.key;
        document.getElementById('cal-tt-pnl').textContent    = fmt2(c.pnl || 0);
        document.getElementById('cal-tt-pnl').style.color    = (c.pnl||0) >= 0 ? '#089981' : '#F23645';
        document.getElementById('cal-tt-trades').textContent = c.trades ? c.trades + ' trade(s)' : 'No trades';
        tt.style.display = 'block';
        tt.style.left    = (e.clientX + 14) + 'px';
        tt.style.top     = (e.clientY - 40) + 'px';
        found = true;
        break;
      }
    }
    if (!found) tt.style.display = 'none';
  };
  canvas.onmouseleave = () => { const tt=document.getElementById('cal-tooltip'); if(tt) tt.style.display='none'; };

  // Draw monthly summary bar chart
  _drawMonthlyBars(data);
}

function _drawMonthlyBars(data) {
  const canvas = document.getElementById('cal-monthly-canvas');
  if (!canvas) return;
  const W = canvas.offsetWidth || 800;
  const H = 150;
  canvas.width  = W;
  canvas.height = H;
  const ctx = canvas.getContext('2d');
  ctx.clearRect(0, 0, W, H);

  const MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  const year   = new Date().getFullYear();

  // Aggregate monthly P&L
  const monthly = Array(12).fill(0);
  Object.entries(data.days || {}).forEach(([k, v]) => {
    const mo = parseInt(k.slice(5, 7)) - 1;
    monthly[mo] += v.pnl;
  });

  const maxAbs = Math.max(...monthly.map(Math.abs), 1);
  const barW   = Math.floor((W - 40) / 12) - 4;
  const midY   = H * 0.55;

  ctx.font = '9px Share Tech Mono, monospace';

  monthly.forEach((pnl, i) => {
    const x    = 20 + i * ((W - 40) / 12);
    const barH = Math.abs(pnl) / maxAbs * (midY - 20);

    ctx.fillStyle = pnl >= 0 ? '#089981' : '#F23645';
    if (pnl >= 0) {
      ctx.fillRect(x, midY - barH, barW, barH);
    } else {
      ctx.fillRect(x, midY, barW, barH);
    }

    // Month label
    ctx.fillStyle = '#6C7284';
    ctx.fillText(MONTHS[i], x, H - 4);

    // Value label
    if (Math.abs(pnl) > 0) {
      ctx.fillStyle = pnl >= 0 ? '#089981' : '#F23645';
      const label = pnl >= 0 ? '+' + _kfmt(pnl) : '-' + _kfmt(Math.abs(pnl));
      ctx.fillText(label, x, pnl >= 0 ? midY - barH - 3 : midY + barH + 11);
    }
  });

  // Baseline
  ctx.strokeStyle = '#2B3139';
  ctx.lineWidth   = 1;
  ctx.beginPath();
  ctx.moveTo(10, midY);
  ctx.lineTo(W - 10, midY);
  ctx.stroke();
}

function _kfmt(v) {
  if (Math.abs(v) >= 100000) return (v/100000).toFixed(1) + 'L';
  if (Math.abs(v) >= 1000)   return (v/1000).toFixed(1) + 'k';
  return v.toFixed(0);
}

// ════════════════════════════════════════════════════
//  TAB 2: EQUITY CURVE
// ════════════════════════════════════════════════════
async function loadEquityCurve() {
  try {
    const resp = await fetch('/api/analytics_data?type=equity_curve');
    const data = resp.ok ? await resp.json() : null;
    _eqData = data || _mockEquityData();
    drawEquityCurve(_eqData);
  } catch(e) {
    _eqData = _mockEquityData();
    drawEquityCurve(_eqData);
  }
}

function _mockEquityData() {
  const pts = 252; // ~1 trading year
  const dates = [];
  const portfolio = [];
  const nifty     = [];
  let pVal = 500000, nVal = 500000;
  let d = new Date();
  d.setFullYear(d.getFullYear() - 1);
  for (let i = 0; i < pts; i++) {
    while ([0,6].includes(d.getDay())) d.setDate(d.getDate() + 1);
    dates.push(d.toISOString().slice(0,10));
    const pr = (Math.random() - 0.44) * 0.018;
    const nr = (Math.random() - 0.46) * 0.014;
    pVal *= (1 + pr);
    nVal *= (1 + nr);
    portfolio.push(Math.round(pVal));
    nifty.push(Math.round(nVal));
    d.setDate(d.getDate() + 1);
  }
  const ret      = ((portfolio.at(-1) - 500000) / 500000 * 100).toFixed(2);
  const niftyRet = ((nifty.at(-1) - 500000) / 500000 * 100).toFixed(2);
  // Approx Sharpe: annualized return / std dev of daily returns
  const daily = portfolio.map((v,i) => i===0 ? 0 : (v - portfolio[i-1]) / portfolio[i-1]);
  const mean  = daily.slice(1).reduce((a,b)=>a+b,0) / (daily.length-1);
  const std   = Math.sqrt(daily.slice(1).reduce((a,b)=>a+(b-mean)**2,0)/(daily.length-2));
  const sharpe = (mean / std * Math.sqrt(252)).toFixed(2);
  // Max drawdown
  let peak = portfolio[0], maxDD = 0;
  portfolio.forEach(v => { if(v>peak) peak=v; const dd=(peak-v)/peak; if(dd>maxDD) maxDD=dd; });

  return { dates, portfolio, nifty, total_return: +ret, nifty_return: +niftyRet, sharpe: +sharpe, max_drawdown: +(maxDD*100).toFixed(2) };
}

function setEqRange(range) {
  _eqRange = range;
  document.querySelectorAll('#eq-range-btns button').forEach(b => {
    const active = b.dataset.range === range;
    b.style.background = active ? 'rgba(41,98,255,0.2)' : 'transparent';
    b.style.borderColor = active ? '#2962FF' : '#2B3139';
    b.style.color = active ? '#2962FF' : '#6C7284';
  });
  if (_eqData) drawEquityCurve(_eqData);
}

function drawEquityCurve(data) {
  // Update metric tiles
  const setEl = (id, val, col) => { const e=document.getElementById(id); if(e){ e.textContent=val; if(col) e.style.color=col; } };
  const ret = data.total_return || 0;
  const nif = data.nifty_return || 0;
  setEl('eq-total-ret',  (ret>=0?'+':'')+ret+'%',         ret>=0?'#089981':'#F23645');
  setEl('eq-vs-nifty',   (ret-nif>=0?'+':'')+(ret-nif).toFixed(2)+'%', ret-nif>=0?'#2962FF':'#F23645');
  setEl('eq-sharpe',     (data.sharpe||0).toFixed(2),     +data.sharpe>=1?'#FF9800':'#D1D4DC');
  setEl('eq-drawdown',   '-'+(data.max_drawdown||0).toFixed(2)+'%', '#F23645');

  const canvas = document.getElementById('eq-curve-canvas');
  if (!canvas) return;

  // Slice data by range
  const allDates = (data.curve || []).map(c => c.date);
  const allPf    = (data.curve || []).map(c => c.value);
  const allNf    = (data.curve || []).map(c => c.nifty || c.value);
  let sliceN     = allDates.length;
  const rangeDays = { '1M':21,'3M':63,'6M':126,'1Y':252,'ALL':9999 };
  sliceN = Math.min(allDates.length, rangeDays[_eqRange] || allDates.length);
  const dates = allDates.slice(-sliceN);
  const pf    = allPf.slice(-sliceN);
  const nf    = allNf.slice(-sliceN);

  // Normalize Nifty to same start as portfolio
  const pfStart = pf[0] || 1;
  const nfStart = nf[0] || 1;
  const nfNorm  = nf.map(v => v / nfStart * pfStart);

  const W = canvas.offsetWidth || 800;
  const H = 320;
  canvas.width  = W;
  canvas.height = H;
  const ctx = canvas.getContext('2d');
  ctx.clearRect(0, 0, W, H);

  const PAD = { l:70, r:20, t:20, b:30 };
  const cW  = W - PAD.l - PAD.r;
  const cH  = H - PAD.t - PAD.b;

  const allVals = [...pf, ...nfNorm];
  const minV    = Math.min(...allVals) * 0.98;
  const maxV    = Math.max(...allVals) * 1.02;
  const range   = maxV - minV || 1;

  const xOf = i  => PAD.l + (i / (pf.length - 1)) * cW;
  const yOf = v  => PAD.t + cH - ((v - minV) / range) * cH;

  // Grid lines
  ctx.strokeStyle = '#2B3139';
  ctx.lineWidth   = 1;
  for (let g = 0; g <= 4; g++) {
    const y = PAD.t + (g / 4) * cH;
    ctx.beginPath(); ctx.moveTo(PAD.l, y); ctx.lineTo(W - PAD.r, y); ctx.stroke();
    const lv = maxV - (g / 4) * range;
    ctx.font = '10px JetBrains Mono, monospace';
    ctx.fillStyle = '#6C7284';
    ctx.textAlign = 'right';
    ctx.fillText('₹' + _kfmt(lv), PAD.l - 4, y + 4);
  }
  ctx.textAlign = 'left';

  // Nifty line (dim gray)
  if (nfNorm.length > 1) {
    ctx.beginPath();
    ctx.strokeStyle = '#3a3f4a';
    ctx.lineWidth   = 1.5;
    nfNorm.forEach((v, i) => { i===0 ? ctx.moveTo(xOf(i), yOf(v)) : ctx.lineTo(xOf(i), yOf(v)); });
    ctx.stroke();
  }

  // Portfolio area fill
  if (pf.length > 1) {
    ctx.beginPath();
    pf.forEach((v, i) => { i===0 ? ctx.moveTo(xOf(i), yOf(v)) : ctx.lineTo(xOf(i), yOf(v)); });
    ctx.lineTo(xOf(pf.length-1), yOf(minV));
    ctx.lineTo(xOf(0), yOf(minV));
    ctx.closePath();
    const grad = ctx.createLinearGradient(0, PAD.t, 0, PAD.t + cH);
    grad.addColorStop(0, 'rgba(41,98,255,0.35)');
    grad.addColorStop(1, 'rgba(41,98,255,0.0)');
    ctx.fillStyle = grad;
    ctx.fill();

    // Portfolio line
    ctx.beginPath();
    ctx.strokeStyle = '#2962FF';
    ctx.lineWidth   = 2;
    ctx.shadowBlur  = 6;
    ctx.shadowColor = 'rgba(41,98,255,0.5)';
    pf.forEach((v, i) => { i===0 ? ctx.moveTo(xOf(i), yOf(v)) : ctx.lineTo(xOf(i), yOf(v)); });
    ctx.stroke();
    ctx.shadowBlur = 0;
  }

  // X-axis date labels
  const labelCount = 6;
  ctx.font = '10px Share Tech Mono, monospace';
  ctx.fillStyle = '#6C7284';
  for (let l = 0; l <= labelCount; l++) {
    const idx = Math.round(l / labelCount * (dates.length - 1));
    if (!dates[idx]) continue;
    const x = xOf(idx);
    ctx.fillText(dates[idx].slice(0, 7), x - 18, H - 6);
  }

  // X-axis endpoints
  const startEl = document.getElementById('eq-x-start');
  const endEl   = document.getElementById('eq-x-end');
  if (startEl) startEl.textContent = dates[0] || '';
  if (endEl)   endEl.textContent   = dates.at(-1) || '';

  // Crosshair on hover
  canvas._pfData   = pf;
  canvas._nfNorm   = nfNorm;
  canvas._dates    = dates;
  canvas._xOf      = xOf;
  canvas._yOf      = yOf;
  canvas._PAD      = PAD;
  canvas._cW       = cW;
  canvas._cH       = cH;
  canvas._minV     = minV;
  canvas._maxV     = maxV;

  canvas.onmousemove = function(e) {
    const rect = canvas.getBoundingClientRect();
    const mx   = e.clientX - rect.left;
    const idx  = Math.round((mx - PAD.l) / cW * (pf.length - 1));
    if (idx < 0 || idx >= pf.length) return;
    const info = document.getElementById('eq-crosshair-info');
    if (info) {
      info.style.display = 'block';
      const pval = pf[idx];
      const nval = nfNorm[idx];
      const ret2 = pf[0] ? ((pval - pf[0]) / pf[0] * 100).toFixed(2) : 0;
      info.innerHTML =
        `<div style="color:#6C7284;margin-bottom:4px;">${dates[idx] || ''}</div>
         <div style="color:#2962FF;font-weight:700;">Portfolio: ₹${pval ? pval.toLocaleString('en-IN') : '—'} <span style="color:${+ret2>=0?'#089981':'#F23645'};">(${+ret2>=0?'+':''}${ret2}%)</span></div>
         <div style="color:#555;">Nifty (norm): ₹${nval ? Math.round(nval).toLocaleString('en-IN') : '—'}</div>`;
    }

    // Redraw with crosshair
    const savedDraw = () => drawEquityCurve(data);
    drawEquityCurve(data);
    const cx = xOf(idx);
    const cy = yOf(pf[idx]);
    const cvs = document.getElementById('eq-curve-canvas');
    const c2  = cvs.getContext('2d');
    c2.strokeStyle = 'rgba(41,98,255,0.4)';
    c2.lineWidth   = 1;
    c2.setLineDash([4, 4]);
    c2.beginPath(); c2.moveTo(cx, PAD.t); c2.lineTo(cx, PAD.t + cH); c2.stroke();
    c2.setLineDash([]);
    c2.beginPath();
    c2.arc(cx, cy, 4, 0, Math.PI*2);
    c2.fillStyle = '#2962FF';
    c2.fill();
  };
  canvas.onmouseleave = function() {
    const info = document.getElementById('eq-crosshair-info');
    if (info) info.style.display = 'none';
  };
}

// ════════════════════════════════════════════════════
//  TAB 3: STATISTICS
// ════════════════════════════════════════════════════
async function loadStatistics() {
  try {
    const resp = await fetch('/api/analytics_data?type=statistics');
    const data = resp.ok ? await resp.json() : null;
    _renderStats(data || _mockStatsData());
  } catch(e) {
    _renderStats(_mockStatsData());
  }
}

function _mockStatsData() {
  return {
    total_trades: 87,
    win_pct: 61.0,
    loss_pct: 39.0,
    avg_win: 8420,
    avg_loss: 4380,
    profit_factor: 3.31,
    expectancy: 3426,
    avg_rr: 2.18,
    avg_hold_days: 4.2,
    best_rr: 8.4,
    worst_rr: -1.0,
    max_consec_wins: 7,
    max_consec_losses: 4,
    recent_streak: ['W','W','L','W','W','W','L','L','W','W','W','W','L','W','W'],
    monthly_pnl: [
      { month: 'Jan', pnl: -3200 },
      { month: 'Feb', pnl: 14500 },
      { month: 'Mar', pnl: 8700  },
      { month: 'Apr', pnl: -1200 },
      { month: 'May', pnl: 22000 },
      { month: 'Jun', pnl: 11300 },
    ],
    weekday: [
      { day: 'Mon', wins: 14, losses: 8  },
      { day: 'Tue', wins: 18, losses: 6  },
      { day: 'Wed', wins: 12, losses: 11 },
      { day: 'Thu', wins: 16, losses: 7  },
      { day: 'Fri', wins: 13, losses: 2  },
    ]
  };
}

function _renderStats(data) {
  const fmtR = v => (v >= 0 ? '+' : '-') + '₹' + Math.abs(v).toLocaleString('en-IN');
  const setEl = (id, val, col) => { const e=document.getElementById(id); if(e){ e.textContent=val; if(col) e.style.color=col; } };

  setEl('s-trades',        data.total_trades + ' trades');
  setEl('s-win-rate',      data.win_pct + '%',          '#089981');
  setEl('s-loss-rate',     data.loss_pct + '%',         '#F23645');
  setEl('s-avg-win',       fmtR(data.avg_win),           '#089981');
  setEl('s-avg-loss',      fmtR(-Math.abs(data.avg_loss)),'#F23645');
  setEl('s-profit-factor', (data.profit_factor||0).toFixed(2), '#FF9800');
  setEl('s-expectancy',    fmtR(data.expectancy),        data.expectancy>=0?'#2962FF':'#F23645');
  setEl('s-avg-rr',        (data.avg_rr||0).toFixed(2) + ':1', '#FF9800');
  setEl('s-avg-hold',      (data.avg_hold_days||0).toFixed(1) + ' days');
  setEl('s-best-rr',       (data.best_rr||0).toFixed(2) + ':1', '#089981');
  setEl('s-worst-rr',      (data.worst_rr||0).toFixed(2) + ':1', '#F23645');
  setEl('s-consec-wins',   data.max_consec_wins + ' trades', '#089981');
  setEl('s-consec-losses', data.max_consec_losses + ' trades', '#F23645');

  // Streak dots
  const dotsEl = document.getElementById('s-streak-dots');
  if (dotsEl && data.recent_streak) {
    dotsEl.innerHTML = data.recent_streak.map(s =>
      `<div title="${s==='W'?'Win':'Loss'}" style="width:18px;height:18px;border-radius:50%;background:${s==='W'?'#089981':'#F23645'};
       display:flex;align-items:center;justify-content:center;font-size:9px;font-family:JetBrains Mono,monospace;color:white;
       font-weight:700;">${s}</div>`
    ).join('');
  }

  // Mini win/loss donut
  _drawStatsDonut(data.win_pct || 0);

  // Monthly bars (last 6)
  _drawStatsMonthlyBars(data.monthly_pnl || []);

  // Weekday rows
  _drawWeekdayBars(data.weekday || []);
}

function _drawStatsDonut(winPct) {
  const canvas = document.getElementById('stats-donut-canvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const cx = 60, cy = 60, r = 48, t = 14;
  ctx.clearRect(0, 0, 120, 120);

  const lossPct = 100 - winPct;
  const start   = -Math.PI / 2;

  // Win arc
  ctx.beginPath();
  ctx.arc(cx, cy, r, start, start + (winPct/100)*Math.PI*2);
  ctx.strokeStyle = '#089981';
  ctx.lineWidth   = t;
  ctx.lineCap     = 'butt';
  ctx.stroke();

  // Loss arc
  ctx.beginPath();
  ctx.arc(cx, cy, r, start + (winPct/100)*Math.PI*2, start + Math.PI*2);
  ctx.strokeStyle = '#F23645';
  ctx.lineWidth   = t;
  ctx.stroke();

  // Center text
  ctx.font = 'bold 16px JetBrains Mono, monospace';
  ctx.fillStyle = '#D1D4DC';
  ctx.textAlign = 'center';
  ctx.fillText(winPct + '%', cx, cy + 4);
  ctx.font = '9px Share Tech Mono, monospace';
  ctx.fillStyle = '#6C7284';
  ctx.fillText('WIN RATE', cx, cy + 18);
}

function _drawStatsMonthlyBars(monthly) {
  const canvas = document.getElementById('stats-monthly-canvas');
  if (!canvas) return;
  const W = canvas.offsetWidth || 280;
  const H = 90;
  canvas.width  = W;
  canvas.height = H;
  const ctx = canvas.getContext('2d');
  ctx.clearRect(0, 0, W, H);
  if (!monthly.length) return;

  const maxAbs = Math.max(...monthly.map(m => Math.abs(m.pnl)), 1);
  const bw     = Math.floor((W - 20) / monthly.length) - 4;
  const midY   = H * 0.55;

  monthly.forEach((m, i) => {
    const x    = 10 + i * ((W - 20) / monthly.length);
    const barH = Math.abs(m.pnl) / maxAbs * (midY - 10);

    ctx.fillStyle = m.pnl >= 0 ? '#089981' : '#F23645';
    if (m.pnl >= 0) {
      ctx.fillRect(x, midY - barH, bw, barH);
    } else {
      ctx.fillRect(x, midY, bw, barH);
    }

    ctx.font = '9px Share Tech Mono, monospace';
    ctx.fillStyle = '#6C7284';
    ctx.textAlign = 'center';
    ctx.fillText(m.month, x + bw/2, H - 2);
    ctx.textAlign = 'left';
  });

  // Baseline
  ctx.strokeStyle = '#2B3139';
  ctx.lineWidth   = 1;
  ctx.beginPath(); ctx.moveTo(0, midY); ctx.lineTo(W, midY); ctx.stroke();
}

function _drawWeekdayBars(weekday) {
  const el = document.getElementById('stats-weekday-body');
  if (!el) return;
  el.innerHTML = weekday.map(d => {
    const total  = (d.wins + d.losses) || 1;
    const winPct = Math.round(d.wins / total * 100);
    return `<div style="display:flex;align-items:center;gap:8px;">
      <span style="font-family:Share Tech Mono,monospace;font-size:0.62rem;color:var(--dim);width:28px;">${d.day}</span>
      <div style="flex:1;height:8px;background:var(--p2);border-radius:4px;overflow:hidden;">
        <div style="width:${winPct}%;height:100%;background:linear-gradient(90deg,#089981,#0fbfa8);border-radius:4px;transition:width 0.5s;"></div>
      </div>
      <span style="font-family:JetBrains Mono,monospace;font-size:0.62rem;color:#089981;width:36px;text-align:right;">${winPct}%</span>
      <span style="font-family:Share Tech Mono,monospace;font-size:0.58rem;color:var(--dim);">${d.wins}W ${d.losses}L</span>
    </div>`;
  }).join('');
}

// ════════════════════════════════════════════════════
//  TAB 4: BEST / WORST TRADES
// ════════════════════════════════════════════════════
async function loadBestWorst(type) {
  _bwMode = type;

  // Update toggle button styles
  const btnBest  = document.getElementById('bw-btn-best');
  const btnWorst = document.getElementById('bw-btn-worst');
  if (btnBest && btnWorst) {
    if (type === 'best') {
      btnBest.style.background  = 'rgba(8,153,129,0.25)';
      btnBest.style.color       = '#089981';
      btnWorst.style.background = 'transparent';
      btnWorst.style.color      = '#6C7284';
    } else {
      btnWorst.style.background = 'rgba(242,54,69,0.2)';
      btnWorst.style.color      = '#F23645';
      btnBest.style.background  = 'transparent';
      btnBest.style.color       = '#6C7284';
    }
  }

  try {
    const resp = await fetch('/api/analytics_data?type=best_worst&mode=' + type);
    const data = resp.ok ? await resp.json() : null;
    _bwData = data || _mockBWData(type);
    _renderBWTable(_bwData, type);
  } catch(e) {
    _bwData = _mockBWData(type);
    _renderBWTable(_bwData, type);
  }
}

function _mockBWData(type) {
  const syms   = ['RELIANCE','TCS','INFY','HDFC','ICICI','SBIN','WIPRO','BAJAJ','MARUTI','HDFCBANK'];
  const trades = syms.map((sym, i) => {
    const entry = 1200 + Math.random() * 2000;
    const mul   = type === 'best' ? (1 + Math.random() * 0.25) : (1 - Math.random() * 0.15);
    const exit  = entry * mul;
    const pnl   = Math.round((exit - entry) * (10 + Math.floor(Math.random()*40)));
    const pct   = ((exit - entry) / entry * 100).toFixed(2);
    const rr    = type === 'best' ? (2 + Math.random() * 5).toFixed(2) : (-0.2 - Math.random()).toFixed(2);
    const eDate = '2025-' + String(Math.floor(Math.random()*11)+1).padStart(2,'0') + '-' + String(Math.floor(Math.random()*27)+1).padStart(2,'0');
    const xDate = '2025-' + String(Math.floor(Math.random()*11)+1).padStart(2,'0') + '-' + String(Math.floor(Math.random()*27)+1).padStart(2,'0');
    return { rank: i+1, symbol: sym, entry: entry.toFixed(2), exit: exit.toFixed(2), entry_date: eDate, exit_date: xDate, pnl, pct, rr, inv_type: Math.random()>0.5?'LONG':'SHORT' };
  });
  return { trades };
}

function _renderBWTable(data, type) {
  const body = document.getElementById('bw-table-body');
  if (!body) return;
  const isGood = type === 'best';
  body.innerHTML = (data.trades || []).map((t, i) => {
    const pnlCol = +t.pnl >= 0 ? '#089981' : '#F23645';
    const bg     = i % 2 === 0 ? 'transparent' : 'rgba(43,49,57,0.25)';
    return `<div onclick="showBWChart('${t.symbol}', '${t.entry_date}', '${t.exit_date}')"
      style="display:grid;grid-template-columns:40px 90px 80px 80px 100px 100px 100px 80px 70px 70px;
             padding:10px 14px;gap:8px;background:${bg};cursor:pointer;
             border-left:3px solid ${isGood?'#089981':'#F23645'};transition:background 0.15s;
             font-family:JetBrains Mono,monospace;font-size:0.7rem;"
      onmouseover="this.style.background='rgba(41,98,255,0.07)'"
      onmouseout="this.style.background='${bg}'">
      <div style="color:var(--dim);">${t.rank}</div>
      <div style="color:var(--text);font-weight:600;">${t.symbol}</div>
      <div style="color:var(--dim);">₹${t.entry}</div>
      <div style="color:var(--dim);">₹${t.exit}</div>
      <div style="color:var(--dim);font-size:0.65rem;">${t.entry_date}</div>
      <div style="color:var(--dim);font-size:0.65rem;">${t.exit_date}</div>
      <div style="color:${pnlCol};font-weight:700;">${+t.pnl>=0?'+':''}₹${Math.abs(t.pnl).toLocaleString('en-IN')}</div>
      <div style="color:${pnlCol};">${+t.pct>=0?'+':''}${t.pct}%</div>
      <div style="color:var(--gold);">${t.rr}</div>
      <div style="color:var(--dim);font-size:0.65rem;">${t.inv_type}</div>
    </div>`;
  }).join('');
}

async function showBWChart(symbol, entryDate, exitDate) {
  const wrap = document.getElementById('bw-mini-chart-wrap');
  const title = document.getElementById('bw-mini-title');
  if (!wrap) return;
  wrap.style.display = 'block';
  if (title) title.textContent = symbol + '  ·  ' + entryDate + ' → ' + exitDate;
  // Scroll to chart
  wrap.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  // Generate mock OHLC price data for the symbol in range
  const canvas = document.getElementById('bw-mini-canvas');
  if (!canvas) return;
  _drawMiniPriceChart(canvas, symbol, entryDate, exitDate);
}

function _drawMiniPriceChart(canvas, symbol, entryDate, exitDate) {
  const W = canvas.offsetWidth || 700;
  const H = 180;
  canvas.width  = W;
  canvas.height = H;
  const ctx = canvas.getContext('2d');
  ctx.clearRect(0, 0, W, H);

  // Mock price line
  const points = 60;
  const prices = [];
  let p = 1500 + Math.random() * 1000;
  for (let i = 0; i < points; i++) {
    p *= (1 + (Math.random() - 0.48) * 0.02);
    prices.push(Math.round(p));
  }

  const minP = Math.min(...prices) * 0.99;
  const maxP = Math.max(...prices) * 1.01;
  const rng  = maxP - minP || 1;
  const PAD  = { l:50, r:10, t:10, b:24 };
  const cW   = W - PAD.l - PAD.r;
  const cH   = H - PAD.t - PAD.b;
  const xOf  = i => PAD.l + (i / (points - 1)) * cW;
  const yOf  = v => PAD.t + cH - ((v - minP) / rng) * cH;

  // Grid
  for (let g = 0; g <= 3; g++) {
    const y = PAD.t + (g / 3) * cH;
    ctx.strokeStyle = '#2B3139'; ctx.lineWidth = 0.5;
    ctx.beginPath(); ctx.moveTo(PAD.l, y); ctx.lineTo(W - PAD.r, y); ctx.stroke();
    const v = maxP - (g / 3) * rng;
    ctx.font = '9px JetBrains Mono, monospace'; ctx.fillStyle = '#6C7284'; ctx.textAlign = 'right';
    ctx.fillText('₹' + Math.round(v), PAD.l - 2, y + 3);
  }

  // Entry / Exit vertical markers
  const ei = Math.floor(points * 0.15);
  const xi = Math.floor(points * 0.85);
  ctx.strokeStyle = 'rgba(8,153,129,0.5)'; ctx.lineWidth = 1; ctx.setLineDash([3,3]);
  ctx.beginPath(); ctx.moveTo(xOf(ei), PAD.t); ctx.lineTo(xOf(ei), H - PAD.b); ctx.stroke();
  ctx.strokeStyle = 'rgba(242,54,69,0.5)';
  ctx.beginPath(); ctx.moveTo(xOf(xi), PAD.t); ctx.lineTo(xOf(xi), H - PAD.b); ctx.stroke();
  ctx.setLineDash([]);

  // Price line
  ctx.beginPath();
  ctx.strokeStyle = '#2962FF'; ctx.lineWidth = 1.5;
  prices.forEach((v, i) => { i===0 ? ctx.moveTo(xOf(i), yOf(v)) : ctx.lineTo(xOf(i), yOf(v)); });
  ctx.stroke();

  // Markers
  ctx.fillStyle = '#089981';
  ctx.beginPath(); ctx.arc(xOf(ei), yOf(prices[ei]), 5, 0, Math.PI*2); ctx.fill();
  ctx.fillStyle = '#F23645';
  ctx.beginPath(); ctx.arc(xOf(xi), yOf(prices[xi]), 5, 0, Math.PI*2); ctx.fill();

  // Labels
  ctx.font = '9px Share Tech Mono, monospace'; ctx.textAlign = 'center';
  ctx.fillStyle = '#089981'; ctx.fillText('ENTRY', xOf(ei), PAD.t + 8);
  ctx.fillStyle = '#F23645'; ctx.fillText('EXIT',  xOf(xi), PAD.t + 8);
  ctx.textAlign = 'left';
}

// ════════════════════════════════════════════════════
//  TAB 5: SECTOR P&L
// ════════════════════════════════════════════════════
async function loadSectorPnl() {
  try {
    const resp = await fetch('/api/analytics_data?type=sector_pnl');
    const data = resp.ok ? await resp.json() : null;
    if (!data || !data.sectors || data.sectors.length === 0) {
      throw new Error("No closed trade records found");
    }
    _sectorData = data;
    _renderSectorTab(_sectorData);
  } catch(e) {
    _renderSectorError(e.message);
  }
}

function _renderSectorError(msg) {
  const tableBody = document.getElementById('sector-table-body');
  if (tableBody) {
    tableBody.innerHTML = `<div style="grid-column:1/-1;text-align:center;padding:24px;color:var(--red);font-family:Share Tech Mono,monospace;font-size:0.75rem;">⚠ Sector statistics unavailable: ${msg}</div>`;
  }
  const legend = document.getElementById('sector-donut-legend');
  if (legend) legend.innerHTML = '';
  const canvas = document.getElementById('sector-donut-canvas');
  if (canvas) {
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0,0,280,280);
    ctx.beginPath();
    ctx.arc(140, 130, 100, 0, Math.PI*2);
    ctx.strokeStyle = '#2B3139';
    ctx.lineWidth = 32;
    ctx.stroke();
    ctx.font = 'bold 12px JetBrains Mono, monospace';
    ctx.fillStyle = '#6C7284';
    ctx.textAlign = 'center';
    ctx.fillText('NO DATA', 140, 130);
  }
}

function _renderSectorTab(data) {
  _drawSectorDonut(data.sectors || []);
  _drawSectorBars(data.sectors || []);
  _renderSectorTable(data.sectors || []);
}

function _drawSectorDonut(sectors) {
  const canvas = document.getElementById('sector-donut-canvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const cx  = 140, cy = 130, R = 100, t = 32;
  ctx.clearRect(0, 0, 280, 280);

  const total = sectors.reduce((a,s) => a + Math.abs(s.net_pnl), 0) || 1;
  const COLORS_POS = ['#089981','#0fbfa8','#00e5c0','#26d4aa','#12b68c','#059e7a','#047d60','#035c47'];
  const COLORS_NEG = ['#F23645','#c9272f','#a01e25','#d94050','#e05060','#b02030','#802018','#601010'];

  let angle = -Math.PI / 2;
  sectors.forEach((s, i) => {
    const frac   = Math.abs(s.net_pnl) / total;
    const sweep  = frac * Math.PI * 2;
    const color  = s.net_pnl >= 0 ? COLORS_POS[i % COLORS_POS.length] : COLORS_NEG[i % COLORS_NEG.length];

    ctx.beginPath();
    ctx.arc(cx, cy, R, angle, angle + sweep);
    ctx.strokeStyle = color;
    ctx.lineWidth   = t;
    ctx.stroke();

    // Small gap
    angle += sweep + 0.03;
  });

  // Center
  ctx.font = 'bold 13px JetBrains Mono, monospace';
  ctx.fillStyle = '#D1D4DC';
  ctx.textAlign = 'center';
  const netTotal = sectors.reduce((a,s) => a + s.net_pnl, 0);
  ctx.fillText((netTotal >= 0 ? '+' : '') + '₹' + _kfmt(Math.abs(netTotal)), cx, cy);
  ctx.font = '10px Share Tech Mono, monospace';
  ctx.fillStyle = '#6C7284';
  ctx.fillText('NET P&L', cx, cy + 16);

  // Legend
  const legendEl = document.getElementById('sector-donut-legend');
  if (legendEl) {
    const COLORS_POS2 = ['#089981','#0fbfa8','#00e5c0','#26d4aa','#12b68c','#059e7a','#047d60','#035c47'];
    const COLORS_NEG2 = ['#F23645','#c9272f','#a01e25','#d94050','#e05060','#b02030','#802018','#601010'];
    legendEl.innerHTML = sectors.map((s, i) => {
      const color = s.net_pnl >= 0 ? COLORS_POS2[i % COLORS_POS2.length] : COLORS_NEG2[i % COLORS_NEG2.length];
      const fmtP  = (s.net_pnl >= 0 ? '+' : '') + '₹' + Math.abs(s.net_pnl).toLocaleString('en-IN');
      return `<div style="display:flex;justify-content:space-between;align-items:center;font-family:Share Tech Mono,monospace;font-size:0.62rem;">
        <div style="display:flex;align-items:center;gap:6px;">
          <div style="width:10px;height:10px;border-radius:50%;background:${color};flex-shrink:0;"></div>
          <span style="color:var(--dim);">${s.name}</span>
        </div>
        <span style="color:${s.net_pnl>=0?'#089981':'#F23645'};font-family:JetBrains Mono,monospace;">${fmtP}</span>
      </div>`;
    }).join('');
  }
}

function _drawSectorBars(sectors) {
  const canvas = document.getElementById('sector-bar-canvas');
  if (!canvas) return;
  const W = canvas.offsetWidth || 600;
  const H = 240;
  canvas.width  = W;
  canvas.height = H;
  const ctx = canvas.getContext('2d');
  ctx.clearRect(0, 0, W, H);

  const n    = sectors.length;
  const grpW = (W - 40) / n;
  const bw   = Math.min(grpW * 0.28, 20);
  const maxT = Math.max(...sectors.map(s => s.wins + s.losses), 1);
  const midY = H - 40;

  sectors.forEach((s, i) => {
    const gx = 20 + i * grpW + grpW * 0.1;

    // Wins bar
    const wH = (s.wins / maxT) * (midY - 20);
    ctx.fillStyle = '#089981';
    ctx.fillRect(gx, midY - wH, bw, wH);

    // Losses bar
    const lH = (s.losses / maxT) * (midY - 20);
    ctx.fillStyle = '#F23645';
    ctx.fillRect(gx + bw + 3, midY - lH, bw, lH);

    // Net P&L indicator dot
    const pnlW = bw * 2 + 3;
    const dotX = gx + pnlW / 2;
    ctx.fillStyle = s.net_pnl >= 0 ? '#089981' : '#F23645';
    ctx.beginPath();
    ctx.arc(dotX, midY + 8, 4, 0, Math.PI * 2);
    ctx.fill();

    // Sector label
    ctx.font = '9px Share Tech Mono, monospace';
    ctx.fillStyle = '#6C7284';
    ctx.textAlign = 'center';
    const shortName = s.name.length > 6 ? s.name.slice(0,6) : s.name;
    ctx.fillText(shortName, gx + pnlW / 2, H - 4);
    ctx.textAlign = 'left';
  });

  // Baseline
  ctx.strokeStyle = '#2B3139'; ctx.lineWidth = 1;
  ctx.beginPath(); ctx.moveTo(20, midY); ctx.lineTo(W - 20, midY); ctx.stroke();

  // Legend
  ctx.font = '9px Share Tech Mono, monospace';
  ctx.fillStyle = '#089981';
  ctx.fillRect(W - 100, 8, 10, 8);
  ctx.fillStyle = '#6C7284';
  ctx.fillText('Wins', W - 86, 16);
  ctx.fillStyle = '#F23645';
  ctx.fillRect(W - 60, 8, 10, 8);
  ctx.fillStyle = '#6C7284';
  ctx.fillText('Losses', W - 46, 16);
}

function _renderSectorTable(sectors) {
  const body = document.getElementById('sector-table-body');
  if (!body) return;
  body.innerHTML = sectors.map((s, i) => {
    const winPct = s.trades ? Math.round(s.wins / s.trades * 100) : 0;
    const fmtP   = v => (v>=0?'+':'-') + '₹' + Math.abs(v).toLocaleString('en-IN');
    const bg     = i % 2 === 0 ? 'transparent' : 'rgba(43,49,57,0.2)';
    return `<div style="display:grid;grid-template-columns:1fr 80px 80px 120px 120px;
                        padding:10px 16px;gap:8px;background:${bg};
                        border-left:3px solid ${s.net_pnl>=0?'#089981':'#F23645'};
                        font-family:JetBrains Mono,monospace;font-size:0.7rem;">
      <div style="color:var(--text);font-weight:600;">${s.name}</div>
      <div style="color:var(--dim);">${s.trades}</div>
      <div style="color:${winPct>=50?'#089981':'#F23645'};">${winPct}%</div>
      <div style="color:${s.net_pnl>=0?'#089981':'#F23645'};font-weight:700;">${fmtP(s.net_pnl)}</div>
      <div style="color:${s.avg_pnl>=0?'#089981':'#F23645'};">${fmtP(s.avg_pnl)}</div>
    </div>`;
  }).join('');
}

function exportSectorCSV() {
  if (!_sectorData || !_sectorData.sectors) return;
  const headers = ['Sector','Trades','Wins','Losses','Win%','Net P&L','Avg P&L'];
  const rows = _sectorData.sectors.map(s => [
    s.name, s.trades, s.wins, s.losses,
    Math.round(s.wins / s.trades * 100) + '%',
    s.net_pnl, s.avg_pnl
  ]);
  const csv = [headers, ...rows].map(r => r.join(',')).join('\n');
  const blob = new Blob([csv], { type: 'text/csv' });
  const a    = document.createElement('a');
  a.href     = URL.createObjectURL(blob);
  a.download = 'sector_pnl.csv';
  a.click();
}

// ════════════════════════════════════════════════════
//  EXPORT FUNCTIONS
// ════════════════════════════════════════════════════
function exportPDF() {
  window.print();
}

async function exportAnalyticsCSV() {
  try {
    const resp = await fetch('/api/portfolio_csv');
    if (resp.ok) {
      const blob = await resp.blob();
      const a    = document.createElement('a');
      a.href     = URL.createObjectURL(blob);
      a.download = 'analytics_portfolio.csv';
      a.click();
    } else {
      alert('CSV export failed. Please try again.');
    }
  } catch(e) {
    alert('CSV export error: ' + e.message);
  }
}

async function sendAnalyticsWhatsApp() {
  try {
    const resp = await fetch('/api/analytics_whatsapp_report', { method: 'POST' });
    const data = resp.ok ? await resp.json() : null;
    if (data && data.ok) {
      alert('✅ Analytics report sent to WhatsApp!');
    } else {
      alert('WhatsApp send failed: ' + (data && data.error ? data.error : 'Unknown error'));
    }
  } catch(e) {
    alert('WhatsApp send error: ' + e.message);
  }
}

// ════════════════════════════════════════════════════
//  BOOT — called when Analytics page is navigated to
// ════════════════════════════════════════════════════
// initAnalytics(); is called dynamically on page nav
"""
