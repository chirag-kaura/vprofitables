"""
report_engine.py  —  GANN-ASTRO Master Analysis Report Generator
Place in: core/report_engine.py

Pure Python rule-based narrative engine.
No external API required. Synthesises data from:
  - Quant / Technical (RSI, SMA, volatility, S/R, candles)
  - Gann (confluence score, Sq9, time cycles, angles)
  - Natal (bull/bear signals, ruler activations)
  - Simons / Regime (trend regime, Fourier)
  - Fundamentals (P/E, ROE, debt)
  - Sentiment (score, news, candle psychology)
"""

import math
from datetime import date, timedelta
from typing import Dict, List, Optional, Any


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _pct(val: float, ref: float) -> float:
    if not ref: return 0.0
    return round((val - ref) / ref * 100, 2)

def _fmt(val, prefix="₹", decimals=2):
    if val is None: return "N/A"
    try:
        n = float(val)
        if n >= 1e7:  return f"{prefix}{n/1e7:.2f} Cr"
        if n >= 1e5:  return f"{prefix}{n/1e5:.2f} L"
        if n >= 1000: return f"{prefix}{n:,.{decimals}f}"
        return f"{prefix}{n:.{decimals}f}"
    except Exception:
        return str(val)

def _direction(val: float) -> str:
    return "rising" if val > 0 else "falling"

def _strong_weak(n: int, threshold: int = 3) -> str:
    return "strong" if n >= threshold else "weak"


# ─────────────────────────────────────────────────────────────────────────────
# SECTION BUILDERS
# ─────────────────────────────────────────────────────────────────────────────

def _build_technical(sym: str, cur: float, m: dict, sr: dict,
                     closes: list, highs: list, lows: list, volumes: list,
                     dates: list) -> dict:
    """Technical analysis narrative."""
    sma20  = float(m.get("sma20",  0) or 0)
    sma50  = float(m.get("sma50",  0) or 0)
    sma200 = float(m.get("sma200", 0) or 0)
    ret20  = float(m.get("ret_20d", 0) or 0)
    ann_vol= float(m.get("annual_vol_pct", 0) or 0)

    # SMA positions
    abv20  = cur > sma20  if sma20  else None
    abv50  = cur > sma50  if sma50  else None
    abv200 = cur > sma200 if sma200 else None

    # RSI(14)
    rsi = 50.0
    if len(closes) >= 15:
        tail = closes[-15:]
        g, l = 0.0, 0.0
        for i in range(1, len(tail)):
            chg = tail[i] - tail[i-1]
            if chg > 0: g += chg
            else:       l -= chg
        ag, al = g/14, l/14
        rsi = round(100 - 100/(1 + ag/al), 1) if al > 0 else 100.0

    # 21-day realised vol
    vol21 = 0.0
    if len(closes) >= 22:
        tail22 = closes[-22:]
        rets = [math.log(tail22[i]/tail22[i-1]) for i in range(1, len(tail22))]
        mean = sum(rets) / len(rets)
        var  = sum((r-mean)**2 for r in rets) / (len(rets)-1)
        vol21 = round(math.sqrt(var * 252) * 100, 1)
    vol_ratio = round(vol21 / ann_vol, 2) if ann_vol else 1.0

    # Volume surge (last bar vs 20-day avg)
    vol_surge = 1.0
    if len(volumes) >= 21:
        avg20  = sum(volumes[-21:-1]) / 20
        last_v = volumes[-1]
        vol_surge = round(last_v / avg20, 2) if avg20 > 0 else 1.0

    # Nearest S/R
    supports    = sr.get("supports",    [])
    resistances = sr.get("resistances", [])
    near_sup = supports[0]    if supports    else None
    near_res = resistances[0] if resistances else None

    # Candle patterns (last 5 bars)
    candle_patterns = []
    n = len(closes)
    if n >= 5 and len(highs) == n and len(lows) == n:
        opens_list = []
        for i in range(max(0, n-5), n):
            o = closes[i-1] if i > 0 else closes[i]
            opens_list.append(o)
        for idx, i in enumerate(range(max(0, n-5), n)):
            o = opens_list[idx]
            h = highs[i]; l2 = lows[i]; c = closes[i]
            body = abs(c-o); rng = h - l2
            if rng < 0.001: continue
            bp = body/rng; wu = (h-max(o,c))/rng; wd = (min(o,c)-l2)/rng
            if wd > 0.55 and bp < 0.35 and wu < 0.15:
                candle_patterns.append("Hammer (bullish reversal)")
            elif wu > 0.55 and bp < 0.35 and wd < 0.15:
                candle_patterns.append("Shooting Star (bearish reversal)")
            elif bp < 0.08:
                candle_patterns.append("Doji (indecision)")
            elif bp > 0.85 and c > o:
                candle_patterns.append("Bullish Marubozu (strong buying)")
            elif bp > 0.85 and c < o:
                candle_patterns.append("Bearish Marubozu (selling pressure)")
            elif wd > 0.35 and bp > 0.3 and c > o:
                candle_patterns.append("Bullish Engulfing / Hammer-like")
    # Engulfing check (last 2 bars)
    if n >= 2:
        o1,c1 = closes[-2], closes[-1]
        o2 = closes[-3] if n >= 3 else o1
        if c1 > o2 and c1 > c1 and o1 < o2:
            candle_patterns.append("Bullish Engulfing pattern")
        elif c1 < o2 and o1 > o2:
            candle_patterns.append("Bearish Engulfing pattern")

    # RSI divergence hint (price lower but RSI higher than 20 bars ago)
    rsi_divergence = None
    if len(closes) >= 20 and rsi > 0:
        rsi_20ago = 50.0
        if len(closes) >= 35:
            tail_old = closes[-35:-20]
            g2, l2 = 0.0, 0.0
            for i in range(1, len(tail_old)):
                chg = tail_old[i] - tail_old[i-1]
                if chg > 0: g2 += chg
                else:       l2 -= chg
            ag2, al2 = g2/max(len(tail_old)-1,1), l2/max(len(tail_old)-1,1)
            rsi_20ago = round(100 - 100/(1+ag2/al2), 1) if al2 > 0 else 100.0
        if closes[-1] < closes[-20] and rsi > rsi_20ago:
            rsi_divergence = "bullish"
        elif closes[-1] > closes[-20] and rsi < rsi_20ago:
            rsi_divergence = "bearish"

    # Narrative
    lines = []

    # Price location
    if near_sup and abs(_pct(cur, near_sup["price"])) < 2:
        lines.append(
            f"Price ₹{cur:,.2f} is trading near the {near_sup['strength'].lower()} "
            f"support zone at ₹{near_sup['price']:,.2f} "
            f"({near_sup['distance_pct']:.1f}% away)"
        )
    elif near_res and abs(_pct(cur, near_res["price"])) < 2:
        lines.append(
            f"Price ₹{cur:,.2f} is testing the {near_res['strength'].lower()} "
            f"resistance at ₹{near_res['price']:,.2f} "
            f"({near_res['distance_pct']:.1f}% away)"
        )
    else:
        sup_str = f"₹{near_sup['price']:,.2f}" if near_sup else "N/A"
        res_str = f"₹{near_res['price']:,.2f}" if near_res else "N/A"
        lines.append(
            f"Price ₹{cur:,.2f} trading between support ₹{sup_str} "
            f"and resistance {res_str}"
        )

    # SMA context
    sma_parts = []
    if abv20  is not None: sma_parts.append(f"{'above' if abv20 else 'below'} SMA20 (₹{sma20:,.2f})")
    if abv50  is not None: sma_parts.append(f"{'above' if abv50 else 'below'} SMA50 (₹{sma50:,.2f})")
    if abv200 is not None: sma_parts.append(f"{'above' if abv200 else 'below'} SMA200 (₹{sma200:,.2f})")
    if sma_parts:
        lines.append("Price is " + ", ".join(sma_parts))

    # RSI
    if rsi <= 30:
        rsi_desc = f"RSI({rsi}) is in oversold territory — historically a high-probability reversal zone"
    elif rsi >= 70:
        rsi_desc = f"RSI({rsi}) is overbought — caution on chasing; look for pullback entry"
    elif rsi < 45:
        rsi_desc = f"RSI({rsi}) remains weak, confirming the prevailing bearish pressure"
    else:
        rsi_desc = f"RSI({rsi}) is neutral-to-positive, showing recovering momentum"
    if rsi_divergence == "bullish":
        rsi_desc += "; a bullish RSI divergence is forming — price made a lower low but RSI did not, signalling hidden strength"
    elif rsi_divergence == "bearish":
        rsi_desc += "; bearish RSI divergence noted — momentum is weakening despite price highs"
    lines.append(rsi_desc)

    # Volume
    if vol_surge >= 1.8:
        lines.append(
            f"Volume spiked {vol_surge:.1f}× the 20-day average — strong institutional participation"
        )
    elif vol_surge >= 1.3:
        lines.append(
            f"Volume is above average ({vol_surge:.1f}×) — meaningful accumulation/distribution visible"
        )
    else:
        lines.append(
            f"Volume is normal ({vol_surge:.1f}× avg) — no unusual activity detected"
        )

    # Candle patterns
    if candle_patterns:
        lines.append(
            "Recent candle patterns: " + "; ".join(candle_patterns[:2])
        )

    # Volatility
    if ann_vol < 20:
        vol_desc = f"Volatility is low ({ann_vol}% annualised) — calm environment suitable for position entry"
    elif ann_vol < 35:
        vol_desc = f"Volatility is moderate ({ann_vol}%) — normal swing-trading conditions"
    else:
        vol_desc = f"Volatility is elevated ({ann_vol}%) — size positions conservatively"
    lines.append(vol_desc)

    return {
        "narrative": " ".join(lines),
        "rsi":        rsi,
        "vol21":      vol21,
        "vol_ratio":  vol_ratio,
        "vol_surge":  vol_surge,
        "sma20":      sma20,
        "sma50":      sma50,
        "sma200":     sma200,
        "abv20":      abv20,
        "abv50":      abv50,
        "abv200":     abv200,
        "ret20":      ret20,
        "ann_vol":    ann_vol,
        "rsi_divergence": rsi_divergence,
        "candle_patterns": candle_patterns[:2],
        "near_sup":   near_sup,
        "near_res":   near_res,
    }


def _build_gann(gann_data: dict, cur: float, dt: date) -> dict:
    """Gann narrative."""
    if not gann_data:
        return {"narrative": "Gann analysis data not available."}

    conf     = gann_data.get("confluence", {})
    score    = conf.get("score", 0)
    verdict  = conf.get("verdict", "")
    signals  = conf.get("signals", [])
    gm       = gann_data.get("gann_math", {})
    sq9      = gm.get("sq9_levels", [])
    cycles_due= gm.get("time_cycles_due", [])
    cycles_app= gm.get("time_cycles_approaching", [])
    angles   = gm.get("angles", [])
    upcoming = gann_data.get("upcoming_signals", [])

    # Best entry from Sq9
    sq9_support    = sq9[0]["below"] if sq9 else None
    sq9_t1         = sq9[0]["above"] if sq9 else None
    sq9_t2         = sq9[1]["above"] if len(sq9) > 1 else None

    # Gann 1x1 angle
    angle_1x1 = next((a for a in angles if a.get("name") == "1x1"), None)

    # Best upcoming date
    best_upcoming  = upcoming[0] if upcoming else None

    lines = []
    if score >= 15:
        lines.append(
            f"Gann confluence is EXTREME at {score}/25 — {verdict}. "
            f"Multiple independent Gann signals are aligning simultaneously"
        )
    elif score >= 8:
        lines.append(
            f"Gann confluence score of {score}/25 ({verdict}) shows meaningful "
            f"convergence across Square of Nine and time cycle levels"
        )
    else:
        lines.append(
            f"Gann confluence is modest at {score}/25. "
            f"Price is not yet at a high-probability Gann level"
        )

    if sq9_t1:
        lines.append(
            f"Square of Nine analysis projects the first resistance / target at "
            f"₹{sq9_t1:,.2f} (+{_pct(sq9_t1,cur):.1f}%)"
            + (f" and secondary target at ₹{sq9_t2:,.2f}" if sq9_t2 else "")
        )
    if sq9_support:
        lines.append(
            f"Key Sq9 support sits at ₹{sq9_support:,.2f}, "
            f"which makes a logical stop-loss reference"
        )

    if angle_1x1:
        direction = "above" if angle_1x1.get("above") else "at/below"
        px_1x1 = angle_1x1.get("price") or angle_1x1.get("price_at_date", 0)
        lines.append(
            f"The 1×1 Gann angle is currently {direction} price "
            f"at ₹{px_1x1:,.2f} — "
            + ("price is trading above the 1×1, maintaining bullish angle integrity"
               if not angle_1x1.get("above") else
               "price needs to reclaim the 1×1 angle to shift bias bullish")
        )

    all_cycles = cycles_due + cycles_app
    if all_cycles:
        c0 = all_cycles[0]
        due_str = "is DUE NOW" if abs(c0.get("days_remaining", 99)) <= 7 else \
                  f"is approaching in {abs(c0.get('days_remaining',0))} days"
        lines.append(
            f"Time cycle '{c0.get('label','').split('—')[0].strip()}' {due_str} "
            f"(target {c0.get('target_date','')}) — Gann time cycles reinforce the "
            f"potential for a trend change at this juncture"
        )

    if best_upcoming:
        lines.append(
            f"The next highest-confluence reversal date is "
            f"{best_upcoming['date']} (score {best_upcoming['score']}) — "
            f"watch for price action confirmation around that window"
        )

    if signals:
        lines.append("Active signals: " + "; ".join(signals[:3]))

    return {
        "narrative":   " ".join(lines),
        "score":        score,
        "verdict":      verdict,
        "sq9_support":  sq9_support,
        "sq9_t1":       sq9_t1,
        "sq9_t2":       sq9_t2,
        "angle_1x1":    (angle_1x1.get("price") or angle_1x1.get("price_at_date")) if angle_1x1 else None,
        "best_date":    best_upcoming["date"] if best_upcoming else None,
        "best_date_score": best_upcoming["score"] if best_upcoming else None,
    }


def _build_natal(natal_data: dict) -> dict:
    """Natal chart narrative."""
    if not natal_data:
        return {"narrative": "Natal chart data not available."}

    bull  = len(natal_data.get("bull_signals", []))
    bear  = len(natal_data.get("bear_signals", []))
    prim  = natal_data.get("primary_ruler", "")
    sec   = natal_data.get("secondary_ruler", "")
    ruler_acts = natal_data.get("ruler_activations", [])
    t2n        = natal_data.get("transit_to_natal", [])

    lines = []
    if bull > bear + 1:
        lines.append(
            f"The natal chart is decisively bullish: {bull} bullish signals vs {bear} bearish. "
            f"Planetary transits are overwhelmingly supporting upward price movement"
        )
    elif bull > bear:
        lines.append(
            f"Natal signals lean bullish with {bull} bull vs {bear} bear signals — "
            f"a mild but positive planetary bias"
        )
    elif bear > bull + 1:
        lines.append(
            f"Natal chart is under bearish pressure: {bear} bearish vs {bull} bullish signals — "
            f"planetary environment is unfavourable"
        )
    else:
        lines.append(
            f"Natal signals are mixed ({bull} bull / {bear} bear) — "
            f"planetary environment is neutral; price action must confirm direction"
        )

    if ruler_acts:
        top_act = ruler_acts[0]
        nat = top_act.get("nature", "NEUTRAL")
        nat_desc = "positively" if nat == "BULLISH" else "negatively" if nat == "BEARISH" else "neutrally"
        lines.append(
            f"The primary ruler {prim} is being {nat_desc} activated — "
            f"transit {top_act.get('transit_planet','')} is forming a "
            f"{top_act.get('aspect','')} to natal {top_act.get('natal_planet','')} "
            f"(orb {top_act.get('orb',0):.1f}°), a key trigger for price movement in this instrument"
        )
        if len(ruler_acts) > 1:
            act2 = ruler_acts[1]
            lines.append(
                f"Secondary ruler {sec} is also activated by "
                f"transit {act2.get('transit_planet','')} {act2.get('aspect','')} "
                f"natal {act2.get('natal_planet','')} — dual ruler activation amplifies the signal"
            )
    else:
        lines.append(
            f"The ruling planets ({prim}, {sec}) are not currently in strong activation — "
            f"planetary influence is background noise rather than a decisive trigger"
        )

    return {
        "narrative": " ".join(lines),
        "bull":       bull,
        "bear":       bear,
        "prim_ruler": prim,
        "sec_ruler":  sec,
        "bias":       "BULLISH" if bull > bear else "BEARISH" if bear > bull else "NEUTRAL",
    }


def _build_simons(quant_data: dict) -> dict:
    """Simons / regime narrative."""
    if not quant_data:
        return {"narrative": "Simons quant data not available."}

    regime_block = quant_data.get("regime", {})
    regime   = regime_block.get("regime", "UNKNOWN")
    advice   = regime_block.get("regime_advice", "")
    metrics  = regime_block.get("metrics", {})
    conf     = regime_block.get("confidence", 0)

    # Fourier / cycle data if present
    fourier  = quant_data.get("fourier", {})
    dominant = fourier.get("dominant_period_days") if fourier else None
    forecast = fourier.get("forecast_prices", []) if fourier else []

    REGIME_DESC = {
        "STRONG_BULL":  "a strong bullish trend — momentum signals dominate and breakouts are reliable",
        "BULL":         "a bullish trend — price is above key moving averages and 20d momentum is positive",
        "SIDEWAYS":     "a sideways / mean-reverting regime — Sq9 S/R levels are highly reliable for swing entries",
        "BEAR":         "a bearish trend — price is below key SMAs and mean-reversion traps are common",
        "STRONG_BEAR":  "a strong bearish trend — rallies are selling opportunities, not buying",
        "VOLATILE":     "a volatile / transitional regime — reduce position size and tighten stops",
        "UNKNOWN":      "an indeterminate regime — insufficient data",
        "INSUFFICIENT_DATA": "an indeterminate regime — insufficient price history",
    }
    desc = REGIME_DESC.get(regime, regime)

    lines = []
    lines.append(
        f"Simons quant analysis classifies this instrument in {desc}. "
        + (f"Confidence: {int(conf*100)}%." if conf else "")
    )
    if advice:
        lines.append(advice)

    if dominant:
        lines.append(
            f"The dominant Fourier price cycle is approximately {dominant} days — "
            f"time your entries/exits around this periodicity for highest-probability trades"
        )
    elif forecast:
        fmax = max(forecast)
        fmin = min(forecast)
        lines.append(
            f"Cycle forecast projects a range of ₹{fmin:,.0f}–₹{fmax:,.0f} "
            f"over the coming weeks"
        )
    else:
        lines.append(
            "Run the Simons Lab page for full Fourier cycle analysis and regime forecasting"
        )

    return {
        "narrative": " ".join(lines),
        "regime":     regime,
        "confidence": conf,
    }


def _build_fundamental(fund_data: dict, sym: str) -> dict:
    """Fundamental analysis narrative."""
    if not fund_data or fund_data.get("error"):
        return {
            "narrative": (
                f"{sym} fundamental data is not available "
                f"(equity-only feature; ensure fundamentals are fetched via the app)"
            )
        }

    tgt = fund_data.get("target", fund_data)
    pe       = tgt.get("pe_ratio")   or fund_data.get("pe_ratio")
    roe      = tgt.get("roe")        or fund_data.get("roe")
    debt_eq  = tgt.get("debt_eq")    or fund_data.get("debt_eq")
    rev_gr   = tgt.get("revenue_growth") or fund_data.get("revenue_growth")
    earn_gr  = tgt.get("earnings_growth") or fund_data.get("earnings_growth")
    sigs     = fund_data.get("fundamental_signals", [])
    peers    = fund_data.get("peers", [])

    lines = []
    fund_bias = "NEUTRAL"

    # P/E
    if pe:
        pe_f = float(pe)
        if pe_f < 0:
            lines.append(f"The company is loss-making (P/E: {pe_f:.1f}) — fundamental risk is elevated")
            fund_bias = "BEARISH"
        elif pe_f < 15:
            lines.append(f"Valuations are attractive at P/E {pe_f:.1f}x — potential value buy zone")
            fund_bias = "BULLISH"
        elif pe_f < 30:
            lines.append(f"P/E of {pe_f:.1f}x is reasonable for the sector — fair to moderately valued")
        else:
            lines.append(f"P/E of {pe_f:.1f}x reflects rich valuations — growth must justify the premium")
            fund_bias = "BEARISH"
    else:
        lines.append("P/E ratio not available from current data")

    # ROE
    if roe:
        roe_f = float(roe)
        if roe_f >= 20:
            lines.append(f"ROE of {roe_f:.1f}% is excellent — management is deploying capital very efficiently, a hallmark of quality compounders")
            if fund_bias != "BEARISH": fund_bias = "BULLISH"
        elif roe_f >= 12:
            lines.append(f"ROE of {roe_f:.1f}% is healthy — above the cost of capital threshold")
        elif roe_f >= 0:
            lines.append(f"ROE of {roe_f:.1f}% is below average — capital allocation needs improvement")
        else:
            lines.append(f"Negative ROE ({roe_f:.1f}%) signals the business is destroying value")
            fund_bias = "BEARISH"

    # Debt
    if debt_eq:
        d_f = float(debt_eq)
        if d_f > 2:
            lines.append(f"Debt/Equity of {d_f:.1f}x is high — balance sheet risk is a concern in a rising rate environment")
        elif d_f > 0.5:
            lines.append(f"Debt/Equity of {d_f:.1f}x is manageable")
        else:
            lines.append(f"Balance sheet is clean (D/E: {d_f:.2f}) — zero leverage risk")

    # Growth
    growth_parts = []
    if earn_gr and float(earn_gr) > 10:
        growth_parts.append(f"earnings growing at {float(earn_gr):.1f}%")
        if fund_bias != "BEARISH": fund_bias = "BULLISH"
    if rev_gr and float(rev_gr) > 8:
        growth_parts.append(f"revenue growth at {float(rev_gr):.1f}%")
    if growth_parts:
        lines.append("Growth trajectory is positive — " + " and ".join(growth_parts))

    if sigs:
        lines.append("Key signals: " + "; ".join(sigs[:3]))

    if not lines:
        lines.append("Fundamental data is limited; refer to the Fundamentals page for full details")

    return {
        "narrative":  " ".join(lines),
        "fund_bias":  fund_bias,
        "pe":         pe,
        "roe":        roe,
        "debt_eq":    debt_eq,
    }


def _build_sentiment(sent_data: dict) -> dict:
    """Sentiment & news narrative."""
    if not sent_data:
        return {"narrative": "Sentiment data not available. Run bulk_news_fetch.py to populate."}

    overall   = float(sent_data.get("overall_score", 0) or 0)
    label     = sent_data.get("sentiment_label", "")
    news      = sent_data.get("news_items", []) or sent_data.get("recent_news", [])
    candles   = sent_data.get("candle_signals", [])
    vol_lbl   = sent_data.get("vol_label", "")

    lines = []
    if overall >= 0.4:
        lines.append(
            f"Sentiment is bullish (score {overall:+.2f} — {label}): "
            f"the news flow and market psychology are supporting buyers"
        )
    elif overall >= 0.1:
        lines.append(
            f"Sentiment is mildly positive (score {overall:+.2f}): "
            f"cautious optimism prevails with no major negative catalysts visible"
        )
    elif overall <= -0.4:
        lines.append(
            f"Sentiment is bearish (score {overall:+.2f} — {label}): "
            f"negative news flow and fear dominate short-term psychology"
        )
    elif overall <= -0.1:
        lines.append(
            f"Sentiment is mildly negative ({overall:+.2f}): "
            f"some caution warranted given the news environment"
        )
    else:
        lines.append(
            f"Sentiment is neutral ({overall:+.2f}): "
            f"no strong directional bias from news or market psychology"
        )

    # Recent news headlines
    headlines = []
    for n in news[:2]:
        t = n.get("title") or n.get("headline") or ""
        if t: headlines.append(f'"{t}"')
    if headlines:
        lines.append("Recent headlines: " + " | ".join(headlines))

    # Candle psychology
    bull_candles = [c for c in candles if c.get("score", 0) > 0]
    bear_candles = [c for c in candles if c.get("score", 0) < 0]
    if bull_candles:
        lines.append(
            "Price action shows bullish psychology: "
            + ", ".join(c["pattern"] for c in bull_candles[:2])
        )
    elif bear_candles:
        lines.append(
            "Price action reflects bearish sentiment: "
            + ", ".join(c["pattern"] for c in bear_candles[:2])
        )

    if vol_lbl:
        lines.append(f"Volatility environment: {vol_lbl}")

    return {
        "narrative": " ".join(lines),
        "score":      overall,
        "label":      label,
    }


# ─────────────────────────────────────────────────────────────────────────────
# TRADE SETUP CALCULATOR
# ─────────────────────────────────────────────────────────────────────────────

def _calc_trade_setup(
    cur: float,
    tech: dict, gann: dict, natal: dict, simons: dict, fund: dict, sent: dict,
    sr: dict,
) -> dict:
    """Derive entry, SL, T1, T2 from the combined data."""

    sq9_t1     = gann.get("sq9_t1")
    sq9_t2     = gann.get("sq9_t2")
    sq9_support= gann.get("sq9_support")
    near_sup   = tech.get("near_sup")
    near_res   = tech.get("near_res")
    sma20      = tech.get("sma20", 0)
    sma50      = tech.get("sma50", 0)
    ann_vol    = tech.get("ann_vol", 25)
    rsi        = tech.get("rsi", 50)
    abv20      = tech.get("abv20")
    natal_bias = natal.get("bias", "NEUTRAL")
    regime     = simons.get("regime", "UNKNOWN")
    fund_bias  = fund.get("fund_bias", "NEUTRAL")
    sent_score = sent.get("score", 0)

    # ── Bias scoring ──────────────────────────────────────────────
    bull_pts = 0; bear_pts = 0

    if rsi < 35:                              bull_pts += 2
    elif rsi > 65:                            bear_pts += 2
    if tech.get("rsi_divergence") == "bullish": bull_pts += 2
    if tech.get("rsi_divergence") == "bearish": bear_pts += 2
    if tech.get("vol_surge", 1) >= 1.5:       bull_pts += 1
    if abv20:                                  bull_pts += 1
    else:                                      bear_pts += 1

    if natal_bias == "BULLISH":   bull_pts += 2
    elif natal_bias == "BEARISH": bear_pts += 2

    if regime in ("STRONG_BULL","BULL"):   bull_pts += 2
    elif regime in ("STRONG_BEAR","BEAR"): bear_pts += 2

    if fund_bias == "BULLISH":   bull_pts += 1
    elif fund_bias == "BEARISH": bear_pts += 1

    if sent_score >= 0.2:  bull_pts += 1
    elif sent_score <= -0.2: bear_pts += 1

    if gann.get("score", 0) >= 10: bull_pts += 1

    bias = "BULLISH" if bull_pts > bear_pts else \
           "BEARISH" if bear_pts > bull_pts else "NEUTRAL"

    # ── Confidence ────────────────────────────────────────────────
    gap = abs(bull_pts - bear_pts)
    confidence = "HIGH" if gap >= 5 else "MEDIUM" if gap >= 2 else "LOW"

    # ── SL % based on volatility ──────────────────────────────────
    daily_vol_pct = ann_vol / math.sqrt(252) if ann_vol else 1.5
    sl_pct = max(1.0, min(5.0, daily_vol_pct * 2.5))

    # ── Levels (BULLISH scenario) ─────────────────────────────────
    if bias == "BULLISH":
        # Entry: near support or current
        if near_sup and abs(_pct(cur, near_sup["price"])) < 3:
            entry = round(near_sup["price"] * 1.002, 2)   # 0.2% above support
        else:
            entry = cur

        # SL: below support or ATR-based
        if sq9_support and sq9_support < entry:
            stop = round(sq9_support * 0.998, 2)
        elif near_sup:
            stop = round(near_sup["price"] * (1 - sl_pct/100), 2)
        else:
            stop = round(entry * (1 - sl_pct/100), 2)

        # T1: nearest resistance or Sq9
        if sq9_t1 and sq9_t1 > entry:
            t1 = sq9_t1
        elif near_res:
            t1 = near_res["price"]
        else:
            t1 = round(entry * 1.05, 2)

        # T2: second resistance or next Sq9
        if sq9_t2 and sq9_t2 > t1:
            t2 = sq9_t2
        elif len(sr.get("resistances",[])) > 1:
            t2 = sr["resistances"][1]["price"]
        else:
            t2 = round(t1 * 1.04, 2)

    elif bias == "BEARISH":
        if near_res and abs(_pct(cur, near_res["price"])) < 3:
            entry = round(near_res["price"] * 0.998, 2)
        else:
            entry = cur
        stop  = round(entry * (1 + sl_pct/100), 2)
        t1    = near_sup["price"] if near_sup else round(entry * 0.95, 2)
        t2    = sq9_support if sq9_support else round(t1 * 0.95, 2)

    else:
        entry = cur
        stop  = round(cur * (1 - sl_pct/100), 2)
        t1    = sq9_t1 or round(cur * 1.04, 2)
        t2    = sq9_t2 or round(cur * 1.08, 2)

    # ── Risk:Reward ───────────────────────────────────────────────
    risk   = abs(entry - stop)
    reward = abs(t1 - entry)
    rr = round(reward / risk, 2) if risk > 0 else 0

    # ── Holding period from regime ─────────────────────────────────
    if regime in ("STRONG_BULL","STRONG_BEAR"):
        horizon = "3–8 days (momentum)"
    elif regime == "SIDEWAYS":
        horizon = "5–15 days (swing from S/R)"
    elif regime == "VOLATILE":
        horizon = "1–3 days (short scalp only)"
    else:
        horizon = "5–12 days (swing)"

    return {
        "bias":           bias,
        "entry":          round(entry, 2),
        "target1":        round(t1, 2),
        "target2":        round(t2, 2),
        "stop_loss":      round(stop, 2),
        "risk_reward":    f"1:{rr}",
        "holding_period": horizon,
        "confidence":     confidence,
        "bull_pts":       bull_pts,
        "bear_pts":       bear_pts,
    }


# ─────────────────────────────────────────────────────────────────────────────
# OVERALL VERDICT
# ─────────────────────────────────────────────────────────────────────────────

def _build_verdict(
    sym: str, cur: float,
    tech: dict, gann: dict, natal: dict, simons: dict,
    fund: dict, sent: dict, trade: dict,
    inv_type: str = "short",
    cycle_phase: str = "",     # ACCUMULATION / EARLY_MARKUP / MARKUP / DISTRIBUTION
    wave_pos_pct: float = 0.5, # 0=bottom, 1=top of cycle
    price_52wk_high: float = 0.0,
    price_52wk_low:  float = 0.0,
    trend_strength:  float = 0.0,
) -> str:

    bias  = trade.get("bias", "NEUTRAL")
    conf  = trade.get("confidence", "LOW")
    entry = trade.get("entry", cur)
    t1    = trade.get("target1", cur)
    t2    = trade.get("target2", cur)
    sl    = trade.get("stop_loss", cur)
    rr    = trade.get("risk_reward", "1:1")
    regime= simons.get("regime", "")
    gann_date = gann.get("best_date")
    rsi   = tech.get("rsi", 50)
    natal_bias = natal.get("bias", "NEUTRAL")

    # ── LONG-TERM CYCLE VERDICT (replaces generic BULLISH/BEARISH) ────────────
    # For long type: the verdict must reflect cycle position, NOT short-term bias.
    # Contradiction (card=BUY but verdict=BEARISH) comes from mixing timeframes.
    # Rule: the cycle position IS the verdict for long-term investments.
    if inv_type == "long":
        parts = []

        # Determine cycle position from wave_pos_pct and trend_strength
        if wave_pos_pct <= 0.30 or trend_strength < -10:
            _cycle_label = "ACCUMULATION ZONE"
            _cycle_color = "🟢"
            _action = "ACCUMULATE"
            _action_detail = (
                f"{sym} is in the ACCUMULATION ZONE of its price-time cycle. "
                f"Price at ₹{cur:,.2f} is near the cycle low — this is where long-term "
                f"positions are built. Smart money accumulates here while retail sells. "
                f"Enter in tranches at support levels."
            )
        elif wave_pos_pct <= 0.55 and trend_strength < 20:
            _cycle_label = "EARLY MARKUP"
            _cycle_color = "🟢"
            _action = "BUY"
            _action_detail = (
                f"{sym} is in the EARLY MARKUP phase of its price-time cycle. "
                f"The positive cycle has begun — price is trending up from the "
                f"accumulation base. This is the high-conviction entry window. "
                f"Buy on pullbacks to support, not on breakouts."
            )
        elif wave_pos_pct <= 0.75 and trend_strength < 30:
            _cycle_label = "MARKUP PHASE"
            _cycle_color = "🟡"
            _action = "HOLD / TRAIL"
            _action_detail = (
                f"{sym} is in the active MARKUP PHASE — the cycle is running. "
                f"If already in position: hold with trailing SL. "
                f"If not yet in: wait for a pullback to the structural support "
                f"₹{entry:,.2f} before adding. Do not chase price at this stage."
            )
        elif wave_pos_pct > 0.75 or (trend_strength > 25 and rsi > 72):
            _cycle_label = "LATE MARKUP / DISTRIBUTION"
            _cycle_color = "🔴"
            _action = "EXIT / AVOID"
            _action_detail = (
                f"{sym} is approaching the DISTRIBUTION ZONE of its cycle — "
                f"price is near the cycle high (wave position {wave_pos_pct:.0%}). "
                f"This is where long-term holders EXIT, not where new positions are opened. "
                f"If holding: begin trimming at T1 ₹{t1:,.2f}. "
                f"If not holding: wait for the next accumulation phase."
            )
        else:
            _cycle_label = "MID CYCLE"
            _cycle_color = "🟡"
            _action = "HOLD / WAIT"
            _action_detail = (
                f"{sym} is in the mid-cycle zone — neither cheap enough to accumulate "
                f"aggressively nor extended enough to exit. "
                f"If holding: trail SL to ₹{sl:,.2f} and hold toward T1 ₹{t1:,.2f}. "
                f"If not holding: set alerts at accumulation support ₹{entry:,.2f}."
            )

        parts.append(f"{_cycle_color} CYCLE PHASE: {_cycle_label} — ACTION: {_action}")
        parts.append(_action_detail)

        # Add Gann time cycle context
        dom_cycles = simons.get("dominant_cycles", [])
        if dom_cycles:
            dc = dom_cycles[0]
            dp  = dc.get("days_to_next_trough", 999)
            dpk = dc.get("days_to_next_peak", 999)
            if dp < 60 and wave_pos_pct > 0.5:
                parts.append(f"⏱ Simons cycle: trough expected in ~{dp}d — cycle may be bottoming soon, prepare watchlist.")
            elif dpk < 90 and wave_pos_pct < 0.5:
                parts.append(f"⏱ Simons cycle: peak expected in ~{dpk}d — ride to T1 ₹{t1:,.2f}, begin trailing SL.")

        # Gann date
        if gann_date:
            parts.append(f"📅 Key Gann date: {gann_date} — cycle inflection point, watch for volume + direction change.")

        # Cycle trade plan
        if _action in ("ACCUMULATE", "BUY"):
            parts.append(
                f"📋 CYCLE PLAN: Entry ₹{entry:,.2f} | SL ₹{sl:,.2f} (below cycle low — invalidation) | "
                f"T1 ₹{t1:,.2f} (exit 50%, activate trailing SL) | "
                f"T2 ₹{t2:,.2f} (distribution zone — full cycle exit). "
                f"No time limit — hold until cycle ends. R:R {rr}."
            )
        elif _action == "HOLD / TRAIL":
            parts.append(
                f"📋 HOLD PLAN: Trail SL up behind price (7–10% step). "
                f"T1 ₹{t1:,.2f} → exit 50% and lock entry cost as SL. "
                f"Let T2 ₹{t2:,.2f} run — the cycle peak will exit naturally via trailing SL."
            )

        # Natal context for long cycles (outer planets only matter)
        if natal_bias == "BULLISH":
            parts.append("🔭 Outer planet transits (Jupiter/Saturn) align bullish — major cycle support confirmed.")
        elif natal_bias == "BEARISH" and _action in ("ACCUMULATE", "BUY"):
            parts.append("⚠ Note: Short-term natal aspects lean bearish — this is normal near accumulation bottoms. The cycle low is often accompanied by negative sentiment.")

        # 52-week context
        if price_52wk_high > 0 and price_52wk_low > 0:
            _52rng = price_52wk_high - price_52wk_low
            _pos = (cur - price_52wk_low) / _52rng if _52rng > 0 else 0.5
            parts.append(
                f"📊 52-week position: {_pos:.0%} of range "
                f"(low ₹{price_52wk_low:,.2f} — high ₹{price_52wk_high:,.2f}). "
                + ("Near cycle low — ideal accumulation zone." if _pos < 0.35 else
                   "Near cycle high — distribution zone, caution." if _pos > 0.70 else
                   "Mid-range — wait for cycle bottom signal.")
            )

        return " ".join(parts)

    # ── SHORT-TERM / SWING VERDICT (unchanged) ────────────────────────────────
    parts = []

    if bias == "BULLISH":
        parts.append(
            f"{sym} presents a {conf.lower()}-confidence BULLISH setup at ₹{cur:,.2f}."
        )
        if rsi <= 35:
            parts.append("The oversold RSI is a key technical catalyst.")
        if natal_bias == "BULLISH":
            parts.append("Planetary rulers are positively activated, adding astrological confluence.")
        if gann_date:
            parts.append(f"The upcoming Gann reversal date {gann_date} further validates the timing.")
        parts.append(
            f"Trade plan: Buy near ₹{entry:,.2f}, target ₹{t1:,.2f}, stop ₹{sl:,.2f} "
            f"({rr} R:R). "
        )
        if conf == "HIGH":
            parts.append("All analytical dimensions — technical, Gann, natal, fundamental, and sentiment — are aligned bullish. Proceed with appropriate position sizing.")
        else:
            parts.append("Not all signals are fully aligned; wait for price confirmation before entry.")

    elif bias == "BEARISH":
        parts.append(
            f"{sym} shows a {conf.lower()}-confidence BEARISH setup at ₹{cur:,.2f}."
        )
        if regime in ("STRONG_BEAR","BEAR"):
            parts.append("Quant regime confirms downtrend.")
        parts.append(
            f"Avoid new long entries at this stage. "
            f"If already holding: consider tightening SL to ₹{sl:,.2f}. "
            f"Re-assess when price reaches Gann Sq9 support ₹{gann.get('sq9_support',sl):,.2f} — "
            f"a bounce from that level with volume + bullish natal aspect would be the entry trigger."
        )
        if gann_date:
            parts.append(f"Watch date: {gann_date} — a trend reversal could begin around this Gann window.")

    else:
        parts.append(
            f"{sym} at ₹{cur:,.2f} shows mixed signals — no high-conviction directional setup right now."
        )
        sq9_sup = gann.get('sq9_support', 0)
        sq9_res = gann.get('sq9_t1', 0)
        if sq9_sup and sq9_res:
            parts.append(
                f"Price is between Sq9 support ₹{sq9_sup:,.2f} and resistance ₹{sq9_res:,.2f}. "
                f"A close above ₹{sq9_res:,.2f} with volume = bullish breakout entry. "
                f"A close below ₹{sq9_sup:,.2f} = avoid / wait for next support."
            )
        if gann_date:
            parts.append(f"High-confluence Gann date approaching: {gann_date} — watch for a directional move.")
        if natal_bias == "BULLISH":
            parts.append("Natal aspects lean bullish — bias toward long if price confirms breakout.")
        elif natal_bias == "BEARISH":
            parts.append("Natal aspects lean bearish — bias toward caution if price breaks support.")

    return " ".join(parts)


# ─────────────────────────────────────────────────────────────────────────────
# HEADLINE BUILDER
# ─────────────────────────────────────────────────────────────────────────────

def _build_headline(sym: str, cur: float, trade: dict, tech: dict,
                    gann: dict, natal: dict) -> str:
    bias  = trade.get("bias", "NEUTRAL")
    conf  = trade.get("confidence", "LOW")
    rsi   = tech.get("rsi", 50)
    gann_date = gann.get("best_date", "")
    sq9t1 = gann.get("sq9_t1")
    natal_bias = natal.get("bias", "NEUTRAL")

    if bias == "BULLISH" and conf == "HIGH":
        return (
            f"{sym} — HIGH CONVICTION BULLISH: RSI {rsi:.0f} oversold at Sq9 support"
            + (f", Gann reversal date {gann_date}" if gann_date else "")
            + (f", target ₹{sq9t1:,.0f}" if sq9t1 else "")
        )
    elif bias == "BULLISH":
        return (
            f"{sym} — Bullish setup developing at ₹{cur:,.0f}"
            + (f" | Next confluence date: {gann_date}" if gann_date else "")
        )
    elif bias == "BEARISH" and conf == "HIGH":
        return f"{sym} — BEARISH CAUTION: Multiple signals warn of further downside from ₹{cur:,.0f}"
    elif bias == "BEARISH":
        return f"{sym} — Bearish pressure at ₹{cur:,.0f} | Avoid long positions for now"
    else:
        return f"{sym} — MIXED SIGNALS at ₹{cur:,.0f} | Wait for directional clarity"


# ─────────────────────────────────────────────────────────────────────────────
# MASTER ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

def generate_master_report(
    sym:          str,
    cur:          float,
    dt:           date,
    quant_data:   dict,
    gann_data:    dict,
    natal_data:   dict,
    fund_data:    Optional[dict],
    sent_data:    Optional[dict],
    advisor_action: str = "",   # "BUY" when called from advisor
    inv_type:     str = "short",
    wave_pos_pct: float = 0.5,
    price_52wk_high: float = 0.0,
    price_52wk_low:  float = 0.0,
    trend_strength:  float = 0.0,
) -> dict:
    """
    Generate the full master analysis report.
    Returns a dict ready to be JSON-serialised and returned to the browser.
    """

    m      = (quant_data.get("regime") or {}).get("metrics") or {}
    sr     = quant_data.get("support_resistance") or {}
    chart  = quant_data.get("chart") or {}
    closes  = chart.get("closes",  [])
    highs   = chart.get("highs",   [])
    lows    = chart.get("lows",    [])
    volumes = chart.get("volumes", [])
    dates   = chart.get("dates",   [])

    # ── Build each section ──
    tech   = _build_technical(sym, cur, m, sr, closes, highs, lows, volumes, dates)
    gann   = _build_gann(gann_data, cur, dt)
    natal  = _build_natal(natal_data)
    simons = _build_simons(quant_data)
    fund   = _build_fundamental(fund_data or {}, sym)
    sent   = _build_sentiment(sent_data or {})

    # ── Trade setup ──
    trade  = _calc_trade_setup(cur, tech, gann, natal, simons, fund, sent, sr)
    # Inject advisor_action so verdict reflects the actual recommendation
    if advisor_action:
        trade["advisor_action"] = advisor_action

    # ── Headline + verdict ──
    headline = _build_headline(sym, cur, trade, tech, gann, natal)
    verdict  = _build_verdict(sym, cur, tech, gann, natal, simons, fund, sent, trade,
                              inv_type=inv_type, wave_pos_pct=wave_pos_pct,
                              price_52wk_high=price_52wk_high,
                              price_52wk_low=price_52wk_low,
                              trend_strength=trend_strength)

    # ── Section 07B: Nakshatra Market Timing ──
    nak_data = {
        "narrative": "Nakshatra calculations not available.",
        "alignment_score": 0,
        "nakshatra_today": {},
        "upcoming_transitions": [],
        "rahu_kaal_schedule": []
    }
    try:
        from core.nakshatra_engine import get_current_nakshatra, get_upcoming_transitions, compute_nakshatra_alignment, get_rahu_kaal_today
        from data.instruments import get_instrument
        from datetime import timedelta
        
        inst = get_instrument(sym)
        sect = inst.sector if inst else "General"
        rp = inst.ruling_planet if inst else None
        
        nak_align = compute_nakshatra_alignment(sym, dt, inv_type, rp, sect)
        nak_today = nak_align
        
        nak_lines = []
        nak_lines.append(
            f"Today's Moon Nakshatra is {nak_today['nakshatra']} (No. {nak_today['number']}, ruled by {nak_today['ruler']}), "
            f"classified as {nak_today['guna']} with a {nak_today['behavior']} behavior pattern."
        )
        if nak_today.get("favored_today"):
            nak_lines.append(
                f"Cosmic alignment indicates {sym} is highly favored under this lunar mansion."
            )
        
        style_rec = {
            "SWING": "favorable for short-term swing setups.",
            "EXIT": "advisable for profit booking/exiting positions only.",
            "BOLD": "highly favorable for aggressive breakout entries.",
            "BUY_HOLD": "excellent for building core long-term holdings.",
            "LONGTERM": "highly auspicious for long-term investments and blue-chips.",
            "MOMENTUM": "ideal for riding strong momentum trends.",
            "TREND": "well-suited for following established medium-term trends.",
            "INTRADAY": "best suited for quick, intraday price action plays.",
            "OPTIONS": "highly suited for options structures due to high implied movement.",
        }
        style_desc = style_rec.get(nak_today.get("trade_style"), "suitable for standard technical setups.")
        nak_lines.append(
            f"The active trading profile is {nak_today.get('trade_style')}, which is {style_desc}"
        )
        if nak_today.get("caution"):
            nak_lines.append(f"Caution: {nak_today.get('caution')}.")
            
        transitions = get_upcoming_transitions(dt, 10)
        upcoming = []
        for t in transitions[:3]:
            tb = t.get("behavior", "")
            if tb in ("BULLISH", "ACCUMULATE", "STABLE"):
                t_bias = "BULLISH"
            elif tb in ("EXIT_ONLY", "CAUTION"):
                t_bias = "BEARISH"
            elif tb in ("VOLATILE", "SPECULATIVE"):
                t_bias = "VOLATILE"
            else:
                t_bias = "NEUTRAL"
            
            upcoming.append({
                "date": t["date"],
                "nakshatra": t["nakshatra"],
                "ruler": t["ruler"],
                "behavior": tb,
                "bias": t_bias,
            })
            
        rahu_days = []
        for offset in range(5):
            rd = dt + timedelta(days=offset)
            if rd.weekday() >= 5:
                continue
            rk_info = get_rahu_kaal_today(rd)
            rahu_days.append({
                "date": rd.isoformat(),
                "day": rk_info["day"],
                "window": rk_info["window_ist"]
            })
            
        nak_data = {
            "narrative": " ".join(nak_lines),
            "alignment_score": nak_today.get("nak_score", 0),
            "nakshatra_today": nak_today,
            "upcoming_transitions": upcoming,
            "rahu_kaal_schedule": rahu_days
        }
    except Exception as _ne:
        print(f"  [REPORT] Nakshatra build failed: {_ne}", flush=True)

    return {
        "symbol":     sym,
        "price":      cur,
        "date":       dt.isoformat(),
        "headline":   headline,
        "inv_type":   inv_type,
        "wave_pos_pct": wave_pos_pct,
        "technical":  tech["narrative"],
        "gann":       gann["narrative"],
        "natal":      natal["narrative"],
        "simons":     simons["narrative"],
        "fundamental":fund["narrative"],
        "sentiment":  sent["narrative"],
        "nakshatra":  nak_data,
        "trade_setup": trade,
        "overall_verdict": verdict,
        # Raw metrics for optional display
        "_metrics": {
            "rsi":          tech.get("rsi"),
            "ann_vol":      tech.get("ann_vol"),
            "vol21":        tech.get("vol21"),
            "vol_surge":    tech.get("vol_surge"),
            "rsi_divergence":tech.get("rsi_divergence"),
            "candle_patterns":tech.get("candle_patterns"),
            "gann_score":   gann.get("score"),
            "gann_date":    gann.get("best_date"),
            "natal_bull":   natal.get("bull"),
            "natal_bear":   natal.get("bear"),
            "regime":       simons.get("regime"),
            "sent_score":   sent.get("score"),
            "fund_bias":    fund.get("fund_bias"),
        }
    }