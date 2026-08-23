"""
page_simons.py — Simons Quant Lab — FFT, autocorrelation, regime, backtest
"""


HTML = r"""
<!-- ═══════════ PAGE: SIMONS LAB ═══════════ -->
<div class="page" id="page-simons">
  <div class="topbar">
    <h2>SIMONS QUANT LAB</h2>
    <span class="page-tag">FFT · AUTOCORRELATION · REGIME · BACKTEST</span>
  </div>

  <div class="card" style="padding:10px 14px;margin-bottom:10px;">
    <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
      <label style="font-family:Share Tech Mono,monospace;font-size:0.6rem;color:var(--dim);letter-spacing:1px;flex-shrink:0;">SYMBOL</label>
      <select id="simons-sym" onchange="autoFetchPrice('simons-sym','simons-price','simons-price-badge')"
        style="background:var(--p2);border:1px solid var(--b2);color:var(--gold);padding:4px 8px;
        font-family:Share Tech Mono,monospace;font-size:0.82rem;font-weight:700;outline:none;min-width:140px;flex:1;"></select>
      <label style="font-family:Share Tech Mono,monospace;font-size:0.6rem;color:var(--dim);letter-spacing:1px;flex-shrink:0;">CURRENT PRICE</label>
      <input type="number" id="simons-price" value="" step="0.01"
        style="background:var(--p2);border:1px solid var(--b2);color:var(--cyan);padding:4px 8px;
        font-family:Share Tech Mono,monospace;font-size:0.82rem;width:100px;outline:none;flex-shrink:0;">
      <span id="simons-price-badge" style="font-family:Share Tech Mono,monospace;font-size:0.68rem;flex-shrink:0;"></span>
      <span id="simons-db-badge" style="font-family:Share Tech Mono,monospace;font-size:0.68rem;flex-shrink:0;"></span>
      
      <button class="btn" onclick="loadSimons()"
        style="padding:6px 20px;background:linear-gradient(135deg,rgba(204,136,255,0.15),rgba(102,0,204,0.1));
        border-color:var(--purple);color:var(--purple);font-size:0.72rem;white-space:nowrap;flex-shrink:0;margin-left:auto;">⚡ RUN ANALYSIS</button>
    </div>
  </div>
  <div id="simons-loading" class="loading" style="display:none;"><div class="spinner"></div>RUNNING FOURIER + REGIME + BACKTEST...</div>
  <div id="simons-content" style="display:none;">
    <div id="simons-banner"></div>
    
    <!-- Actionable Simons Signal Advisor -->
    <div class="card" style="border:1px solid var(--purple);background:linear-gradient(135deg,rgba(204,136,255,0.05),rgba(102,0,204,0.02));margin-bottom:14px;padding:16px;">
      <div class="card-title" style="color:var(--purple);display:flex;align-items:center;justify-content:space-between;margin-bottom:14px;">
        <span>💡 STRATEGY ADVISOR MATRIX (TIMEFRAME ALIGNED DIRECTIVES)</span>
        <span style="font-family:Share Tech Mono,monospace;font-size:0.62rem;color:var(--dim);">GARCH-VOL & CYCLE ADJUSTED</span>
      </div>
      
      <div style="display:grid;grid-template-columns:repeat(auto-fit, minmax(280px, 1fr));gap:16px;">
        <!-- Swing trades Column -->
        <div style="background:rgba(0,0,0,0.15);border:1px solid rgba(255,255,255,0.04);border-radius:4px;padding:12px;display:flex;flex-direction:column;gap:10px;">
          <div style="display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid rgba(255,255,255,0.06);padding-bottom:6px;">
            <strong style="color:var(--cyan);font-size:0.8rem;letter-spacing:1px;">📊 SWING (5-15 DAYS)</strong>
            <span id="simons-long-status" style="font-family:Orbitron,sans-serif;font-size:0.65rem;padding:2px 8px;border-radius:2px;font-weight:700;"></span>
          </div>
          <div id="simons-long-desc" style="font-size:0.75rem;color:var(--text);line-height:1.5;min-height:54px;"></div>
          <div style="display:flex;flex-direction:column;gap:6px;font-size:0.72rem;margin-top:auto;border-top:1px solid rgba(255,255,255,0.03);padding-top:8px;">
            <div style="display:flex;justify-content:space-between;"><span style="color:var(--dim);">Entry Target:</span><strong id="simons-long-entry" style="font-family:Share Tech Mono,monospace;color:var(--cyan);"></strong></div>
            <div style="display:flex;justify-content:space-between;"><span style="color:var(--dim);">Stop Loss:</span><strong id="simons-long-sl" style="color:var(--red);font-family:Share Tech Mono,monospace;"></strong></div>
            <div style="display:flex;justify-content:space-between;"><span style="color:var(--dim);">Target Profit:</span><strong id="simons-long-t1" style="color:var(--green);font-family:Share Tech Mono,monospace;"></strong></div>
            <div style="display:flex;justify-content:space-between;"><span style="color:var(--dim);">Hold / Date:</span><strong id="simons-long-hold" style="color:var(--cyan);font-family:Share Tech Mono,monospace;"></strong></div>
          </div>
        </div>

        <!-- Short-Term Column -->
        <div style="background:rgba(0,0,0,0.15);border:1px solid rgba(255,255,255,0.04);border-radius:4px;padding:12px;display:flex;flex-direction:column;gap:10px;">
          <div style="display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid rgba(255,255,255,0.06);padding-bottom:6px;">
            <strong style="color:var(--gold);font-size:0.8rem;letter-spacing:1px;">📈 SHORT-TERM (UP TO 3M)</strong>
            <span id="simons-short-status" style="font-family:Orbitron,sans-serif;font-size:0.65rem;padding:2px 8px;border-radius:2px;font-weight:700;"></span>
          </div>
          <div id="simons-short-desc" style="font-size:0.75rem;color:var(--text);line-height:1.5;min-height:54px;"></div>
          <div style="display:flex;flex-direction:column;gap:6px;font-size:0.72rem;margin-top:auto;border-top:1px solid rgba(255,255,255,0.03);padding-top:8px;">
            <div style="display:flex;justify-content:space-between;"><span style="color:var(--dim);">Entry Target:</span><strong id="simons-short-entry" style="font-family:Share Tech Mono,monospace;color:var(--cyan);"></strong></div>
            <div style="display:flex;justify-content:space-between;"><span style="color:var(--dim);">Stop Loss:</span><strong id="simons-short-sl" style="color:var(--red);font-family:Share Tech Mono,monospace;"></strong></div>
            <div style="display:flex;justify-content:space-between;"><span style="color:var(--dim);">Target Profit:</span><strong id="simons-short-t1" style="color:var(--green);font-family:Share Tech Mono,monospace;"></strong></div>
            <div style="display:flex;justify-content:space-between;"><span style="color:var(--dim);">Hold / Date:</span><strong id="simons-short-hold" style="color:var(--cyan);font-family:Share Tech Mono,monospace;"></strong></div>
          </div>
        </div>

        <!-- Long-Term Column -->
        <div style="background:rgba(0,0,0,0.15);border:1px solid rgba(255,255,255,0.04);border-radius:4px;padding:12px;display:flex;flex-direction:column;gap:10px;">
          <div style="display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid rgba(255,255,255,0.06);padding-bottom:6px;">
            <strong style="color:var(--purple);font-size:0.8rem;letter-spacing:1px;">🔮 LONG-TERM (3M+)</strong>
            <span id="simons-swing-status" style="font-family:Orbitron,sans-serif;font-size:0.65rem;padding:2px 8px;border-radius:2px;font-weight:700;"></span>
          </div>
          <div id="simons-swing-desc" style="font-size:0.75rem;color:var(--text);line-height:1.5;min-height:54px;"></div>
          <div style="display:flex;flex-direction:column;gap:6px;font-size:0.72rem;margin-top:auto;border-top:1px solid rgba(255,255,255,0.03);padding-top:8px;">
            <div style="display:flex;justify-content:space-between;"><span style="color:var(--dim);">Entry Target:</span><strong id="simons-swing-entry" style="font-family:Share Tech Mono,monospace;color:var(--cyan);"></strong></div>
            <div style="display:flex;justify-content:space-between;"><span style="color:var(--dim);">Stop Loss:</span><strong id="simons-swing-sl" style="color:var(--red);font-family:Share Tech Mono,monospace;"></strong></div>
            <div style="display:flex;justify-content:space-between;"><span style="color:var(--dim);">Target Profit:</span><strong id="simons-swing-t1" style="color:var(--green);font-family:Share Tech Mono,monospace;"></strong></div>
            <div style="display:flex;justify-content:space-between;"><span style="color:var(--dim);">Hold / Date:</span><strong id="simons-swing-hold" style="color:var(--cyan);font-family:Share Tech Mono,monospace;"></strong></div>
          </div>
        </div>
      </div>
    </div>

    <!-- Regime -->
    <div class="g2" style="margin-bottom:14px;">
      <div class="card">
        <div class="card-title" style="color:var(--purple);">🎯 MARKET REGIME</div>
        <div id="regime-display"></div>
      </div>
      <div class="card">
        <div class="card-title" style="color:var(--purple);">📊 BACKTEST RESULT (SWING)</div>
        <div id="backtest-display"></div>
      </div>
    </div>
    <!-- Fourier cycles -->
    <div class="card">
      <div class="card-title" style="color:var(--purple);">🌀 DOMINANT FOURIER CYCLES (hidden periodicities)</div>
      <p style="font-size:0.8rem;color:var(--text);margin-bottom:10px;">These are the cycles Simons would find. Strong cycles = real market memory. Planetary attribution shown where cycles match known periods.</p>
      <div class="trow hdr cycle-row2" style="grid-template-columns:70px 1fr 70px 80px 90px 90px;">
        <div>PERIOD</div><div>GANN LABEL</div><div>POWER%</div><div>PLANET</div><div>NEXT PEAK</div><div>NEXT TROUGH</div>
      </div>
      <div id="fourier-table"></div>
      <div style="margin-top:10px;padding:8px;background:rgba(0,0,0,0.3);font-family:Share Tech Mono,monospace;font-size:0.65rem;color:var(--dim);" id="fourier-meta"></div>
    </div>
    <!-- Fourier chart -->
    <div class="card" style="padding:0;">
      <div class="card-title" style="padding:12px 16px 0;color:var(--purple);">📉 CYCLE POWER SPECTRUM</div>
      <div class="chart-wrap" id="spectrum-wrap" style="height:200px;"><canvas id="spectrum-canvas"></canvas></div>
    </div>
    <!-- Autocorrelation -->
    <div class="card">
      <div class="card-title" style="color:var(--purple);">🔁 AUTOCORRELATION — SIGNIFICANT LAGS</div>
      <p style="font-size:0.8rem;color:var(--text);margin-bottom:10px;">
        Lags where price is predictive. <span class="bull">MOMENTUM</span> = positive ACF (trend continues).
        <span class="bear">MEAN REVERT</span> = negative ACF (price snaps back).
      </p>
      <div id="acf-table"></div>
      <div style="margin-top:10px;padding:8px;background:rgba(0,0,0,0.3);font-family:Share Tech Mono,monospace;font-size:0.65rem;color:var(--dim);" id="acf-meta"></div>
    </div>
    <!-- ACF chart -->
    <div class="card" style="padding:0;">
      <div class="card-title" style="padding:12px 16px 0;color:var(--purple);">📊 AUTOCORRELATION CHART</div>
      <div class="chart-wrap" id="acf-wrap" style="height:200px;"><canvas id="acf-canvas"></canvas></div>
    </div>
    <!-- 60-day Fourier Price Forecast (moved from Chart+S/R) -->
    <div class="card" style="padding:0;margin-top:14px;">
      <div class="card-title" style="padding:12px 16px 8px;color:var(--purple);">
        🔮 60-DAY FOURIER PRICE FORECAST
        <span style="font-size:0.62rem;color:var(--dim);font-weight:400;margin-left:10px;">
          — Reconstructed from dominant cycles · Simons-style extrapolation
        </span>
      </div>
      <div class="chart-wrap" id="forecast-chart-wrap" style="height:260px;">
        <canvas id="forecast-canvas"></canvas>
      </div>
    </div>
  </div>
</div>

"""


JS = r"""
async function loadSimons() {
  const sym=document.getElementById('simons-sym').value;
  let price=parseFloat(document.getElementById('simons-price').value)||0;
  if(!sym) return;

  refreshDbBadge(sym,'simons-db-badge');
  if(!price||GANN_DATE!==today){try{const px=await api('price',{symbol:sym,date:GANN_DATE});if(px.close){price=px.close;document.getElementById('simons-price').value=price;}}catch(e){}}
  loading('simons-loading', true);
  show('simons-content', false);
  try {
    const d = await api('quant', {
      symbol: sym, 
      price: price||'',
      signal_type: 'fourier',
      forward_days: '10'
    });
    renderSimons(d);
  } catch(e) {
    document.getElementById('simons-loading').innerHTML = `<div class="err">${e.message}</div>`;
  }
}

function renderSimons(d) {
  loading('simons-loading', false);
  show('simons-content');
  let bannerHtml = backtestBanner();
  if (d.data_source === "synthetic") {
    bannerHtml += `
      <div style="display:flex;align-items:center;gap:12px;padding:12px 18px;margin-bottom:14px;background:rgba(242,54,69,0.12);border:1px solid var(--red);border-radius:4px;font-family:'Share Tech Mono',monospace;font-size:0.75rem;line-height:1.4;">
        <span style="color:var(--red);font-size:1.2rem;font-weight:bold;margin-right:4px;">⚠️ WARNING:</span>
        <div style="flex:1;">
          <span style="color:var(--white);font-weight:700;letter-spacing:1px;text-transform:uppercase;">Simulated / Synthetic Data In Use</span><br>
          <span style="color:var(--dim);">This symbol has fewer than 60 days of real price history. All cycles, forecasts, and backtests shown are computed from <b>simulated mathematical model data</b> (fabricated cycle parameters), not real market history. Do not trade live capital based on these signals.</span>
        </div>
      </div>
    `;
  }
  document.getElementById('simons-banner').innerHTML = bannerHtml;

  const reg = d.regime||{};
  const btSwing = d.backtest_swing||{};
  const btShort = d.backtest_short||{};
  const btLong  = d.backtest_long||{};
  
  const bt  = btSwing; // default backtest display evaluates Swing (10d)
  const fou = d.fourier||{};
  const acf = d.autocorrelation||{};
  const garch = d.garch||{};
  const hmm = d.regime?.hmm||{};

  // Regime
  const regColor = {STRONG_BULL:'var(--green)',WEAK_BULL:'#8fea80',SIDEWAYS:'var(--gold)',
    WEAK_BEAR:'var(--orange)',STRONG_BEAR:'var(--red)',HIGH_VOLATILITY:'var(--orange)'}[reg.regime]||'var(--t2)';
  const m = reg.metrics||{};

  let hmmHtml = '';
  if (hmm.regime) {
    const hmmColor = {HMM_BULL:'var(--green)',HMM_SIDEWAYS:'var(--gold)',HMM_BEAR:'var(--red)'}[hmm.regime]||'var(--t2)';
    
    // Draw transition matrix
    let tmHtml = '<div style="display:grid;grid-template-columns:repeat(3, 1fr);gap:4px;margin-top:6px;font-family:Share Tech Mono,monospace;font-size:0.65rem;text-align:center;">';
    (hmm.transition_matrix || []).forEach((row, i) => {
      row.forEach((val, j) => {
        const cellColor = i === j ? 'rgba(0,212,255,0.1)' : 'transparent';
        tmHtml += `<div style="background:${cellColor};border:1px solid var(--border);padding:2px;border-radius:2px;">${(val*100).toFixed(0)}%</div>`;
      });
    });
    tmHtml += '</div>';

    hmmHtml = `
      <div style="margin-top:14px;border-top:1px dashed var(--border);padding-top:12px;">
        <div style="font-family:Share Tech Mono,monospace;font-size:0.62rem;color:var(--dim);letter-spacing:1px;text-transform:uppercase;margin-bottom:6px;">Gaussian HMM State (State-Space Mode)</div>
        <div style="display:flex;align-items:center;justify-content:space-between;background:rgba(0,0,0,0.15);padding:6px 10px;border-left:3px solid ${hmmColor};">
          <span style="font-family:Orbitron,sans-serif;font-weight:700;color:${hmmColor};font-size:0.85rem;letter-spacing:1px;">${hmm.regime.replace('_',' ')}</span>
          <span style="font-family:Share Tech Mono,monospace;font-size:0.68rem;color:var(--dim);">Iter EM: 20</span>
        </div>
        <div style="font-family:Share Tech Mono,monospace;font-size:0.62rem;color:var(--dim);margin-top:10px;letter-spacing:1px;">HMM STATE TRANSITION MATRIX</div>
        ${tmHtml}
      </div>
    `;
  }

  let garchHtml = '';
  if (garch.forecasted_vol_ann) {
    garchHtml = `
      <div style="margin-top:14px;border-top:1px dashed var(--border);padding-top:12px;">
        <div style="font-family:Share Tech Mono,monospace;font-size:0.62rem;color:var(--dim);letter-spacing:1px;text-transform:uppercase;margin-bottom:6px;">GARCH(1,1) Volatility Predictor</div>
        <div style="display:flex;align-items:baseline;justify-content:space-between;background:rgba(0,0,0,0.15);padding:6px 10px;">
          <span style="font-family:Share Tech Mono,monospace;font-size:0.75rem;color:var(--dim);">Forecasted Vol (Ann):</span>
          <span style="font-family:Orbitron,sans-serif;font-weight:900;color:var(--cyan);font-size:1.1rem;">${garch.forecasted_vol_ann}%</span>
        </div>
        <div style="font-family:Share Tech Mono,monospace;font-size:0.6rem;color:var(--dim);margin-top:6px;line-height:1.4;">
          &omega;=${garch.omega.toFixed(6)} | &alpha;=${garch.alpha.toFixed(2)} | &beta;=${garch.beta.toFixed(2)}<br>
          Tomorrow's Variance: ${garch.last_variance.toFixed(8)}
        </div>
      </div>
    `;
  }

  document.getElementById('regime-display').innerHTML = `
    <div style="border:2px solid ${regColor};padding:14px;text-align:center;margin-bottom:12px;">
      <div style="font-family:Orbitron,sans-serif;font-size:1.2rem;font-weight:700;color:${regColor};letter-spacing:3px;">${(reg.regime||'--').replace(/_/g,' ')}</div>
      <div style="font-family:Share Tech Mono,monospace;font-size:0.65rem;color:var(--dim);margin-top:6px;">CONFIDENCE: ${reg.confidence||'--'}% | BIAS: ${reg.bias||'--'}</div>
    </div>
    <div style="font-size:0.8rem;color:var(--t2);line-height:1.6;padding:8px;background:rgba(0,0,0,0.2);">${reg.signal_advice||''}</div>
    <div class="g2" style="margin-top:10px;">
      <div class="stat"><span class="val" style="font-size:1rem;">${m.sma20||'--'}</span><span class="lbl">SMA 20</span></div>
      <div class="stat"><span class="val" style="font-size:1rem;">${m.sma200||'--'}</span><span class="lbl">SMA 200</span></div>
      <div class="stat"><span class="val" style="font-size:1rem;color:${(m.ret_20d||0)>=0?'var(--green)':'var(--red)'};">${m.ret_20d||'--'}%</span><span class="lbl">20D RETURN</span></div>
      <div class="stat"><span class="val" style="font-size:1rem;">${m.annual_vol_pct||'--'}%</span><span class="lbl">ANN VOL</span></div>
    </div>
    ${hmmHtml}
    ${garchHtml}
  `;

  // Backtest Display (Swing 10d by default)
  const valid = bt.is_statistically_valid;
  const bColor = valid ? 'var(--green)' : bt.hit_rate_pct > 50 ? 'var(--gold)' : 'var(--red)';
  
  let kellyHtml = '';
  if (bt.kelly) {
    kellyHtml = `
      <div style="margin-top:14px;border-top:1px dashed var(--border);padding-top:12px;text-align:left;">
        <div style="font-family:Share Tech Mono,monospace;font-size:0.62rem;color:var(--dim);letter-spacing:1px;text-transform:uppercase;margin-bottom:6px;">OPTIMAL KELLY POSITION SIZING</div>
        <div class="g2" style="gap:8px;">
          <div style="background:rgba(0,212,255,0.06);border:1px solid rgba(0,212,255,0.15);padding:8px;text-align:center;border-radius:4px;">
            <div style="font-family:Orbitron,sans-serif;font-size:1rem;color:var(--cyan);font-weight:700;">${bt.kelly.full_kelly_pct}%</div>
            <div style="font-family:Share Tech Mono,monospace;font-size:0.55rem;color:var(--dim);margin-top:2px;">FULL KELLY</div>
          </div>
          <div style="background:rgba(8,153,129,0.06);border:1px solid rgba(8,153,129,0.15);padding:8px;text-align:center;border-radius:4px;">
            <div style="font-family:Orbitron,sans-serif;font-size:1rem;color:var(--green);font-weight:700;">${bt.kelly.half_kelly_pct}%</div>
            <div style="font-family:Share Tech Mono,monospace;font-size:0.55rem;color:var(--dim);margin-top:2px;">HALF KELLY</div>
          </div>
        </div>
        <div style="font-family:Share Tech Mono,monospace;font-size:0.6rem;color:var(--dim);margin-top:8px;text-align:center;">
          Payoff Ratio (Win/Loss Avg): <strong>${bt.kelly.payoff_ratio}</strong>
        </div>
      </div>
    `;
  }

  document.getElementById('backtest-display').innerHTML = `
    <div style="text-align:center;padding:12px;border:1px solid ${bColor};background:rgba(0,0,0,0.2);margin-bottom:10px;">
      <div style="font-family:Orbitron,sans-serif;font-size:1.3rem;color:${bColor};font-weight:900;">${bt.hit_rate_pct || 0}%</div>
      <div style="font-family:Share Tech Mono,monospace;font-size:0.6rem;color:var(--dim);margin-top:4px;">HIT RATE (Fourier Trough - 10d)</div>
    </div>
    <div style="font-family:Share Tech Mono,monospace;font-size:0.68rem;line-height:1.7;color:var(--t2);">
      SIGNALS TESTED: <strong>${bt.n_signals || 0}</strong><br>
      AVG RETURN: <strong style="color:${(bt.avg_return_pct||0)>0?'var(--green)':'var(--red)'};">${bt.avg_return_pct||0}%</strong><br>
      SHARPE RATIO: <strong>${bt.sharpe_ratio||0}</strong><br>
      P-VALUE: <strong style="color:${(bt.p_value||1)<0.05?'var(--green)':'var(--red)'};">${bt.p_value||1}</strong><br>
      EXPECTANCY: <strong>${bt.expectancy_pct||0}%</strong>
    </div>
    <div style="margin-top:10px;padding:8px;background:rgba(0,0,0,0.3);font-family:Share Tech Mono,monospace;font-size:0.65rem;color:${bColor};">${bt.simons_verdict||''}</div>
    ${kellyHtml}`;

  // ── Strategy Advisor Matrix Calculation ──
  const longStatus = document.getElementById('simons-long-status');
  const longDesc = document.getElementById('simons-long-desc');
  const longEntry = document.getElementById('simons-long-entry');
  const longSl = document.getElementById('simons-long-sl');
  const longT1 = document.getElementById('simons-long-t1');
  const longHold = document.getElementById('simons-long-hold');

  const shortStatus = document.getElementById('simons-short-status');
  const shortDesc = document.getElementById('simons-short-desc');
  const shortEntry = document.getElementById('simons-short-entry');
  const shortSl = document.getElementById('simons-short-sl');
  const shortT1 = document.getElementById('simons-short-t1');
  const shortHold = document.getElementById('simons-short-hold');

  const swingStatus = document.getElementById('simons-swing-status');
  const swingDesc = document.getElementById('simons-swing-desc');
  const swingEntry = document.getElementById('simons-swing-entry');
  const swingSl = document.getElementById('simons-swing-sl');
  const swingT1 = document.getElementById('simons-swing-t1');
  const swingHold = document.getElementById('simons-swing-hold');

  const curPrice = d.current_price || 0;
  
  const garchVol = (garch.forecasted_vol_ann || reg.metrics?.annual_vol_pct || 20) / 100.0;
  const dailyVol = garchVol / Math.sqrt(252);
  const slPct = Math.max(0.015, dailyVol * 1.5);

  // Time base values
  const baseDateStr = GANN_DATE || today.isoformat();
  
  const getFutureDate = (startStr, days) => {
    const dObj = new Date(startStr);
    const calendarDays = Math.round(days * 1.4);
    dObj.setDate(dObj.getDate() + calendarDays);
    return dObj.toISOString().slice(0, 10);
  };

  // Find nearest support / resistance for swings
  const supports = d.support_resistance?.supports || [];
  const resistances = d.support_resistance?.resistances || [];
  let nearSup = curPrice * 0.985;
  let nearRes = curPrice * 1.015;
  
  const supsBelow = supports.filter(s => s.price < curPrice).sort((a,b) => b.price - a.price);
  if (supsBelow.length) nearSup = supsBelow[0].price;
  
  const resAbove = resistances.filter(r => r.price > curPrice).sort((a,b) => a.price - b.price);
  if (resAbove.length) nearRes = resAbove[0].price;

  // 1. SWING TRADES (5-15 Days)
  const isShortTermBull = reg.bias === 'BUY_DIPS' || reg.regime === 'STRONG_BULL' || reg.regime === 'WEAK_BULL';
  const isShortTermBear = reg.bias === 'SELL_RALLIES' || reg.regime === 'STRONG_BEAR' || reg.regime === 'WEAK_BEAR';
  const swingEdge = btSwing.is_statistically_valid || (btSwing.hit_rate_pct > 53 && btSwing.p_value < 0.15);
  
  if (isShortTermBull && swingEdge) {
    longStatus.textContent = `BUY / LONG (${btSwing.hit_rate_pct}% HR)`;
    longStatus.style.color = "var(--green)";
    longStatus.style.background = "rgba(8,153,129,0.15)";
    longStatus.style.border = "1px solid var(--green)";
    longDesc.innerHTML = `Short-term fourier trough bottoming. Buy near local support (₹${nearSup.toFixed(0)}) with <strong>Half-Kelly size ${btSwing.kelly?.half_kelly_pct || 0}%</strong>.`;
    longEntry.textContent = `₹${nearSup.toFixed(2)}`;
    longSl.textContent = `₹${(nearSup * (1 - slPct)).toFixed(2)}`;
    longT1.textContent = `₹${nearRes.toFixed(2)}`;
    longHold.textContent = `10d / ${getFutureDate(baseDateStr, 10)}`;
  } else if (isShortTermBear && swingEdge) {
    longStatus.textContent = `SELL / SHORT (${btSwing.hit_rate_pct}% HR)`;
    longStatus.style.color = "var(--red)";
    longStatus.style.background = "rgba(242,54,69,0.15)";
    longStatus.style.border = "1px solid var(--red)";
    longDesc.innerHTML = `Short-term fourier peak rollover. Sell near local resistance (₹${nearRes.toFixed(0)}) with <strong>Half-Kelly size ${btSwing.kelly?.half_kelly_pct || 0}%</strong>.`;
    longEntry.textContent = `₹${nearRes.toFixed(2)}`;
    longSl.textContent = `₹${(nearRes * (1 + slPct)).toFixed(2)}`;
    longT1.textContent = `₹${nearSup.toFixed(2)}`;
    longHold.textContent = `10d / ${getFutureDate(baseDateStr, 10)}`;
  } else {
    longStatus.textContent = "STAY FLAT";
    longStatus.style.color = "var(--gold)";
    longStatus.style.background = "rgba(255,152,0,0.15)";
    longStatus.style.border = "1px solid var(--gold)";
    longDesc.innerHTML = `Sideways range trading or weak swing edge (Hit Rate ${btSwing.hit_rate_pct || 0}%). Reversion advised: Buy supports, sell resistance.`;
    longEntry.textContent = `₹${nearSup.toFixed(2)}`;
    longSl.textContent = `₹${(nearSup * 0.985).toFixed(2)}`;
    longT1.textContent = `₹${nearRes.toFixed(2)}`;
    longHold.textContent = `10d / ${getFutureDate(baseDateStr, 10)}`;
  }

  // 2. SHORT-TERM POSITION (Up to 3 Months)
  const isMedTermBull = hmm.regime === 'HMM_BULL' || reg.regime === 'STRONG_BULL' || reg.regime === 'WEAK_BULL';
  const isMedTermBear = hmm.regime === 'HMM_BEAR' || reg.regime === 'STRONG_BEAR' || reg.regime === 'WEAK_BEAR';
  const shortEdge = btShort.is_statistically_valid || (btShort.hit_rate_pct > 53 && btShort.p_value < 0.15);
  
  if (isMedTermBull && shortEdge) {
    shortStatus.textContent = `BUY / LONG (${btShort.hit_rate_pct}% HR)`;
    shortStatus.style.color = "var(--green)";
    shortStatus.style.background = "rgba(8,153,129,0.15)";
    shortStatus.style.border = "1px solid var(--green)";
    shortDesc.innerHTML = `State-space is Bullish. 45d backtest hit rate is <strong>${btShort.hit_rate_pct}%</strong> (Sharpe ${btShort.sharpe_ratio}). Rec: <strong>Half-Kelly size ${btShort.kelly?.half_kelly_pct || 0}%</strong>.`;
    shortEntry.textContent = `₹${curPrice.toFixed(2)}`;
    shortSl.textContent = `₹${(curPrice * (1 - slPct * 1.5)).toFixed(2)}`;
    shortT1.textContent = `₹${(curPrice * (1 + slPct * 3.0)).toFixed(2)}`;
    shortHold.textContent = `45d / ${getFutureDate(baseDateStr, 45)}`;
  } else if (isMedTermBear && shortEdge) {
    shortStatus.textContent = `SELL / SHORT (${btShort.hit_rate_pct}% HR)`;
    shortStatus.style.color = "var(--red)";
    shortStatus.style.background = "rgba(242,54,69,0.15)";
    shortStatus.style.border = "1px solid var(--red)";
    shortDesc.innerHTML = `State-space is Bearish. 45d backtest hit rate is <strong>${btShort.hit_rate_pct}%</strong>. Rec: <strong>Half-Kelly size ${btShort.kelly?.half_kelly_pct || 0}%</strong>.`;
    shortEntry.textContent = `₹${curPrice.toFixed(2)}`;
    shortSl.textContent = `₹${(curPrice * (1 + slPct * 1.5)).toFixed(2)}`;
    shortT1.textContent = `₹${(curPrice * (1 - slPct * 3.0)).toFixed(2)}`;
    shortHold.textContent = `45d / ${getFutureDate(baseDateStr, 45)}`;
  } else {
    shortStatus.textContent = "STAY FLAT";
    shortStatus.style.color = "var(--gold)";
    shortStatus.style.background = "rgba(255,152,0,0.15)";
    shortStatus.style.border = "1px solid var(--gold)";
    shortDesc.innerHTML = `No clear 45-day position trend edge (Hit Rate ${btShort.hit_rate_pct || 0}%). Stay flat.`;
    shortEntry.textContent = "—";
    shortSl.textContent = "—";
    shortT1.textContent = "—";
    shortHold.textContent = "—";
  }

  // 3. LONG-TERM POSITION (3+ Months)
  const isLongTermBull = (curPrice > m.sma200) && (hmm.regime !== 'HMM_BEAR');
  const isLongTermBear = (curPrice < m.sma200) && (hmm.regime !== 'HMM_BULL');
  const longEdge = btLong.is_statistically_valid || (btLong.hit_rate_pct > 53 && btLong.p_value < 0.15);
  
  if (isLongTermBull && longEdge) {
    swingStatus.textContent = `BUY / LONG (${btLong.hit_rate_pct}% HR)`;
    swingStatus.style.color = "var(--green)";
    swingStatus.style.background = "rgba(8,153,129,0.15)";
    swingStatus.style.border = "1px solid var(--green)";
    swingDesc.innerHTML = `Structural uptrend above SMA 200. 90d backtest hit rate is <strong>${btLong.hit_rate_pct}%</strong> (Sharpe ${btLong.sharpe_ratio}). Rec: <strong>Half-Kelly size ${btLong.kelly?.half_kelly_pct || 0}%</strong>.`;
    swingEntry.textContent = `₹${curPrice.toFixed(2)}`;
    swingSl.textContent = `₹${(curPrice * 0.92).toFixed(2)}`;
    swingT1.textContent = `₹${(curPrice * 1.15).toFixed(2)}`;
    swingHold.textContent = `90d / ${getFutureDate(baseDateStr, 90)}`;
  } else if (isLongTermBear && longEdge) {
    swingStatus.textContent = `SELL / SHORT (${btLong.hit_rate_pct}% HR)`;
    swingStatus.style.color = "var(--red)";
    swingStatus.style.background = "rgba(242,54,69,0.15)";
    swingStatus.style.border = "1px solid var(--red)";
    swingDesc.innerHTML = `Structural bear trend below SMA 200. 90d backtest hit rate is <strong>${btLong.hit_rate_pct}%</strong>. Rec: <strong>Half-Kelly size ${btLong.kelly?.half_kelly_pct || 0}%</strong>.`;
    swingEntry.textContent = `₹${curPrice.toFixed(2)}`;
    swingSl.textContent = `₹${(curPrice * 1.08).toFixed(2)}`;
    swingT1.textContent = `₹${(curPrice * 0.85).toFixed(2)}`;
    swingHold.textContent = `90d / ${getFutureDate(baseDateStr, 90)}`;
  } else {
    swingStatus.textContent = "STAY FLAT";
    swingStatus.style.color = "var(--gold)";
    swingStatus.style.background = "rgba(255,152,0,0.15)";
    swingStatus.style.border = "1px solid var(--gold)";
    swingDesc.innerHTML = `No clear 90-day structural edge (Hit Rate ${btLong.hit_rate_pct || 0}%). Stay flat or hedge portfolio.`;
    swingEntry.textContent = "—";
    swingSl.textContent = "—";
    swingT1.textContent = "—";
    swingHold.textContent = "—";
  }

  // Fourier table
  let ft = '';
  (fou.dominant_cycles||[]).forEach((c,i) => {
    const isStrong = c.strength_pct > 10;
    ft += `<div class="trow cycle-row2" style="grid-template-columns:70px 1fr 70px 80px 90px 90px;${isStrong?'background:rgba(204,136,255,0.03);':''}">
      <div style="font-family:Share Tech Mono,monospace;font-weight:600;color:${isStrong?'var(--purple)':'var(--t2)'};">${c.period_days}d</div>
      <div style="font-size:0.8rem;">${c.gann_label}</div>
      <div style="font-family:Share Tech Mono,monospace;font-size:0.72rem;color:var(--gold);">${c.strength_pct}%</div>
      <div style="font-size:0.75rem;color:${pcolor(c.planetary_ruler.split(' ')[0])};">${c.planetary_ruler.split('(')[0].trim()}</div>
      <div style="font-family:Share Tech Mono,monospace;font-size:0.7rem;color:var(--green);">+${c.days_to_next_peak}d</div>
      <div style="font-family:Share Tech Mono,monospace;font-size:0.7rem;color:var(--red);">+${c.days_to_next_trough}d</div>
    </div>`;
  });
  document.getElementById('fourier-table').innerHTML = ft;
  document.getElementById('fourier-meta').textContent =
    `Trend: ${fou.trend_direction||'--'} | ${fou.trend_per_day||'--'}/day | R²=${fou.r_squared||'--'} | ${fou.method||''}`;

  // Autocorrelation table
  let at = '';
  const sigLags = acf.significant_lags || [];
  sigLags.slice(0,15).forEach(l => {
    const dc = l.direction === 'MOMENTUM' ? 'var(--green)' : 'var(--red)';
    at += `<div class="trow" style="grid-template-columns:50px 70px 110px 80px 1fr;font-size:0.8rem;">
      <div style="font-family:Share Tech Mono,monospace;font-weight:600;color:var(--cyan);">${l.lag}d</div>
      <div style="font-family:Share Tech Mono,monospace;font-size:0.72rem;color:${(l.acf||0)>0?'var(--green)':'var(--red)'};">${(l.acf||0).toFixed(4)}</div>
      <div style="color:${dc};font-family:Share Tech Mono,monospace;font-size:0.68rem;">${l.direction}</div>
      <div><span class="badge ${l.strength==='STRONG'?'bg':'bd'}">${l.strength}</span></div>
      <div style="font-size:0.78rem;color:var(--text);">${l.gann_label} · ${l.planet}</div>
    </div>`;
  });
  if (!at) at = '<div style="padding:10px;color:var(--dim);">No significant lags found</div>';
  document.getElementById('acf-table').innerHTML = at;
  document.getElementById('acf-meta').textContent =
    `${acf.interpretation||''} | Significant lags: ${acf.n_significant||0} | Ljung-Box Q: ${acf.ljung_box_q||'--'}`;

  // Charts
  drawSpectrumChart('spectrum-canvas', (fou.dominant_cycles||[]).slice(0,8));
  drawAcfChart('acf-canvas', acf.autocorrelations||[], acf.sig_threshold||0);

  // 60-day Fourier forecast
  const forecast60 = (fou.forecast_60d || []);
  const fPrice = d.support_resistance?.current_price || d.current_price || curPrice || 0;
  if (forecast60.length && fPrice) {
    const fdates  = forecast60.map(f => f[0]);
    const fprices = forecast60.map(f => f[1]);
    drawForecastChart('forecast-canvas', 'forecast-chart-wrap', fdates, fprices, fPrice);
  } else {
    const fc = document.getElementById('forecast-canvas');
    if (fc) {
      const wrap = document.getElementById('forecast-chart-wrap');
      fc.width  = wrap ? wrap.clientWidth  : 800;
      fc.height = 260;
      const ctx2 = fc.getContext('2d');
      ctx2.fillStyle = '#071219';
      ctx2.fillRect(0, 0, fc.width, fc.height);
      ctx2.fillStyle = '#3a5a70';
      ctx2.font = '13px Share Tech Mono';
      ctx2.textAlign = 'center';
      ctx2.fillText('Run analysis to see 60-day Fourier forecast', fc.width/2, fc.height/2);
    }
  }
}

function setupCanvas(canvasId, wrapId) {
  const wrap  = document.getElementById(wrapId);
  const canvas = document.getElementById(canvasId);
  const W = wrap.clientWidth || 800;
  const W_fixed = W < 100 ? 800 : W; // Prevent zero dimensions in tab changes
  const H = wrap.clientHeight || 420;
  const H_fixed = H < 100 ? 420 : H;
  canvas.width  = W_fixed;
  canvas.height = H_fixed;
  canvas.style.width  = W_fixed + 'px';
  canvas.style.height = H_fixed + 'px';
  return {canvas, ctx: canvas.getContext('2d'), W: W_fixed, H: H_fixed};
}

function drawPriceChart(cid, wid, dates, closes, highs, lows, sma20, sma50, sma200, supports, resistances, currentPrice) {
  const {ctx, W, H} = setupCanvas(cid, wid);
  const PAD = {top:20, right:80, bottom:40, left:70};
  const cW = W - PAD.left - PAD.right;
  const cH = H - PAD.top  - PAD.bottom;

  ctx.fillStyle = '#071219';
  ctx.fillRect(0,0,W,H);

  if (!closes.length) {
    ctx.fillStyle = '#3a5a70';
    ctx.font = '14px Share Tech Mono';
    ctx.textAlign = 'center';
    ctx.fillText('NO DATA', W/2, H/2);
    return;
  }

  const allVals = [...closes, ...highs, ...lows,
    ...supports.map(s=>s.price), ...resistances.map(r=>r.price)];
  const minV = Math.min(...allVals) * 0.995;
  const maxV = Math.max(...allVals) * 1.005;
  const xScale = i => PAD.left + (i / (closes.length-1)) * cW;
  const yScale = v => PAD.top + cH - ((v - minV) / (maxV - minV)) * cH;

  ctx.strokeStyle = 'rgba(13,34,51,0.8)';
  ctx.lineWidth = 1;
  for (let i=0; i<=5; i++) {
    const y = PAD.top + (i/5)*cH;
    ctx.beginPath(); ctx.moveTo(PAD.left, y); ctx.lineTo(PAD.left+cW, y); ctx.stroke();
    const val = maxV - (i/5)*(maxV-minV);
    ctx.fillStyle = '#3a5a70';
    ctx.font = '10px Share Tech Mono';
    ctx.textAlign = 'right';
    ctx.fillText(val.toFixed(0), PAD.left-5, y+3);
  }

  supports.forEach(s => {
    const y = yScale(s.price);
    ctx.strokeStyle = s.strength==='STRONG' ? 'rgba(0,255,136,0.6)' : 'rgba(0,255,136,0.3)';
    ctx.lineWidth = s.strength==='STRONG' ? 1.5 : 1;
    ctx.setLineDash([4,4]);
    ctx.beginPath(); ctx.moveTo(PAD.left, y); ctx.lineTo(PAD.left+cW, y); ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle = 'rgba(0,255,136,0.7)';
    ctx.font = '9px Share Tech Mono';
    ctx.textAlign = 'left';
    ctx.fillText(s.price.toFixed(0), PAD.left+cW+2, y+3);
  });
  resistances.forEach(r => {
    const y = yScale(r.price);
    ctx.strokeStyle = r.strength==='STRONG' ? 'rgba(255,51,85,0.6)' : 'rgba(255,51,85,0.3)';
    ctx.lineWidth = r.strength==='STRONG' ? 1.5 : 1;
    ctx.setLineDash([4,4]);
    ctx.beginPath(); ctx.moveTo(PAD.left, y); ctx.lineTo(PAD.left+cW, y); ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle = 'rgba(255,51,85,0.7)';
    ctx.font = '9px Share Tech Mono';
    ctx.textAlign = 'left';
    ctx.fillText(r.price.toFixed(0), PAD.left+cW+2, y+3);
  });

  const drawLine = (arr, color, alpha=0.6) => {
    if (!arr.length) return;
    ctx.strokeStyle = color;
    ctx.globalAlpha = alpha;
    ctx.lineWidth = 1.2;
    ctx.beginPath();
    arr.forEach((v,i) => {
      if (!v) return;
      i===0 ? ctx.moveTo(xScale(i), yScale(v)) : ctx.lineTo(xScale(i), yScale(v));
    });
    ctx.stroke();
    ctx.globalAlpha = 1;
  };
  drawLine(sma200, '#DEB887', 0.5);
  drawLine(sma50,  '#B5B5FF', 0.6);
  drawLine(sma20,  '#7FFFD4', 0.65);

  ctx.fillStyle = 'rgba(0,212,255,0.04)';
  ctx.beginPath();
  ctx.moveTo(xScale(0), yScale(closes[0]));
  closes.forEach((c,i) => ctx.lineTo(xScale(i), yScale(c)));
  ctx.lineTo(xScale(closes.length-1), yScale(minV));
  ctx.lineTo(xScale(0), yScale(minV));
  ctx.closePath();
  ctx.fill();

  ctx.strokeStyle = '#00d4ff';
  ctx.lineWidth = 1.8;
  ctx.shadowColor = '#00d4ff';
  ctx.shadowBlur = 3;
  ctx.beginPath();
  closes.forEach((c,i) => i===0 ? ctx.moveTo(xScale(i),yScale(c)) : ctx.lineTo(xScale(i),yScale(c)));
  ctx.stroke();
  ctx.shadowBlur = 0;

  if (currentPrice) {
    const cy = yScale(currentPrice);
    ctx.strokeStyle = 'rgba(255,204,0,0.8)';
    ctx.lineWidth = 1.5;
    ctx.setLineDash([3,3]);
    ctx.beginPath(); ctx.moveTo(PAD.left,cy); ctx.lineTo(PAD.left+cW,cy); ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle = 'rgba(255,204,0,0.9)';
    ctx.font = 'bold 10px Share Tech Mono';
    ctx.textAlign = 'right';
    ctx.fillText('▶ ' + currentPrice.toLocaleString(), PAD.left+cW-2, cy-3);
  }

  ctx.fillStyle = '#3a5a70';
  ctx.font = '9px Share Tech Mono';
  ctx.textAlign = 'center';
  const step = Math.floor(dates.length / 6);
  for (let i=0; i<dates.length; i+=step) {
    ctx.fillText(dates[i].slice(5), xScale(i), H-PAD.bottom+14);
  }

  const legend = [['Price','#00d4ff'],['SMA20','#7FFFD4'],['SMA50','#B5B5FF'],['SMA200','#DEB887']];
  legend.forEach(([label,color],i) => {
    ctx.fillStyle = color;
    ctx.fillRect(PAD.left + i*80, 5, 12, 2);
    ctx.fillStyle = '#3a5a70';
    ctx.font = '9px Share Tech Mono';
    ctx.textAlign = 'left';
    ctx.fillText(label, PAD.left + i*80 + 15, 9);
  });
}

function drawForecastChart(cid, wid, dates, prices, lastActual) {
  const {ctx, W, H} = setupCanvas(cid, wid);
  const PAD = {top:15, right:70, bottom:30, left:65};
  const cW = W - PAD.left - PAD.right;
  const cH = H - PAD.top  - PAD.bottom;

  ctx.fillStyle = '#071219';
  ctx.fillRect(0,0,W,H);

  if (!prices.length) return;
  const minV = Math.min(...prices, lastActual||prices[0]) * 0.995;
  const maxV = Math.max(...prices, lastActual||prices[0]) * 1.005;
  const xScale = i => PAD.left + (i/(prices.length-1))*cW;
  const yScale = v => PAD.top + cH - ((v-minV)/(maxV-minV))*cH;

  ctx.strokeStyle = 'rgba(13,34,51,0.8)';
  for (let i=0;i<=4;i++) {
    const y=PAD.top+(i/4)*cH;
    ctx.lineWidth=1; ctx.beginPath(); ctx.moveTo(PAD.left,y); ctx.lineTo(PAD.left+cW,y); ctx.stroke();
    const val=maxV-(i/4)*(maxV-minV);
    ctx.fillStyle='#3a5a70'; ctx.font='9px Share Tech Mono'; ctx.textAlign='right';
    ctx.fillText(val.toFixed(0),PAD.left-4,y+3);
  }

  ctx.fillStyle = 'rgba(204,136,255,0.06)';
  ctx.beginPath();
  ctx.moveTo(xScale(0), yScale(prices[0]));
  prices.forEach((p,i) => ctx.lineTo(xScale(i), yScale(p)));
  ctx.lineTo(xScale(prices.length-1), PAD.top+cH);
  ctx.lineTo(xScale(0), PAD.top+cH);
  ctx.closePath(); ctx.fill();

  const isUp = prices[prices.length-1] > prices[0];
  ctx.strokeStyle = isUp ? 'rgba(0,255,136,0.8)' : 'rgba(255,51,85,0.8)';
  ctx.lineWidth = 2;
  ctx.shadowColor = isUp ? '#00ff88' : '#ff3355';
  ctx.shadowBlur = 4;
  ctx.beginPath();
  prices.forEach((p,i) => i===0?ctx.moveTo(xScale(i),yScale(p)):ctx.lineTo(xScale(i),yScale(p)));
  ctx.stroke();
  ctx.shadowBlur = 0;

  if (lastActual) {
    const y=yScale(lastActual);
    ctx.strokeStyle='rgba(255,204,0,0.6)';
    ctx.lineWidth=1; ctx.setLineDash([3,3]);
    ctx.beginPath(); ctx.moveTo(PAD.left,y); ctx.lineTo(PAD.left+cW,y); ctx.stroke();
    ctx.setLineDash([]);
  }

  ctx.fillStyle='#3a5a70'; ctx.font='9px Share Tech Mono'; ctx.textAlign='center';
  [0,15,30,45,59].forEach(i => {
    if (i<dates.length) ctx.fillText(dates[i].slice(5), xScale(i), H-4);
  });

  ctx.fillStyle=isUp?'rgba(0,255,136,0.6)':'rgba(255,51,85,0.6)';
  ctx.font='bold 10px Share Tech Mono'; ctx.textAlign='left';
  ctx.fillText('60-DAY FOURIER FORECAST', PAD.left+4, PAD.top+12);
  ctx.fillStyle=isUp?'var(--green)':'var(--red)';
  ctx.font='bold 11px Share Tech Mono'; ctx.textAlign='right';
  const finalP = prices[prices.length-1];
  const pct = lastActual ? ((finalP-lastActual)/lastActual*100).toFixed(1) : '0';
  ctx.fillText(`Target: ${finalP.toFixed(0)} (${pct>0?'+':''}${pct}%)`, PAD.left+cW, PAD.top+12);
}

function drawSpectrumChart(cid, cycles) {
  const canvas = document.getElementById(cid);
  const wrap   = canvas.parentElement;
  const W = wrap.clientWidth || 800, H = 200;
  canvas.width=W; canvas.height=H;
  canvas.style.width=W+'px'; canvas.style.height=H+'px';
  const ctx = canvas.getContext('2d');
  const PAD={top:20,right:20,bottom:35,left:50};
  const cW=W-PAD.left-PAD.right, cH=H-PAD.top-PAD.bottom;

  ctx.fillStyle='#071219'; ctx.fillRect(0,0,W,H);
  if (!cycles.length) return;

  const maxPow = Math.max(...cycles.map(c=>c.strength_pct));
  const barW   = cW / cycles.length * 0.7;

  cycles.forEach((c,i) => {
    const barH = (c.strength_pct / maxPow) * cH;
    const x    = PAD.left + (i+0.5) * (cW/cycles.length) - barW/2;
    const y    = PAD.top + cH - barH;
    const col  = c.strength_pct > 10 ? '#cc88ff' : 'rgba(204,136,255,0.4)';
    ctx.fillStyle = col;
    ctx.fillRect(x, y, barW, barH);
    ctx.fillStyle = '#3a5a70';
    ctx.font = '8px Share Tech Mono';
    ctx.textAlign = 'center';
    ctx.fillText(c.period_days+'d', x+barW/2, H-PAD.bottom+10);
    ctx.fillStyle = '#cc88ff';
    ctx.font = '8px Share Tech Mono';
    ctx.fillText(c.strength_pct+'%', x+barW/2, y-4);
  });

  ctx.strokeStyle='rgba(13,34,51,0.8)'; ctx.lineWidth=1;
  for (let i=0;i<=4;i++) {
    const y=PAD.top+(i/4)*cH;
    ctx.beginPath(); ctx.moveTo(PAD.left,y); ctx.lineTo(PAD.left+cW,y); ctx.stroke();
    ctx.fillStyle='#3a5a70'; ctx.font='8px Share Tech Mono'; ctx.textAlign='right';
    ctx.fillText((maxPow*(1-i/4)).toFixed(1)+'%',PAD.left-3,y+3);
  }
  ctx.fillStyle='rgba(204,136,255,0.5)'; ctx.font='9px Share Tech Mono'; ctx.textAlign='left';
  ctx.fillText('CYCLE POWER SPECTRUM', PAD.left+4, PAD.top+12);
}

function drawAcfChart(cid, autocorrs, sigThreshold) {
  const canvas = document.getElementById(cid);
  const wrap   = canvas.parentElement;
  const W=wrap.clientWidth||800, H=200;
  canvas.width=W; canvas.height=H;
  const ctx=canvas.getContext('2d');
  const PAD={top:20,right:20,bottom:30,left:50};
  const cW=W-PAD.left-PAD.right, cH=H-PAD.top-PAD.bottom;

  ctx.fillStyle='#071219'; ctx.fillRect(0,0,W,H);
  if (!autocorrs.length) return;

  const n = Math.min(autocorrs.length, 120);
  const vals = autocorrs.slice(0,n).map(a=>a.acf);
  const maxA = Math.max(Math.abs(Math.min(...vals)), Math.max(...vals), sigThreshold*1.5, 0.05);
  const xScale = i => PAD.left + (i/n)*cW;
  const yScale = v => PAD.top + cH/2 - (v/maxA)*(cH/2);

  ctx.strokeStyle='rgba(13,34,51,0.8)'; ctx.lineWidth=1;
  [0.5,0,-0.5].forEach(v => {
    const y=yScale(v);
    ctx.beginPath(); ctx.moveTo(PAD.left,y); ctx.lineTo(PAD.left+cW,y); ctx.stroke();
  });

  ctx.strokeStyle='rgba(58,90,112,0.5)'; ctx.lineWidth=1;
  ctx.beginPath(); ctx.moveTo(PAD.left,yScale(0)); ctx.lineTo(PAD.left+cW,yScale(0)); ctx.stroke();

  ctx.fillStyle='rgba(0,212,255,0.04)';
  ctx.fillRect(PAD.left, yScale(sigThreshold), cW, yScale(-sigThreshold)-yScale(sigThreshold));

  ctx.strokeStyle='rgba(0,212,255,0.3)'; ctx.lineWidth=1; ctx.setLineDash([2,4]);
  ctx.beginPath(); ctx.moveTo(PAD.left,yScale(sigThreshold)); ctx.lineTo(PAD.left+cW,yScale(sigThreshold)); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(PAD.left,yScale(-sigThreshold)); ctx.lineTo(PAD.left+cW,yScale(-sigThreshold)); ctx.stroke();
  ctx.setLineDash([]);

  autocorrs.slice(0,n).forEach((a,i) => {
    const x=xScale(i)+1, barH=yScale(0)-yScale(a.acf);
    const col=Math.abs(a.acf)>sigThreshold?(a.acf>0?'rgba(0,255,136,0.7)':'rgba(255,51,85,0.7)'):'rgba(58,90,112,0.4)';
    ctx.fillStyle=col;
    ctx.fillRect(x, a.acf>0?yScale(a.acf):yScale(0), Math.max(cW/n-2,1), Math.abs(barH));
  });

  ctx.fillStyle='#3a5a70'; ctx.font='8px Share Tech Mono'; ctx.textAlign='center';
  [0,20,40,60,80,100].forEach(i => { if(i<n) ctx.fillText(i+'d', xScale(i), H-4); });
  ctx.textAlign='right';
  [maxA*0.5,0,-maxA*0.5].forEach(v => {
    ctx.fillText(v.toFixed(3),PAD.left-3,yScale(v)+3);
  });
  ctx.fillStyle='rgba(0,212,255,0.5)'; ctx.font='9px Share Tech Mono'; ctx.textAlign='left';
  ctx.fillText('AUTOCORRELATION', PAD.left+4, PAD.top+12);
  ctx.fillStyle='rgba(0,212,255,0.4)'; ctx.textAlign='right';
  ctx.fillText('±95% significance', PAD.left+cW, PAD.top+12);
}
"""
