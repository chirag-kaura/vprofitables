"""
core/swarm/subgraphs/ml_subgraph.py
===================================
Deep Learning & Machine Learning Predictive Specialist Subgraph.
Responsible for:
  - PyTorch Deep MLP Trend Continuation Probability & CWT Wavelet Phase
  - XGBoost Multi-Horizon Directional Reversal Classifier
"""

from typing import List, Dict, Any
from langgraph.graph import StateGraph, START, END
from core.swarm.state import SwarmState, SpecialistOutput
from core.tools.contracts import ToolResult
from core.tools.ml_signal_tools import ml_trend_continuation, ml_deep_reversal_score

def node_execute_ml(state: SwarmState) -> Dict[str, Any]:
    """Executes PyTorch MLP and XGBoost deep learning predictive tools."""
    sym = state.get("symbol")
    sym2 = state.get("second_symbol")
    sub_intents = state.get("sub_intents", [])
    results: List[ToolResult] = []

    if not sym:
        return {"tool_results": []}

    # Comparison Mode
    if "comparison" in sub_intents and sym and sym2:
        if "ml_continuation" in sub_intents or "deep_ml" in state.get("domains", []):
            results.append(ml_trend_continuation(sym))
            results.append(ml_trend_continuation(sym2))
        if "ml_reversal" in sub_intents:
            results.append(ml_deep_reversal_score(sym))
            results.append(ml_deep_reversal_score(sym2))
        return {"tool_results": results}

    # Single-Stock Mode
    run_all = ("dossier" in sub_intents) or (not sub_intents)

    # 1. PyTorch Deep MLP Trend Continuation
    if run_all or "ml_continuation" in sub_intents:
        results.append(ml_trend_continuation(sym))

    # 2. XGBoost Multi-Horizon Reversal Score
    if run_all or "ml_reversal" in sub_intents:
        results.append(ml_deep_reversal_score(sym))

    return {"tool_results": results}

def build_ml_subgraph():
    builder = StateGraph(SwarmState, output_schema=SpecialistOutput)
    builder.add_node("exec_ml", node_execute_ml)
    builder.add_edge(START, "exec_ml")
    builder.add_edge("exec_ml", END)
    return builder.compile()

ml_subgraph = build_ml_subgraph()
