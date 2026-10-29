import os
import re

helpers_code = '''
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
'''

def update_file(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Insert helpers right before loadSymbolsCatalog
    target = "  // Load 501 Symbols into dropdown"
    if target in content and "function getChatSessionId" not in content:
        content = content.replace(target, helpers_code + "\n" + target, 1)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Successfully injected helpers into {filepath}")
    elif "function getChatSessionId" in content:
        print(f"Helpers already in {filepath}")
    else:
        # Fallback: insert before sendAIChatMessage
        target_fallback = "  // Send message API call"
        if target_fallback in content:
            content = content.replace(target_fallback, helpers_code + "\n" + target_fallback, 1)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"Injected helpers before sendAIChatMessage in {filepath}")
        else:
            print(f"Target not found in {filepath}")

update_file("scripts/append_chat_js.py")
update_file("pages/_shared.js")
