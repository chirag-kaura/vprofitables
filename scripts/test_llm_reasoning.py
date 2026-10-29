import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.tools.portfolio_tool import fetch_portfolio_positions
import urllib.request
import json
import time

port = fetch_portfolio_positions(user_id=1)
pos_lines = []
for p in port.get("positions", []):
    pos_lines.append(f"- {p['symbol']}: {p['shares']} shares, Entry: Rs {p['entry_price']:,.2f}, CMP: Rs {p['current_price']:,.2f}, PnL: Rs {p['pnl']:,.2f} ({p['pnl_pct']:.1f}%), Sector: {p['sector']}, Health: {p['health']}")

positions_str = "\n".join(pos_lines)

prompt = f"""You are Vprofitables Quant Copilot, an elite quantitative hedge fund trading assistant.
Your trading engine operates strictly on two principles:
1. Reversal days and price levels (Gann Sq9, cycle turning dates).
2. Continuation days and price levels (20-EMA trend, momentum).

ACTIVE TRADER CONTEXT:
Total Invested: Rs {port['total_invested']:,.2f} | Current Value: Rs {port['current_value']:,.2f} | Overall PnL: Rs {port['unrealized_pnl']:,.2f} ({port['unrealized_pct']:.2f}%)
Active Holdings:
{positions_str}

Sector Allocation: {port.get('sector_weights')}

TRADER'S INQUIRY:
"Which of my positions is performing worst and what should I do with it?"

Provide a concise, direct, professional quantitative answer in markdown format. Be specific with figures."""

payload = json.dumps({
    "model": "gemma4:latest",
    "prompt": prompt,
    "stream": False,
    "keep_alive": "24h",
    "options": {
        "temperature": 0.15,
        "num_predict": 300
    }
}).encode("utf-8")

req = urllib.request.Request(
    "http://localhost:11434/api/generate",
    data=payload,
    headers={"Content-Type": "application/json"}
)

print("Sending prompt to Ollama gemma4...")
t0 = time.time()
with urllib.request.urlopen(req, timeout=30) as resp:
    data = json.loads(resp.read().decode("utf-8"))
    print(f"Done in {time.time()-t0:.2f}s!")
    print("\nREPLY:\n" + data.get("response", ""))
