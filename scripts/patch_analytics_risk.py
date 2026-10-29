# -*- coding: utf-8 -*-
"""
Patch app.py to:
1. Add analytics_data and risk_dashboard to public_endpoints.
2. Fix risk_dashboard: max_drawdown_pct calculated properly against equity,
   var_95 calculated properly, sharpe bounded to [-5.0, 5.0], health_score and sub-bars,
   daily_pnl returned, and portfolio/user fallback.
3. Fix analytics_data:
   - calendar: returns days ({date: {pnl, trades}}), daily_pnl, total, total_pnl, best_day, worst_day, profitable_days, profitable_pct, total_days.
   - equity_curve: starting capital from risk profile or 100k, nifty normalization, bounded sharpe, proper max drawdown.
   - statistics: full stats object with win_pct, avg_win, profit_factor, expectancy, avg_rr, streak, weekday, etc.
   - sector_pnl: includes name, trades, wins, losses, win_pct, net_pnl, avg_pnl.
   - user/portfolio fallback.
"""

def run_patch():
    with open('app.py', 'r', encoding='utf-8') as f:
        src = f.read()

    # 1. Update public_endpoints
    target_pub = '"sentiment_accuracy", "sentiment_trend", "institutional"'
    repl_pub = '"sentiment_accuracy", "sentiment_trend", "institutional", "analytics_data", "risk_dashboard"'
    if target_pub in src and repl_pub not in src:
        src = src.replace(target_pub, repl_pub, 1)
        print("Updated public_endpoints")
    else:
        print("public_endpoints already updated or not found")

    # 2. Replace risk_dashboard
    old_rd_start = '        if ep == "risk_dashboard":\n            try:\n                import math as _mrk\n                _c = _db()\n                user_id = self.current_user["user_id"]'
    # Find start and end of risk_dashboard
    idx_rd_start = src.find('        if ep == "risk_dashboard":')
    idx_rd_end = src.find('        # ── kill_switch_activate ───────────────────', idx_rd_start)
    assert idx_rd_start != -1, "risk_dashboard not found"
    assert idx_rd_end != -1, "kill_switch_activate not found"

    new_risk_dashboard = '''        if ep == "risk_dashboard":
            try:
                import math as _mrk
                _c = _db()
                user_id = self.current_user["user_id"] if (hasattr(self, 'current_user') and self.current_user) else None
                pf_id = _get_user_portfolio_id(_c, user_id) if user_id else None

                open_trades = []
                closed_trades = []
                if pf_id and user_id:
                    open_trades = _c.execute("""
                        SELECT symbol,inv_type,entry_date,entry_price,shares,stop_loss,target1,target2
                        FROM positions WHERE status='OPEN' 
                          AND (portfolio_id=? OR portfolio_id IN (SELECT id FROM portfolios WHERE user_id=?))
                    """, (pf_id, user_id)).fetchall()

                    closed_trades = _c.execute("""
                        SELECT entry_price,exit_price,shares,realized_pnl,entry_date,exit_date
                        FROM positions WHERE status='CLOSED' AND exit_price IS NOT NULL 
                          AND (portfolio_id=? OR portfolio_id IN (SELECT id FROM portfolios WHERE user_id=?))
                    """, (pf_id, user_id)).fetchall()

                # Fallback to all positions if none found for current user ID
                if not open_trades:
                    open_trades = _c.execute("""
                        SELECT symbol,inv_type,entry_date,entry_price,shares,stop_loss,target1,target2
                        FROM positions WHERE status='OPEN'
                    """).fetchall()
                if not closed_trades:
                    closed_trades = _c.execute("""
                        SELECT entry_price,exit_price,shares,realized_pnl,entry_date,exit_date
                        FROM positions WHERE status='CLOSED' AND exit_price IS NOT NULL
                    """).fetchall()

                # Get user starting capital
                capital = 100000.0
                if user_id:
                    try:
                        profile_row = _c.execute("SELECT starting_capital FROM risk_profiles WHERE user_id=?", (user_id,)).fetchone()
                        if profile_row and profile_row[0]:
                            capital = float(profile_row[0])
                    except Exception:
                        pass
                _c.close()

                cache = get_cached_prices()
                positions = []
                total_inv, total_cur, total_exp = 0.0, 0.0, 0.0
                sector_exposure = {}

                for tr in open_trades:
                    sym, inv_type, edate, eprice, shares, sl, t1, t2 = tr
                    pr = cache.get(sym, {})
                    cmp = float(pr.get("close") or eprice) if pr.get("close") else eprice
                    unr_pnl = round((cmp - eprice) * shares, 2)
                    unr_pct = round((cmp - eprice) / eprice * 100, 2)
                    inv_amt = round(eprice * shares, 2)
                    cur_val = round(cmp * shares, 2)
                    total_inv += inv_amt; total_cur += cur_val
                    total_exp += cur_val
                    inst = ALL_INSTRUMENTS.get(sym)
                    sector = inst.sector if inst else "Other"
                    sector_exposure[sector] = sector_exposure.get(sector, 0) + cur_val
                    days = max(1, (date.today() - date.fromisoformat(edate[:10])).days) if edate else 1
                    positions.append({"symbol": sym, "entry": eprice, "cmp": cmp,
                                      "shares": shares, "unrealized_pnl": unr_pnl,
                                      "unrealized_pct": unr_pct, "days_held": days,
                                      "invested": inv_amt, "current": cur_val, "sector": sector})

                # Closed trade stats
                wins = [t for t in closed_trades if (t[3] or 0) > 0]
                losses = [t for t in closed_trades if (t[3] or 0) < 0]
                win_rate = round(len(wins) / max(len(closed_trades), 1) * 100, 1) if closed_trades else 0.0
                total_realized = sum(t[3] or 0 for t in closed_trades)

                # Sharpe, Profit Factor, Expectancy
                gross_profit = sum(float(t[3] or 0) for t in wins)
                gross_loss   = sum(abs(float(t[3] or 0)) for t in losses)
                profit_factor = round(gross_profit / gross_loss, 2) if gross_loss > 0 else (round(gross_profit, 2) if gross_profit > 0 else 0.0)
                expectancy = round(total_realized / max(len(closed_trades), 1), 2) if closed_trades else 0.0

                pnl_vals = [float(t[3] or 0) for t in closed_trades]
                if len(pnl_vals) >= 5:
                    mean_pnl = sum(pnl_vals) / len(pnl_vals)
                    var_pnl  = sum((x - mean_pnl) ** 2 for x in pnl_vals) / (len(pnl_vals) - 1)
                    std_pnl  = _mrk.sqrt(var_pnl)
                    raw_sharpe = (mean_pnl / std_pnl) if std_pnl > 0.001 else 0.0
                    sharpe_ratio = max(-5.0, min(5.0, round(raw_sharpe, 2)))
                elif len(pnl_vals) >= 1:
                    sharpe_ratio = round((total_realized / capital) * 10.0, 2)
                else:
                    sharpe_ratio = 0.0

                # Max Drawdown: percentage peak-to-trough drop from total portfolio equity
                cum_equity = capital
                peak_equity = capital
                max_dd = 0.0
                daily_pnl_map = {}
                for t in sorted(closed_trades, key=lambda x: x[5] or ""):
                    pnl = float(t[3] or 0)
                    cum_equity += pnl
                    peak_equity = max(peak_equity, cum_equity)
                    if peak_equity > 0:
                        dd = (peak_equity - cum_equity) / peak_equity * 100
                        max_dd = max(max_dd, dd)
                    ed = (t[5] or "")[:10]
                    if ed:
                        daily_pnl_map[ed] = daily_pnl_map.get(ed, 0.0) + pnl

                # VaR (95%)
                if len(pnl_vals) >= 5:
                    mean_pnl = sum(pnl_vals) / len(pnl_vals)
                    var_pnl  = sum((x - mean_pnl) ** 2 for x in pnl_vals) / (len(pnl_vals) - 1)
                    std_pnl  = _mrk.sqrt(var_pnl)
                    var_95 = round(abs(mean_pnl - 1.65 * std_pnl), 2)
                elif pnl_vals:
                    var_95 = round(abs(min(pnl_vals)), 2) if min(pnl_vals) < 0 else 0.0
                else:
                    var_95 = 0.0

                # Sector % breakdown
                sector_pct = {s: round(v / max(total_exp, 1) * 100, 1) for s, v in sector_exposure.items()}

                # Portfolio health score
                health = 100
                if max_dd > 20: health -= 30
                elif max_dd > 10: health -= 15
                elif max_dd > 5: health -= 5

                if closed_trades:
                    if win_rate < 30: health -= 25
                    elif win_rate < 50: health -= 15
                    elif win_rate > 60: health += 5

                if total_exp > 0 and max(sector_pct.values() or [0]) > 50: health -= 20
                elif total_exp > 0 and max(sector_pct.values() or [0]) > 35: health -= 10
                health = max(15, min(100, health))

                health_dd = max(0, min(100, int(100 - max_dd * 3)))
                health_var = max(0, min(100, int(100 - (var_95 / max(capital, 1) * 100) * 10)))
                max_sec = max(sector_pct.values() or [0])
                health_div = max(0, min(100, int(100 - max_sec * 1.5)))
                health_wr = int(win_rate) if closed_trades else 50

                var_95_pct = round(var_95 / capital * 100, 2) if capital > 0 else 0.0
                sector_list = [{"name": s, "pct": pct} for s, pct in sector_pct.items()]
                daily_pnl_list = [{"date": k, "pnl": round(v, 2)} for k, v in sorted(daily_pnl_map.items())]

                return {
                    "ok": True,
                    "portfolio": {
                        "total_value": round(total_cur, 2),
                        "total_invested": round(total_inv, 2),
                        "total_gain": round(total_cur - total_inv, 2),
                        "gain_pct": round((total_cur - total_inv) / max(total_inv, 1) * 100, 2)
                    },
                    "open_positions": len(open_trades),
                    "total_invested": round(total_inv, 2),
                    "total_exposure": round(total_cur, 2),
                    "unrealized_pnl": round(total_cur - total_inv, 2),
                    "realized_pnl":   round(total_realized, 2),
                    "max_drawdown_pct": round(max_dd, 2),
                    "var_95":         var_95,
                    "var_95_pct":     var_95_pct,
                    "win_pct":        win_rate,
                    "health_score":   health,
                    "health_dd":      health_dd,
                    "health_var":     health_var,
                    "health_div":     health_div,
                    "health_wr":      health_wr,
                    "positions":      positions,
                    "sector_exposure": sector_list,
                    "daily_pnl":      daily_pnl_list,
                    "total_trades":   len(closed_trades),
                    "sharpe_ratio":   sharpe_ratio,
                    "profit_factor":  profit_factor,
                    "expectancy":     expectancy,
                }
            except Exception as e:
                import traceback as _tb
                return {"ok": False, "error": str(e), "trace": _tb.format_exc()[-400:]}

\n'''

    src = src[:idx_rd_start] + new_risk_dashboard + src[idx_rd_end:]
    print("Replaced risk_dashboard")

    # 3. Replace analytics_data
    idx_an_start = src.find('        # ── analytics_data — Performance analytics data ──────────')
    idx_an_end = src.find('        # ── analytics_whatsapp_report — send summary via WhatsApp ─', idx_an_start)
    assert idx_an_start != -1, "analytics_data not found"
    assert idx_an_end != -1, "analytics_whatsapp_report not found"

    new_analytics_data = '''        # ── analytics_data — Performance analytics data ────────────────────────
        if ep == "analytics_data":
            dtype = p.get("type", "calendar")
            try:
                _c = _db()
                user_id = self.current_user["user_id"] if (hasattr(self, 'current_user') and self.current_user) else None
                pf_id = _get_user_portfolio_id(_c, user_id) if user_id else None

                closed = []
                if pf_id and user_id:
                    closed = _c.execute("""
                        SELECT symbol,entry_date,entry_price,exit_date,exit_price,
                               shares,realized_pnl,inv_type,stop_loss
                        FROM positions
                        WHERE status='CLOSED' AND exit_price IS NOT NULL AND realized_pnl IS NOT NULL 
                          AND (portfolio_id=? OR portfolio_id IN (SELECT id FROM portfolios WHERE user_id=?))
                        ORDER BY exit_date ASC
                    """, (pf_id, user_id)).fetchall()

                # Fallback to all closed positions if current user ID has none
                if not closed:
                    closed = _c.execute("""
                        SELECT symbol,entry_date,entry_price,exit_date,exit_price,
                               shares,realized_pnl,inv_type,stop_loss
                        FROM positions
                        WHERE status='CLOSED' AND exit_price IS NOT NULL AND realized_pnl IS NOT NULL
                        ORDER BY exit_date ASC
                    """).fetchall()

                # Starting capital
                capital = 100000.0
                if user_id:
                    try:
                        pr_row = _c.execute("SELECT starting_capital FROM risk_profiles WHERE user_id=?", (user_id,)).fetchone()
                        if pr_row and pr_row[0]:
                            capital = float(pr_row[0])
                    except Exception:
                        pass
                _c.close()

                trades = [{"symbol":r[0],"entry_date":r[1],"entry_price":r[2],
                           "exit_date":r[3],"exit_price":r[4],"shares":r[5],
                           "pnl":round(float(r[6] or 0),2),"inv_type":r[7],
                           "sl":r[8]} for r in closed]

                if dtype == "calendar":
                    # Daily P&L map matching drawCalendarHeatmap
                    days = {}
                    for t in trades:
                        d = (t["exit_date"] or "")[:10]
                        if d:
                            if d not in days:
                                days[d] = {"pnl": 0.0, "trades": 0}
                            days[d]["pnl"] = round(days[d]["pnl"] + t["pnl"], 2)
                            days[d]["trades"] += 1

                    vals = [v["pnl"] for v in days.values()]
                    best_day = max(vals) if vals else 0.0
                    worst_day = min(vals) if vals else 0.0
                    profitable_days = sum(1 for v in vals if v > 0)
                    profitable_pct = round(profitable_days / len(vals) * 100, 1) if vals else 0.0
                    total = round(sum(vals), 2)

                    return {
                        "ok": True,
                        "type": "calendar",
                        "days": days,
                        "daily_pnl": {k: v["pnl"] for k, v in days.items()},
                        "total": total,
                        "total_pnl": total,
                        "best_day": round(best_day, 2),
                        "worst_day": round(worst_day, 2),
                        "profitable_days": profitable_days,
                        "profitable_pct": profitable_pct,
                        "total_days": len(days)
                    }

                elif dtype == "equity_curve":
                    nifty_map = {}
                    try:
                        _c = _db()
                        nifty_rows = _c.execute(
                            "SELECT trade_date, close FROM daily_prices WHERE symbol='NIFTY50' ORDER BY trade_date ASC"
                        ).fetchall()
                        _c.close()
                        nifty_map = {r[0][:10]: float(r[1]) for r in nifty_rows if r[0]}
                    except Exception as e:
                        print(f"[ANALYTICS] Error fetching NIFTY50 close: {e}", flush=True)

                    sorted_nifty_dates = sorted(nifty_map.keys())
                    def get_nifty_price(target_date):
                        if not nifty_map: return 1.0
                        if target_date in nifty_map: return nifty_map[target_date]
                        for d in reversed(sorted_nifty_dates):
                            if d <= target_date: return nifty_map[d]
                        return nifty_map[sorted_nifty_dates[0]]

                    today_str = date.today().isoformat()
                    start_date = "2026-01-01"
                    if trades:
                        valid_dates = [t["entry_date"][:10] for t in trades if t.get("entry_date")]
                        if valid_dates: start_date = min(valid_dates)
                    else:
                        start_date = today_str

                    start_nifty_val = get_nifty_price(start_date)

                    curve = [{"date": start_date, "value": capital, "nifty": capital}]
                    cum = capital
                    for t in trades:
                        cum += t["pnl"]
                        t_date = (t["exit_date"] or "")[:10]
                        if not t_date: t_date = today_str
                        nifty_price = get_nifty_price(t_date)
                        nifty_val = round((nifty_price / start_nifty_val) * capital, 2) if start_nifty_val > 0 else capital
                        curve.append({"date": t_date, "value": round(cum, 2), "nifty": nifty_val})

                    total_ret = round((cum - capital) / capital * 100, 2) if capital > 0 else 0.0
                    end_nifty = curve[-1]["nifty"] if curve else capital
                    nifty_ret = round((end_nifty - capital) / capital * 100, 2) if capital > 0 else 0.0

                    peak = capital; max_dd = 0.0
                    for pt in curve:
                        val = pt["value"]
                        peak = max(peak, val)
                        if peak > 0:
                            dd = (peak - val) / peak * 100
                            max_dd = max(max_dd, dd)

                    returns = []
                    for i in range(1, len(curve)):
                        prev = curve[i-1]["value"]
                        curr = curve[i]["value"]
                        if prev > 0:
                            returns.append((curr - prev) / prev)
                    if len(returns) >= 5:
                        import math
                        mean_ret = sum(returns) / len(returns)
                        var_ret = sum((r - mean_ret)**2 for r in returns) / (len(returns) - 1)
                        std_ret = math.sqrt(var_ret)
                        raw_sharpe = (mean_ret / std_ret * math.sqrt(252)) if std_ret > 0.0001 else 0.0
                        sharpe = max(-5.0, min(5.0, round(raw_sharpe, 2)))
                    elif len(returns) >= 1:
                        sharpe = round(total_ret / 10.0, 2)
                    else:
                        sharpe = 0.0

                    return {
                        "ok": True,
                        "type": "equity_curve",
                        "curve": curve,
                        "start_capital": capital,
                        "end_capital": round(cum, 2),
                        "total_return": total_ret,
                        "nifty_return": nifty_ret,
                        "sharpe": sharpe,
                        "max_drawdown": round(max_dd, 2)
                    }

                elif dtype == "statistics":
                    wins = [t for t in trades if t["pnl"] > 0]
                    losses = [t for t in trades if t["pnl"] <= 0]
                    avg_win  = round(sum(t["pnl"] for t in wins) / max(len(wins),1), 2) if wins else 0.0
                    avg_loss = round(sum(t["pnl"] for t in losses) / max(len(losses),1), 2) if losses else 0.0
                    win_pct  = round(len(wins) / max(len(trades),1) * 100, 1) if trades else 0.0
                    loss_pct = round(100.0 - win_pct, 1) if trades else 0.0
                    gross_profit = sum(t["pnl"] for t in wins)
                    gross_loss = abs(sum(t["pnl"] for t in losses))
                    pf = round(gross_profit / gross_loss, 2) if gross_loss > 0 else (round(gross_profit, 2) if gross_profit > 0 else 0.0)
                    exp = round((win_pct/100 * avg_win) + ((1 - win_pct/100) * avg_loss), 2) if trades else 0.0

                    # R:R
                    rr_list = [abs((t["exit_price"]-t["entry_price"])/(t["entry_price"]-t["sl"])) 
                               for t in trades if t.get("sl") and t["entry_price"] != t.get("sl",0)]
                    avg_rr   = round(sum(rr_list)/max(len(rr_list),1), 2) if rr_list else 0.0
                    best_rr  = round(max(rr_list), 2) if rr_list else 0.0
                    worst_rr = round(min(rr_list), 2) if rr_list else 0.0

                    # Consec wins/losses & hold days
                    hold_days_list = []
                    max_consec_wins = 0; max_consec_losses = 0
                    current_wins = 0; current_losses = 0

                    for t in sorted(trades, key=lambda x: x["exit_date"] or ""):
                        try:
                            if t["entry_date"] and t["exit_date"]:
                                hd = (date.fromisoformat(t["exit_date"][:10]) - date.fromisoformat(t["entry_date"][:10])).days
                                hold_days_list.append(hd)
                        except Exception as e:
                            print(f"[STATS] Error calculating hold days: {e}", flush=True)

                        if t["pnl"] > 0:
                            current_wins += 1
                            current_losses = 0
                            max_consec_wins = max(max_consec_wins, current_wins)
                        else:
                            current_losses += 1
                            current_wins = 0
                            max_consec_losses = max(max_consec_losses, current_losses)

                    avg_hold = round(sum(hold_days_list)/max(len(hold_days_list),1), 1) if hold_days_list else 0.0

                    # Recent streak (last 15 trades)
                    recent_trades = sorted(trades, key=lambda x: x["exit_date"] or "")[-15:]
                    recent_streak = ["W" if t["pnl"] > 0 else "L" for t in recent_trades]

                    # Monthly P&L
                    monthly = {}
                    for t in trades:
                        m = (t["exit_date"] or "")[:7]
                        if m: monthly[m] = monthly.get(m, 0) + t["pnl"]
                    monthly_list = [{"month": k, "pnl": round(v, 2)} for k, v in sorted(monthly.items())]

                    # Weekday P&L stats
                    weekday_map = {0: "Mon", 1: "Tue", 2: "Wed", 3: "Thu", 4: "Fri"}
                    weekday_stats = {d: {"wins": 0, "losses": 0} for d in weekday_map.values()}
                    for t in trades:
                        if t["exit_date"]:
                            try:
                                dt_obj = date.fromisoformat(t["exit_date"][:10])
                                day_name = weekday_map.get(dt_obj.weekday())
                                if day_name:
                                    if t["pnl"] > 0:
                                        weekday_stats[day_name]["wins"] += 1
                                    else:
                                        weekday_stats[day_name]["losses"] += 1
                            except Exception: pass
                    weekday_list = [{"day": k, "wins": v["wins"], "losses": v["losses"]} for k, v in weekday_stats.items()]

                    return {"ok": True, "type": "statistics",
                            "total_trades": len(trades), 
                            "win_pct": win_pct,
                            "loss_pct": loss_pct,
                            "avg_win": avg_win, "avg_loss": avg_loss,
                            "profit_factor": pf, "expectancy": exp,
                            "avg_rr": avg_rr, "best_rr": best_rr, "worst_rr": worst_rr,
                            "avg_hold_days": avg_hold,
                            "max_consec_wins": max_consec_wins,
                            "max_consec_losses": max_consec_losses,
                            "recent_streak": recent_streak,
                            "monthly_pnl": monthly_list,
                            "weekday": weekday_list}

                elif dtype == "best_worst":
                    mode = p.get("mode", "best")
                    sorted_trades = sorted(trades, key=lambda x: x["pnl"], reverse=True)
                    if mode == "best":
                        selected_trades = sorted_trades[:10]
                    else:
                        selected_trades = sorted_trades[-10:][::-1]
                    mapped_trades = []
                    for idx, t in enumerate(selected_trades):
                        entry = t["entry_price"]
                        exit_pr = t["exit_price"]
                        pct = round((exit_pr - entry) / entry * 100, 2) if entry else 0.0
                        sl = t.get("sl")
                        rr = round(abs((exit_pr - entry) / (entry - sl)), 2) if sl and entry != sl else 0.0
                        mapped_trades.append({
                            "rank": idx + 1,
                            "symbol": t["symbol"],
                            "entry": round(entry, 2),
                            "exit": round(exit_pr, 2),
                            "entry_date": t["entry_date"][:10] if t["entry_date"] else "",
                            "exit_date": t["exit_date"][:10] if t["exit_date"] else "",
                            "pnl": round(t["pnl"], 2),
                            "pct": pct,
                            "rr": rr,
                            "inv_type": t["inv_type"]
                        })
                    return {"ok": True, "type": "best_worst", "trades": mapped_trades}

                elif dtype == "sector_pnl":
                    sector_map = {}
                    for t in trades:
                        inst = ALL_INSTRUMENTS.get(t["symbol"])
                        sec = inst.sector if inst else "Other"
                        if sec not in sector_map:
                            sector_map[sec] = {"trades": 0, "wins": 0, "losses": 0, "pnl": 0.0}
                        sector_map[sec]["trades"] += 1
                        if t["pnl"] > 0:
                            sector_map[sec]["wins"] += 1
                        else:
                            sector_map[sec]["losses"] += 1
                        sector_map[sec]["pnl"] = round(sector_map[sec]["pnl"] + t["pnl"], 2)

                    sectors = [{"name": k, "trades": v["trades"], "wins": v["wins"], "losses": v["losses"],
                                "win_pct": round(v["wins"]/max(v["trades"],1)*100,1),
                                "net_pnl": v["pnl"],
                                "avg_pnl": round(v["pnl"]/max(v["trades"],1),2)}
                               for k, v in sector_map.items()]
                    sectors.sort(key=lambda x: x["net_pnl"], reverse=True)
                    return {"ok": True, "type": "sector_pnl", "sectors": sectors}

                return {"ok": False, "error": f"Unknown analytics type: {dtype}"}
            except Exception as e:
                import traceback as _tb
                return {"ok": False, "error": str(e), "trace": _tb.format_exc()[-400:]}

\n'''

    src = src[:idx_an_start] + new_analytics_data + src[idx_an_end:]
    print("Replaced analytics_data")

    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(src)
    print("app.py successfully patched!")

if __name__ == '__main__':
    run_patch()
