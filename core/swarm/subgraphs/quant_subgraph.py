"""
core/swarm/subgraphs/quant_subgraph.py
======================================
Quant & Mathematical Specialist Subgraph.
Responsible for:
  - W.D. Gann Square of 9 geometry, cardinal and ordinal support/resistance levels
  - Richard Wyckoff Accumulation/Distribution phases, volatility compression, and hedge fund levels
"""

from typing import List, Dict, Any
from langgraph.graph import StateGraph, START, END
from core.swarm.state import SwarmState, SpecialistOutput
from core.tools.contracts import ToolResult
from core.tools.quant_tools import quant_gann_sq9, quant_wyckoff_structure

def node_execute_quant(state: SwarmState) -> Dict[str, Any]:
    """Executes Gann and Wyckoff quantitative tools."""
    sym = state.get("symbol")
    sym2 = state.get("second_symbol")
    sub_intents = state.get("sub_intents", [])
    results: List[ToolResult] = []

    if not sym:
        return {"tool_results": []}

    # Comparison Mode
    if "comparison" in sub_intents and sym and sym2:
        if "quant_wyckoff" in sub_intents or "quant" in state.get("domains", []):
            results.append(quant_wyckoff_structure(sym))
            results.append(quant_wyckoff_structure(sym2))
        if "quant_gann" in sub_intents:
            results.append(quant_gann_sq9(sym))
            results.append(quant_gann_sq9(sym2))
        return {"tool_results": results}

    # Single-Stock Mode
    run_all = ("dossier" in sub_intents) or (not sub_intents)

    # 1. Gann Square of 9
    if run_all or "quant_gann" in sub_intents:
        results.append(quant_gann_sq9(sym))

    # 2. Wyckoff Market Structure
    if run_all or "quant_wyckoff" in sub_intents:
        results.append(quant_wyckoff_structure(sym))

    return {"tool_results": results}

def build_quant_subgraph():
    builder = StateGraph(SwarmState, output_schema=SpecialistOutput)
    builder.add_node("exec_quant", node_execute_quant)
    builder.add_edge(START, "exec_quant")
    builder.add_edge("exec_quant", END)
    return builder.compile()

quant_subgraph = build_quant_subgraph()
