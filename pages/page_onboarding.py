# pages/page_onboarding.py

HTML = r"""
<!-- ═══════════ PAGE: ONBOARDING WIZARD ═══════════ -->
<div id="page-onboarding" class="page" style="display:flex; justify-content:center; align-items:center; min-height:100vh; padding:20px; background:var(--bg);">
  <div class="card" style="width:100%; max-width:600px; padding:36px; border-radius:8px; border:1px solid var(--border); box-shadow:0 12px 40px rgba(0,0,0,0.6); background:var(--panel);">
    
    <!-- Onboarding Header -->
    <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid var(--border); padding-bottom:18px; margin-bottom:24px;">
      <span style="font-family:Orbitron,sans-serif; font-size:1.1rem; font-weight:700; color:var(--cyan); letter-spacing:1px;">🛡️ RISK & PREFERENCE WIZARD</span>
      <span id="onb-step-indicator" style="font-family:'JetBrains Mono',monospace; font-size:0.75rem; color:var(--dim);">Step 1 of 7</span>
    </div>

    <!-- Onboarding Error Alert -->
    <div id="onb-error" class="err" style="display:none; margin-bottom:20px; padding:10px 14px; font-size:0.75rem;"></div>

    <!-- Wizard Panes -->
    <div id="onb-panes-container">
      
      <!-- Step 1: About You -->
      <div id="onb-step-1" class="onb-pane">
        <h3 style="font-size:1rem; color:var(--white); margin-bottom:12px; font-weight:600;">1. Tell us about yourself</h3>
        <p style="font-size:0.75rem; color:var(--dim); margin-bottom:20px;">This helps personalize market updates and recommendations.</p>
        
        <div style="margin-bottom:16px;">
          <label style="display:block; font-size:0.7rem; text-transform:uppercase; color:var(--text); letter-spacing:1px; margin-bottom:6px; font-weight:600;">Full Name</label>
          <input type="text" id="onb-name" placeholder="John Doe" 
            style="width:100%; padding:10px 12px; background:var(--p2); border:1px solid var(--border); border-radius:4px; color:var(--white); font-size:0.85rem; outline:none;">
        </div>

        <div style="margin-bottom:16px;">
          <label style="display:block; font-size:0.7rem; text-transform:uppercase; color:var(--text); letter-spacing:1px; margin-bottom:6px; font-weight:600;">Age Range</label>
          <select id="onb-age" style="width:100%; padding:10px 12px; background:var(--p2); border:1px solid var(--border); border-radius:4px; color:var(--white); font-size:0.85rem; outline:none; cursor:pointer;">
            <option value="Under 25">Under 25</option>
            <option value="25-34" selected>25-34</option>
            <option value="35-44">35-44</option>
            <option value="45-54">45-54</option>
            <option value="55+">55+</option>
          </select>
        </div>

        <div style="margin-bottom:16px;">
          <label style="display:block; font-size:0.7rem; text-transform:uppercase; color:var(--text); letter-spacing:1px; margin-bottom:6px; font-weight:600;">Occupation</label>
          <input type="text" id="onb-occupation" placeholder="e.g. Engineer, Business Owner, Student" 
            style="width:100%; padding:10px 12px; background:var(--p2); border:1px solid var(--border); border-radius:4px; color:var(--white); font-size:0.85rem; outline:none;">
        </div>

        <div style="margin-bottom:24px;">
          <label style="display:block; font-size:0.7rem; text-transform:uppercase; color:var(--text); letter-spacing:1px; margin-bottom:6px; font-weight:600;">Location (City, Country)</label>
          <input type="text" id="onb-location" placeholder="e.g. Mumbai, India" 
            style="width:100%; padding:10px 12px; background:var(--p2); border:1px solid var(--border); border-radius:4px; color:var(--white); font-size:0.85rem; outline:none;">
        </div>

        <button onclick="onbNext(1)" class="btn" style="width:100%; padding:12px;">CONTINUE</button>
      </div>

      <!-- Step 2: Experience -->
      <div id="onb-step-2" class="onb-pane" style="display:none;">
        <h3 style="font-size:1rem; color:var(--white); margin-bottom:12px; font-weight:600;">2. How experienced are you in the stock market?</h3>
        <p style="font-size:0.75rem; color:var(--dim); margin-bottom:20px;">We tailor terminology and adjust default risk gates based on your experience.</p>
        
        <div style="margin-bottom:20px;">
          <label style="display:block; font-size:0.7rem; text-transform:uppercase; color:var(--text); letter-spacing:1px; margin-bottom:10px; font-weight:600;">Experience Level</label>
          <div style="display:grid; grid-template-columns:1fr; gap:10px;">
            <button onclick="selectOnbExperience('Beginner', this)" class="btn onb-exp-btn" style="background:var(--p2); border:1px solid var(--border); text-align:left; padding:12px; font-size:0.85rem; color:var(--text);">🔰 <b>BEGINNER</b> — Just starting out or under 1 year of investing</button>
            <button onclick="selectOnbExperience('Intermediate', this)" class="btn onb-exp-btn active" style="background:var(--p2); border:1px solid var(--cyan); text-align:left; padding:12px; font-size:0.85rem; color:var(--text);">📈 <b>INTERMEDIATE</b> — Some experience, understand basics, buy/sell stocks</button>
            <button onclick="selectOnbExperience('Advanced', this)" class="btn onb-exp-btn" style="background:var(--p2); border:1px solid var(--border); text-align:left; padding:12px; font-size:0.85rem; color:var(--text);">🔥 <b>ADVANCED</b> — Experienced trader, familiar with technical charts and stop losses</button>
            <button onclick="selectOnbExperience('Professional', this)" class="btn onb-exp-btn" style="background:var(--p2); border:1px solid var(--border); text-align:left; padding:12px; font-size:0.85rem; color:var(--text);">👑 <b>PROFESSIONAL</b> — Pro trader, use options/hedging, quantitative models</button>
          </div>
        </div>

        <div style="margin-bottom:24px;">
          <label style="display:block; font-size:0.7rem; text-transform:uppercase; color:var(--text); letter-spacing:1px; margin-bottom:6px; font-weight:600;">Investing/Trading Duration</label>
          <select id="onb-duration" style="width:100%; padding:10px 12px; background:var(--p2); border:1px solid var(--border); border-radius:4px; color:var(--white); font-size:0.85rem; outline:none; cursor:pointer;">
            <option value="Just starting">Just starting</option>
            <option value="Less than 1 year">Less than 1 year</option>
            <option value="1-3 years" selected>1-3 years</option>
            <option value="3-5 years">3-5 years</option>
            <option value="5+ years">5+ years</option>
          </select>
        </div>

        <div style="display:flex; gap:12px;">
          <button onclick="onbBack(2)" class="btn" style="background:var(--p2); border:1px solid var(--border); color:var(--text); flex:1;">BACK</button>
          <button onclick="onbNext(2)" class="btn" style="flex:1;">CONTINUE</button>
        </div>
      </div>

      <!-- Step 3: Goals -->
      <div id="onb-step-3" class="onb-pane" style="display:none;">
        <h3 style="font-size:1rem; color:var(--white); margin-bottom:12px; font-weight:600;">3. What are your primary investment goals?</h3>
        <p style="font-size:0.75rem; color:var(--dim); margin-bottom:20px;">Select all objectives that apply to your current capital.</p>
        
        <div class="chip-grid" style="margin-bottom:28px;" id="onb-goals-container">
          <div class="chip" onclick="toggleOnbGoal('Long-term wealth creation', this)">📈 Long-term wealth creation</div>
          <div class="chip" onclick="toggleOnbGoal('Short-term trading', this)">⚡ Short-term trading</div>
          <div class="chip" onclick="toggleOnbGoal('Intraday trading', this)">🏎️ Intraday trading</div>
          <div class="chip" onclick="toggleOnbGoal('Swing trading', this)">🌊 Swing trading</div>
          <div class="chip" onclick="toggleOnbGoal('Portfolio building', this)">🏛️ Portfolio building</div>
          <div class="chip" onclick="toggleOnbGoal('Retirement planning', this)">👴 Retirement planning</div>
          <div class="chip" onclick="toggleOnbGoal('Passive income', this)">💵 Passive income</div>
          <div class="chip" onclick="toggleOnbGoal('Learning stock markets', this)">🎓 Learning stock markets</div>
          <div class="chip" onclick="toggleOnbGoal('Finding investment opportunities', this)">🎯 Finding opportunities</div>
          <div class="chip" onclick="toggleOnbGoal('Risk management', this)">🛡️ Risk management</div>
          <div class="chip" onclick="toggleOnbGoal('Market research', this)">🔬 Market research</div>
        </div>

        <div style="display:flex; gap:12px;">
          <button onclick="onbBack(3)" class="btn" style="background:var(--p2); border:1px solid var(--border); color:var(--text); flex:1;">BACK</button>
          <button onclick="onbNext(3)" class="btn" style="flex:1;">CONTINUE</button>
        </div>
      </div>

      <!-- Step 4: Risk Profile -->
      <div id="onb-step-4" class="onb-pane" style="display:none;">
        <h3 style="font-size:1rem; color:var(--white); margin-bottom:12px; font-weight:600;">4. Define your risk comfort zone</h3>
        <p style="font-size:0.75rem; color:var(--dim); margin-bottom:20px;">Helps us establish safety margins and filter high-volatility recommendations.</p>
        
        <div style="margin-bottom:18px;">
          <label style="display:block; font-size:0.7rem; text-transform:uppercase; color:var(--text); letter-spacing:1px; margin-bottom:6px; font-weight:600;">Risk Comfort level</label>
          <select id="onb-risk-comfort" style="width:100%; padding:10px 12px; background:var(--p2); border:1px solid var(--border); border-radius:4px; color:var(--white); font-size:0.85rem; outline:none; cursor:pointer;">
            <option value="Conservative">Conservative (Minimize loss, lower gains)</option>
            <option value="Moderately Conservative">Moderately Conservative</option>
            <option value="Moderate" selected>Moderate (Balanced risk and reward)</option>
            <option value="Aggressive">Aggressive (High volatility, maximize gains)</option>
            <option value="Very Aggressive">Very Aggressive (Day trading, options, leverage)</option>
          </select>
        </div>

        <div style="margin-bottom:28px;">
          <label style="display:block; font-size:0.7rem; text-transform:uppercase; color:var(--text); letter-spacing:1px; margin-bottom:6px; font-weight:600;">Scenario: Your stock falls 15% in a short period. What would you do?</label>
          <select id="onb-risk-scenario" style="width:100%; padding:10px 12px; background:var(--p2); border:1px solid var(--border); border-radius:4px; color:var(--white); font-size:0.85rem; outline:none; cursor:pointer;">
            <option value="sell_all">🚨 Sell All (Preserve capital, avoid further drops)</option>
            <option value="sell_some">📉 Sell Some (Lower position size to reduce risk)</option>
            <option value="hold" selected>✊ Hold Patiently (Wait for cycle reversal / market recovery)</option>
            <option value="buy_more">🛍️ Buy More (Discount price, load up at supports)</option>
          </select>
        </div>

        <div style="display:flex; gap:12px;">
          <button onclick="onbBack(4)" class="btn" style="background:var(--p2); border:1px solid var(--border); color:var(--text); flex:1;">BACK</button>
          <button onclick="onbNext(4)" class="btn" style="flex:1;">CONTINUE</button>
        </div>
      </div>

      <!-- Step 5: Preferences -->
      <div id="onb-step-5" class="onb-pane" style="display:none;">
        <h3 style="font-size:1rem; color:var(--white); margin-bottom:12px; font-weight:600;">5. What markets & styles do you trade?</h3>
        <p style="font-size:0.75rem; color:var(--dim); margin-bottom:20px;">We filters recommended opportunities to match your chosen styles.</p>
        
        <div style="margin-bottom:18px;">
          <label style="display:block; font-size:0.7rem; text-transform:uppercase; color:var(--text); letter-spacing:1px; margin-bottom:8px; font-weight:600;">Preferred Markets</label>
          <div class="chip-grid" id="onb-markets-container">
            <div class="chip active" onclick="toggleOnbMarket('Indian Stocks', this)">🇮🇳 Indian Stocks</div>
            <div class="chip" onclick="toggleOnbMarket('US Stocks', this)">🇺🇸 US Stocks</div>
            <div class="chip" onclick="toggleOnbMarket('ETFs', this)">📦 ETFs</div>
            <div class="chip" onclick="toggleOnbMarket('Mutual Funds', this)">📈 Mutual Funds</div>
            <div class="chip" onclick="toggleOnbMarket('Commodities', this)">🪵 Commodities</div>
            <div class="chip" onclick="toggleOnbMarket('Forex', this)">💱 Forex</div>
            <div class="chip" onclick="toggleOnbMarket('Crypto', this)">🪙 Crypto</div>
          </div>
        </div>

        <div style="margin-bottom:24px;">
          <label style="display:block; font-size:0.7rem; text-transform:uppercase; color:var(--text); letter-spacing:1px; margin-bottom:8px; font-weight:600;">Preferred Trading Styles</label>
          <div class="chip-grid" id="onb-styles-container">
            <div class="chip active" onclick="toggleOnbStyle('Long-term investing', this)">🏛️ Long-term investing</div>
            <div class="chip active" onclick="toggleOnbStyle('Swing trading', this)">🌊 Swing trading</div>
            <div class="chip" onclick="toggleOnbStyle('Positional trading', this)">📈 Positional trading</div>
            <div class="chip" onclick="toggleOnbStyle('Intraday', this)">🏎️ Intraday</div>
            <div class="chip" onclick="toggleOnbStyle('Momentum', this)">🚀 Momentum</div>
            <div class="chip" onclick="toggleOnbStyle('Value investing', this)">🏷️ Value investing</div>
            <div class="chip" onclick="toggleOnbStyle('Growth investing', this)">📊 Growth investing</div>
            <div class="chip active" onclick="toggleOnbStyle('Technical analysis', this)">📈 Technical analysis</div>
            <div class="chip" onclick="toggleOnbStyle('Fundamental analysis', this)">🔍 Fundamental analysis</div>
          </div>
        </div>

        <div style="display:flex; gap:12px;">
          <button onclick="onbBack(5)" class="btn" style="background:var(--p2); border:1px solid var(--border); color:var(--text); flex:1;">BACK</button>
          <button onclick="onbNext(5)" class="btn" style="flex:1;">CONTINUE</button>
        </div>
      </div>

      <!-- Step 6: Sectors & Seeding -->
      <div id="onb-step-6" class="onb-pane" style="display:none;">
        <h3 style="font-size:1rem; color:var(--white); margin-bottom:12px; font-weight:600;">6. Sector Preferences & Watchlist</h3>
        <p style="font-size:0.75rem; color:var(--dim); margin-bottom:20px;">We check exclusions to filter out sectors you don't wish to invest in.</p>
        
        <div style="margin-bottom:18px;">
          <label style="display:block; font-size:0.7rem; text-transform:uppercase; color:var(--text); letter-spacing:1px; margin-bottom:8px; font-weight:600;">Preferred Sectors (Excludes unselected)</label>
          <div class="chip-grid" id="onb-sectors-container">
            <div class="chip active" onclick="toggleOnbSector('IT', this)">🖥️ IT</div>
            <div class="chip active" onclick="toggleOnbSector('Banking', this)">🏦 Banking</div>
            <div class="chip active" onclick="toggleOnbSector('Pharma', this)">💊 Pharma</div>
            <div class="chip active" onclick="toggleOnbSector('Auto', this)">🚗 Auto</div>
            <div class="chip active" onclick="toggleOnbSector('Energy', this)">⚡ Energy</div>
            <div class="chip active" onclick="toggleOnbSector('FMCG', this)">📦 FMCG</div>
            <div class="chip active" onclick="toggleOnbSector('Defence', this)">🛡️ Defence</div>
            <div class="chip active" onclick="toggleOnbSector('Infrastructure', this)">🏗️ Infra</div>
            <div class="chip active" onclick="toggleOnbSector('Telecom', this)">📡 Telecom</div>
          </div>
        </div>

        <div style="margin-bottom:24px;">
          <label style="display:block; font-size:0.7rem; text-transform:uppercase; color:var(--text); letter-spacing:1px; margin-bottom:6px; font-weight:600;">Add Favourite Stocks (Comma separated symbols, optional)</label>
          <input type="text" id="onb-fav-stocks" placeholder="e.g. NIFTY50, RELIANCE, TCS, INFOSYS" 
            style="width:100%; padding:10px 12px; background:var(--p2); border:1px solid var(--border); border-radius:4px; color:var(--white); font-family:'JetBrains Mono',monospace; font-size:0.85rem; outline:none;">
        </div>

        <div style="display:flex; gap:12px;">
          <button onclick="onbBack(6)" class="btn" style="background:var(--p2); border:1px solid var(--border); color:var(--text); flex:1;">BACK</button>
          <button onclick="onbNext(6)" class="btn" style="flex:1;">CONTINUE</button>
        </div>
      </div>

      <!-- Step 7: Capital & Horizon -->
      <div id="onb-step-7" class="onb-pane" style="display:none;">
        <h3 style="font-size:1rem; color:var(--white); margin-bottom:12px; font-weight:600;">7. Investment Capital & Horizon</h3>
        <p style="font-size:0.75rem; color:var(--dim); margin-bottom:20px;">Directly guides capital allocation risk limits and lot sizes.</p>
        
        <div style="margin-bottom:18px;">
          <label style="display:block; font-size:0.7rem; text-transform:uppercase; color:var(--text); letter-spacing:1px; margin-bottom:6px; font-weight:600;">Typical Investment Horizon</label>
          <select id="onb-horizon" style="width:100%; padding:10px 12px; background:var(--p2); border:1px solid var(--border); border-radius:4px; color:var(--white); font-size:0.85rem; outline:none; cursor:pointer;">
            <option value="Intraday">Intraday (Daily exit)</option>
            <option value="Days">Days (1 to 7 days swing)</option>
            <option value="Weeks">Weeks (1 to 4 weeks trend)</option>
            <option value="Months" selected>Months (1 to 12 months positional)</option>
            <option value="Years">Years (1+ years long-term)</option>
          </select>
        </div>

        <div style="margin-bottom:24px;">
          <label style="display:block; font-size:0.7rem; text-transform:uppercase; color:var(--text); letter-spacing:1px; margin-bottom:6px; font-weight:600;">Starting Capital (₹)</label>
          <div style="position:relative;">
            <span style="position:absolute; left:14px; top:11px; font-family:'JetBrains Mono',monospace; color:var(--dim); font-size:0.9rem;">₹</span>
            <input type="number" id="onb-capital" value="100000" min="5000" step="10000" 
              style="width:100%; padding:10px 12px 10px 28px; background:var(--p2); border:1px solid var(--border); border-radius:4px; color:var(--white); font-family:'JetBrains Mono',monospace; font-size:1rem; outline:none;">
          </div>
        </div>

        <div style="display:flex; gap:12px;">
          <button onclick="onbBack(7)" class="btn" style="background:var(--p2); border:1px solid var(--border); color:var(--text); flex:1;">BACK</button>
          <button onclick="onbNext(7)" class="btn" style="flex:1;">CALCULATE LIMITS</button>
        </div>
      </div>

      <!-- Step 8: Confirm Risk Limits -->
      <div id="onb-step-8" class="onb-pane" style="display:none;">
        <h3 style="font-size:1.1rem; color:var(--white); margin-bottom:12px; font-weight:600; text-align:center;">📋 CONFIRM DERIVED RISK PARAMETERS</h3>
        <p style="font-size:0.75rem; color:var(--dim); margin-bottom:20px; text-align:center;">These settings will govern automated recommendation safeguards.</p>
        
        <div style="background:var(--p2); border:1px solid var(--border); border-radius:4px; padding:18px; margin-bottom:24px; font-family:'JetBrains Mono',monospace; font-size:0.8rem;">
          <div style="display:flex; justify-content:space-between; margin-bottom:10px;">
            <span style="color:var(--dim);">Full Name:</span>
            <span id="rev-name" style="color:var(--white); font-weight:bold;">--</span>
          </div>
          <div style="display:flex; justify-content:space-between; margin-bottom:10px;">
            <span style="color:var(--dim);">Experience Level:</span>
            <span id="rev-exp" style="color:var(--white); font-weight:bold; text-transform:uppercase;">--</span>
          </div>
          <div style="display:flex; justify-content:space-between; margin-bottom:10px;">
            <span style="color:var(--dim);">Primary Goal:</span>
            <span id="rev-goal" style="color:var(--white); font-weight:bold; text-transform:uppercase;">--</span>
          </div>
          <div style="display:flex; justify-content:space-between; margin-bottom:10px;">
            <span style="color:var(--dim);">Starting Capital:</span>
            <span id="rev-capital" style="color:var(--green); font-weight:bold;">₹--</span>
          </div>
          <div style="display:flex; justify-content:space-between; margin-bottom:10px; border-top:1px solid var(--border); padding-top:10px;">
            <span style="color:var(--dim);">Derived Max Position:</span>
            <span id="rev-max-pos" style="color:var(--gold); font-weight:bold;">10%</span>
          </div>
          <div style="display:flex; justify-content:space-between;">
            <span style="color:var(--dim);">Derived Max Sector:</span>
            <span id="rev-max-sec" style="color:var(--gold); font-weight:bold;">30%</span>
          </div>
        </div>

        <button onclick="submitOnboarding()" class="btn" style="width:100%; padding:14px; font-size:0.9rem; font-weight:700; background:var(--green); color:var(--white); box-shadow:0 0 15px rgba(8,153,129,0.25);">
          🚀 SAVE PROFILE & START TERMINAL
        </button>
      </div>

    </div>
  </div>
</div>
"""

JS = r"""
let onbSelectedExperience = 'Intermediate';
let onbGoals = [];
let onbMarkets = ['Indian Stocks'];
let onbStyles = ['Long-term investing', 'Swing trading', 'Technical analysis'];
let onbSectors = ['IT', 'Banking', 'Pharma', 'Auto', 'Energy', 'FMCG', 'Defence', 'Infrastructure', 'Telecom'];

function selectOnbExperience(val, btn) {
  onbSelectedExperience = val;
  document.querySelectorAll('.onb-exp-btn').forEach(b => b.classList.remove('active'));
  if (btn) btn.classList.add('active');
}

function toggleOnbGoal(val, chip) {
  if (onbGoals.includes(val)) {
    onbGoals = onbGoals.filter(g => g !== val);
    if (chip) chip.classList.remove('active');
  } else {
    onbGoals.push(val);
    if (chip) chip.classList.add('active');
  }
}

function toggleOnbMarket(val, chip) {
  if (onbMarkets.includes(val)) {
    onbMarkets = onbMarkets.filter(m => m !== val);
    if (chip) chip.classList.remove('active');
  } else {
    onbMarkets.push(val);
    if (chip) chip.classList.add('active');
  }
}

function toggleOnbStyle(val, chip) {
  if (onbStyles.includes(val)) {
    onbStyles = onbStyles.filter(s => s !== val);
    if (chip) chip.classList.remove('active');
  } else {
    onbStyles.push(val);
    if (chip) chip.classList.add('active');
  }
}

function toggleOnbSector(val, chip) {
  if (onbSectors.includes(val)) {
    onbSectors = onbSectors.filter(s => s !== val);
    if (chip) chip.classList.remove('active');
  } else {
    onbSectors.push(val);
    if (chip) chip.classList.add('active');
  }
}

function onbNext(step) {
  const errDiv = document.getElementById('onb-error');
  if (errDiv) errDiv.style.display = 'none';

  // Validation
  if (step === 1) {
    const name = document.getElementById('onb-name').value.trim();
    if (!name) {
      showOnbError("Please enter your name to proceed.");
      return;
    }
  }
  if (step === 3) {
    if (onbGoals.length === 0) {
      showOnbError("Please select at least one investment goal.");
      return;
    }
  }
  if (step === 5) {
    if (onbMarkets.length === 0) {
      showOnbError("Please select at least one preferred market.");
      return;
    }
  }

  if (step < 7) {
    const nextStep = step + 1;
    showOnbStep(nextStep);
  } else if (step === 7) {
    calculateAndShowLimits();
  }
}

function onbBack(step) {
  const errDiv = document.getElementById('onb-error');
  if (errDiv) errDiv.style.display = 'none';
  if (step > 1) {
    showOnbStep(step - 1);
  }
}

function showOnbStep(step) {
  document.querySelectorAll('.onb-pane').forEach(p => p.style.display = 'none');
  const nextPane = document.getElementById('onb-step-' + step);
  if (nextPane) nextPane.style.display = 'block';

  const indicator = document.getElementById('onb-step-indicator');
  if (indicator) indicator.textContent = 'Step ' + step + ' of 7';
}

function showOnbError(msg) {
  const errDiv = document.getElementById('onb-error');
  if (errDiv) {
    errDiv.textContent = msg;
    errDiv.style.display = 'block';
  }
}

let calculatedPosPct = 10;
let calculatedSecPct = 30;

function calculateAndShowLimits() {
  const name = document.getElementById('onb-name').value.trim();
  const capital = parseFloat(document.getElementById('onb-capital').value) || 100000;
  const comfort = document.getElementById('onb-risk-comfort').value;

  // Base sizing from experience
  let basePos = 10;
  let baseSec = 20;

  if (onbSelectedExperience === 'Beginner') {
    basePos = 10;
    baseSec = 20;
  } else if (onbSelectedExperience === 'Intermediate') {
    basePos = 15;
    baseSec = 30;
  } else if (onbSelectedExperience === 'Advanced') {
    basePos = 20;
    baseSec = 35;
  } else { // Professional
    basePos = 25;
    baseSec = 40;
  }

  // Adjustments based on risk comfort
  if (comfort === 'Conservative') {
    basePos -= 3;
    baseSec -= 5;
  } else if (comfort === 'Moderately Conservative') {
    basePos -= 1;
    baseSec -= 2;
  } else if (comfort === 'Aggressive') {
    basePos += 3;
    baseSec += 5;
  } else if (comfort === 'Very Aggressive') {
    basePos += 5;
    baseSec += 10;
  }

  // Caps
  calculatedPosPct = Math.max(5, Math.min(30, basePos));
  calculatedSecPct = Math.max(10, Math.min(50, baseSec));

  // Populate Summary Step
  document.getElementById('rev-name').textContent = name;
  document.getElementById('rev-exp').textContent = onbSelectedExperience + ' (' + document.getElementById('onb-duration').value + ')';
  document.getElementById('rev-goal').textContent = onbGoals.slice(0, 2).join(', ') + (onbGoals.length > 2 ? '...' : '');
  document.getElementById('rev-capital').textContent = '₹' + capital.toLocaleString('en-IN');
  document.getElementById('rev-max-pos').textContent = calculatedPosPct + '% (₹' + (capital * calculatedPosPct / 100).toLocaleString('en-IN') + ' max per stock)';
  document.getElementById('rev-max-sec').textContent = calculatedSecPct + '% (₹' + (capital * calculatedSecPct / 100).toLocaleString('en-IN') + ' max per sector)';

  document.querySelectorAll('.onb-pane').forEach(p => p.style.display = 'none');
  document.getElementById('onb-step-8').style.display = 'block';
  
  const indicator = document.getElementById('onb-step-indicator');
  if (indicator) indicator.textContent = 'Verification';
}

async function submitOnboarding() {
  const errDiv = document.getElementById('onb-error');
  if (errDiv) errDiv.style.display = 'none';

  const name = document.getElementById('onb-name').value.trim();
  const age = document.getElementById('onb-age').value;
  const occupation = document.getElementById('onb-occupation').value.trim();
  const location = document.getElementById('onb-location').value.trim();
  const duration = document.getElementById('onb-duration').value;
  const comfort = document.getElementById('onb-risk-comfort').value;
  const scenario = document.getElementById('onb-risk-scenario').value;
  const horizon = document.getElementById('onb-horizon').value;
  const capital = parseFloat(document.getElementById('onb-capital').value) || 100000;
  
  const favStocks = document.getElementById('onb-fav-stocks').value.trim();
  let watchlistSymbols = [];
  if (favStocks) {
    watchlistSymbols = favStocks.split(',').map(s => s.trim().toUpperCase()).filter(s => s.length > 0);
  }

  const payload = {
    age_range: age,
    occupation: occupation,
    location: location,
    experience_level: onbSelectedExperience,
    experience_duration: duration,
    primary_goals: onbGoals,
    risk_comfort: comfort,
    risk_scenario_answer: scenario,
    preferred_markets: onbMarkets,
    trading_styles: onbStyles,
    preferred_sectors: onbSectors,
    investment_horizon: horizon,
    starting_capital: capital,
    max_position_pct: calculatedPosPct,
    max_sector_pct: calculatedSecPct,
    onboarding_version: 1
  };

  try {
    const res = await api('onboarding/submit', payload);
    if (res.ok) {
      // Seed watchlist stocks if any were provided
      if (watchlistSymbols.length > 0) {
        for (const sym of watchlistSymbols) {
          try {
            await api('watchlist_add', { symbol: sym });
          } catch (we) {
            console.warn('Failed to seed symbol to watchlist:', sym, we);
          }
        }
      }
      showDashboardTerminal();
    } else {
      throw new Error(res.error || 'Failed to submit onboarding profile.');
    }
  } catch (e) {
    showOnbError(e.message || 'Onboarding submission failed.');
    showOnbStep(7);
  }
}
"""
