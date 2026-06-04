"""
data_fetch.py
-------------
Récupération des données live pour le Terminal Crypto Pro v2.

Sources choisies pour fonctionner DEPUIS UN SERVEUR US (Streamlit Cloud) :
  - DÉRIVÉS    -> API native Hyperliquid (jamais géo-bloquée, sans rate-limit).
  - MACRO BTC  -> CoinGecko (prix + variation 24h + MA200). Pas Binance (451 en US).
  - FEAR&GREED -> alternative.me (gratuit, sans clé).

Tout est caché (TTL) et chaque fetch dégrade gracieusement : en cas d'échec il
renvoie {"error": ...} sans casser l'app.

Dépendances : requests (+ streamlit pour le cache, optionnel).
"""

import requests

HL_API = "https://api.hyperliquid.xyz/info"
CG     = "https://api.coingecko.com/api/v3"
FNG    = "https://api.alternative.me/fng/"

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
    """raw = réponse metaAndAssetCtxs : [meta, assetCtxs] (listes parallèles)."""
    meta, ctxs = raw[0], raw[1]
    names = [u["name"] for u in meta["universe"]]
    if coin not in names:
        return {"error": f"{coin} introuvable sur Hyperliquid"}
    c = ctxs[names.index(coin)]
    mark = float(c["markPx"])
    oi_units = float(c["openInterest"])
    funding_hr = float(c["funding"])          # taux HORAIRE (décimal)
    return {
        "mark_price":          mark,
        "open_interest_usd":   round(oi_units * mark, 2),
        "open_interest_units": oi_units,
        "funding_hourly_pct":  round(funding_hr * 100, 5),
        "funding_8h_pct":      round(funding_hr * 8 * 100, 5),   # convention CEX
        "funding_annual_pct":  round(funding_hr * 24 * 365 * 100, 2),
        "volume_24h_usd":      round(float(c.get("dayNtlVlm", 0)), 2),
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
def fetch_btc_macro(with_ma=True, timeout=10):
    """Prix BTC + variation 24h (+ test sous MA200 daily) via CoinGecko."""
    out = {}
    try:
        r = requests.get(f"{CG}/simple/price",
                         params={"ids": "bitcoin", "vs_currencies": "usd",
                                 "include_24hr_change": "true"}, timeout=timeout)
        r.raise_for_status()
        d = r.json()["bitcoin"]
        out["btc_price"] = float(d["usd"])
        out["btc_change_24h"] = round(float(d.get("usd_24h_change", 0.0)), 2)
    except Exception as e:
        return {"error": f"fetch BTC échoué : {e}"}
    if with_ma:
        try:
            k = requests.get(f"{CG}/coins/bitcoin/market_chart",
                             params={"vs_currency": "usd", "days": "200",
                                     "interval": "daily"}, timeout=timeout)
            k.raise_for_status()
            prices = [p[1] for p in k.json().get("prices", [])]
            if prices:
                ma200 = sum(prices) / len(prices)
                out["btc_ma200"] = round(ma200, 2)
                out["btc_below_key_ma"] = out["btc_price"] < ma200
        except Exception:
            out["btc_below_key_ma"] = False
    return out


@_cache(600)
def fetch_fear_greed(timeout=8):
    """Indice Fear & Greed (alternative.me)."""
    try:
        r = requests.get(FNG, params={"limit": 1}, timeout=timeout)
        r.raise_for_status()
        return _parse_fng(r.json())
    except Exception as e:
        return {"error": f"fetch Fear&Greed échoué : {e}"}
