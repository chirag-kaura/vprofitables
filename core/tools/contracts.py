"""
core/tools/contracts.py
======================
Standard Data Contract for the Vprofitables Unified Tool Adapter Layer.
Guarantees consistent, zero-hallucination, structured outputs across all domains:
OHLC, Derivatives, Smart Money, 10Y Financials, Quant/Gann, Deep ML, and Astro.
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
import time

class ToolResult(BaseModel):
    domain: str = Field(description="Domain name: DERIVATIVES, SMART_MONEY, QUANT_GANN, WYCKOFF, DEEP_ML, ASTRO, FINANCIALS, OHLC, NEWS")
    symbol: Optional[str] = Field(default=None, description="Underlying NSE symbol or index")
    headline_metric: str = Field(description="Single-line institutional summary metric")
    tabular_summary: str = Field(description="Pre-formatted Markdown table ready for LLM grounding")
    raw_data: Dict[str, Any] = Field(default_factory=dict, description="Structured key-value metrics")
    execution_ms: int = Field(default=0, description="Execution time in milliseconds")
    error: Optional[str] = Field(default=None, description="Error message if tool execution failed")

    def to_markdown(self) -> str:
        """Standard Markdown formatting for LLM context grounding."""
        sym_str = f" [{self.symbol}]" if self.symbol else ""
        if self.error:
            return f"### {self.domain}{sym_str} Tool Result\n> [!WARNING]\n> Execution note: {self.error}\n"

        out = [
            f"### {self.domain}{sym_str} Tool Result",
            f"**Headline Metric**: {self.headline_metric}",
            "",
            self.tabular_summary.strip(),
            ""
        ]
        return "\n".join(out)
