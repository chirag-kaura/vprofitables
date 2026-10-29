"""
core/swarm/subgraphs/astro_subgraph.py
======================================
Vedic Astrology & Celestial Timing Specialist Subgraph.
Responsible for:
  - Vedic Nakshatra, Lordship, Guna, Rahu Kaal, Abhijit Muhurat, and stock alignment score
  - Western harmonic aspects (Trine, Square, Conjunction) and stationary turning points
"""

from typing import List, Dict, Any
from langgraph.graph import StateGraph, START, END
from core.swarm.state import SwarmState, SpecialistOutput
from core.tools.contracts import ToolResult
from core.tools.astro_tools import astro_nakshatra_guidance, astro_planetary_aspects

def node_execute_astro(state: SwarmState) -> Dict[str, Any]:
    """Executes Nakshatra timing and planetary aspect tools."""
    sym = state.get("symbol")
    sub_intents = state.get("sub_intents", [])
    results: List[ToolResult] = []

    run_all = ("dossier" in sub_intents) or (not sub_intents)

    # 1. Nakshatra Alignment
    if run_all or "astro_nakshatra" in sub_intents or sym:
        results.append(astro_nakshatra_guidance(sym or "NIFTY"))

    # 2. Planetary Aspects & Stations
    if run_all or "astro_aspects" in sub_intents or not sym:
        results.append(astro_planetary_aspects())

    return {"tool_results": results}

def build_astro_subgraph():
    builder = StateGraph(SwarmState, output_schema=SpecialistOutput)
    builder.add_node("exec_astro", node_execute_astro)
    builder.add_edge(START, "exec_astro")
    builder.add_edge("exec_astro", END)
    return builder.compile()

astro_subgraph = build_astro_subgraph()
