import os

widget_js = r'''
// ════════════════════════════════════════════════════════════════════
// FLOATING AI ASSISTANT CHATBOT CONTROLLER (Vprofitables Quant Copilot)
// ════════════════════════════════════════════════════════════════════
(function() {
  window.__vprof_chat_symbol = "";
  window.__vprof_symbols_loaded = false;

  // Simple Markdown Parser for Assistant Responses
  function parseMarkdown(md) {
    if (!md) return "";
    let html = md;
    
    // Escape standard HTML
    html = html.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    html = html.replace(/&lt;(\/?(?:div|button|span|b|strong|em|p|blockquote|table|tr|th|td|ul|li|br|hr)[^&]*)&gt;/gi, '<$1>');
    html = html.replace(/(<[^>]+?)&quot;/g, '$1"');

    // Unescape our specific table pipes and blockquote markers
    html = html.replace(/^&gt;\s?(.*)$/gm, '<blockquote>$1</blockquote>');
    
    // Headers
    html = html.replace(/^### (.*$)/gim, '<h3>$1</h3>');
    html = html.replace(/^#### (.*$)/gim, '<h4>$1</h4>');
    
    // Bold & Italic
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');
    
    // Unordered lists
    html = html.replace(/^\- (.*$)/gim, '<li>$1</li>');
    html = html.replace(/(<li>.*<\/li>)/gim, '<ul>$1</ul>');
    // Deduplicate nested <ul> tags
    html = html.replace(/<\/ul>\s*<ul>/g, '');

    // Tables
    const lines = html.split('\n');
    let inTable = false;
    let tableHtml = '';
    let newLines = [];

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i].trim();
      if (line.startsWith('|') && line.endsWith('|')) {
        if (!inTable) {
          inTable = true;
          tableHtml = '<table>';
        }
        if (line.includes('---')) {
          continue; // separator line
        }
        const cells = line.split('|').slice(1, -1);
        const isHeader = !tableHtml.includes('<tr>');
        const tag = isHeader ? 'th' : 'td';
        tableHtml += '<tr>' + cells.map(c => `<${tag}>${c.trim()}</${tag}>`).join('') + '</tr>';
      } else {
        if (inTable) {
          tableHtml += '</table>';
          newLines.push(tableHtml);
          inTable = false;
          tableHtml = '';
        }
        newLines.push(lines[i]);
      }
    }
    if (inTable) {
      tableHtml += '</table>';
      newLines.push(tableHtml);
    }
    html = newLines.join('\n');

    // Paragraph linebreaks (excluding tables/lists/headers)
    html = html.replace(/\n\n/g, '<br><br>');
    return html;
  }

  // Toggle Drawer Open/Close
  window.toggleAIChatDrawer = function() {
    const drawer = document.getElementById("vprof-ai-chat-drawer");
    if (!drawer) return;
    const isHidden = drawer.style.display === "none" || !drawer.style.display;
    if (isHidden) {
      drawer.style.display = "flex";
      // Auto-focus input
      setTimeout(() => {
        const inp = document.getElementById("vprof-chat-input");
        if (inp) inp.focus();
        scrollChatToBottom();
      }, 100);
      loadSymbolsCatalog();
      loadChatStatus();
      syncActiveSymbolContext();
    } else {
      drawer.style.display = "none";
    }
  };

  // Scroll message thread to bottom
  function scrollChatToBottom() {
    const container = document.getElementById("vprof-chat-messages");
    if (container) {
      container.scrollTop = container.scrollHeight;
    }
  }


  // ── Session & Status Helpers ──────────────────────────────────────────────
  function getChatSessionId() {
    try {
      let sid = sessionStorage.getItem("vprof_chat_session_id");
      if (!sid) {
        sid = "sess_" + Math.random().toString(36).substring(2, 10) + "_" + Date.now();
        sessionStorage.setItem("vprof_chat_session_id", sid);
      }
      return sid;
    } catch (e) {
      return "sess_fallback_" + Date.now();
    }
  }

  // Load Status / Model Info
  async function loadChatStatus() {
    try {
      const res = await fetch("/api/chat/status").then(r => r.json());
      const label = document.getElementById("vprof-chat-model-label");
      if (label && res) {
        if (res.active_model) {
          label.textContent = res.active_model;
        } else if (res.model) {
          label.textContent = res.model;
        }
      }
    } catch (err) {
      // Non-fatal
    }
  }

  // Sync active page symbol into chatbot (badge only, no sticky dropdown)
  function syncActiveSymbolContext() {
    try {
      let sym = null;
      const urlParams = new URLSearchParams(window.location.search);
      if (urlParams.get("sym")) sym = urlParams.get("sym");
      else if (urlParams.get("symbol")) sym = urlParams.get("symbol");
      else if (window.selectedSymbol) sym = window.selectedSymbol;
      else if (window.currentSymbol) sym = window.currentSymbol;

      if (sym) {
        sym = sym.toUpperCase().trim();
        const fabBadge = document.getElementById("vprof-ai-fab-sym");
        if (fabBadge) fabBadge.textContent = sym;
      }
    } catch (e) {
      // Non-fatal
    }
  }

  // Load 501 Symbols into dropdown
  async function loadSymbolsCatalog() { /* Deprecated - Zero Dropdown Architecture */ }


  // Symbol change handler
  window.onChatSymbolChange = function(sym) {};


  // Quick Prompt chip clicked
  window.askQuickPrompt = function(promptText) {
    const input = document.getElementById("vprof-chat-input");
    if (input) {
      input.value = promptText;
      window.sendAIChatMessage();
    }
  };

  // Clear chat messages
  window.clearAIChatHistory = function() {
    const container = document.getElementById("vprof-chat-messages");
    if (container) {
      container.innerHTML = `
        <div class="vprof-chat-msg msg-assistant">
          <div class="vprof-msg-avatar">⚡</div>
          <div class="vprof-msg-bubble">
            <h3>Vprofitables Quant Copilot</h3>
            <p>Chat cleared. Ask anything regarding <strong>${window.__vprof_chat_symbol || 'RELIANCE'}</strong> or any of the 501 tracked equities.</p>
          </div>
        </div>
      `;
    }
  };

  // Keyboard listener
  window.handleChatInputKey = function(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      window.sendAIChatMessage();
    }
  };

  // Send message API call
  window.sendAIChatMessage = async function() {
    const input = document.getElementById("vprof-chat-input");
    const sendBtn = document.getElementById("vprof-chat-send-btn");
    const typing = document.getElementById("vprof-chat-typing");
    const container = document.getElementById("vprof-chat-messages");

    if (!input || !input.value.trim()) return;
    const msg = input.value.trim();
    input.value = "";

    // 1. Append User Message
    const userDiv = document.createElement("div");
    userDiv.className = "vprof-chat-msg msg-user";
    userDiv.innerHTML = `
      <div class="vprof-msg-avatar">👤</div>
      <div class="vprof-msg-bubble">${msg.replace(/</g, "&lt;").replace(/>/g, "&gt;")}</div>
    `;
    container.appendChild(userDiv);
    scrollChatToBottom();

    // 2. Show Typing Indicator
    if (typing) typing.style.display = "flex";
    if (sendBtn) sendBtn.disabled = true;

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: msg,
          session_id: getChatSessionId()
        })
      }).then(r => r.json());

      if (typing) typing.style.display = "none";
      if (sendBtn) sendBtn.disabled = false;

      if (res && res.error) {
        const errDiv = document.createElement("div");
        errDiv.className = "vprof-chat-msg msg-assistant";
        errDiv.innerHTML = `
          <div class="vprof-msg-avatar">⚠️</div>
          <div class="vprof-msg-bubble" style="border-color:#F23645; color:#F23645;">
            <strong>Error:</strong> ${res.error}
          </div>
        `;
        container.appendChild(errDiv);
      } else if (res && res.reply) {
        // Sync detected symbol if different
        if (res.symbol && res.symbol !== window.__vprof_chat_symbol) {
          window.__vprof_chat_symbol = res.symbol;
          
          const fabBadge = document.getElementById("vprof-ai-fab-sym");
          if (fabBadge) fabBadge.textContent = res.symbol;
        }

        // Update model label
        if (res.model_used) {
          const label = document.getElementById("vprof-chat-model-label");
          if (label) label.textContent = res.is_fallback ? "Deterministic RAG" : res.model_used;
        }

        const replyHtml = parseMarkdown(res.reply);
        const botDiv = document.createElement("div");
        botDiv.className = "vprof-chat-msg msg-assistant";
        botDiv.innerHTML = `
          <div class="vprof-msg-avatar">⚡</div>
          <div class="vprof-msg-bubble">${replyHtml}</div>
        `;
        container.appendChild(botDiv);
      }
    } catch (err) {
      if (typing) typing.style.display = "none";
      if (sendBtn) sendBtn.disabled = false;
      const errDiv = document.createElement("div");
      errDiv.className = "vprof-chat-msg msg-assistant";
      errDiv.innerHTML = `
        <div class="vprof-msg-avatar">⚠️</div>
        <div class="vprof-msg-bubble" style="border-color:#F23645;">
          <strong>Connection Error:</strong> Could not reach AI Copilot backend server.
        </div>
      `;
      container.appendChild(errDiv);
    }

    scrollChatToBottom();
  };

  
  // ── Institutional In-Chat Paper Trade Execution ─────────────────────────────
  window.executePaperTrade = async function(symbol, shares, entryPrice, stopLoss, target1, btnElem) {
    if (!btnElem) return;
    const originalText = btnElem.innerHTML;
    btnElem.disabled = true;
    btnElem.innerHTML = '⏳ Committing Order to Risk Engine...';

    try {
      const resp = await fetch('/api/chat/execute_order', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          symbol: symbol,
          shares: shares,
          entry_price: entryPrice,
          stop_loss: stopLoss,
          target1: target1,
          order_type: 'BUY'
        })
      });
      const data = await resp.json();
      if (data && data.status === 'success') {
        btnElem.innerHTML = `✅ Order Filled (#${data.order_id || 'OPEN'}) · Active in Portfolio`;
        btnElem.style.background = '#059669';
        btnElem.style.cursor = 'default';
        btnElem.disabled = true;
      } else {
        alert('Order Execution Error: ' + (data.error || 'Failed to place paper trade.'));
        btnElem.disabled = false;
        btnElem.innerHTML = originalText;
      }
    } catch (e) {
      alert('Network Error placing order: ' + e.message);
      btnElem.disabled = false;
      btnElem.innerHTML = originalText;
    }
  };

  // Keyboard shortcut: Ctrl + Space or Alt + C to toggle Copilot
  document.addEventListener("keydown", function(e) {
    if ((e.ctrlKey && e.code === "Space") || (e.altKey && (e.key === "c" || e.key === "C"))) {
      e.preventDefault();
      window.toggleAIChatDrawer();
    }
  });

  // Run initial symbol synchronization on page load
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", syncActiveSymbolContext);
  } else {
    syncActiveSymbolContext();
  }
})();
'''

shared_path = os.path.join("pages", "_shared.js")
with open(shared_path, "r", encoding="utf-8") as f:
    orig = f.read()

if "FLOATING AI ASSISTANT CHATBOT CONTROLLER" not in orig:
    with open(shared_path, "a", encoding="utf-8") as f:
        f.write("\n" + widget_js)
    print("Appended floating AI controller to pages/_shared.js")
else:
    print("Controller already present in pages/_shared.js")
