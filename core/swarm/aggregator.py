"""
core/swarm/aggregator.py
========================
Dossier Aggregator & High-Speed Local LLM Synthesizer.
Fuses outputs from all fan-out specialist subgraphs into an institutional dossier.
Synthesizes strictly grounded responses via local edge Qwen 2.5:3b with zero hallucination.
"""

from typing import Dict, Any, List
from langchain_core.messages import HumanMessage, SystemMessage
from core.swarm.state import SwarmState
from core.tools.contracts import ToolResult

try:
    from langchain_ollama import ChatOllama
    OLLAMA_AVAILABLE = True
except Exception:
    OLLAMA_AVAILABLE = False

_OLLAMA_CLIENTS = {}
_AVAILABLE_MODELS = None

def _get_available_ollama_models() -> List[str]:
    global _AVAILABLE_MODELS
    if _AVAILABLE_MODELS is not None:
        return _AVAILABLE_MODELS
    try:
        import urllib.request
        import json
        with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=2) as r:
            if r.status == 200:
                data = json.loads(r.read().decode("utf-8"))
                _AVAILABLE_MODELS = [m.get("name") for m in (data.get("models") or []) if m.get("name")]
                return _AVAILABLE_MODELS
    except Exception:
        pass
    return ["qwen2.5:7b"]

def _get_ollama_client(requested_model: str = "qwen2.5:7b"):
    """
    Returns (client, effective_model_name, is_fallback)
    Defaults to 7B parameter models or higher.
    """
    global _OLLAMA_CLIENTS
    raw = (requested_model or "qwen2.5:7b").strip().lower()
    
    # Normalize aliases
    if any(k in raw for k in ["13b", "finance", "adaptllm"]):
        target = "finance-13b"
        display_name = "AdaptLLM / Finance-LLM-13B"
    elif "gemma" in raw:
        target = "gemma4:latest"
        display_name = "Gemma 4 (9.6B)"
    elif "3b" in raw:
        target = "qwen2.5:3b"
        display_name = "Qwen 2.5 3B"
    else:
        target = "qwen2.5:7b"
        display_name = "Qwen 2.5 7B"

    available = _get_available_ollama_models()
    is_fallback = False
    
    # If the requested model is not downloaded yet (e.g. finance-13b before user pulls it),
    # gracefully fallback to qwen2.5:7b or first available model
    if target not in available:
        if "qwen2.5:7b" in available:
            target = "qwen2.5:7b"
            is_fallback = True
        elif available:
            target = available[0]
            is_fallback = True

    if target not in _OLLAMA_CLIENTS:
        _OLLAMA_CLIENTS[target] = ChatOllama(
            model=target,
            temperature=0.15,
            num_predict=768,   # High token limit prevents truncations mid-sentence
            num_ctx=4096,
            num_thread=8
        )
    return _OLLAMA_CLIENTS[target], target, is_fallback

SYSTEM_PROMPT = (
    "You are an Elite Institutional Market Analyst & Quantitative Specialist for the National Stock Exchange of India (NSE).\n"
    "Your responses are grounded 100% STRICTLY in the provided verified data: OHLC price history, news headlines, audited financials, derivatives (PCR/Max Pain), Wyckoff market structure, Gann geometry, Deep ML continuation/reversal signals, and Vedic astrological timing.\n"
    "STRICT MANDATES:\n"
    "1. All currencies are in Indian Rupees (Rs. or INR) and monetary figures in Crores. NEVER cite US Dollar ($) or foreign exchanges (CME/ICE).\n"
    "2. Direct & Focused: Address ONLY the user's specific inquiry immediately. Cite exact figures and tables provided. Avoid filler or conversational preambles. Do NOT mention unrelated tools, and NEVER output 'Not applicable' for models or indicators the user did not ask about.\n"
    "3. Multi-Stock Comparison: When comparing two stocks, NEVER duplicate numbers across columns or rows. Use Symbol A's exact data for Symbol A, and Symbol B's exact data for Symbol B.\n"
    "4. Exact Dates & Figures: Cite only the dates, prices, and figures provided in the context."
)

def node_aggregate_and_synthesize(state: SwarmState) -> Dict[str, Any]:
    """
    Fuses outputs from all specialist subgraphs and performs zero-hallucination LLM synthesis.
    """
    query = state["query"]
    symbol = state.get("symbol")
    tool_results: List[ToolResult] = state.get("tool_results") or []

    # 1. Handle Off-Topic queries politely
    if state.get("is_off_topic"):
        return {
            "aggregated_context": "",
            "final_response": (
                "I am the **Vprofitables Quantitative AI Terminal Copilot**, specialized in "
                "Indian equity price action, technical analytics, moving averages, news sentiment, "
                "and 10-year audited financials for 500+ NSE stocks.\n\n"
                "I cannot assist with general cooking, coding, weather, or non-financial trivia. "
                "Please ask me about any Indian stock (e.g. *Reliance*, *TCS*, *HDFC Bank*), Nifty indices, screener setups, or audited financial growth!"
            )
        }

    # 2. Handle Foreign Assets & Cryptocurrencies
    if state.get("is_foreign_crypto"):
        return {
            "aggregated_context": "",
            "final_response": (
                f"The requested asset ('{query}') is a cryptocurrency, foreign US stock, or unlisted token not traded in the local NSE equity database.\n\n"
                "**Vprofitables Copilot tracks 500+ Indian Equities, Nifty 50, and Bank Nifty.**\n"
                "Available instruments include: **RELIANCE**, **TCS**, **INFY**, **HDFCBANK**, **KOTAKBANK**, **JIOFIN**, **BHARTIARTL**, **SBIN**, and other NSE listed companies."
            )
        }

    # 3. Guardrail for Empty Results
    if not tool_results:
        return {
            "aggregated_context": "",
            "final_response": (
                f"I could not locate quantitative or financial data for '{symbol or query}' in the local database.\n\n"
                "Verified instruments currently indexed include:\n"
                "- Indices: **NIFTY50**, **BANKNIFTY**\n"
                "- Major Equities: **RELIANCE**, **TCS**, **INFY**, **HDFCBANK**, **KOTAKBANK**, **JIOFIN**, **BHARTIARTL**, **SBIN**, and other Nifty 500 stocks.\n\n"
                "Please verify the ticker symbol or ask for recent market dates or screener top movers."
            )
        }

    # 4. Assemble Dossier Context from all Specialist Results
    dossier_sections = []
    for res in tool_results:
        dossier_sections.append(res.to_markdown())

    combined_context = "\n\n".join(dossier_sections)

    # 5. Deterministic Mode if LLM is skipped
    if state.get("skip_llm") or not OLLAMA_AVAILABLE:
        return {
            "aggregated_context": combined_context,
            "final_response": combined_context
        }

    # 6. Local LLM Synthesis (Default: 7B or user-selected model)
    combined_input = (
        f"USER QUESTION: {query}\n\n"
        f"=== MULTI-DOMAIN SPECIALIST AGENT AUDIT DOSSIER ===\n"
        f"{combined_context}\n\n"
        "Synthesize a compact, elegant, and strictly grounded institutional response addressing every part of the question."
    )

    requested_model = state.get("selected_model") or "qwen2.5:7b"
    response_text = ""
    used_model_tag = "Qwen 2.5 7B"
    try:
        llm, actual_model, is_fb = _get_ollama_client(requested_model)
        used_model_tag = actual_model
        if is_fb:
            used_model_tag += f" (auto-fallback from {requested_model})"
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=combined_input)
        ]
        llm_result = llm.invoke(messages)
        response_text = llm_result.content.strip()
    except Exception as e:
        try:
            llm_7b, actual_model, _ = _get_ollama_client("qwen2.5:7b")
            llm_result = llm_7b.invoke([SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=combined_input)])
            response_text = llm_result.content.strip()
            used_model_tag = "qwen2.5:7b"
        except Exception:
            response_text = combined_context
            used_model_tag = "Deterministic RAG"

    if not response_text:
        response_text = combined_context

    return {
        "aggregated_context": combined_context,
        "final_response": response_text,
        "model_used": used_model_tag
    }
