import sys, os
sys.path.insert(0, os.getcwd())
from core.tools.capital_allocation_tool import allocate_capital, format_capital_allocation_markdown

plan = allocate_capital(amount_inr=50000.0, user_id=1)
print("Allocation plan generated successfully:")
print("Regime:", plan["regime"]["regime"])
print("Sectors:", plan["sectors_count"])
print("Allocations:", [a["symbol"] for a in plan["allocations"]])
md = format_capital_allocation_markdown(plan)
print("Markdown length:", len(md))
print("First 200 chars:\n", md[:200])
