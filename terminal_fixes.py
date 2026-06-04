"""
terminal_fixes.py
-----------------
Corrections pour le Terminal Crypto Pro v2 (Streamlit).

Trois bugs corrigés :
  1. find_key_levels        -> support/résistance basés sur les pivots RÉCENTS
                               (corrige les niveaux périmés type "résistance 44,78$"
                                alors que le prix est à 68$).
  2. apply_macro_guardrail  -> dégrade/veto le score quand BTC est en risk-off,
                               peur extrême, et alt haut bêta proche de son ATH
                               (corrige le "10/10 ENTRÉE" dans un contexte piège).
  3. suggest_stop_and_size  -> stop basé structure/ATR + sizing cohérent avec le
                               risque en $ (corrige le stop absurde à -41,7%).

Dépendances : numpy, pandas (déjà présents dans ton app).
"""

import numpy as np
import pandas as pd


# --------------------------------------------------------------------------- #
# 1. BÊTA (optionnel, alimente le garde-fou)                                   #
# --------------------------------------------------------------------------- #
def compute_beta(asset_returns, btc_returns):
    """Bêta de l'actif vs BTC sur des séries de rendements alignées.
    Bêta > 1 => plus volatil que BTC (haut bêta). Renvoie None si trop peu de data."""
    a = np.asarray(asset_returns, dtype=float)
    b = np.asarray(btc_returns, dtype=float)
    n = min(len(a), len(b))
    if n < 20:
        return None
    a, b = a[-n:], b[-n:]
    var_btc = np.var(b)
    if var_btc == 0:
        return None
    return float(np.cov(a, b)[0, 1] / var_btc)


# --------------------------------------------------------------------------- #
# 2. DÉTECTEUR DE NIVEAUX (le bug le plus grave)                               #
# --------------------------------------------------------------------------- #
def _pivots(highs, lows, left, right):
    """Pivots façon fractales : sommet/creux local strict sur [i-left, i+right]."""
    piv_hi, piv_lo = [], []
    n = len(highs)
    for i in range(left, n - right):
        h, l = highs[i], lows[i]
        if h > highs[i - left:i].max() and h > highs[i + 1:i + right + 1].max():
            piv_hi.append(h)
        if l < lows[i - left:i].min() and l < lows[i + 1:i + right + 1].min():
            piv_lo.append(l)
    return piv_hi, piv_lo


def _cluster(levels, cluster_pct):
    """Regroupe les niveaux distants de moins de cluster_pct en un seul (moyenne)."""
    if not levels:
        return []
    levels = sorted(levels)
    clusters = [[levels[0]]]
    for lv in levels[1:]:
        if abs(lv - clusters[-1][-1]) / clusters[-1][-1] <= cluster_pct:
            clusters[-1].append(lv)
        else:
            clusters.append([lv])
    return [sum(c) / len(c) for c in clusters]


def find_key_levels(df, current_price, left=3, right=3, lookback=180,
                    cluster_pct=0.015, ath_proximity_pct=0.05):
    """
    Support le plus proche SOUS le prix et résistance la plus proche AU-DESSUS,
    calculés sur les pivots récents (pas l'historique complet).

    df : DataFrame avec colonnes 'high' et 'low' (bougie récente en dernier).
    Retourne un dict prêt à afficher dans le terminal.
    """
    data = df.tail(lookback)
    highs = data["high"].to_numpy(dtype=float)
    lows = data["low"].to_numpy(dtype=float)
    if len(highs) < (left + right + 5):
        return {"error": "pas assez de bougies pour détecter des pivots"}

    piv_hi, piv_lo = _pivots(highs, lows, left, right)
    res_levels = _cluster(piv_hi, cluster_pct)
    sup_levels = _cluster(piv_lo, cluster_pct)

    ath = float(highs.max())
    near_ath = current_price >= ath * (1 - ath_proximity_pct)

    res_above = sorted(r for r in res_levels if r > current_price)
    sup_below = sorted((s for s in sup_levels if s < current_price), reverse=True)

    nearest_res = res_above[0] if res_above else None
    nearest_sup = sup_below[0] if sup_below else None

    # Découverte de prix : aucune résistance pivot au-dessus.
    price_discovery = nearest_res is None and near_ath
    if nearest_res is None and not near_ath:
        nearest_res = ath  # l'ATH sert de borne si on n'est pas déjà dessus

    sup_dist = (nearest_sup - current_price) / current_price * 100 if nearest_sup else None
    res_dist = (nearest_res - current_price) / current_price * 100 if nearest_res else None

    # "Air" sous le prix : support le plus proche dangereusement loin (> 12%).
    air_below = sup_dist is not None and sup_dist < -12

    return {
        "nearest_support": round(nearest_sup, 4) if nearest_sup else None,
        "nearest_resistance": round(nearest_res, 4) if nearest_res else None,
        "support_dist_pct": round(sup_dist, 2) if sup_dist is not None else None,
        "resistance_dist_pct": round(res_dist, 2) if res_dist is not None else None,
        "all_supports": [round(s, 4) for s in sup_below[:3]],
        "all_resistances": [round(r, 4) for r in res_above[:3]],
        "ath": round(ath, 4),
        "price_discovery": bool(price_discovery),
        "air_below": bool(air_below),
    }


# --------------------------------------------------------------------------- #
# 3. GARDE-FOU MACRO / BÊTA                                                    #
# --------------------------------------------------------------------------- #
def apply_macro_guardrail(raw_score, *, btc_change_24h, fng_index,
                          dist_from_ath_pct, asset_beta=None,
                          btc_below_key_ma=False, funding_rate=None,
                          setup_type="breakout"):
    """
    Dégrade (ou veto) un score de setup 0-10 selon le risque macro.

    btc_change_24h    : variation % de BTC sur 24h (ex: -3.43)
    fng_index         : Fear & Greed 0-100
    dist_from_ath_pct : distance du prix à son ATH en % (ex: -8 = 8% sous l'ATH)
    asset_beta        : bêta vs BTC (None -> on suppose haut bêta par prudence)
    funding_rate      : funding perp en % (>0.05% = longs surchargés)
    setup_type        : 'breakout', 'pullback', 'reversal'

    Retourne (score_ajuste, raisons:list, veto:bool).
    """
    reasons, penalty, veto = [], 0.0, False

    risk_off = (btc_change_24h is not None and btc_change_24h <= -2) or btc_below_key_ma
    extreme_fear = fng_index is not None and fng_index < 20
    near_ath = dist_from_ath_pct is not None and dist_from_ath_pct > -8
    high_beta = asset_beta is None or asset_beta >= 1.3  # prudence si inconnu

    if risk_off and high_beta:
        penalty += 2.5
        reasons.append("BTC en risk-off + actif haut bêta : la corrélation prime sur le setup")
    if extreme_fear:
        penalty += 1.5
        reasons.append(f"Peur extrême (F&G {fng_index}) : contexte hostile aux entrées longues")
    if near_ath and setup_type == "breakout":
        penalty += 1.5
        reasons.append("Breakout proche de l'ATH : risque de chasse / faux signal")
    if funding_rate is not None and funding_rate > 0.05:
        penalty += 1.0
        reasons.append(f"Funding élevé ({funding_rate:.3f}%) : longs surchargés, risque de squeeze")

    # Veto dur : la combinaison classique du piège.
    if risk_off and extreme_fear and near_ath and high_beta and setup_type == "breakout":
        veto = True
        reasons.append("VETO : breakout d'un alt haut bêta près de l'ATH pendant que BTC casse en peur extrême")

    adjusted = max(0.0, raw_score - penalty)
    if veto:
        adjusted = min(adjusted, 3.0)  # l'entrée n'est plus 'envisageable'

    return round(adjusted, 1), reasons, veto


# --------------------------------------------------------------------------- #
# 4. STOP + SIZING (alimenté par find_key_levels)                             #
# --------------------------------------------------------------------------- #
def suggest_stop_and_size(entry, atr, capital, risk_pct, nearest_support=None,
                          atr_mult=1.5, direction="long"):
    """
    Stop basé sur la structure (support pivot) OU l'ATR, et taille de position
    cohérente avec le risque en $. Empêche le stop absurde à -41%.
    """
    if direction != "long":
        raise ValueError("exemple fourni pour le long uniquement")

    atr_stop = entry - atr_mult * atr
    if nearest_support is not None and nearest_support < entry:
        struct_stop = nearest_support * 0.997           # petite marge sous le support
        stop = max(atr_stop, struct_stop)               # le plus haut = le plus serré
    else:
        stop = atr_stop

    risk_per_unit = entry - stop
    if risk_per_unit <= 0:
        return {"error": "stop invalide"}

    risk_dollars = capital * (risk_pct / 100.0)
    size_units = risk_dollars / risk_per_unit
    return {
        "stop": round(stop, 4),
        "stop_pct": round((stop - entry) / entry * 100, 2),
        "risk_dollars": round(risk_dollars, 2),
        "position_units": round(size_units, 4),
        "position_value": round(size_units * entry, 2),
    }


# --------------------------------------------------------------------------- #
# EXEMPLE D'INTÉGRATION STREAMLIT (à adapter à tes variables)                  #
# --------------------------------------------------------------------------- #
# import streamlit as st
# from terminal_fixes import find_key_levels, apply_macro_guardrail, suggest_stop_and_size
#
# levels = find_key_levels(df_ohlc, current_price=price)
# stop_info = suggest_stop_and_size(
#     entry=price, atr=atr_value, capital=capital_total,
#     risk_pct=risk_par_trade, nearest_support=levels["nearest_support"],
# )
# score_final, raisons, veto = apply_macro_guardrail(
#     raw_score=score_brut,                 # ton score de setup actuel (ex 10.0)
#     btc_change_24h=btc_24h_change,        # à fetcher (CoinGecko/CoinGlass)
#     fng_index=fear_greed,                 # 12 dans ton screenshot
#     dist_from_ath_pct=(price - ath) / ath * 100,
#     asset_beta=beta_vs_btc,               # compute_beta(...) ou None
#     funding_rate=funding,                 # depuis CoinGlass/Hyperliquid API
#     setup_type="breakout",
# )
#
# if veto:
#     st.error("⛔ ENTRÉE DÉCONSEILLÉE — garde-fou macro déclenché")
# elif score_final >= 7:
#     st.success(f"Entrée envisageable — {score_final}/10")
# else:
#     st.warning(f"Setup dégradé par le contexte — {score_final}/10")
# for r in raisons:
#     st.caption("• " + r)
