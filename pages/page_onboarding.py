# pages/page_onboarding.py

HTML = r"""
<!-- ═══════════ PAGE: ONBOARDING WIZARD ═══════════ -->
<div id="page-onboarding" class="page" style="display:flex; justify-content:center; align-items:center; min-height:100vh; padding:20px; background:var(--bg);">
  <div class="card" style="width:100%; max-width:600px; padding:36px; border-radius:12px; border:1px solid var(--border); box-shadow:0 16px 50px rgba(0,0,0,0.7); background:var(--panel);">
    
    <!-- Onboarding Header -->
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
      <span style="font-family:Orbitron,sans-serif; font-size:1.2rem; font-weight:700; color:var(--cyan); letter-spacing:1px;">🛡️ RISK & PREFERENCE WIZARD</span>
      <span id="onb-step-indicator" style="font-family:'JetBrains Mono',monospace; font-size:0.75rem; color:var(--dim); font-weight:600;">Step 1 of 7</span>
    </div>

    <!-- Progress Bar -->
    <div style="width:100%; background:var(--p2); height:6px; border-radius:3px; margin-bottom:24px; overflow:hidden;">
      <div id="onb-progress" style="width:14%; height:100%; background:linear-gradient(90deg, var(--cyan), var(--blue)); transition:width 0.4s ease;"></div>
    </div>

    <!-- Onboarding Error Alert -->
    <div id="onb-error" class="err" style="display:none; margin-bottom:20px; padding:12px; font-size:0.8rem; border-radius:6px;"></div>

    <!-- Wizard Panes -->
    <div id="onb-panes-container">
      
      <!-- Step 1: About You -->
      <div id="onb-step-1" class="onb-pane" style="animation: fade-in 0.3s ease;">
        <h3 style="font-size:1.1rem; color:var(--white); margin-bottom:8px; font-weight:600;">1. Tell us about yourself</h3>
        <p style="font-size:0.8rem; color:var(--dim); margin-bottom:24px;">This helps personalize market updates and recommendations.</p>
        
        <div style="margin-bottom:20px;">
          <label style="display:block; font-size:0.75rem; text-transform:uppercase; color:var(--text); letter-spacing:1px; margin-bottom:8px; font-weight:600;">Username</label>
          <input type="text" id="onb-name" placeholder="JohnDoe" 
            style="width:100%; padding:12px 14px; background:var(--p2); border:1px solid var(--border); border-radius:6px; color:var(--white); font-size:0.9rem; outline:none; transition:border-color 0.2s;">
        </div>

        <div style="margin-bottom:20px;">
          <label style="display:block; font-size:0.75rem; text-transform:uppercase; color:var(--text); letter-spacing:1px; margin-bottom:8px; font-weight:600;">Age Range</label>
          <div class="chip-grid" id="onb-age-container">
            <div class="chip" onclick="selectOnbSingle('age', 'Under 25', this)">Under 25</div>
            <div class="chip active" onclick="selectOnbSingle('age', '25-34', this)">25-34</div>
            <div class="chip" onclick="selectOnbSingle('age', '35-44', this)">35-44</div>
            <div class="chip" onclick="selectOnbSingle('age', '45-54', this)">45-54</div>
            <div class="chip" onclick="selectOnbSingle('age', '55+', this)">55+</div>
          </div>
        </div>

        <div style="margin-bottom:20px;">
          <label style="display:block; font-size:0.75rem; text-transform:uppercase; color:var(--text); letter-spacing:1px; margin-bottom:8px; font-weight:600;">Occupation</label>
          <div class="chip-grid" id="onb-occupation-container">
            <div class="chip active" onclick="selectOnbSingle('occupation', 'Job', this)">Job</div>
            <div class="chip" onclick="selectOnbSingle('occupation', 'Business', this)">Business</div>
            <div class="chip" onclick="selectOnbSingle('occupation', 'Student', this)">Student</div>
            <div class="chip" onclick="selectOnbSingle('occupation', 'Self-Employed', this)">Self-Employed</div>
            <div class="chip" onclick="selectOnbSingle('occupation', 'Retired', this)">Retired</div>
          </div>
        </div>

        <div style="margin-bottom:28px;">
          <label style="display:block; font-size:0.75rem; text-transform:uppercase; color:var(--text); letter-spacing:1px; margin-bottom:8px; font-weight:600;">Location (State)</label>
          <select id="onb-location" style="width:100%; padding:12px 14px; background:var(--p2); border:1px solid var(--border); border-radius:6px; color:var(--white); font-size:0.9rem; outline:none; transition:border-color 0.2s;">
            <option value="" disabled selected>Select your state</option>
            <option value="Andhra Pradesh">Andhra Pradesh</option>
            <option value="Arunachal Pradesh">Arunachal Pradesh</option>
            <option value="Assam">Assam</option>
            <option value="Bihar">Bihar</option>
            <option value="Chhattisgarh">Chhattisgarh</option>
            <option value="Goa">Goa</option>
            <option value="Gujarat">Gujarat</option>
            <option value="Haryana">Haryana</option>
            <option value="Himachal Pradesh">Himachal Pradesh</option>
            <option value="Jharkhand">Jharkhand</option>
            <option value="Karnataka">Karnataka</option>
            <option value="Kerala">Kerala</option>
            <option value="Madhya Pradesh">Madhya Pradesh</option>
            <option value="Maharashtra">Maharashtra</option>
            <option value="Manipur">Manipur</option>
            <option value="Meghalaya">Meghalaya</option>
            <option value="Mizoram">Mizoram</option>
            <option value="Nagaland">Nagaland</option>
            <option value="Odisha">Odisha</option>
            <option value="Punjab">Punjab</option>
            <option value="Rajasthan">Rajasthan</option>
            <option value="Sikkim">Sikkim</option>
            <option value="Tamil Nadu">Tamil Nadu</option>
            <option value="Telangana">Telangana</option>
            <option value="Tripura">Tripura</option>
            <option value="Uttar Pradesh">Uttar Pradesh</option>
            <option value="Uttarakhand">Uttarakhand</option>
            <option value="West Bengal">West Bengal</option>
            <option value="Delhi">Delhi</option>
            <option value="Jammu and Kashmir">Jammu and Kashmir</option>
          </select>
        </div>

        <button onclick="onbNext(1)" class="btn" style="width:100%; padding:14px; font-weight:600;">CONTINUE</button>
      </div>

      <!-- Step 2: Experience -->
      <div id="onb-step-2" class="onb-pane" style="display:none; animation: fade-in 0.3s ease;">
        <h3 style="font-size:1.1rem; color:var(--white); margin-bottom:8px; font-weight:600;">2. How experienced are you in the stock market?</h3>
        <p style="font-size:0.8rem; color:var(--dim); margin-bottom:24px;">We tailor terminology and adjust default risk gates based on your experience.</p>
        
        <div style="margin-bottom:24px;">
          <label style="display:block; font-size:0.75rem; text-transform:uppercase; color:var(--text); letter-spacing:1px; margin-bottom:10px; font-weight:600;">Experience Level</label>
          <div style="display:grid; grid-template-columns:1fr; gap:10px;">
            <button onclick="selectOnbExperience('Beginner', this)" class="btn onb-exp-btn" style="background:var(--p2); border:1px solid var(--border); text-align:left; padding:14px; font-size:0.9rem; color:var(--text); border-radius:6px; transition:all 0.2s;">🔰 <b>BEGINNER</b> — Just starting out or under 1 year</button>
            <button onclick="selectOnbExperience('Intermediate', this)" class="btn onb-exp-btn active" style="background:var(--p2); border:1px solid var(--cyan); text-align:left; padding:14px; font-size:0.9rem; color:var(--text); border-radius:6px; transition:all 0.2s;">📈 <b>INTERMEDIATE</b> — Understand basics, buy/sell stocks</button>
            <button onclick="selectOnbExperience('Advanced', this)" class="btn onb-exp-btn" style="background:var(--p2); border:1px solid var(--border); text-align:left; padding:14px; font-size:0.9rem; color:var(--text); border-radius:6px; transition:all 0.2s;">🔥 <b>ADVANCED</b> — Familiar with technicals and stop losses</button>
            <button onclick="selectOnbExperience('Professional', this)" class="btn onb-exp-btn" style="background:var(--p2); border:1px solid var(--border); text-align:left; padding:14px; font-size:0.9rem; color:var(--text); border-radius:6px; transition:all 0.2s;">👑 <b>PROFESSIONAL</b> — Pro trader, quantitative models</button>
          </div>
        </div>

        <div style="margin-bottom:28px;">
          <label style="display:block; font-size:0.75rem; text-transform:uppercase; color:var(--text); letter-spacing:1px; margin-bottom:8px; font-weight:600;">Investing/Trading Duration</label>
          <div class="chip-grid" id="onb-duration-container">
            <div class="chip" onclick="selectOnbSingle('duration', 'Less than 1 year', this)">< 1 year</div>
            <div class="chip active" onclick="selectOnbSingle('duration', '1-3 years', this)">1-3 years</div>
            <div class="chip" onclick="selectOnbSingle('duration', '3+ years', this)">3+ years</div>
          </div>
        </div>

        <div style="display:flex; gap:12px;">
          <button onclick="onbBack(2)" class="btn" style="background:var(--p2); border:1px solid var(--border); color:var(--text); flex:1; font-weight:600;">BACK</button>
          <button onclick="onbNext(2)" class="btn" style="flex:2; font-weight:600;">CONTINUE</button>
        </div>
      </div>

      <!-- Step 3: Goals -->
      <div id="onb-step-3" class="onb-pane" style="display:none; animation: fade-in 0.3s ease;">
        <h3 style="font-size:1.1rem; color:var(--white); margin-bottom:8px; font-weight:600;">3. What are your primary investment goals?</h3>
        <p style="font-size:0.8rem; color:var(--dim); margin-bottom:24px;">Select all objectives that apply to your current capital.</p>
        
        <div class="chip-grid" style="margin-bottom:28px; gap:12px;" id="onb-goals-container">
          <div class="chip" onclick="toggleOnbGoal('Long-term wealth creation', this)" style="padding:10px 14px; font-size:0.85rem;">📈 Long-term wealth creation</div>
          <div class="chip" onclick="toggleOnbGoal('Short-term trading', this)" style="padding:10px 14px; font-size:0.85rem;">⚡ Short-term trading</div>
          <div class="chip" onclick="toggleOnbGoal('Intraday trading', this)" style="padding:10px 14px; font-size:0.85rem;">🏎️ Intraday trading</div>
          <div class="chip" onclick="toggleOnbGoal('Swing trading', this)" style="padding:10px 14px; font-size:0.85rem;">🌊 Swing trading</div>
          <div class="chip" onclick="toggleOnbGoal('Portfolio building', this)" style="padding:10px 14px; font-size:0.85rem;">🏛️ Portfolio building</div>
        </div>

        <div style="display:flex; gap:12px;">
          <button onclick="onbBack(3)" class="btn" style="background:var(--p2); border:1px solid var(--border); color:var(--text); flex:1; font-weight:600;">BACK</button>
          <button onclick="onbNext(3)" class="btn" style="flex:2; font-weight:600;">CONTINUE</button>
        </div>
      </div>

      <!-- Step 4: Risk Profile -->
      <div id="onb-step-4" class="onb-pane" style="display:none; animation: fade-in 0.3s ease;">
        <h3 style="font-size:1.1rem; color:var(--white); margin-bottom:8px; font-weight:600;">4. Define your risk comfort zone</h3>
        <p style="font-size:0.8rem; color:var(--dim); margin-bottom:24px;">Helps us establish safety margins and filter high-volatility recommendations.</p>
        
        <div style="margin-bottom:24px;">
          <label style="display:block; font-size:0.75rem; text-transform:uppercase; color:var(--text); letter-spacing:1px; margin-bottom:10px; font-weight:600;">Which portfolio would you be most comfortable with?</label>
          <select id="onb-risk-comfort" style="width:100%; padding:12px 14px; background:var(--p2); border:1px solid var(--border); border-radius:6px; color:var(--white); font-size:0.9rem; outline:none; transition:border-color 0.2s;" onchange="onbSelections.riskComfort = this.value;">
            <option value="Conservative">🟢 Capital First (Lower volatility • Protect wealth)</option>
            <option value="Moderately Conservative">🟡 Steady Growth (Lower risk • Consistent growth)</option>
            <option value="Moderate" selected>🟠 Balanced Growth (Moderate risk • Growth + stability)</option>
            <option value="Aggressive">🔴 High Growth (Higher volatility • Higher growth potential)</option>
            <option value="Very Aggressive">🟣 Maximum Growth (Very high volatility • Maximum growth potential)</option>
          </select>
        </div>

        <div style="margin-bottom:28px;">
          <label style="display:block; font-size:0.75rem; text-transform:uppercase; color:var(--text); letter-spacing:1px; margin-bottom:10px; font-weight:600;">Your ₹1,00,000 investment falls to ₹75,000 in 2 weeks. What feels most like you?</label>
          <select id="onb-risk-scenario" style="width:100%; padding:12px 14px; background:var(--p2); border:1px solid var(--border); border-radius:6px; color:var(--white); font-size:0.9rem; outline:none; transition:border-color 0.2s;" onchange="onbSelections.riskScenario = this.value;">
            <option value="sell_all">🛡️ “I want out.” (Protect what's left)</option>
            <option value="sell_some">😟 “I'll reduce my exposure.” (Cut some risk)</option>
            <option value="hold" selected>😐 “I'll wait and reassess.” (Stay invested)</option>
            <option value="hold_strong">💪 “I'm comfortable holding.” (Ignore short-term noise)</option>
            <option value="buy_more">🔥 “This is an opportunity.” (Consider adding)</option>
          </select>
        </div>

        <div style="display:flex; gap:12px;">
          <button onclick="onbBack(4)" class="btn" style="background:var(--p2); border:1px solid var(--border); color:var(--text); flex:1; font-weight:600;">BACK</button>
          <button onclick="onbNext(4)" class="btn" style="flex:2; font-weight:600;">CONTINUE</button>
        </div>
      </div>

      <!-- Step 5: Preferences -->
      <div id="onb-step-5" class="onb-pane" style="display:none; animation: fade-in 0.3s ease;">
        <h3 style="font-size:1.1rem; color:var(--white); margin-bottom:8px; font-weight:600;">5. What markets & styles do you trade?</h3>
        <p style="font-size:0.8rem; color:var(--dim); margin-bottom:24px;">We filters recommended opportunities to match your chosen styles.</p>
        
        <div style="margin-bottom:24px;">
          <label style="display:block; font-size:0.75rem; text-transform:uppercase; color:var(--text); letter-spacing:1px; margin-bottom:10px; font-weight:600;">Preferred Markets</label>
          <div class="chip-grid" id="onb-markets-container" style="gap:10px;">
            <div class="chip active" onclick="toggleOnbMarket('Equity', this)" style="padding:10px 14px;">📈 Equity</div>
            <div class="chip" onclick="toggleOnbMarket('Commodities', this)" style="padding:10px 14px;">🪵 Commodities</div>
          </div>
        </div>

        <div style="display:flex; gap:12px;">
          <button onclick="onbBack(5)" class="btn" style="background:var(--p2); border:1px solid var(--border); color:var(--text); flex:1; font-weight:600;">BACK</button>
          <button onclick="onbNext(5)" class="btn" style="flex:2; font-weight:600;">CONTINUE</button>
        </div>
      </div>

      <!-- Step 6: Sectors & Seeding -->
      <div id="onb-step-6" class="onb-pane" style="display:none; animation: fade-in 0.3s ease;">
        <h3 style="font-size:1.1rem; color:var(--white); margin-bottom:8px; font-weight:600;">6. Sector Preferences & Watchlist</h3>
        <p style="font-size:0.8rem; color:var(--dim); margin-bottom:24px;">We check exclusions to filter out sectors you don't wish to invest in.</p>
        
        <div style="margin-bottom:24px;">
          <label style="display:block; font-size:0.75rem; text-transform:uppercase; color:var(--text); letter-spacing:1px; margin-bottom:10px; font-weight:600;">Preferred Sectors (Excludes unselected)</label>
          <div style="margin-bottom: 12px; display: flex; gap: 10px;">
            <button onclick="selectAllSectors()" class="btn" style="background:var(--p2); border:1px solid var(--border); padding:6px 12px; font-size:0.8rem; color:var(--text); border-radius:4px;">Select All</button>
            <button onclick="deselectAllSectors()" class="btn" style="background:var(--p2); border:1px solid var(--border); padding:6px 12px; font-size:0.8rem; color:var(--text); border-radius:4px;">Deselect All</button>
          </div>
          <div class="chip-grid" id="onb-sectors-container" style="gap:10px;">
            <div class="chip" onclick="toggleOnbSector('IT', this)" style="padding:10px 14px;">🖥️ IT</div>
            <div class="chip" onclick="toggleOnbSector('Banking', this)" style="padding:10px 14px;">🏦 Banking</div>
            <div class="chip" onclick="toggleOnbSector('Pharma', this)" style="padding:10px 14px;">💊 Pharma</div>
            <div class="chip" onclick="toggleOnbSector('Auto', this)" style="padding:10px 14px;">🚗 Auto</div>
            <div class="chip" onclick="toggleOnbSector('Energy', this)" style="padding:10px 14px;">⚡ Energy</div>
            <div class="chip" onclick="toggleOnbSector('FMCG', this)" style="padding:10px 14px;">📦 FMCG</div>
            <div class="chip" onclick="toggleOnbSector('Defence', this)" style="padding:10px 14px;">🛡️ Defence</div>
            <div class="chip" onclick="toggleOnbSector('Infrastructure', this)" style="padding:10px 14px;">🏗️ Infra</div>
            <div class="chip" onclick="toggleOnbSector('Telecom', this)" style="padding:10px 14px;">📡 Telecom</div>
          </div>
        </div>

        <div style="display:flex; gap:12px;">
          <button onclick="onbBack(6)" class="btn" style="background:var(--p2); border:1px solid var(--border); color:var(--text); flex:1; font-weight:600;">BACK</button>
          <button onclick="onbNext(6)" class="btn" style="flex:2; font-weight:600;">CONTINUE</button>
        </div>
      </div>

      <!-- Step 7: Capital & Horizon -->
      <div id="onb-step-7" class="onb-pane" style="display:none; animation: fade-in 0.3s ease;">
        <h3 style="font-size:1.1rem; color:var(--white); margin-bottom:8px; font-weight:600;">7. Investment Capital & Horizon</h3>
        <p style="font-size:0.8rem; color:var(--dim); margin-bottom:24px;">Directly guides capital allocation risk limits and lot sizes.</p>
        
        <div style="margin-bottom:28px;">
          <label style="display:block; font-size:0.75rem; text-transform:uppercase; color:var(--text); letter-spacing:1px; margin-bottom:8px; font-weight:600;">Starting Capital (₹)</label>
          <div style="position:relative; text-align:center; margin-bottom: 20px;">
             <span id="capital-display" style="font-family:'JetBrains Mono',monospace; color:var(--cyan); font-size:1.5rem; font-weight:bold;">₹1,00,000</span>
          </div>
          <input type="range" id="onb-capital" min="5000" max="10000000" step="5000" value="100000" 
            style="width:100%; cursor:pointer;" oninput="document.getElementById('capital-display').innerText = '₹' + parseInt(this.value).toLocaleString('en-IN')">
        </div>

        <div style="display:flex; gap:12px;">
          <button onclick="onbBack(7)" class="btn" style="background:var(--p2); border:1px solid var(--border); color:var(--text); flex:1; font-weight:600;">BACK</button>
          <button onclick="onbNext(7)" class="btn" style="flex:2; font-weight:600;">CALCULATE LIMITS</button>
        </div>
      </div>

      <!-- Step 8: Confirm Risk Limits -->
      <div id="onb-step-8" class="onb-pane" style="display:none; animation: fade-in 0.3s ease;">
        <h3 style="font-size:1.2rem; color:var(--white); margin-bottom:12px; font-weight:600; text-align:center;">📋 CONFIRM DERIVED RISK PARAMETERS</h3>
        <p style="font-size:0.8rem; color:var(--dim); margin-bottom:24px; text-align:center;">These settings will govern automated recommendation safeguards.</p>
        
        <div style="background:var(--p2); border:1px solid var(--border); border-radius:8px; padding:20px; margin-bottom:28px; font-family:'JetBrains Mono',monospace; font-size:0.85rem;">
          <div style="display:flex; justify-content:space-between; margin-bottom:12px;">
            <span style="color:var(--dim);">Full Name:</span>
            <span id="rev-name" style="color:var(--white); font-weight:bold;">--</span>
          </div>
          <div style="display:flex; justify-content:space-between; margin-bottom:12px;">
            <span style="color:var(--dim);">Experience Level:</span>
            <span id="rev-exp" style="color:var(--white); font-weight:bold; text-transform:uppercase;">--</span>
          </div>
          <div style="display:flex; justify-content:space-between; margin-bottom:12px;">
            <span style="color:var(--dim);">Primary Goal:</span>
            <span id="rev-goal" style="color:var(--white); font-weight:bold; text-transform:uppercase;">--</span>
          </div>
          <div style="display:flex; justify-content:space-between; margin-bottom:12px;">
            <span style="color:var(--dim);">Starting Capital:</span>
            <span id="rev-capital" style="color:var(--green); font-weight:bold;">₹--</span>
          </div>
          <div style="display:flex; justify-content:space-between; margin-bottom:12px; border-top:1px solid var(--border); padding-top:12px;">
            <span style="color:var(--dim);">Derived Max Position:</span>
            <span id="rev-max-pos" style="color:var(--gold); font-weight:bold;">10%</span>
          </div>
          <div style="display:flex; justify-content:space-between;">
            <span style="color:var(--dim);">Derived Max Sector:</span>
            <span id="rev-max-sec" style="color:var(--gold); font-weight:bold;">30%</span>
          </div>
        </div>

        <button onclick="submitOnboarding()" class="btn" style="width:100%; padding:16px; font-size:1rem; font-weight:700; background:var(--green); color:var(--white); box-shadow:0 0 20px rgba(8,153,129,0.3); border-radius:6px; transition:transform 0.2s, box-shadow 0.2s;">
          🚀 SAVE PROFILE & START TERMINAL
        </button>
      </div>

    </div>
  </div>
</div>
<style>
@keyframes fade-in {
  from { opacity: 0; transform: translateY(5px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
"""

JS = r"""
let onbSelectedExperience = 'Intermediate';
let onbGoals = [];
let onbMarkets = ['Equity'];
let onbStyles = [];
let onbSectors = [];

let onbSelections = {
  age: '25-34',
  occupation: 'Job',
  duration: '1-3 years',
  horizon: 'Months'
};

function selectAllSectors() {
  onbSectors = ['IT', 'Banking', 'Pharma', 'Auto', 'Energy', 'FMCG', 'Defence', 'Infrastructure', 'Telecom'];
  document.querySelectorAll('#onb-sectors-container .chip').forEach(chip => chip.classList.add('active'));
}

function deselectAllSectors() {
  onbSectors = [];
  document.querySelectorAll('#onb-sectors-container .chip').forEach(chip => chip.classList.remove('active'));
}

function selectOnbSingle(group, val, el) {
  onbSelections[group] = val;
  const container = el.parentElement;
  
  if (el.classList.contains('chip')) {
    container.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
    el.classList.add('active');
  } else if (el.classList.contains('onb-single-btn')) {
    container.querySelectorAll('.onb-single-btn').forEach(btn => {
      btn.classList.remove('active');
      btn.style.borderColor = 'var(--border)';
    });
    el.classList.add('active');
    el.style.borderColor = 'var(--cyan)';
  }
}

function selectOnbExperience(val, btn) {
  onbSelectedExperience = val;
  const container = btn.parentElement;
  container.querySelectorAll('.onb-exp-btn').forEach(b => {
    b.classList.remove('active');
    b.style.borderColor = 'var(--border)';
  });
  if (btn) {
    btn.classList.add('active');
    btn.style.borderColor = 'var(--cyan)';
  }
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
  
  const progBar = document.getElementById('onb-progress');
  if (progBar) {
    progBar.style.width = Math.min(100, (step / 7) * 100) + '%';
  }
}

function showOnbError(msg) {
  const errDiv = document.getElementById('onb-error');
  if (errDiv) {
    errDiv.textContent = msg;
    errDiv.style.display = 'block';
    errDiv.style.background = 'rgba(239, 83, 80, 0.1)';
    errDiv.style.border = '1px solid var(--red)';
    errDiv.style.color = 'var(--red)';
  }
}

let calculatedPosPct = 10;
let calculatedSecPct = 30;

function calculateAndShowLimits() {
  const name = document.getElementById('onb-name').value.trim();
  const capital = parseFloat(document.getElementById('onb-capital').value) || 100000;
  const comfortElement = document.getElementById('onb-risk-comfort');
  const comfort = comfortElement ? comfortElement.value : 'Moderate';

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
  document.getElementById('rev-exp').textContent = onbSelectedExperience + ' (' + onbSelections.duration + ')';
  document.getElementById('rev-goal').textContent = onbGoals.slice(0, 2).join(', ') + (onbGoals.length > 2 ? '...' : '');
  document.getElementById('rev-capital').textContent = '₹' + capital.toLocaleString('en-IN');
  document.getElementById('rev-max-pos').textContent = calculatedPosPct + '% (₹' + (capital * calculatedPosPct / 100).toLocaleString('en-IN') + ' max per stock)';
  document.getElementById('rev-max-sec').textContent = calculatedSecPct + '% (₹' + (capital * calculatedSecPct / 100).toLocaleString('en-IN') + ' max per sector)';

  document.querySelectorAll('.onb-pane').forEach(p => p.style.display = 'none');
  document.getElementById('onb-step-8').style.display = 'block';
  
  const indicator = document.getElementById('onb-step-indicator');
  if (indicator) indicator.textContent = 'Verification';
  
  const progBar = document.getElementById('onb-progress');
  if (progBar) progBar.style.width = '100%';
}

async function submitOnboarding() {
  const errDiv = document.getElementById('onb-error');
  if (errDiv) errDiv.style.display = 'none';

  const name = document.getElementById('onb-name').value.trim();
  const age = onbSelections.age;
  const occupation = onbSelections.occupation;
  const locationElement = document.getElementById('onb-location');
  const location = locationElement ? locationElement.value : '';
  const duration = onbSelections.duration;
  const comfortElement = document.getElementById('onb-risk-comfort');
  const comfort = comfortElement ? comfortElement.value : 'Moderate';
  const scenarioElement = document.getElementById('onb-risk-scenario');
  const scenario = scenarioElement ? scenarioElement.value : 'hold';
  const horizon = onbSelections.horizon;
  const capital = parseFloat(document.getElementById('onb-capital').value) || 100000;
  
  let watchlistSymbols = [];

  const payload = {
    display_name: name,
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

