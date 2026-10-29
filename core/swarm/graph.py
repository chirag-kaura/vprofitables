"""
core/swarm/graph.py
===================
Master Hierarchical Multi-Agent Swarm Orchestrator.
Coordinates:
  1. Master Supervisor Router (Context budgeting & entity resolution)
  2. 6 Domain Specialist Subgraphs in conditional fan-out:
     - Derivatives & Microstructure Agent
     - Quant & Gann Mathematical Agent
     - Deep ML Predictive Signals Agent
     - Vedic Astro & Celestial Timing Agent
     - Fundamental & News Sentiment Agent
     - OHLC Technical Price Action Agent
  3. Dossier Aggregator & Qwen 2.5:3b Local Edge Synthesizer
"""

import os
import sys
from typing import Dict, Any, List, Optional
from langgraph.graph import StateGraph, START, END

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.swarm.state import SwarmState
from core.swarm.supervisor import node_supervisor, route_to_specialists
from core.swarm.subgraphs.derivatives_subgraph import derivatives_subgraph
from core.swarm.subgraphs.quant_subgraph import quant_subgraph
from core.swarm.subgraphs.ml_subgraph import ml_subgraph
from core.swarm.subgraphs.astro_subgraph import astro_subgraph
from core.swarm.subgraphs.fundamental_subgraph import fundamental_subgraph
from core.swarm.subgraphs.ohlc_subgraph import ohlc_subgraph
from core.swarm.aggregator import node_aggregate_and_synthesize
from core.swarm.cache import global_cache, make_query_key, TTL_QUERY_RESPONSE

def build_swarm_graph():
    """Compiles the full Hierarchical LangGraph Multi-Agent Swarm."""
    builder = StateGraph(SwarmState)

    # 1. Master Supervisor Node
    builder.add_node("supervisor", node_supervisor)

    # 2. Domain Specialist Subgraph Nodes
    builder.add_node("derivatives_agent", derivatives_subgraph)
    builder.add_node("quant_agent", quant_subgraph)
    builder.add_node("deep_ml_agent", ml_subgraph)
    builder.add_node("astro_agent", astro_subgraph)
    builder.add_node("fundamental_agent", fundamental_subgraph)
    builder.add_node("ohlc_agent", ohlc_subgraph)

    # 3. Dossier Aggregator & Synthesizer Node
    builder.add_node("aggregator", node_aggregate_and_synthesize)

    # 4. Routing Graph Edges
    builder.add_edge(START, "supervisor")

    # Conditional fan-out to specialists or direct to aggregator if off-topic
    builder.add_conditional_edges(
        "supervisor",
        route_to_specialists,
        {
            "derivatives_agent": "derivatives_agent",
            "quant_agent": "quant_agent",
            "deep_ml_agent": "deep_ml_agent",
            "astro_agent": "astro_agent",
            "fundamental_agent": "fundamental_agent",
            "ohlc_agent": "ohlc_agent",
            "aggregator": "aggregator"
        }
    )

    # All specialists fan-in to Dossier Aggregator
    builder.add_edge("derivatives_agent", "aggregator")
    builder.add_edge("quant_agent", "aggregator")
    builder.add_edge("deep_ml_agent", "aggregator")
    builder.add_edge("astro_agent", "aggregator")
    builder.add_edge("fundamental_agent", "aggregator")
    builder.add_edge("ohlc_agent", "aggregator")

    # Aggregator outputs to END
    builder.add_edge("aggregator", END)

    return builder.compile()

# Singleton compiled swarm
swarm_graph = build_swarm_graph()

def run_swarm_graph(
    query: str,
    symbol: Optional[str] = None,
    history: Optional[List[Dict[str, str]]] = None,
    skip_llm: bool = False,
    model: Optional[str] = None
) -> Dict[str, Any]:
    """
    Public entrypoint for the Multi-Agent Swarm.
    Takes user natural language query and executes through the hierarchical state graph.
    Employs sub-millisecond in-memory query response caching for repeated questions.
    """
    query_key = f"{make_query_key(query, symbol)}:{model or 'default'}"
    if not skip_llm and not history:
        cached_result = global_cache.get(query_key)
        if cached_result is not None:
            res_copy = dict(cached_result)
            res_copy["is_cached"] = True
            return res_copy

    initial_state: SwarmState = {
        "query": query,
        "symbol": symbol,
        "second_symbol": None,
        "intent": "",
        "domains": [],
        "sub_intents": [],
        "timeframe": None,
        "history": history or [],
        "tool_results": [],
        "aggregated_context": "",
        "is_off_topic": False,
        "is_foreign_crypto": False,
        "skip_llm": skip_llm,
        "selected_model": model,
        "final_response": ""
    }
    res = swarm_graph.invoke(initial_state)

    if not skip_llm and not history and res.get("final_response") and not res.get("is_off_topic"):
        global_cache.set(query_key, res, ttl=TTL_QUERY_RESPONSE)

    return res
