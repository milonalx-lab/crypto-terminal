"""
data_fetch.py
-------------
Récupération des données live pour le Terminal Crypto Pro v2.

Choix des sources (le point clé) :
  - DÉRIVÉS HYPE  -> API native Hyperliquid (gratuite, sans rate-limit).
                    Corrige le N/A causé par la limite CoinGecko.
  - MACRO BTC     -> Binance (prix + variation 24h + MA200), limites larges, sans clé.
  - FEAR & GREED  -> alternative.me (gratuit, sans clé).
  - LONG/SHORT    -> Binance futures, en PROXY marché (BTC). Le L/S spécifique HYPE
                    n'est pas dispo gratuitement (nécessite une clé CoinGlass payante).

Tout est caché (TTL) pour ne plus saturer, et chaque fetch dégrade gracieusement :
en cas d'échec il renvoie {"error": ...} sans casser l'app.

Dépendances : requests (+ streamlit pour le cache, optionnel).
"""

import requests

HL_API      = "https://api.hyperliquid.xyz/info"
BINANCE     = "https://api.binance.com/api/v3"
BINANCE_FUT = "https://fapi.binance.com/futures/data"
FNG_API     = "https://api.alternative.me/fng/"

# --- shim de cache : utilise st.cache_data si Streamlit est là, sinon no-op --- #
try:
    import streamlit as st
    _HAS_ST = True
except Exception:
    _HAS_ST = False


def _cache(ttl):
    if _HAS_ST:
        return st.cache_data(ttl=ttl, show_spinner=False)
    def _identity(func):
        return func
    return _identity


# --------------------------------------------------------------------------- #
# PARSERS PURS (testables sans réseau)                                         #
# --------------------------------------------------------------------------- #
def _parse_hl_ctx(raw, coin):
    """raw = réponse de metaAndAssetCtxs : [meta, assetCtxs] (listes parallèles)."""
    meta, ctxs = raw[0], raw[1]
    names = [u["name"] for u in meta["universe"]]
    if coin not in names:
        return {"error": f"{coin} introuvable sur Hyperliquid"}
    c = ctxs[names.index(coin)]
    mark = float(c["markPx"])
    oi_units = float(c["openInterest"])          # en unités du coin
    funding_hr = float(c["funding"])             # taux HORAIRE (décimal)
    return {
        "mark_price":          mark,
        "open_interest_usd":   round(oi_units * mark, 2),
        "open_interest_units": oi_units,
        "funding_hourly_pct":  round(funding_hr * 100, 5),
        "funding_8h_pct":      round(funding_hr * 8 * 100, 5),     # comparable aux CEX
        "funding_annual_pct":  round(funding_hr * 24 * 365 * 100, 2),
        "volume_24h_usd":      round(float(c.get("dayNtlVlm", 0)), 2),
    }


def _parse_binance_24h(raw):
    return {
        "btc_price":      float(raw["lastPrice"]),
        "btc_change_24h": round(float(raw["priceChangePercent"]), 2),
    }


def _parse_fng(raw):
    d = raw["data"][0]
    return {"fng_index": int(d["value"]), "fng_label": d.get("value_classification")}


# --------------------------------------------------------------------------- #
# FETCHS (réseau + cache)                                                      #
# --------------------------------------------------------------------------- #
@_cache(120)
def fetch_hyperliquid_derivs(coin="HYPE", timeout=8):
    """Funding + OI + volume du perp depuis l'API native Hyperliquid."""
    try:
        r = requests.post(HL_API, json={"type": "metaAndAssetCtxs"}, timeout=timeout)
        r.raise_for_status()
        return _parse_hl_ctx(r.json(), coin)
    except Exception as e:
        return {"error": f"fetch Hyperliquid échoué : {e}"}


@_cache(120)
def fetch_btc_macro(with_ma=True, timeout=8):
    """Prix BTC + variation 24h (+ test sous MA200 daily pour le garde-fou)."""
    out = {}
    try:
        r = requests.get(f"{BINANCE}/ticker/24hr", params={"symbol": "BTCUSDT"}, timeout=timeout)
        r.raise_for_status()
        out.update(_parse_binance_24h(r.json()))
    except Exception as e:
        return {"error": f"fetch BTC échoué : {e}"}
    if with_ma:
        try:
            k = requests.get(f"{BINANCE}/klines",
                             params={"symbol": "BTCUSDT", "interval": "1d", "limit": 200},
                             timeout=timeout)
            k.raise_for_status()
            closes = [float(c[4]) for c in k.json()]
            ma200 = sum(closes) / len(closes)
            out["btc_ma200"] = round(ma200, 2)
            out["btc_below_key_ma"] = out["btc_price"] < ma200
        except Exception:
            out["btc_below_key_ma"] = False     # dégradation gracieuse
    return out


@_cache(600)
def fetch_fear_greed(timeout=8):
    """Indice Fear & Greed (alternative.me)."""
    try:
        r = requests.get(FNG_API, params={"limit": 1}, timeout=timeout)
        r.raise_for_status()
        return _parse_fng(r.json())
    except Exception as e:
        return {"error": f"fetch Fear&Greed échoué : {e}"}


@_cache(300)
def fetch_btc_long_short(timeout=8):
    """Ratio long/short BTC (proxy marché — pas spécifique HYPE)."""
    try:
        r = requests.get(f"{BINANCE_FUT}/globalLongShortAccountRatio",
                         params={"symbol": "BTCUSDT", "period": "1h", "limit": 1}, timeout=timeout)
        r.raise_for_status()
        return {"btc_long_short_ratio": round(float(r.json()[0]["longShortRatio"]), 3)}
    except Exception as e:
        return {"error": f"fetch long/short échoué : {e}"}


@_cache(120)
def fetch_all_context(coin="HYPE"):
    """Agrège tout en un dict, prêt à nourrir le garde-fou. Jamais d'exception."""
    derivs = fetch_hyperliquid_derivs(coin)
    macro  = fetch_btc_macro()
    fng    = fetch_fear_greed()
    ls     = fetch_btc_long_short()
    ctx = {"derivs": derivs, "macro": macro, "fear_greed": fng, "long_short": ls}
    # raccourcis plats pour le garde-fou (None si la source a échoué)
    ctx["btc_change_24h"]  = macro.get("btc_change_24h")  if "error" not in macro else None
    ctx["btc_below_key_ma"] = macro.get("btc_below_key_ma", False)
    ctx["fng_index"]       = fng.get("fng_index")         if "error" not in fng else None
    ctx["funding_8h_pct"]  = derivs.get("funding_8h_pct") if "error" not in derivs else None
    ctx["open_interest_usd"] = derivs.get("open_interest_usd") if "error" not in derivs else None
    return ctx
