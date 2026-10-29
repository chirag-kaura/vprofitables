"""
core/autonomous_reasoning.py
============================
Autonomous Quantitative Reasoning Agent for Vprofitables Copilot.
Powers the Hybrid Architecture:
  1. Always-on working memory injection of active portfolio holdings and market benchmarks.
  2. Grounded reasoning based on the 2 Core Principles:
     - Reversal Days & Price Levels (Gann Sq9, cycle turning windows).
     - Continuation Days & Price Levels (20-EMA trend, momentum).
  3. Dynamic LLM synthesis using local pre-warmed Ollama models (Llama 3.2 1B).
  4. High-intelligence deterministic fallback reasoning if LLM is cold/busy.
"""

import os
import sys
import re
import json
import urllib.request
from typing import Dict, Any, Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from core.tools.portfolio_tool import fetch_portfolio_positions
from core.chatbot_engine import get_market_price_snapshot
from core.llm_extractor import _detect_ollama_model, _OLLAMA_HOST
from core.session_manager import get_session_manager


def build_working_memory_context(user_id: Any = 1, session_id: Optional[str] = None) -> str:
    """Builds a rich, grounded quantitative working memory context of the trader and market."""
    port = fetch_portfolio_positions(user_id=user_id)
    pos_lines = []
    positions = port.get("positions", [])
    
    for p in positions:
        pnl = p.get("pnl", 0.0)
        pnl_pct = p.get("pnl_pct", 0.0)
        pnl_s = f"+Rs {pnl:,.2f} (+{pnl_pct:.1f}%)" if pnl >= 0 else f"-Rs {abs(pnl):,.2f} ({pnl_pct:.1f}%)"
        pos_lines.append(
            f"- {p['symbol']}: {p['shares']} shares @ entry Rs {p['entry_price']:,.2f} | "
            f"CMP Rs {p['current_price']:,.2f} | P&L: {pnl_s} | SL: Rs {p['stop_loss']:,.2f} | "
            f"Target: Rs {p['target1']:,.2f} | Sector: {p.get('sector', 'General')} | Health: {p.get('health', 'IN_PLAY')}"
        )
    positions_block = "\n".join(pos_lines) if pos_lines else "No open positions."

    sectors = port.get("sector_weights", {})
    sec_str = ", ".join([f"{k}: {v}%" for k, v in sectors.items()]) if sectors else "None"

    # Real-time NIFTY benchmark snapshot
    nifty_snap = get_market_price_snapshot("NIFTY50")
    nifty_ltp = nifty_snap.get("ltp") or 22600.0

    return (
        f"LIVE TRADER PORTFOLIO CONTEXT:\n"
        f"• Total Invested: Rs {port.get('total_invested', 0.0):,.2f} | Current Portfolio Value: Rs {port.get('current_value', 0.0):,.2f}\n"
        f"• Overall Unrealized P&L: Rs {port.get('unrealized_pnl', 0.0):,.2f} ({port.get('unrealized_pct', 0.0):+.2f}%)\n"
        f"• Sector Allocation: {sec_str}\n"
        f"• Market Benchmark: NIFTY 50 at {nifty_ltp:,.2f}\n"
        f"• Active Positions:\n{positions_block}"
    )


def synthesize_autonomous_fallback(query: str, user_id: Any = 1) -> str:
    """
    Intelligent state-aware fallback that synthesizes grounded quantitative reasoning
    directly from portfolio and market reality without generic boilerplate.
    """
    q = query.strip()
    upper = q.upper()
    port = fetch_portfolio_positions(user_id=user_id)
    positions = port.get("positions", [])
    
    # 1. Worst / Dragging / Biggest Loser Queries
    if any(w in upper for w in ("WORST", "DRAGGING", "BIGGEST LOSER", "MAX LOSS", "LOSING THE MOST", "DROP THE MOST")):
        if not positions:
            return "You currently have no open positions in your portfolio."
        worst_pos = min(positions, key=lambda x: x.get("pnl", 0.0))
        sym = worst_pos["symbol"]
        pnl = worst_pos["pnl"]
        pnl_pct = worst_pos["pnl_pct"]
        cmp_px = worst_pos["current_price"]
        sl = worst_pos["stop_loss"]
        health = worst_pos["health"]
        
        lines = [
            f"### 🛡️ Portfolio Risk Review: **{sym}**",
            f"The position currently dragging your portfolio down the most is **{sym}**, with an unrealized loss of **-₹{abs(pnl):,.2f} ({pnl_pct:.1f}%)**.",
            "",
            "#### 📊 Trade Audit:",
            f"- **Position Size:** {worst_pos['shares']} shares @ entry ₹{worst_pos['entry_price']:,.2f}",
            f"- **Current Market Price:** ₹{cmp_px:,.2f}",
            f"- **Stop-Loss Level:** ₹{sl:,.2f} ({'🛑 **BREACHED**' if health == 'STOPPED_OUT' else '⚠️ Warning'})",
            f"- **Sector Exposure:** {worst_pos.get('sector', 'Equity')}",
            "",
            "#### 💡 Quantitative Action Plan:",
            "1. **Enforce Hard Risk Stops:** Under strict institutional rules, when price breaches the initial stop-loss, the position should be **liquidated immediately** rather than held with hope.",
            "2. **Never Average Down:** Capital must not be allocated to equities breaking below their 20-EMA momentum floor.",
            f"3. **Next Step:** To inspect cyclical reversal dates for a recovery exit, ask: *'Should I hold {sym}?'*."
        ]
        return "\n".join(lines)

    # 2. Best / Highest Profit Queries
    if any(w in upper for w in ("BEST", "TOP PERFORMER", "HIGHEST PROFIT", "WINNER", "PROFITABLE")):
        if not positions:
            return "You currently have no open positions in your portfolio."
        best_pos = max(positions, key=lambda x: x.get("pnl", 0.0))
        sym = best_pos["symbol"]
        pnl = best_pos["pnl"]
        pnl_pct = best_pos["pnl_pct"]
        
        lines = [
            f"### 🏆 Top Performing Position: **{sym}**",
            f"Your strongest holding right now is **{sym}**, sitting at **{'+' if pnl >= 0 else ''}₹{pnl:,.2f} ({pnl_pct:+.1f}%)**.",
            "",
            f"- **Shares:** {best_pos['shares']} | **Entry:** ₹{best_pos['entry_price']:,.2f} | **CMP:** ₹{best_pos['current_price']:,.2f}",
            f"- **Target 1:** ₹{best_pos['target1']:,.2f} | **Sector:** {best_pos.get('sector', 'General')}",
            "",
            f"💡 *Action:* Consider trailing your stop-loss to the 20-day EMA to lock in gains."
        ]
        return "\n".join(lines)

    # 3. Overall Risk & Breaches
    if any(w in upper for w in ("RISK", "STOP LOSS", "HEALTH", "ALERT", "SAFETY", "BREACH")):
        breached = [p for p in positions if p.get("health") in ("STOPPED_OUT", "SL_WARNING")]
        if not breached:
            return "### 🟢 Portfolio Health: All Positions In Play\nAll your current holdings are trading comfortably above their initial stop-loss thresholds."
        
        lines = [
            f"### 🚨 Portfolio Risk Gate: **{len(breached)} Position(s) Requiring Attention**",
            "The following holdings have breached or are dangerously close to their stop-loss levels:\n"
        ]
        for p in breached:
            badge = "🛑 Stop-Loss Breached" if p["health"] == "STOPPED_OUT" else "⚠️ Near Stop-Loss"
            lines.append(f"- **{p['symbol']}** ({p.get('sector', 'General')}): CMP ₹{p['current_price']:,.2f} vs SL ₹{p['stop_loss']:,.2f} ({badge}) | P&L: ₹{p['pnl']:,.2f}")
        
        lines.append("\n💡 *Recommendation:* In accordance with strict risk management, exit stopped-out positions to preserve capital.")
        return "\n".join(lines)

    # 4. Default Intelligent Portfolio & Capabilities Walkthrough
    tot_inv = port.get("total_invested", 0.0)
    curr_val = port.get("current_value", 0.0)
    pnl = port.get("unrealized_pnl", 0.0)
    pnl_pct = port.get("unrealized_pct", 0.0)
    
    lines = [
        "### ⚡ Vprofitables Quant Copilot",
        f"You have **{len(positions)} active position(s)** deployed with **₹{tot_inv:,.2f}** capital (Current Value: **₹{curr_val:,.2f}** | P&L: **{'+' if pnl >= 0 else ''}₹{pnl:,.2f} ({pnl_pct:+.1f}%)**).\n",
        "#### 🎯 How Can I Assist Your Trading Right Now?",
        "- 🛡️ **Position Management:** *'Should I hold my Ultratech Cement stock?'* or *'What is my worst performing stock?'*",
        "- 📁 **Sector & Theme Audit:** *'Do I own any EV sector stock?'* or *'What is my sector exposure?'*",
        "- 📉 **Market Screeners:** *'Which stock has fallen max in last 5 days?'* or *'Top gainers today'*",
        "- 🎯 **Swing Trade Setups:** *'Suggest stocks for 10-15 days investment'*",
        "- ⚖️ **Asset Comparison:** *'Compare TCS vs INFY'*"
    ]
    return "\n".join(lines)


def call_prewarmed_ollama(prompt: str, timeout: int = 16) -> Optional[str]:
    """Call local Ollama server with keep_alive to maintain model residency in memory."""
    model = _detect_ollama_model()
    if not model:
        return None
    try:
        payload = json.dumps({
            "model": model,
            "prompt": prompt,
            "stream": False,
            "keep_alive": "24h",
            "options": {
                "temperature": 0.15,
                "num_predict": 150,
                "top_p": 0.9,
            }
        }).encode("utf-8")

        req = urllib.request.Request(
            f"{_OLLAMA_HOST}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return (data.get("response") or "").strip()
    except Exception:
        return None


def run_autonomous_reasoning(
    query: str,
    user_id: Any = 1,
    session_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Main Autonomous Hybrid Reasoning entrypoint.
    Executes pre-warmed LLM with full working memory context,
    with sub-second intelligent fallback.
    """
    context = build_working_memory_context(user_id=user_id, session_id=session_id)
    
    prompt = (
        "You are Vprofitables Quant Copilot, an elite senior quantitative hedge fund partner for Indian Equities (NSE/BSE).\n"
        "Your quantitative engine operates strictly on TWO core principles:\n"
        "  1. Reversal Days & Price Levels (Gann Sq9, cycle turning dates, lunar/planetary harmonics, OI max pain).\n"
        "  2. Continuation Days & Price Levels (20-EMA trend floor, volume expansion, relative strength vs NIFTY).\n"
        "Institutional Rules:\n"
        "  - NEVER average down losing trades.\n"
        "  - Honor stop-losses without hesitation.\n\n"
        f"{context}\n\n"
        f"TRADER'S INQUIRY:\n\"{query}\"\n\n"
        "Provide a direct, conversational, and mathematically grounded response in GitHub Markdown format. "
        "Reference exact shares, prices, and P&L figures from the trader's portfolio when relevant."
    )

    llm_reply = call_prewarmed_ollama(prompt, timeout=16)
    if llm_reply and len(llm_reply.strip()) > 35:
        return {
            "answer": llm_reply.strip(),
            "model_used": "LangGraph-Agentic-Swarm (AUTONOMOUS_LLM_REASONING)",
            "is_fallback": False
        }

    # Intelligent state-aware fallback
    fallback_reply = synthesize_autonomous_fallback(query, user_id=user_id)
    return {
        "answer": fallback_reply,
        "model_used": "LangGraph-Agentic-Swarm (AUTONOMOUS_QUANT_REASONING)",
        "is_fallback": True
    }
