import os

widget_html = '''
<!-- ════════════════════════════════════════════════════════════════════
     FLOATING AI ASSISTANT CHATBOT WIDGET (Vprofitables Quant Copilot)
     ════════════════════════════════════════════════════════════════════ -->
<style>
#vprof-ai-widget-container {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
  z-index: 99990;
}

/* Floating Action Button (FAB) */
#vprof-ai-fab {
  position: fixed;
  bottom: 24px;
  right: 24px;
  z-index: 99990;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  background: linear-gradient(135deg, #1E53E5, #0B39A0);
  border: 1px solid rgba(0, 212, 255, 0.4);
  border-radius: 30px;
  color: #FFFFFF;
  cursor: pointer;
  box-shadow: 0 6px 24px rgba(30, 83, 229, 0.45), 0 2px 8px rgba(0,0,0,0.6);
  transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
  user-select: none;
}
#vprof-ai-fab:hover {
  transform: translateY(-2px) scale(1.02);
  box-shadow: 0 8px 30px rgba(0, 212, 255, 0.5), 0 4px 12px rgba(0,0,0,0.7);
  border-color: rgba(0, 212, 255, 0.7);
}
#vprof-ai-fab .fab-icon {
  font-size: 1.15rem;
  line-height: 1;
}
#vprof-ai-fab .fab-label {
  font-weight: 600;
  font-size: 0.82rem;
  letter-spacing: 0.3px;
}
#vprof-ai-fab .fab-badge {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.68rem;
  background: rgba(0, 0, 0, 0.35);
  border: 1px solid rgba(255, 255, 255, 0.2);
  padding: 2px 6px;
  border-radius: 10px;
  color: #FF9800;
  font-weight: 700;
}

/* Chat Drawer Window */
#vprof-ai-chat-drawer {
  position: fixed;
  bottom: 78px;
  right: 24px;
  width: 440px;
  max-width: calc(100vw - 32px);
  height: 590px;
  max-height: calc(100vh - 100px);
  background: #11151F;
  border: 1px solid rgba(41, 98, 255, 0.4);
  border-radius: 12px;
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.8), 0 0 0 1px rgba(255, 255, 255, 0.05);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  z-index: 99995;
  animation: vprofChatSlideUp 0.22s cubic-bezier(0.16, 1, 0.3, 1);
}

@keyframes vprofChatSlideUp {
  from { opacity: 0; transform: translateY(16px) scale(0.97); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}

/* Drawer Header */
.vprof-chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  background: #151924;
  border-bottom: 1px solid #2B3139;
}
.vprof-chat-header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}
.vprof-chat-header-icon {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  background: linear-gradient(135deg, #2962FF, #1E53E5);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.95rem;
  color: #FFF;
}
.vprof-chat-header-title {
  font-size: 0.85rem;
  font-weight: 700;
  color: #FFFFFF;
}
.vprof-chat-header-subtitle {
  font-size: 0.68rem;
  color: #787B86;
  display: flex;
  align-items: center;
  gap: 5px;
}
.vprof-chat-header-subtitle .status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #089981;
  display: inline-block;
}
.vprof-chat-header-right {
  display: flex;
  align-items: center;
  gap: 6px;
}
.vprof-chat-select {
  background: #1E222D;
  color: #D1D4DC;
  border: 1px solid #363A45;
  border-radius: 4px;
  padding: 4px 6px;
  font-size: 0.72rem;
  font-family: 'JetBrains Mono', monospace;
  font-weight: 600;
  outline: none;
  cursor: pointer;
  max-width: 110px;
}
.vprof-chat-select:focus {
  border-color: #2962FF;
}
.vprof-chat-btn-icon {
  background: transparent;
  border: none;
  color: #787B86;
  cursor: pointer;
  padding: 4px 6px;
  border-radius: 4px;
  font-size: 0.85rem;
  transition: all 0.15s;
}
.vprof-chat-btn-icon:hover {
  background: #1E222D;
  color: #FFFFFF;
}

/* Quick Suggestion Chips */
.vprof-chat-suggestions {
  display: flex;
  gap: 6px;
  padding: 8px 12px;
  overflow-x: auto;
  white-space: nowrap;
  background: #0D1017;
  border-bottom: 1px solid rgba(255, 255, 255, 0.04);
  scrollbar-width: none;
}
.vprof-chat-suggestions::-webkit-scrollbar {
  display: none;
}
.vprof-chat-chip {
  background: #1E222D;
  border: 1px solid #2B3139;
  border-radius: 14px;
  padding: 4px 10px;
  font-size: 0.7rem;
  color: #B2B5BE;
  cursor: pointer;
  transition: all 0.15s;
  flex-shrink: 0;
}
.vprof-chat-chip:hover {
  background: rgba(41, 98, 255, 0.15);
  border-color: #2962FF;
  color: #FFFFFF;
}

/* Message History Stream */
.vprof-chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  background: #0B0E14;
}
.vprof-chat-msg {
  display: flex;
  gap: 10px;
  max-width: 94%;
}
.vprof-chat-msg.msg-user {
  align-self: flex-end;
  flex-direction: row-reverse;
}
.vprof-chat-msg.msg-assistant {
  align-self: flex-start;
}
.vprof-msg-avatar {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  background: #1E222D;
  border: 1px solid #363A45;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.75rem;
  flex-shrink: 0;
}
.msg-user .vprof-msg-avatar {
  background: #2962FF;
  color: #FFF;
  border-color: transparent;
}
.vprof-msg-bubble {
  background: #151924;
  border: 1px solid #2B3139;
  border-radius: 8px;
  padding: 10px 12px;
  font-size: 0.78rem;
  line-height: 1.5;
  color: #D1D4DC;
  word-break: break-word;
}
.msg-user .vprof-msg-bubble {
  background: #1E3A8A;
  border-color: #2563EB;
  color: #FFFFFF;
}

/* Markdown styling inside bubble */
.vprof-msg-bubble h3 { font-size: 0.88rem; margin: 4px 0 6px 0; color: #FFF; }
.vprof-msg-bubble h4 { font-size: 0.82rem; margin: 8px 0 4px 0; color: #FF9800; }
.vprof-msg-bubble p { margin-bottom: 6px; }
.vprof-msg-bubble p:last-child { margin-bottom: 0; }
.vprof-msg-bubble ul { margin: 4px 0 6px 18px; padding: 0; }
.vprof-msg-bubble li { margin-bottom: 3px; }
.vprof-msg-bubble blockquote {
  border-left: 3px solid #2962FF;
  background: rgba(41, 98, 255, 0.08);
  margin: 6px 0;
  padding: 6px 10px;
  font-style: italic;
  font-size: 0.74rem;
  color: #B2B5BE;
  border-radius: 0 4px 4px 0;
}
.vprof-msg-bubble table {
  width: 100%;
  border-collapse: collapse;
  margin: 8px 0;
  font-size: 0.7rem;
}
.vprof-msg-bubble th, .vprof-msg-bubble td {
  border: 1px solid #2B3139;
  padding: 4px 6px;
  text-align: left;
}
.vprof-msg-bubble th {
  background: #1E222D;
  color: #FF9800;
}

/* Typing Row */
.vprof-chat-typing-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 14px;
  background: #0B0E14;
  font-size: 0.72rem;
  color: #787B86;
  border-top: 1px solid rgba(255, 255, 255, 0.03);
}
.vprof-typing-dots {
  display: inline-flex;
  gap: 3px;
}
.vprof-typing-dots span {
  width: 4px;
  height: 4px;
  background: #2962FF;
  border-radius: 50%;
  animation: vprofBlink 1.4s infinite both;
}
.vprof-typing-dots span:nth-child(2) { animation-delay: 0.2s; }
.vprof-typing-dots span:nth-child(3) { animation-delay: 0.4s; }
@keyframes vprofBlink {
  0%, 80%, 100% { opacity: 0.2; transform: scale(0.8); }
  40% { opacity: 1; transform: scale(1.2); }
}

/* Input Area */
.vprof-chat-input-area {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  background: #151924;
  border-top: 1px solid #2B3139;
}
.vprof-chat-textarea {
  flex: 1;
  background: #0B0E14;
  border: 1px solid #2B3139;
  border-radius: 6px;
  padding: 8px 10px;
  font-size: 0.78rem;
  color: #FFFFFF;
  font-family: inherit;
  resize: none;
  outline: none;
  max-height: 80px;
  min-height: 36px;
  line-height: 1.4;
  transition: border-color 0.15s;
}
.vprof-chat-textarea:focus {
  border-color: #2962FF;
}
.vprof-chat-send-btn {
  background: #2962FF;
  border: none;
  color: #FFFFFF;
  border-radius: 6px;
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.15s;
  flex-shrink: 0;
  font-size: 0.95rem;
}
.vprof-chat-send-btn:hover {
  background: #1E53E5;
  transform: scale(1.05);
}
.vprof-chat-send-btn:disabled {
  background: #2B3139;
  color: #787B86;
  cursor: not-allowed;
  transform: none;
}

@media(max-width: 600px) {
  #vprof-ai-chat-drawer {
    width: calc(100vw - 20px);
    right: 10px;
    bottom: 74px;
    height: 70vh;
  }
}
</style>

<div id="vprof-ai-widget-container">
  <!-- Trigger Button -->
  <button id="vprof-ai-fab" onclick="toggleAIChatDrawer()" title="Open AI Quant Copilot">
    <span class="fab-icon">⚡</span>
    <span class="fab-label">AI Copilot</span>
    <span id="vprof-ai-fab-sym" class="fab-badge">NIFTY 500</span>
  </button>

  <!-- Drawer Window -->
  <div id="vprof-ai-chat-drawer" style="display:none;">
    <!-- Header -->
    <div class="vprof-chat-header">
      <div class="vprof-chat-header-left">
        <div class="vprof-chat-header-icon">⚡</div>
        <div>
          <div class="vprof-chat-header-title">Vprofitables Copilot</div>
          <div class="vprof-chat-header-subtitle">
            <span class="status-dot"></span>
            <span id="vprof-chat-model-label">Ollama / In-Memory RAG</span>
          </div>
        </div>
      </div>
      <div class="vprof-chat-header-right">
        <button class="vprof-chat-btn-icon" onclick="clearAIChatHistory()" title="Clear Chat History">🗑️</button>
        <button class="vprof-chat-btn-icon" onclick="toggleAIChatDrawer()" title="Close Copilot">✕</button>
      </div>
    </div>

    <!-- Suggestions Bar -->
    <div id="vprof-chat-suggestions" class="vprof-chat-suggestions">
      <div class="vprof-chat-chip" onclick="askQuickPrompt('Which stock has fallen max in last 5 days?')">📉 5D Losers</div>
      <div class="vprof-chat-chip" onclick="askQuickPrompt('Which stock has gained most today?')">🚀 Top Gainers</div>
      <div class="vprof-chat-chip" onclick="askQuickPrompt('Compare TCS vs INFY')">⚖️ TCS vs INFY</div>
      <div class="vprof-chat-chip" onclick="askQuickPrompt('What was revenue and net profit in latest FY?')">📊 FY Financials</div>
      <div class="vprof-chat-chip" onclick="askQuickPrompt('What is management forward guidance and capex?')">🎙️ Concall Guidance</div>
    </div>

    <!-- Messages Container -->
    <div id="vprof-chat-messages" class="vprof-chat-messages">
      <div class="vprof-chat-msg msg-assistant">
        <div class="vprof-msg-avatar">⚡</div>
        <div class="vprof-msg-bubble">
          <h3>Vprofitables Quant Copilot</h3>
          <p>Quantitative terminal copilot for <strong>500+ NSE Equities</strong>. Instant technical screeners & verified audited financials.</p>
          <p style="color:#00d4ff; font-size:0.72rem; margin-top:4px;">
            🔒 <em>Zero hallucinations: exact figures verified in ₹ Crores. Ask for screeners, fundamentals, or concall guidance.</em>
          </p>
        </div>
      </div>
    </div>

    <!-- Typing Row -->
    <div id="vprof-chat-typing" class="vprof-chat-typing-row" style="display:none;">
      <div class="vprof-typing-dots"><span></span><span></span><span></span></div>
      <span id="vprof-chat-typing-text">Analyzing SQLite financials & transcripts...</span>
    </div>

    <!-- Input Area -->
    <div class="vprof-chat-input-area">
      <textarea id="vprof-chat-input" class="vprof-chat-textarea" rows="1" placeholder="Ask about earnings, margins, guidance..." onkeydown="handleChatInputKey(event)"></textarea>
      <button id="vprof-chat-send-btn" class="vprof-chat-send-btn" onclick="sendAIChatMessage()" title="Send Message">
        ➔
      </button>
    </div>
  </div>
</div>
'''

head_path = os.path.join("pages", "_html_head.html")
with open(head_path, "r", encoding="utf-8") as f:
    orig = f.read()

if "vprof-ai-widget-container" not in orig:
    with open(head_path, "a", encoding="utf-8") as f:
        f.write("\n" + widget_html)
    print("Appended floating AI widget to pages/_html_head.html")
else:
    print("Widget already present in pages/_html_head.html")
