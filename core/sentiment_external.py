"""
sentiment_external.py — External Sentiment Engine for GANN·ASTRO v3.7
Free sources: Yahoo Finance News + Google News RSS + yfinance analyst data
NLP: VADER + custom financial lexicon + exponential time-decay weighting

Time decay (half-life = 7 days):
    Today       = weight 1.00x
    3 days ago  = weight 0.74x
    7 days ago  = weight 0.50x
    14 days ago = weight 0.25x
    30 days ago = weight 0.06x  (near-zero influence)

Deep Learning data: every scored headline is saved to
    core/sentiment_training_data.jsonl
Run:  python core/train_sentiment_model.py  to train your model.

Install:  pip install vaderSentiment
"""

import re, os, math, html as _html_mod, asyncio
from datetime import datetime
from urllib.request import urlopen, Request
from urllib.error import URLError
from urllib.parse import quote_plus

# ── Base dir ──────────────────────────────────────────────────────────────────
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ── Time decay ────────────────────────────────────────────────────────────────
_HALF_LIFE   = 7.0                          # days
_LAMBDA      = math.log(2) / _HALF_LIFE    # 0.0990

def _time_weight(published_str):
    """Exponential decay weight: today=1.0, 7d=0.5, 30d=0.06."""
    if not published_str:
        return 0.5
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            dt       = datetime.strptime(published_str[:16 if " " in published_str else 10], fmt)
            age_days = max(0.0, (datetime.now() - dt).total_seconds() / 86400.0)
            return round(math.exp(-_LAMBDA * age_days), 4)
        except ValueError:
            continue
    return 0.5

def _age_label(published_str):
    """Human-readable age: TODAY, 2d ago, 3w ago."""
    if not published_str:
        return ""
    try:
        for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d"):
            try:
                dt = datetime.strptime(published_str[:16 if " " in published_str else 10], fmt)
                break
            except ValueError:
                continue
        else:
            return ""
        d = (datetime.now() - dt).total_seconds() / 86400.0
        if d < 1:   return "TODAY"
        if d < 2:   return "YESTERDAY"
        if d < 7:   return f"{int(d)}d ago"
        if d < 30:  return f"{int(d/7)}w ago"
        return f"{int(d/30)}mo ago"
    except Exception:
        return ""

def _weight_bar(w):
    filled = max(0, min(5, round(w * 5)))
    return "█" * filled + "░" * (5 - filled)

# ── Financial lexicon ─────────────────────────────────────────────────────────
FINANCIAL_LEXICON = {
    "crash":-2.5,"crashes":-2.5,"crashed":-2.5,"wipeout":-2.5,"wiped":-2.2,
    "wiped out":-2.5,"collapse":-2.5,"collapses":-2.5,"collapsed":-2.5,
    "plunge":-2.2,"plunges":-2.2,"plunged":-2.2,"tumble":-1.8,"tumbles":-1.8,
    "tumbled":-1.8,"selloff":-2.0,"sell-off":-2.0,"bloodbath":-2.8,"carnage":-2.5,
    "rout":-2.0,"default":-2.5,"bankruptcy":-2.8,"insolvency":-2.5,
    "downgrade":-2.0,"downgraded":-2.0,"penalty":-1.5,"fraud":-2.5,"scam":-2.5,
    "probe":-1.5,"losses":-1.8,"loss":-1.5,"deficit":-1.5,"weak":-1.3,
    "weakness":-1.3,"disappoints":-1.8,"missed":-1.5,"miss":-1.5,
    "below estimates":-1.8,"npa":-2.0,"bad loans":-2.0,"stressed":-1.5,
    "fall":-1.0,"falling":-1.2,"falls":-1.0,"fell":-1.2,
    "drop":-1.0,"drops":-1.0,"dropped":-1.2,"decline":-1.0,"declines":-1.0,
    "declined":-1.0,"concern":-1.0,"concerns":-1.0,"worry":-1.2,"risk":-0.8,
    "warning":-1.3,"52-week low":-2.0,"52 week low":-2.0,"multi-year low":-2.2,
    "slump":-1.8,"slumped":-1.8,"tank":-1.8,"tanked":-1.8,"stumble":-1.5,
    "stumbled":-1.5,"disappointing":-1.6,"layoffs":-1.5,"job cuts":-1.5,
    "restructuring":-1.2,"volatile":-0.8,"volatility":-0.5,"uncertain":-0.8,
    "pressure":-0.8,"headwinds":-1.0,"slowdown":-1.2,
    "surge":2.2,"surges":2.2,"surged":2.2,"rally":1.5,"rallies":1.5,
    "rallied":1.5,"rallying":1.8,"soar":2.2,"soars":2.2,"soared":2.2,
    "jump":1.5,"jumps":1.5,"jumped":1.5,"beats":1.8,"beat":1.5,
    "exceeded":1.8,"above estimates":2.0,"record profit":2.5,"record revenue":2.2,
    "record high":2.0,"upgrade":1.8,"upgraded":1.8,"buy rating":2.0,
    "strong buy":2.5,"outperform":1.8,"overweight":1.5,"recovery":1.5,
    "rebound":1.5,"bounce":1.2,"growth":1.0,"profit":1.2,"revenue growth":1.5,
    "expansion":1.2,"acquisition":0.8,"dividend":1.0,"buyback":1.2,"bonus":1.0,
    "52-week high":2.0,"52 week high":2.0,"all-time high":2.5,"breakout":1.8,
    "bullish":1.8,"momentum":1.0,"strong":0.8,"robust":1.0,
    "positive outlook":1.5,"partnership":0.8,"deal":0.7,"contract":0.8,
    "order win":1.5,"market share":0.8,"new high":1.8,"stable":0.5,
    "optimism":1.2,"confident":1.0,
}

SINGLE_WORD_LEXICON = {k: v for k, v in FINANCIAL_LEXICON.items() if " " not in k}
PHRASE_LEXICON = {k: v for k, v in FINANCIAL_LEXICON.items() if " " in k}

_vader = None
def _get_vader():
    global _vader
    if _vader is None:
        try:
            from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
            va = SentimentIntensityAnalyzer()
            va.lexicon.update(SINGLE_WORD_LEXICON)
            _vader = va
        except ImportError:
            _vader = None
    return _vader

def _score_text(text):
    if not text: return 0.0
    
    t = text.lower()
    phrase_adjustment = 0.0
    num_phrases = 0
    
    sorted_phrase_keys = sorted(PHRASE_LEXICON.keys(), key=len, reverse=True)
    phrase_stripped_text = text
    matched_phrases = []
    
    for phrase in sorted_phrase_keys:
        val = PHRASE_LEXICON[phrase]
        count = t.count(phrase)
        if count > 0:
            phrase_adjustment += val * count
            num_phrases += count
            matched_phrases.append(f"'{phrase}' (val={val}, count={count})")
            phrase_stripped_text = re.sub(re.escape(phrase), " ", phrase_stripped_text, flags=re.IGNORECASE)
            t = phrase_stripped_text.lower()
            
    phrase_stripped_text = re.sub(r"\s+", " ", phrase_stripped_text).strip()
    
    va = _get_vader()
    vader_compound = 0.0
    
    if va:
        vader_compound = va.polarity_scores(phrase_stripped_text)["compound"]
    else:
        t_fallback = phrase_stripped_text.lower()
        sc, n = 0.0, 0
        for k, v in SINGLE_WORD_LEXICON.items():
            if k in t_fallback: sc += v; n += 1
        vader_compound = max(-1.0, min(1.0, (sc / n) / 3.0)) if n else 0.0
        
    if num_phrases > 0:
        phrase_score = max(-1.0, min(1.0, phrase_adjustment / 3.0))
        final_score = 0.6 * vader_compound + 0.4 * phrase_score
    else:
        final_score = vader_compound
        
    final_score = max(-1.0, min(1.0, final_score))
    
    if num_phrases > 0:
        print(f"  [DEBUG] Scored text: final={final_score:+.3f} (vader_raw={vader_compound:+.3f}, phrase_adj={phrase_adjustment:+.3f}, phrases={matched_phrases}) | Text: '{text[:80]}...'", flush=True)
        
    return final_score

def _clean(text):
    text = _html_mod.unescape(text or "")
    text = re.sub(r"<[^>]+>"," ",text)
    return re.sub(r"\s+"," ",text).strip()[:500]

def _label(s):
    if s>=0.35:  return "STRONGLY BULLISH"
    if s>=0.10:  return "BULLISH"
    if s>-0.10:  return "NEUTRAL"
    if s>-0.35:  return "BEARISH"
    return "STRONGLY BEARISH"

def _color(s):
    if s>=0.35:  return "#00ff88"
    if s>=0.10:  return "#26a69a"
    if s>-0.10:  return "#7aa8c0"
    if s>-0.35:  return "#ffcc00"
    return "#ef5350"

def _icon(s):
    if s>=0.35:  return "▲▲"
    if s>=0.10:  return "▲"
    if s>-0.10:  return "●"
    if s>-0.35:  return "▼"
    return "▼▼"

# ── Training data saver → SQLite DB ──────────────────────────────────────────
def _save_training(headlines, symbol, instrument_type="EQUITY"):
    """
    Save headlines to news_sentiment table in market_data_v2.db.
    Works whether this module is imported as 'core.sentiment_external'
    or called standalone — tries both import paths.
    """
    try:
        # Try absolute import (works from app.py context)
        try:
            from core.sentiment_db import save_headlines
        except ImportError:
            # Fallback: direct import from same directory (core/)
            import sys as _sys, os as _os
            _core_dir = _os.path.dirname(_os.path.abspath(__file__))
            if _core_dir not in _sys.path:
                _sys.path.insert(0, _core_dir)
            from sentiment_db import save_headlines

        n = save_headlines(symbol, headlines, instrument_type)
        # n=0 means rows already existed (updated) — still successful
        print(f"  [SENT ] DB save: {len(headlines)} headlines for {symbol} "
              f"({n} new rows)", flush=True)
    except Exception as _e:
        import traceback as _tb
        print(f"  [WARN ] sentiment DB save failed [{symbol}]: {_e}", flush=True)
        print(_tb.format_exc()[-600:], flush=True)


# ── Headline builder ──────────────────────────────────────────────────────────
def _make_hl(title, snippet, url, source, pub_dt):
    raw  = _score_text(title + (" "+snippet if snippet else ""))
    tw   = _time_weight(pub_dt)
    return {
        "title":          title,
        "source":         source,
        "url":            url,
        "published":      pub_dt,
        "age_label":      _age_label(pub_dt),
        "score":          round(raw, 3),
        "time_weight":    tw,
        "weighted_score": round(raw * tw, 4),
        "label":          _label(raw),
        "color":          _color(raw),
        "icon":           _icon(raw),
        "weight_bar":     _weight_bar(tw),
        "snippet":        snippet[:160] if snippet else "",
    }

# ── Source 1: Yahoo Finance ───────────────────────────────────────────────────
def _parse_yf_item(item):
    c   = item.get("content", item)
    ttl = _clean(c.get("title","") or item.get("title",""))
    snp = _clean(c.get("summary","") or item.get("summary","") or c.get("description","") or "")
    url = (c.get("canonicalUrl",{}).get("url","") or
           c.get("clickThroughUrl",{}).get("url","") or
           item.get("link","") or c.get("url",""))
    src = (c.get("provider",{}).get("displayName","") or item.get("publisher","") or "Yahoo Finance")
    ts  = c.get("pubDate","") or item.get("providerPublishTime",0)
    pub = ""
    if isinstance(ts,(int,float)) and ts:
        pub = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
    elif isinstance(ts,str) and ts:
        try: pub = datetime.fromisoformat(ts[:19]).strftime("%Y-%m-%d %H:%M")
        except Exception: pub = ts[:16]
    return ttl, snp, url, src, pub

def _fetch_yahoo(yf_sym, n=20):
    out = []
    if not yf_sym: return out
    try:
        import yfinance as yf
        for item in (yf.Ticker(yf_sym).news or [])[:n]:
            t,s,u,src,p = _parse_yf_item(item)
            if t: out.append(_make_hl(t,s,u,src,p))
    except Exception: pass
    if not out:
        try:
            rss = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={yf_sym}&region=IN&lang=en-IN"
            req = Request(rss,headers={"User-Agent":"Mozilla/5.0"})
            with urlopen(req,timeout=6) as r: raw=r.read().decode("utf-8",errors="replace")
            for ix in re.findall(r"<item>(.*?)</item>",raw,re.DOTALL)[:n]:
                tm=re.search(r"<title>(.*?)</title>",ix,re.DOTALL)
                lm=re.search(r"<link>(.*?)</link>",ix,re.DOTALL)
                dm=re.search(r"<pubDate>(.*?)</pubDate>",ix,re.DOTALL)
                xm=re.search(r"<description>(.*?)</description>",ix,re.DOTALL)
                t=_clean(tm.group(1)) if tm else ""
                if not t: continue
                d=_clean(xm.group(1)) if xm else ""
                p=""
                if dm:
                    try: p=datetime.strptime(_clean(dm.group(1))[:25],"%a, %d %b %Y %H:%M:%S").strftime("%Y-%m-%d %H:%M")
                    except Exception: pass
                out.append(_make_hl(t,d,_clean(lm.group(1)) if lm else "","Yahoo Finance",p))
        except Exception: pass
    return out

# ── Source 2: Google News RSS ─────────────────────────────────────────────────
def _fetch_google(company, symbol, itype="EQUITY", n=15, days=7):
    """
    days: how many days back to search (1-30). Used for gap-filling.
    Default 7 = last week. Pass gap_days from sentiment_db.get_google_date_param().
    """
    out  = []
    seen = set()
    days = max(1, min(30, int(days)))
    when = f"when:{days}d"
    if itype=="INDEX":      queries=[f'"{company}" Nifty market today',"Nifty Sensex market outlook"]
    elif itype=="COMMODITY": queries=[f'"{company}" MCX price today',f'"{symbol}" commodity India']
    else:                   queries=[f'"{company}" share NSE',f'"{company}" stock result earnings']
    for q in queries:
        url = f"https://news.google.com/rss/search?q={quote_plus(q)}+{when}&hl=en-IN&gl=IN&ceid=IN:en"
        try:
            req = Request(url,headers={"User-Agent":"Mozilla/5.0 (compatible; GannAstro/3.6)"})
            with urlopen(req,timeout=6) as r: raw=r.read().decode("utf-8",errors="replace")
            for ix in re.findall(r"<item>(.*?)</item>",raw,re.DOTALL)[:n]:
                tm=re.search(r"<title>(.*?)</title>",ix,re.DOTALL)
                lm=re.search(r"<link>(.*?)</link>",ix,re.DOTALL)
                dm=re.search(r"<pubDate>(.*?)</pubDate>",ix,re.DOTALL)
                sm=re.search(r"<source[^>]*>(.*?)</source>",ix,re.DOTALL)
                xm=re.search(r"<description>(.*?)</description>",ix,re.DOTALL)
                t = _clean(tm.group(1)) if tm else ""
                if not t or t in seen: continue
                seen.add(t)
                ct = re.sub(r"\s+-\s+[A-Z][^-]{3,40}$","",t).strip() or t
                d  = _clean(xm.group(1)) if xm else ""
                if d.startswith(ct[:40]):
                    si = d.find(" - ",len(ct)-10)
                    d  = d[si+3:].strip() if si>0 else ""
                p = ""
                if dm:
                    try: p=datetime.strptime(_clean(dm.group(1))[:25],"%a, %d %b %Y %H:%M:%S").strftime("%Y-%m-%d %H:%M")
                    except Exception: pass
                out.append(_make_hl(ct,d[:160] if len(d)>30 else "",
                    _clean(lm.group(1)) if lm else "",
                    _clean(sm.group(1)) if sm else "Google News",p))
        except (URLError,Exception): continue
    seen2,uniq=[],[]
    for h in out:
        k=h["title"][:60]
        if k not in seen2: seen2.append(k); uniq.append(h)
    return uniq[:15]


async def _fetch_yahoo_async(client, yf_sym, n=20):
    out = []
    if not yf_sym: return out
    headers = {"User-Agent": "Mozilla/5.0"}
    
    # Try Yahoo search API (async)
    try:
        url = f"https://query2.finance.yahoo.com/v1/finance/search?q={yf_sym}&newsCount={n}"
        r = await client.get(url, headers=headers, timeout=6.0)
        if r.status_code == 200:
            data = r.json()
            for item in (data.get("news", []))[:n]:
                t, s, u, src, p = _parse_yf_item(item)
                if t: out.append(_make_hl(t, s, u, src, p))
    except Exception:
        pass
        
    # Fallback to RSS Feed (async)
    if not out:
        try:
            rss = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={yf_sym}&region=IN&lang=en-IN"
            r = await client.get(rss, headers=headers, timeout=6.0)
            if r.status_code == 200:
                raw = r.text
                for ix in re.findall(r"<item>(.*?)</item>", raw, re.DOTALL)[:n]:
                    tm = re.search(r"<title>(.*?)</title>", ix, re.DOTALL)
                    lm = re.search(r"<link>(.*?)</link>", ix, re.DOTALL)
                    dm = re.search(r"<pubDate>(.*?)</pubDate>", ix, re.DOTALL)
                    xm = re.search(r"<description>(.*?)</description>", ix, re.DOTALL)
                    t = _clean(tm.group(1)) if tm else ""
                    if not t: continue
                    d = _clean(xm.group(1)) if xm else ""
                    p = ""
                    if dm:
                        try:
                            p = datetime.strptime(_clean(dm.group(1))[:25], "%a, %d %b %Y %H:%M:%S").strftime("%Y-%m-%d %H:%M")
                        except Exception:
                            pass
                    out.append(_make_hl(t, d, _clean(lm.group(1)) if lm else "", "Yahoo Finance", p))
        except Exception:
            pass
    return out


async def _fetch_google_async(client, company, symbol, itype="EQUITY", n=15, days=7):
    days = max(1, min(30, int(days)))
    when = f"when:{days}d"
    if itype == "INDEX":
        queries = [f'"{company}" Nifty market today', "Nifty Sensex market outlook"]
    elif itype == "COMMODITY":
        queries = [f'"{company}" MCX price today', f'"{symbol}" commodity India']
    else:
        queries = [f'"{company}" share NSE', f'"{company}" stock result earnings']
        
    out = []
    seen = set()
    
    async def fetch_query(q):
        q_out = []
        url = f"https://news.google.com/rss/search?q={quote_plus(q)}+{when}&hl=en-IN&gl=IN&ceid=IN:en"
        try:
            headers = {"User-Agent": "Mozilla/5.0 (compatible; GannAstro/3.6)"}
            r = await client.get(url, headers=headers, timeout=6.0)
            if r.status_code == 200:
                raw = r.text
                for ix in re.findall(r"<item>(.*?)</item>", raw, re.DOTALL)[:n]:
                    tm = re.search(r"<title>(.*?)</title>", ix, re.DOTALL)
                    lm = re.search(r"<link>(.*?)</link>", ix, re.DOTALL)
                    dm = re.search(r"<pubDate>(.*?)</pubDate>", ix, re.DOTALL)
                    sm = re.search(r"<source[^>]*>(.*?)</source>", ix, re.DOTALL)
                    xm = re.search(r"<description>(.*?)</description>", ix, re.DOTALL)
                    t = _clean(tm.group(1)) if tm else ""
                    if not t:
                        continue
                    ct = re.sub(r"\s+-\s+[A-Z][^-]{3,40}$", "", t).strip() or t
                    d = _clean(xm.group(1)) if xm else ""
                    if d.startswith(ct[:40]):
                        si = d.find(" - ", len(ct) - 10)
                        d = d[si+3:].strip() if si > 0 else ""
                    p = ""
                    if dm:
                        try:
                            p = datetime.strptime(_clean(dm.group(1))[:25], "%a, %d %b %Y %H:%M:%S").strftime("%Y-%m-%d %H:%M")
                        except Exception:
                            pass
                    q_out.append((ct, d, lm, sm, p))
        except Exception:
            pass
        return q_out

    results = await asyncio.gather(*(fetch_query(q) for q in queries), return_exceptions=True)
    
    for res in results:
        if isinstance(res, Exception) or not res:
            continue
        for ct, d, lm, sm, p in res:
            if ct in seen:
                continue
            seen.add(ct)
            out.append(_make_hl(
                ct, d[:160] if len(d) > 30 else "",
                _clean(lm.group(1)) if lm else "",
                _clean(sm.group(1)) if sm else "Google News",
                p
            ))
            
    seen2, uniq = [], []
    for h in out:
        k = h["title"][:60]
        if k not in seen2:
            seen2.append(k)
            uniq.append(h)
    return uniq[:15]

# ── Source 3: Analyst data ────────────────────────────────────────────────────
def _fetch_analyst(yf_sym, itype="EQUITY"):
    res = {"recommendation":None,"target_price":None,"current_price":None,
           "upside_pct":None,"analyst_count":0,"score":0.0,
           "label":"NO DATA","color":"#7aa8c0","summary":"","recent_actions":[],
           "not_applicable": itype!="EQUITY"}
    if itype!="EQUITY" or not yf_sym:
        res["summary"] = ("Analyst ratings N/A for indices/commodities." if itype!="EQUITY"
                          else "No yfinance symbol.")
        return res
    try:
        import yfinance as yf
        info=yf.Ticker(yf_sym).info or {}
        rec=info.get("recommendationKey",""); mean=info.get("recommendationMean")
        tgt=info.get("targetMeanPrice"); cur=info.get("currentPrice") or info.get("regularMarketPrice")
        n=int(info.get("numberOfAnalystOpinions",0) or 0)
        sc=round((3.0-float(mean))/2.0,3) if mean is not None else 0.0
        up=None
        if tgt and cur and float(cur)>0: up=round((float(tgt)-float(cur))/float(cur)*100,1)
        rd={"strongbuy":"STRONG BUY","buy":"BUY","hold":"HOLD","sell":"SELL","strongsell":"STRONG SELL"}.get((rec or "").lower(),(rec or "—").upper())
        parts=[]
        if rd and rd!="—": parts.append(f"Consensus: {rd}")
        if n:   parts.append(f"{n} analysts")
        if tgt: parts.append(f"Avg target ₹{float(tgt):,.0f}")
        if up is not None: parts.append(f"{abs(up):.1f}% {'upside' if up>=0 else 'downside'} from CMP")
        res.update({"recommendation":rd,"target_price":round(float(tgt),2) if tgt else None,
                    "current_price":round(float(cur),2) if cur else None,"upside_pct":up,
                    "analyst_count":n,"score":max(-1.0,min(1.0,sc)),"label":_label(sc),
                    "color":_color(sc),"summary":" · ".join(parts) if parts else "No coverage found",
                    "not_applicable":False})
        try:
            df=yf.Ticker(yf_sym).recommendations
            if df is not None and not df.empty:
                acts=[]
                for idx,row in df.tail(8).iterrows():
                    g=str(row.get("To Grade") or row.get("toGrade") or "").strip()
                    f_=str(row.get("Firm") or row.get("firm") or "").strip()
                    a_=str(row.get("Action") or row.get("action") or "").strip()
                    if not g and not f_: continue
                    gs=_score_text(f"{g} {a_}")
                    acts.append({"date":str(idx)[:10],"firm":f_[:30],"grade":g,"action":a_,
                                 "score":round(gs,3),"color":_color(gs)})
                res["recent_actions"]=acts
        except Exception: pass
    except Exception: pass
    return res

# ── Time-decayed average ──────────────────────────────────────────────────────
def _td_avg(headlines):
    if not headlines: return 0.0
    tw = sum(h["time_weight"] for h in headlines)
    return sum(h["score"]*h["time_weight"] for h in headlines)/tw if tw else 0.0

# ── Narrative builder ─────────────────────────────────────────────────────────
def _narrative(headlines, analyst, symbol, name, itype="EQUITY"):
    if not headlines:
        return {"paragraphs":[],"themes":[],"why":"No news data available.",
                "avg_score":0.0,"weighted_avg":0.0,"pos_count":0,"neg_count":0,"neut_count":0}
    w_avg  = _td_avg(headlines)
    s_avg  = sum(h["score"] for h in headlines)/len(headlines)
    pos    = [h for h in headlines if h["score"]>=0.10]
    neg    = [h for h in headlines if h["score"]<=-0.10]
    neut   = [h for h in headlines if -0.10<h["score"]<0.10]
    by_imp = sorted(headlines, key=lambda x: abs(x["score"])*x["time_weight"], reverse=True)
    all_txt= " ".join(h["title"] for h in headlines).lower()
    theme_kws = {
        "earnings":["earnings","profit","revenue","result","quarterly","q1","q2","q3","q4","ebitda","pat","pbt"],
        "management":["ceo","cfo","md","management","board","appointed","resigned","leadership","promoter"],
        "expansion":["expansion","capacity","launch","new plant","capex","investment","acquisition","merger","stake"],
        "regulatory":["sebi","rbi","government","policy","regulation","penalty","fine","notice","gst","tax","court"],
        "debt":["debt","loan","borrowing","npa","default","credit rating","downgrade","interest","repay"],
        "dividend":["dividend","buyback","bonus share","split"],
        "outlook":["guidance","forecast","outlook","target","upgrade","downgrade","estimate","expectation"],
        "macro":["inflation","rate","rbi","fed","gdp","iip","cpi","interest rate","crude","dollar","rupee"],
        "technical":["support","resistance","breakout","52-week","all-time","overbought","oversold","chart"],
        "ai":["ai","artificial intelligence","machine learning","automation","digital"],
    }
    themes = [t for t,kws in theme_kws.items() if any(k in all_txt for k in kws)]
    paras  = []
    tc     = _color(w_avg)
    diff   = abs(w_avg-s_avg)
    dn     = (f" <span style='color:var(--dim);font-size:0.75rem;'>(simple avg {s_avg:+.3f} — "
              f"recent news {'raises' if w_avg>s_avg else 'lowers'} it)</span>") if diff>0.08 else ""
    paras.append(
        f"Out of <b>{len(headlines)}</b> news items for <b>{name}</b> ({symbol}), "
        f"the <b>time-weighted</b> tone is <b style='color:{tc}'>{_label(w_avg)}</b> "
        f"at <b style='color:{tc}'>{w_avg:+.3f}</b>{dn}. "
        f"<span style='color:var(--dim);font-size:0.75rem;'>Today=1.0× · 7d=0.5× · 30d=0.06×</span>"
    )
    paras.append(
        f"<b style='color:#26a69a'>{len(pos)} bullish</b>, "
        f"<b style='color:#ef5350'>{len(neg)} bearish</b>, "
        f"<b style='color:#7aa8c0'>{len(neut)} neutral</b> headlines."
    )
    sp,sn=0,0
    for h in by_imp:
        if sp>=2 and sn>=2: break
        age = f" <span style='color:var(--dim);font-size:0.72rem;'>[{h['age_label']}  {h['weight_bar']} {h['time_weight']:.2f}×]</span>"
        if h["score"]>=0.10 and sp<2:
            paras.append(f"<span style='color:#26a69a'>▲ BULLISH ({h['score']:+.3f}):</span> "
                         f"\"{h['title']}\"{age} — <span style='color:var(--dim)'>{h['source']}</span>")
            sp+=1
        elif h["score"]<=-0.10 and sn<2:
            paras.append(f"<span style='color:#ef5350'>▼ BEARISH ({h['score']:+.3f}):</span> "
                         f"\"{h['title']}\"{age} — <span style='color:var(--dim)'>{h['source']}</span>")
            sn+=1
    if analyst and analyst.get("analyst_count",0)>0:
        a=analyst
        ts=f"₹{a['target_price']:,.0f}" if a.get("target_price") else ""
        ut=f", implying <b>{a['upside_pct']:+.1f}%</b> {'upside' if (a.get('upside_pct') or 0)>=0 else 'downside'} from CMP" if a.get("upside_pct") is not None else ""
        paras.append(f"<b style='color:{a['color']}'>📊 Analyst consensus:</b> <b>{a['analyst_count']}</b> analysts "
                     f"rate <b style='color:{a['color']}'>{a['recommendation']}</b>"
                     f"{(' — avg target <b>'+ts+'</b>') if ts else ''}{ut}.")
    elif itype!="EQUITY":
        paras.append(f"<span style='color:var(--dim)'>ℹ Analyst ratings N/A for "
                     f"{'indices' if itype=='INDEX' else 'commodities'}.</span>")
    s=w_avg
    if   s>=0.30: why=f"📗 NEWS STRONGLY BULLISH — Predominantly positive & recent. Strong tailwinds for {symbol}."
    elif s>=0.10: why=f"📈 MILD POSITIVE BIAS — More positive than negative recent coverage for {symbol}."
    elif s>-0.10: why=f"📊 NEUTRAL NEWS FLOW — No strong directional bias in recent media for {symbol}."
    elif s>-0.30: why=f"📉 MILD NEGATIVE BIAS — Recent coverage leans negative. Watch for catalysts."
    else:         why=f"📕 NEWS STRONGLY BEARISH — Recent headlines predominantly negative for {symbol}."
    return {"paragraphs":paras,"themes":themes,"why":why,
            "avg_score":round(s_avg,3),"weighted_avg":round(w_avg,3),
            "pos_count":len(pos),"neg_count":len(neg),"neut_count":len(neut)}

# ── Cache Table Initialization ───────────────────────────────────────────────
def _init_sentiment_cache_table():
    try:
        import sqlite3
        from core.scheduler import DB_PATH
        conn = sqlite3.connect(DB_PATH, timeout=5)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sentiment_cache (
                symbol      TEXT PRIMARY KEY NOT NULL,
                cache_date  TEXT NOT NULL,
                payload     TEXT NOT NULL,
                updated_at  TEXT
            )
        """)
        conn.commit()
        conn.close()
    except Exception:
        pass


# ── Master function ───────────────────────────────────────────────────────────
def get_external_sentiment(symbol, yfinance_symbol, company_name="", instrument_type="EQUITY", force_refresh=False):
    """Fetch, time-decay-weight, score, save training data, return full result with SQLite caching."""
    import sqlite3, json
    from datetime import date
    
    _init_sentiment_cache_table()
    
    from core.scheduler import DB_PATH
    today_str = date.today().isoformat()
    
    # ── Cache check ──
    if not force_refresh:
        try:
            conn = sqlite3.connect(DB_PATH, timeout=5)
            row = conn.execute(
                "SELECT payload, cache_date FROM sentiment_cache WHERE symbol=?",
                (symbol,)
            ).fetchone()
            conn.close()
            if row:
                cached_date = row[1]
                if cached_date == today_str:
                    cached_data = json.loads(row[0])
                    cached_data["source"] = "CACHE"
                    return cached_data
        except Exception:
            pass

    name    = company_name or symbol
    yhl     = _fetch_yahoo(yfinance_symbol)
    ghl     = _fetch_google(name, symbol, instrument_type)
    analyst = _fetch_analyst(yfinance_symbol, instrument_type)
    seen,all_hl=[],[]
    for h in yhl+ghl:
        k=h["title"][:50].lower()
        if k not in seen: seen.append(k); all_hl.append(h)
    all_hl.sort(key=lambda x: abs(x["score"])*x["time_weight"], reverse=True)
    y_wa = _td_avg(yhl) if yhl else None
    g_wa = _td_avg(ghl) if ghl else None
    # ── Source 4: LLM mgmt_tone (free local extraction via llm_extractor) ─────
    llm_result = None
    mgmt_tone  = None
    guidance   = "none"
    llm_result = None
    try:
        if instrument_type == "EQUITY":
            # CACHE ONLY — never trigger live LLM extraction during sentiment fetch.
            # Live extraction happens via /api/llm_extract or nightly ingest job only.
            from core.llm_extractor import _get_cached
            llm_result = _get_cached(symbol)
            if llm_result:
                mgmt_tone = llm_result.get("mgmt_tone")
                guidance  = llm_result.get("guidance_direction", "none")
    except Exception:
        pass

    sc,wt=[],[]
    if yhl:                             sc.append(y_wa); wt.append(len(yhl))
    if ghl:                             sc.append(g_wa); wt.append(len(ghl)*1.2)
    if analyst.get("analyst_count",0)>0: sc.append(analyst["score"]); wt.append(min(analyst["analyst_count"],20)*1.5)
    if mgmt_tone is not None:           sc.append(mgmt_tone); wt.append(8.0)  # fixed weight for LLM tone
    ext = round(max(-1.0,min(1.0,sum(s*w for s,w in zip(sc,wt))/sum(wt))),3) if sc else 0.0
    narr = _narrative(all_hl[:20], analyst, symbol, name, instrument_type)
    _save_training(all_hl, symbol, instrument_type)
    
    res = {
        "external_score":  ext,
        "external_label":  _label(ext),
        "external_color":  _color(ext),
        "yahoo_headlines": yhl[:10],
        "google_headlines":ghl[:10],
        "all_headlines":   all_hl[:20],
        "analyst":         analyst,
        "narrative":       narr,
        "llm_extraction":  llm_result,
        "source_scores":   {
            "yahoo":     round(y_wa,3) if y_wa is not None else None,
            "google":    round(g_wa,3) if g_wa is not None else None,
            "analyst":   analyst["score"] if analyst.get("analyst_count",0)>0 else None,
            "mgmt_tone": round(mgmt_tone,3) if mgmt_tone is not None else None,
        },
        "guidance_direction": guidance,
        "total_items":     len(all_hl),
        "analyst_count":   analyst.get("analyst_count",0),
        "instrument_type": instrument_type,
        "decay_half_life": f"{_HALF_LIFE}d",
    }
    
    # ── Write to sentiment_cache ──
    try:
        conn = sqlite3.connect(DB_PATH, timeout=5)
        conn.execute(
            "INSERT OR REPLACE INTO sentiment_cache (symbol, cache_date, payload, updated_at) VALUES (?, ?, ?, ?)",
            (symbol, today_str, json.dumps(res), datetime.now().isoformat())
        )
        conn.commit()
        conn.close()
    except Exception:
        pass
        
    return res