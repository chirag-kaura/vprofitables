"""
core/swarm/subgraphs/derivatives_subgraph.py
============================================
Derivatives Specialist Subgraph.
Responsible for:
  - Put-Call Ratio (PCR), Max Pain, ATM Strike, Call/Put Walls
  - FII, Pro, Client Participant Open Interest positioning
  - Institutional Bulk and Block Deals Flow
"""

import re
from typing import List, Dict, Any
from langgraph.graph import StateGraph, START, END
from core.swarm.state import SwarmState, SpecialistOutput
from core.tools.contracts import ToolResult
from core.tools.derivatives_tools import derivatives_pcr_maxpain, derivatives_participant_oi
from core.tools.smart_money_tools import smart_money_deal_flow

def node_execute_derivatives(state: SwarmState) -> Dict[str, Any]:
    """Executes derivatives and institutional flow tools."""
    sym = state.get("symbol")
    sym2 = state.get("second_symbol")
    sub_intents = state.get("sub_intents", [])
    results: List[ToolResult] = []

    # Comparison Mode
    if "comparison" in sub_intents and sym and sym2:
        if "derivatives_pcr" in sub_intents or "options" in state.get("domains", []):
            results.append(derivatives_pcr_maxpain(sym))
            results.append(derivatives_pcr_maxpain(sym2))
        if "smart_money_deals" in sub_intents:
            results.append(smart_money_deal_flow(sym, limit=4))
            results.append(smart_money_deal_flow(sym2, limit=4))
        return {"tool_results": results}

    # Single-Stock / Market-Wide Mode
    run_all = ("dossier" in sub_intents) or (not sub_intents)
    
    # 1. PCR & Max Pain
    if run_all or "derivatives_pcr" in sub_intents or "options" in sub_intents:
        results.append(derivatives_pcr_maxpain(sym or "NIFTY"))

    # 2. Participant OI
    if run_all or "participant_oi" in sub_intents or not sym:
        results.append(derivatives_participant_oi())

    # 3. Institutional Bulk/Block Deals
    if run_all or "smart_money_deals" in sub_intents:
        results.append(smart_money_deal_flow(sym, limit=5))

    return {"tool_results": results}

def build_derivatives_subgraph():
    builder = StateGraph(SwarmState, output_schema=SpecialistOutput)
    builder.add_node("exec_derivatives", node_execute_derivatives)
    builder.add_edge(START, "exec_derivatives")
    builder.add_edge("exec_derivatives", END)
    return builder.compile()

derivatives_subgraph = build_derivatives_subgraph()
