"""
core/swarm/state.py
===================
Unified State Schema for the Hierarchical LangGraph Multi-Agent Swarm.
Uses operator.add to collect ToolResults concurrently from fan-out specialist subgraphs.
"""

import operator
from typing import TypedDict, List, Dict, Any, Optional, Annotated
from core.tools.contracts import ToolResult

class SpecialistOutput(TypedDict):
    tool_results: Annotated[List[ToolResult], operator.add]

class SwarmState(TypedDict):
    query: str
    symbol: Optional[str]
    second_symbol: Optional[str]
    intent: str
    domains: List[str]                          # List of active domain specialist subgraphs to invoke
    sub_intents: List[str]                      # Granular tool operations requested
    timeframe: Optional[str]
    history: List[Dict[str, str]]
    tool_results: Annotated[List[ToolResult], operator.add]  # Concurrent accumulator for all specialists
    aggregated_context: str
    is_off_topic: bool
    is_foreign_crypto: bool
    skip_llm: bool
    selected_model: Optional[str]
    final_response: str
