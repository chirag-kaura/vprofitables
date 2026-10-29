import sqlite3
import re
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "market_data_v2.db")

def classify_client(name: str) -> str:
    name_upper = name.upper()
    inst_keywords = ["FUND", "ASSET", "CAPITAL", "MANAGEMENT", "LTD", "LIMITED", "INVEST", "PARTNERS", "ADVISOR", "TRUST", "SECURITIES", "WEALTH"]
    
    for kw in inst_keywords:
        if kw in name_upper:
            return "INSTITUTIONAL"
            
    if "HUF" in name_upper:
        return "RETAIL_HNI"
        
    # If it doesn't have inst keywords, assume retail/HNI
    return "RETAIL_HNI"


def process_bulk_deals():
    if not os.path.exists(DB_PATH):
        print(f"Error: {DB_PATH} not found.")
        return
        
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    
    # 1. Add client_category to bulk_block_deals if missing
    try:
        conn.execute("ALTER TABLE bulk_block_deals ADD COLUMN client_category TEXT")
    except sqlite3.OperationalError:
        pass
        
    print("Classifying clients in bulk_block_deals...")
    rows = conn.execute("SELECT id, client_name FROM bulk_block_deals WHERE client_category IS NULL").fetchall()
    
    updates = []
    for r in rows:
        cat = classify_client(r[1])
        updates.append((cat, r[0]))
        
    if updates:
        conn.executemany("UPDATE bulk_block_deals SET client_category = ? WHERE id = ?", updates)
        conn.commit()
        print(f"Updated {len(updates)} clients.")

    # 2. Create daily_bulk_summary table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS daily_bulk_summary (
            symbol TEXT NOT NULL,
            deal_date TEXT NOT NULL,
            net_quantity INTEGER,
            net_capital_flow REAL,
            deal_volume_pct REAL,
            institutional_buy_pressure REAL,
            PRIMARY KEY (symbol, deal_date)
        )
    """)
    
    # 3. Aggregate data
    print("Aggregating daily bulk deals into net flows...")
    
    # Fetch all dates and symbols that have deals
    deals_raw = conn.execute("""
        SELECT symbol, deal_date, client_category, deal_type, quantity, price
        FROM bulk_block_deals
    """).fetchall()
    
    # Organize by (symbol, date)
    from collections import defaultdict
    summary = defaultdict(lambda: {
        "inst_buy_qty": 0, "inst_sell_qty": 0,
        "inst_buy_val": 0.0, "inst_sell_val": 0.0,
        "ret_buy_qty": 0, "ret_sell_qty": 0,
        "ret_buy_val": 0.0, "ret_sell_val": 0.0,
        "total_qty_abs": 0,
        "total_buy_qty": 0, "total_sell_qty": 0,
        "total_buy_val": 0.0, "total_sell_val": 0.0,
    })
    
    for symbol, deal_date, cat, deal_type, qty, price in deals_raw:
        k = (symbol, deal_date)
        val = qty * price
        
        summary[k]["total_qty_abs"] += qty
        
        if deal_type == "BUY":
            summary[k]["total_buy_qty"] += qty
            summary[k]["total_buy_val"] += val
            if cat == "INSTITUTIONAL":
                summary[k]["inst_buy_qty"] += qty
                summary[k]["inst_buy_val"] += val
            else:
                summary[k]["ret_buy_qty"] += qty
                summary[k]["ret_buy_val"] += val
        else: # SELL
            summary[k]["total_sell_qty"] += qty
            summary[k]["total_sell_val"] += val
            if cat == "INSTITUTIONAL":
                summary[k]["inst_sell_qty"] += qty
                summary[k]["inst_sell_val"] += val
            else:
                summary[k]["ret_sell_qty"] += qty
                summary[k]["ret_sell_val"] += val
                
    # Fetch daily_prices volume for these days
    # To avoid many queries, we fetch the needed ones
    symbol_dates = list(summary.keys())
    vol_dict = {}
    
    # Doing it in chunks to avoid sqlite variable limit
    print("Fetching daily volumes...")
    for i in range(0, len(symbol_dates), 100):
        chunk = symbol_dates[i:i+100]
        query = "SELECT symbol, trade_date, volume FROM daily_prices WHERE (symbol, trade_date) IN ({seq})".format(
            seq=','.join(['(?,?)']*len(chunk))
        )
        flat_chunk = [item for sublist in chunk for item in sublist]
        vol_rows = conn.execute(query, flat_chunk).fetchall()
        for sym, d, v in vol_rows:
            vol_dict[(sym, d)] = v
            
    insert_rows = []
    for (symbol, deal_date), data in summary.items():
        net_qty = data["total_buy_qty"] - data["total_sell_qty"]
        net_capital = data["total_buy_val"] - data["total_sell_val"]
        
        inst_net_qty = data["inst_buy_qty"] - data["inst_sell_qty"]
        
        daily_vol = vol_dict.get((symbol, deal_date))
        if daily_vol is None:
            daily_vol = 0
            
        deal_volume_pct = (data["total_qty_abs"] / daily_vol) if daily_vol > 0 else 0.0
        
        # Institutional Buy Pressure
        # e.g., if Inst is heavily buying (inst_net_qty > 0), pressure is high. 
        # Using inst_buy_qty / (inst_buy_qty + inst_sell_qty) as pressure?
        # Or just scaling the Inst Net Qty relative to total absolute qty?
        inst_total_qty = data["inst_buy_qty"] + data["inst_sell_qty"]
        inst_buy_pressure = (data["inst_buy_qty"] / inst_total_qty) if inst_total_qty > 0 else 0.5
        
        insert_rows.append((
            symbol, deal_date, net_qty, net_capital, deal_volume_pct, inst_buy_pressure
        ))
        
    conn.executemany("""
        INSERT OR REPLACE INTO daily_bulk_summary
        (symbol, deal_date, net_quantity, net_capital_flow, deal_volume_pct, institutional_buy_pressure)
        VALUES (?, ?, ?, ?, ?, ?)
    """, insert_rows)
    
    conn.commit()
    try:
        from core.tracker import handle_bulk_deals_drip
        formatted_deals = []
        for symbol, deal_date, net_qty, net_capital, deal_volume_pct, inst_buy_pressure in insert_rows:
            formatted_deals.append({
                "symbol": symbol,
                "deal_date": deal_date,
                "deal_type": "BUY" if net_qty >= 0 else "SELL",
                "quantity": abs(net_qty),
                "price": round(abs(net_capital / net_qty), 2) if net_qty != 0 else 0.0,
                "deal_kind": "BULK_SUMMARY",
                "client_name": f"Net Institutional Flow ({deal_volume_pct*100:.1f}% of Vol)"
            })
        handle_bulk_deals_drip(formatted_deals, conn=conn)
    except Exception as _e:
        pass
    conn.close()
    print(f"Saved {len(insert_rows)} summary records.")

if __name__ == "__main__":
    process_bulk_deals()
