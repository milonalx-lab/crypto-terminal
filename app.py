import requests
import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

# ══════════════════════════════════════════════════════════════════════════════
# 1. INITIALISATION
# ══════════════════════════════════════════════════════════════════════════════
st.set_page_config(page_title="Terminal Crypto Pro v2", layout="wide")
st.title("🛡️ Terminal Crypto Professionnel v2 — Confluence Multi-Dimensionnelle")

# ══════════════════════════════════════════════════════════════════════════════
# 2. RÉPERTOIRE FONDAMENTAL ÉTENDU
# ══════════════════════════════════════════════════════════════════════════════
repo_fondamental = {
    "Bitcoin (BTC)": {
        "coingecko_id": "bitcoin",
        "contract_mult": 1,  # 1 contrat = 1 BTC sur Binance Futures
        "tokenomics": "**Offre plafonnée à 21M**. Actif déflationniste. >94% en circulation. Émission divisée par 2 tous les ~4 ans (halving).",
        "roadmap": "Prochain halving en 2028 (1.56 BTC/bloc). Lightning Network pour la scalabilité. Adoption institutionnelle via ETF Spot.",
        "sensibilite": "Or numérique. Très corrélé à la liquidité mondiale (M2), inversement corrélé au DXY et aux taux réels US.",
        "ticker_news": "BTC",
        "lien_x": "https://x.com/Bitcoin",
        "fallback_news": [
            {"title": "Whitepaper de Satoshi Nakamoto", "body": "Document fondateur décrivant le réseau pair-à-pair.", "url": "https://bitcoin.org/bitcoin.pdf"},
            {"title": "Thèse d'Investissement BTC", "body": "Analyse des cycles de liquidité et réserve de valeur.", "url": "https://www.coindesk.com/learn/what-is-bitcoin-the-ultimate-guide/"}
        ]
    },
    "Ethereum (ETH)": {
        "coingecko_id": "ethereum",
        "contract_mult": 1,  # 1 contrat = 1 ETH
        "tokenomics": "Offre dynamique avec burn EIP-1559. Peut devenir déflationniste en période de forte activité réseau.",
        "roadmap": "Phase 'The Surge' : optimisation L2 pour >100k TPS. Proto-danksharding (EIP-4844) actif.",
        "sensibilite": "Actif de croissance tech. Corrélé au BTC mais amplifié. TVL DeFi et volumes NFT comme catalyseurs.",
        "ticker_news": "ETH",
        "lien_x": "https://x.com/ethereum",
        "fallback_news": [
            {"title": "Whitepaper Ethereum", "body": "Fonctionnement de l'EVM et des smart contracts.", "url": "https://ethereum.org/en/whitepaper/"},
            {"title": "Roadmap Ethereum", "body": "The Merge, Surge, Scourge et mise à l'échelle.", "url": "https://www.coindesk.com/learn/what-is-ethereum/"}
        ]
    },
    "Solana (SOL)": {
        "coingecko_id": "solana",
        "contract_mult": 1,  # 1 contrat = 1 SOL
        "tokenomics": "Inflation décroissante vers 1.5%. 50% des frais de transaction brûlés. Staking yield ~7%.",
        "roadmap": "Client Firedancer (Jump Crypto) pour éliminer les pannes. Compression d'état pour réduire les coûts.",
        "sensibilite": "Actif à haut bêta. Très sensible au sentiment retail et aux volumes spéculatifs (memecoins).",
        "ticker_news": "SOL",
        "lien_x": "https://x.com/solana",
        "fallback_news": [
            {"title": "Whitepaper Proof-of-History", "body": "Synchronisation des horloges pour la vitesse réseau.", "url": "https://solana.com/solana-whitepaper.pdf"},
            {"title": "Architecture Solana", "body": "Transactions, frais et décentralisation.", "url": "https://www.coindesk.com/learn/what-is-solana/"}
        ]
    },
    "Chainlink (LINK)": {
        "coingecko_id": "chainlink",
        "contract_mult": 1,
        "tokenomics": "Offre fixe de 1Md de LINK. ~60% en circulation. Utilisation pour payer les services d'oracles.",
        "roadmap": "CCIP (Cross-Chain Interoperability Protocol) en expansion. Staking v0.2 avec slashing.",
        "sensibilite": "Infrastructure DeFi. Bêta moyen. Catalyseurs : nouveaux partenariats, intégrations CCIP, adoption institutionnelle.",
        "ticker_news": "LINK",
        "lien_x": "https://x.com/chainlink",
        "fallback_news": [
            {"title": "Whitepaper Chainlink", "body": "Réseau d'oracles décentralisé.", "url": "https://chain.link/whitepaper"},
            {"title": "CCIP Protocol", "body": "Interopérabilité cross-chain.", "url": "https://chain.link/cross-chain"}
        ]
    },
    "Avalanche (AVAX)": {
        "coingecko_id": "avalanche-2",
        "contract_mult": 1,
        "tokenomics": "Offre plafonnée à 720M. Frais brûlés intégralement. Staking yield ~8%.",
        "roadmap": "Subnets personnalisables. Avalanche9000 (réduction des coûts). Adoption gaming et RWA.",
        "sensibilite": "Concurrent L1. Bêta élevé. Sensible à l'activité des subnets et aux partenariats institutionnels.",
        "ticker_news": "AVAX",
        "lien_x": "https://x.com/avaborneofficial",
        "fallback_news": [
            {"title": "Whitepaper Avalanche", "body": "Consensus Snow et architecture multi-chain.", "url": "https://www.avax.network/whitepapers"},
            {"title": "Subnets Avalanche", "body": "Blockchains personnalisées.", "url": "https://www.coindesk.com/learn/what-is-avalanche/"}
        ]
    }
}

options_cryptos = {
    "Bitcoin (BTC)": "BTCUSDT",
    "Ethereum (ETH)": "ETHUSDT",
    "Solana (SOL)": "SOLUSDT",
    "Chainlink (LINK)": "LINKUSDT",
    "Avalanche (AVAX)": "AVAXUSDT",
}

# ══════════════════════════════════════════════════════════════════════════════
# 3. FONCTIONS DE CHARGEMENT SÉCURISÉES
# ══════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=60)
def charger_donnees_prix(symbole, intervalle="1d", limite=200):
    """Charge les bougies OHLC via CoinGecko (sans restriction géographique).
    symbole ici = coingecko_id (ex: 'bitcoin', 'ethereum')
    """
    try:
        # CoinGecko OHLC : valeurs acceptées = 1,7,14,30,90,180,365
        jours = 365
        url = f"https://api.coingecko.com/api/v3/coins/{symbole}/ohlc?vs_currency=usd&days={jours}"
        reponse = requests.get(url, timeout=15)
        reponse.raise_for_status()
        data = reponse.json()
        df = pd.DataFrame(data, columns=['Timestamp', 'Open', 'High', 'Low', 'Close'])
        df['Date'] = pd.to_datetime(df['Timestamp'], unit='ms')
        for col in ['Open', 'High', 'Low', 'Close']:
            df[col] = pd.to_numeric(df[col])
        # Volume via market_chart (requête séparée)
        url_vol = f"https://api.coingecko.com/api/v3/coins/{symbole}/market_chart?vs_currency=usd&days={jours}&interval=daily"
        rep_vol = requests.get(url_vol, timeout=15).json()
        volumes = rep_vol.get('total_volumes', [])
        df_vol = pd.DataFrame(volumes, columns=['Timestamp_v', 'Volume'])
        df_vol['Date_v'] = pd.to_datetime(df_vol['Timestamp_v'], unit='ms').dt.normalize()
        df['Date_norm'] = df['Date'].dt.normalize()
        df = df.merge(df_vol[['Date_v', 'Volume']], left_on='Date_norm', right_on='Date_v', how='left')
        df['Volume'] = df['Volume'].fillna(0)
        df['Quote_volume'] = df['Volume']
        df['Trades'] = 0
        df = df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume', 'Quote_volume', 'Trades']].copy()
        df = df.drop_duplicates(subset='Date').reset_index(drop=True)
        return df
    except Exception as e:
        st.error(f"Erreur de chargement CoinGecko ({symbole}) : {e}")
        return pd.DataFrame()


@st.cache_data(ttl=30)
def charger_metrics_derives(symbole):
    """Funding Rate + Open Interest depuis Binance Futures."""
    funding, oi = 0.0, 0.0
    try:
        rep_f = requests.get(f"https://fapi.binance.com/fapi/v1/premiumIndex?symbol={symbole}", timeout=5).json()
        funding = float(rep_f.get('lastFundingRate', 0)) * 100
    except Exception:
        pass
    try:
        rep_oi = requests.get(f"https://fapi.binance.com/fapi/v1/openInterest?symbol={symbole}", timeout=5).json()
        oi = float(rep_oi.get('openInterest', 0))
    except Exception:
        pass
    return funding, oi


@st.cache_data(ttl=300)
def charger_long_short_ratio(symbole):
    """Ratio Long/Short des top traders Binance."""
    try:
        url = f"https://fapi.binance.com/futures/data/topLongShortAccountRatio?symbol={symbole}&period=1h&limit=1"
        rep = requests.get(url, timeout=5).json()
        if rep:
            return float(rep[0].get('longShortRatio', 1.0))
    except Exception:
        pass
    return 1.0


@st.cache_data(ttl=300)
def charger_liquidations_proxy(symbole):
    """Proxy des liquidations via variation soudaine de l'OI sur 24h (historique OI)."""
    try:
        url = f"https://fapi.binance.com/futures/data/openInterestHist?symbol={symbole}&period=1h&limit=24"
        rep = requests.get(url, timeout=5).json()
        if rep and len(rep) >= 2:
            oi_debut = float(rep[0]['sumOpenInterest'])
            oi_fin = float(rep[-1]['sumOpenInterest'])
            variation_pct = ((oi_fin - oi_debut) / oi_debut) * 100 if oi_debut > 0 else 0
            return variation_pct
    except Exception:
        pass
    return 0.0


@st.cache_data(ttl=600)
def charger_donnees_coingecko(coin_id):
    """Données globales CoinGecko : market cap, supply, ATH, variation."""
    try:
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}?localization=false&tickers=false&community_data=false&developer_data=false"
        rep = requests.get(url, timeout=10).json()
        market = rep.get('market_data', {})
        return {
            "market_cap": market.get('market_cap', {}).get('usd', 0),
            "total_volume_24h": market.get('total_volume', {}).get('usd', 0),
            "circulating_supply": market.get('circulating_supply', 0),
            "total_supply": market.get('total_supply', 0),
            "max_supply": market.get('max_supply', None),
            "ath": market.get('ath', {}).get('usd', 0),
            "ath_date": market.get('ath_date', {}).get('usd', ''),
            "ath_change_pct": market.get('ath_change_percentage', {}).get('usd', 0),
            "price_change_24h_pct": market.get('price_change_percentage_24h', 0),
            "price_change_7d_pct": market.get('price_change_percentage_7d', 0),
            "price_change_30d_pct": market.get('price_change_percentage_30d', 0),
            "price_change_1y_pct": market.get('price_change_percentage_1y', 0),
            "fully_diluted_valuation": market.get('fully_diluted_valuation', {}).get('usd', 0),
        }
    except Exception:
        return {}


@st.cache_data(ttl=600)
def charger_dominance_btc():
    """BTC Dominance + Total Market Cap depuis CoinGecko."""
    try:
        url = "https://api.coingecko.com/api/v3/global"
        rep = requests.get(url, timeout=10).json()
        data = rep.get('data', {})
        return {
            "btc_dominance": data.get('market_cap_percentage', {}).get('btc', 0),
            "eth_dominance": data.get('market_cap_percentage', {}).get('eth', 0),
            "total_market_cap": data.get('total_market_cap', {}).get('usd', 0),
            "total_volume_24h": data.get('total_volume', {}).get('usd', 0),
            "market_cap_change_24h_pct": data.get('market_cap_change_percentage_24h_usd', 0),
        }
    except Exception:
        return {}


@st.cache_data(ttl=120)
def charger_fear_and_greed():
    """Fear & Greed Index + historique 30j."""
    try:
        rep = requests.get("https://api.alternative.me/fng/?limit=30", timeout=5).json()
        data = rep.get('data', [])
        actuel = data[0] if data else {}
        historique = [(int(d['value']), d['value_classification']) for d in data]
        return int(actuel.get('value', 50)), actuel.get('value_classification', 'Neutre'), historique
    except Exception:
        return 50, "Neutre", []


@st.cache_data(ttl=600)
def charger_actualites(ticker):
    """Actualités CryptoCompare."""
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        url = f"https://min-api.cryptocompare.com/data/v2/news/?categories={ticker}&lang=EN"
        reponse = requests.get(url, headers=headers, timeout=5)
        if reponse.status_code == 200:
            return reponse.json().get('Data', [])[:5]
    except Exception:
        pass
    return []


# ══════════════════════════════════════════════════════════════════════════════
# 4. MOTEUR D'ANALYSE TECHNIQUE
# ══════════════════════════════════════════════════════════════════════════════

def calculer_rsi_wilder(series, period=14):
    """RSI avec lissage exponentiel de Wilder (méthode correcte)."""
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    perte = -delta.where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    avg_perte = perte.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_perte
    return 100 - (100 / (1 + rs))


def calculer_macd(series, fast=12, slow=26, signal=9):
    """MACD classique avec ligne de signal et histogramme."""
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def calculer_atr(df, period=14):
    """Average True Range pour mesurer la volatilité."""
    high_low = df['High'] - df['Low']
    high_close = (df['High'] - df['Close'].shift()).abs()
    low_close = (df['Low'] - df['Close'].shift()).abs()
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return true_range.ewm(alpha=1/period, min_periods=period, adjust=False).mean()


def calculer_adx(df, period=14):
    """ADX — mesure la force de la tendance (pas la direction)."""
    plus_dm = df['High'].diff()
    minus_dm = -df['Low'].diff()
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)
    atr = calculer_atr(df, period)
    plus_di = 100 * (plus_dm.ewm(alpha=1/period, adjust=False).mean() / atr)
    minus_di = 100 * (minus_dm.ewm(alpha=1/period, adjust=False).mean() / atr)
    dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di))
    adx = dx.ewm(alpha=1/period, adjust=False).mean()
    return adx, plus_di, minus_di


def calculer_stochastic_rsi(rsi_series, period=14, smooth_k=3, smooth_d=3):
    """Stochastic RSI — mesure le RSI par rapport à sa propre plage."""
    min_rsi = rsi_series.rolling(window=period).min()
    max_rsi = rsi_series.rolling(window=period).max()
    stoch_rsi = (rsi_series - min_rsi) / (max_rsi - min_rsi)
    k = stoch_rsi.rolling(window=smooth_k).mean() * 100
    d = k.rolling(window=smooth_d).mean()
    return k, d


def calculer_obv(df):
    """On-Balance Volume — flux de volume cumulé."""
    obv = (np.sign(df['Close'].diff()) * df['Volume']).fillna(0).cumsum()
    return obv


def calculer_vwap_rolling(df, period=20):
    """VWAP glissant sur N périodes."""
    cumul_vol = df['Volume'].rolling(window=period).sum()
    cumul_vol_prix = (df['Close'] * df['Volume']).rolling(window=period).sum()
    return cumul_vol_prix / cumul_vol


def calculer_ichimoku(df):
    """Ichimoku Cloud complet."""
    tenkan = (df['High'].rolling(9).max() + df['Low'].rolling(9).min()) / 2
    kijun = (df['High'].rolling(26).max() + df['Low'].rolling(26).min()) / 2
    senkou_a = ((tenkan + kijun) / 2).shift(26)
    senkou_b = ((df['High'].rolling(52).max() + df['Low'].rolling(52).min()) / 2).shift(26)
    chikou = df['Close'].shift(-26)
    return tenkan, kijun, senkou_a, senkou_b, chikou


def calculer_fibonacci(df, lookback=100):
    """Niveaux de retracement Fibonacci sur le swing récent."""
    recent = df.tail(lookback)
    swing_high = recent['High'].max()
    swing_low = recent['Low'].min()
    diff = swing_high - swing_low
    niveaux = {
        "0% (High)": swing_high,
        "23.6%": swing_high - 0.236 * diff,
        "38.2%": swing_high - 0.382 * diff,
        "50%": swing_high - 0.5 * diff,
        "61.8%": swing_high - 0.618 * diff,
        "78.6%": swing_high - 0.786 * diff,
        "100% (Low)": swing_low,
    }
    return niveaux


def detecter_supports_resistances(df, window=15, nb=3):
    """Détection améliorée : exclut les bougies non confirmées."""
    df_confirmed = df.iloc[:-window]  # Exclure les bougies trop récentes
    if len(df_confirmed) < window * 2:
        return [], []
    is_min = df_confirmed['Low'] == df_confirmed['Low'].rolling(window=window, center=True).min()
    is_max = df_confirmed['High'] == df_confirmed['High'].rolling(window=window, center=True).max()
    supports = df_confirmed[is_min]['Low'].tail(nb).tolist()
    resistances = df_confirmed[is_max]['High'].tail(nb).tolist()
    return supports, resistances


def appliquer_analyse_technique(df):
    """Applique l'ensemble des indicateurs techniques au DataFrame."""
    # Moyennes mobiles
    df['EMA_12'] = df['Close'].ewm(span=12, adjust=False).mean()
    df['EMA_26'] = df['Close'].ewm(span=26, adjust=False).mean()
    df['MA_20'] = df['Close'].rolling(20).mean()
    df['MA_50'] = df['Close'].rolling(50).mean()
    df['MA_100'] = df['Close'].rolling(100).mean()
    df['MA_200'] = df['Close'].rolling(200).mean()

    # Bollinger Bands
    df['STD_20'] = df['Close'].rolling(20).std()
    df['BB_Haute'] = df['MA_20'] + (2 * df['STD_20'])
    df['BB_Basse'] = df['MA_20'] - (2 * df['STD_20'])
    df['BB_Width'] = (df['BB_Haute'] - df['BB_Basse']) / df['MA_20'] * 100

    # RSI (Wilder)
    df['RSI'] = calculer_rsi_wilder(df['Close'], 14)

    # Stochastic RSI
    df['StochRSI_K'], df['StochRSI_D'] = calculer_stochastic_rsi(df['RSI'])

    # MACD
    df['MACD'], df['MACD_Signal'], df['MACD_Hist'] = calculer_macd(df['Close'])

    # ATR
    df['ATR'] = calculer_atr(df, 14)
    df['ATR_Pct'] = (df['ATR'] / df['Close']) * 100

    # ADX
    df['ADX'], df['Plus_DI'], df['Minus_DI'] = calculer_adx(df, 14)

    # OBV
    df['OBV'] = calculer_obv(df)
    df['OBV_MA'] = df['OBV'].rolling(20).mean()

    # VWAP Rolling
    df['VWAP_20'] = calculer_vwap_rolling(df, 20)

    # Volume
    df['Vol_MA_20'] = df['Volume'].rolling(20).mean()

    # Ichimoku
    df['Tenkan'], df['Kijun'], df['Senkou_A'], df['Senkou_B'], df['Chikou'] = calculer_ichimoku(df)

    return df


# ══════════════════════════════════════════════════════════════════════════════
# 5. MOTEUR DE CONFLUENCE — SCORING MULTI-DIMENSIONNEL
# ══════════════════════════════════════════════════════════════════════════════

def calculer_score_confluence(df, funding, fng_valeur, ls_ratio, oi_var_24h, statut_roadmap, statut_politique):
    """
    Score de confluence sur 10 points répartis en 3 dimensions :
    - Technique (max 5 pts)
    - Dérivés & Sentiment (max 3 pts)
    - Fondamental manuel (max 2 pts)
    """
    infos = df.iloc[-1]
    prix = infos['Close']
    details = {}

    # ──── TECHNIQUE (5 pts max) ────

    # 1. Tendance : Prix vs MA50 + MA200
    score_tendance = 0
    if prix < infos['MA_50']:
        score_tendance += 0.5
    if not pd.isna(infos.get('MA_200')) and prix < infos['MA_200']:
        score_tendance += 0.5
    details["Tendance (prix < MA)"] = f"{score_tendance}/1.0"

    # 2. Bollinger : prix sous bande basse
    score_bollinger = 1.0 if prix <= infos['BB_Basse'] else 0.0
    details["Bollinger Basse touchée"] = f"{score_bollinger}/1.0"

    # 3. RSI < 38 (survendu)
    score_rsi = 0
    if infos['RSI'] < 30:
        score_rsi = 1.0
    elif infos['RSI'] < 38:
        score_rsi = 0.5
    details[f"RSI ({infos['RSI']:.1f})"] = f"{score_rsi}/1.0"

    # 4. Volume climax (> 1.5x moyenne)
    score_volume = 1.0 if infos['Volume'] > (1.5 * infos['Vol_MA_20']) else 0.0
    details["Volume Climax"] = f"{score_volume}/1.0"

    # 5. MACD croisement haussier OU histogramme en rebond
    score_macd = 0
    if infos['MACD_Hist'] > 0 and df['MACD_Hist'].iloc[-2] < 0:
        score_macd = 1.0  # Croisement haussier frais
    elif infos['MACD_Hist'] > df['MACD_Hist'].iloc[-2] and infos['MACD'] < 0:
        score_macd = 0.5  # Momentum en amélioration en zone négative
    details["MACD Signal"] = f"{score_macd}/1.0"

    score_technique = score_tendance + score_bollinger + score_rsi + score_volume + score_macd

    # ──── DÉRIVÉS & SENTIMENT (3 pts max) ────

    # 6. Fear & Greed < 30 (panique)
    score_fng = 0
    if fng_valeur < 20:
        score_fng = 1.0
    elif fng_valeur < 30:
        score_fng = 0.5
    details[f"Fear & Greed ({fng_valeur})"] = f"{score_fng}/1.0"

    # 7. Funding Rate (malus si > 0.05%, bonus si très négatif)
    score_funding = 0
    if funding < -0.01:
        score_funding = 1.0  # Shorts paient cher = pression de rachat
    elif funding < 0.02:
        score_funding = 0.5  # Neutre sain
    elif funding > 0.05:
        score_funding = -1.0  # Surchauffe levier
    details[f"Funding ({funding:.4f}%)"] = f"{score_funding}/1.0"

    # 8. Long/Short ratio + variation OI
    score_derives = 0
    if ls_ratio < 0.85:
        score_derives += 0.5  # Majorité short = carburant de squeeze
    if oi_var_24h < -5:
        score_derives += 0.5  # Purge d'OI = liquidations passées
    details["Positionnement dérivés"] = f"{score_derives}/1.0"

    score_sentiment = score_fng + score_funding + score_derives

    # ──── FONDAMENTAL MANUEL (2 pts max) ────
    score_fonda = 0.0
    if "Favorable" in statut_roadmap:
        score_fonda += 0.5
    elif "Défavorable" in statut_roadmap:
        score_fonda -= 1.5
    if "Favorable" in statut_politique:
        score_fonda += 0.5
    elif "Défavorable" in statut_politique:
        score_fonda -= 1.5
    score_fonda = max(-2.0, min(2.0, score_fonda))
    details["Fondamental manuel"] = f"{score_fonda}/2.0"

    # ──── TOTAL ────
    score_total = max(0.0, min(10.0, score_technique + score_sentiment + score_fonda))

    return score_total, score_technique, score_sentiment, score_fonda, details


# ══════════════════════════════════════════════════════════════════════════════
# 6. INTERFACE — SÉLECTION & CHARGEMENT
# ══════════════════════════════════════════════════════════════════════════════

choix = st.selectbox("Sélectionne un actif :", list(options_cryptos.keys()))
symbole_api = options_cryptos[choix]
fiche = repo_fondamental[choix]

# Chargement des données (CoinGecko ID pour les prix OHLC)
df = charger_donnees_prix(fiche['coingecko_id'])
if df.empty:
    st.stop()

funding, open_interest = charger_metrics_derives(symbole_api)
ls_ratio = charger_long_short_ratio(symbole_api)
oi_var_24h = charger_liquidations_proxy(symbole_api)
fng_valeur, fng_statut, fng_historique = charger_fear_and_greed()
cg_data = charger_donnees_coingecko(fiche['coingecko_id'])
global_data = charger_dominance_btc()

# Analyse technique
df = appliquer_analyse_technique(df)
infos = df.iloc[-1]
prix = infos['Close']

# Correction OI avec multiplicateur de contrat
contract_mult = fiche.get('contract_mult', 1)
open_interest_usd = open_interest * contract_mult * prix

# Supports / Résistances
liste_supports, liste_resistances = detecter_supports_resistances(df)

# Fibonacci
niveaux_fib = calculer_fibonacci(df)

# ══════════════════════════════════════════════════════════════════════════════
# 7. BARRE LATÉRALE — RISK MANAGEMENT + FONDAMENTAL
# ══════════════════════════════════════════════════════════════════════════════

st.sidebar.header("🧮 Gestion du Risque")
capital = st.sidebar.number_input("Capital total ($)", value=10000, step=500)
risque_pct = st.sidebar.slider("Risque par trade (%)", 0.5, 5.0, 1.0, 0.5)
stop_loss_suggere = liste_supports[-1] if liste_supports else prix * 0.95
stop_loss = st.sidebar.number_input("Stop Loss ($)", value=float(stop_loss_suggere))

risque_dollars = capital * (risque_pct / 100)
distance_sl = ((prix - stop_loss) / prix) * 100
taille_position = risque_dollars / (distance_sl / 100) if distance_sl > 0 else 0
unites = taille_position / prix if prix > 0 else 0

# Calcul du Take Profit basé sur ratio Risk/Reward
rr_ratio = st.sidebar.select_slider("Ratio Risk/Reward", options=[1.5, 2.0, 2.5, 3.0, 4.0, 5.0], value=2.0)
take_profit = prix + (prix - stop_loss) * rr_ratio if distance_sl > 0 else prix * 1.1

st.sidebar.markdown("---")
st.sidebar.write(f"**Perte max :** {risque_dollars:.2f} $")
if distance_sl > 0:
    st.sidebar.info(f"👉 **Position : {taille_position:,.2f} $**\n({unites:.4f} {choix.split()[0]})")
    st.sidebar.write(f"📍 Stop Loss : {stop_loss:,.2f} $ (−{distance_sl:.1f}%)")
    st.sidebar.write(f"🎯 Take Profit ({rr_ratio}R) : {take_profit:,.2f} $ (+{distance_sl * rr_ratio:.1f}%)")
    st.sidebar.write(f"💰 Gain potentiel : {risque_dollars * rr_ratio:,.2f} $")

st.sidebar.markdown("---")
st.sidebar.header("🏛️ Pondération Fondamentale")
statut_roadmap = st.sidebar.selectbox("Feuille de Route :", ["Neutre", "Favorable (+0.5 pt)", "Défavorable (-1.5 pt)"])
statut_politique = st.sidebar.selectbox("Contexte Légal :", ["Neutre", "Favorable (+0.5 pt)", "Défavorable (-1.5 pt)"])

st.sidebar.markdown("---")
st.sidebar.header("📱 Liens")
st.sidebar.link_button(f"Flux X de {choix.split()[0]} ↗", fiche["lien_x"])

# ══════════════════════════════════════════════════════════════════════════════
# 8. SCORE DE CONFLUENCE
# ══════════════════════════════════════════════════════════════════════════════

score_total, score_tech, score_sent, score_fonda, score_details = calculer_score_confluence(
    df, funding, fng_valeur, ls_ratio, oi_var_24h, statut_roadmap, statut_politique
)

# ══════════════════════════════════════════════════════════════════════════════
# 9. AFFICHAGE PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════

st.markdown(f"# 💰 {choix.split()[0]} : **{prix:,.2f} USD**")

# ── Métriques principales ──
c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Prix", f"{prix:,.2f} $",
          delta=f"{cg_data.get('price_change_24h_pct', 0):.1f}% (24h)" if cg_data else None)
c2.metric("RSI (14j)", f"{infos['RSI']:.1f}")
c3.metric("MACD Hist", f"{infos['MACD_Hist']:.2f}",
          delta="Haussier" if infos['MACD_Hist'] > 0 else "Baissier",
          delta_color="normal" if infos['MACD_Hist'] > 0 else "inverse")
c4.metric("ATR (volatilité)", f"{infos['ATR']:.2f} ({infos['ATR_Pct']:.1f}%)")
c5.metric("Funding Rate", f"{funding:.4f}%",
          delta="Surchauffe" if funding > 0.05 else "Sain",
          delta_color="inverse" if funding > 0.05 else "normal")
c6.metric("ADX (force tendance)", f"{infos['ADX']:.1f}",
          delta="Tendance forte" if infos['ADX'] > 25 else "Range",
          delta_color="normal" if infos['ADX'] > 25 else "off")

# ── Signal de confluence ──
st.markdown("---")
col_score, col_detail = st.columns([1, 2])

with col_score:
    if score_total >= 7:
        st.success(f"🔥 CONFLUENCE FORTE — {score_total:.1f}/10")
        st.caption("Zone d'achat institutionnelle. Convergence de signaux exceptionnelle.")
    elif score_total >= 4.5:
        st.warning(f"⚠️ SIGNAL MODÉRÉ — {score_total:.1f}/10")
        st.caption("Configuration intéressante. Accumulation fractionnée envisageable.")
    else:
        st.error(f"❌ PAS DE SIGNAL — {score_total:.1f}/10")
        st.caption("Absence de panique ou configuration défavorable. Rester à l'écart.")

    st.caption(f"Technique: {score_tech:.1f}/5 · Sentiment: {score_sent:.1f}/3 · Fonda: {score_fonda:.1f}/2")

with col_detail:
    with st.expander("📊 Détail du score de confluence", expanded=False):
        for critere, valeur in score_details.items():
            st.write(f"• **{critere}** : {valeur}")

# ══════════════════════════════════════════════════════════════════════════════
# 10. GRAPHIQUE PRINCIPAL — PRIX + INDICATEURS
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("---")
tab_chart, tab_oscillateurs, tab_ichimoku, tab_volume = st.tabs(
    ["📈 Prix & Tendance", "📉 Oscillateurs", "☁️ Ichimoku", "📊 Volume & OBV"]
)

with tab_chart:
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03,
                        row_heights=[0.75, 0.25],
                        subplot_titles=("", "Volume"))

    # Chandelier
    fig.add_trace(go.Candlestick(
        x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
        name="Prix", hoverinfo="none"
    ), row=1, col=1)

    # Moyennes mobiles
    fig.add_trace(go.Scatter(x=df['Date'], y=df['MA_50'], line=dict(color='cyan', width=1.5),
                             name="MA50", hovertemplate="MA50: %{y:,.2f}$<extra></extra>"), row=1, col=1)
    if df['MA_200'].notna().sum() > 0:
        fig.add_trace(go.Scatter(x=df['Date'], y=df['MA_200'], line=dict(color='orange', width=1.5),
                                 name="MA200", hovertemplate="MA200: %{y:,.2f}$<extra></extra>"), row=1, col=1)

    # Bollinger
    fig.add_trace(go.Scatter(x=df['Date'], y=df['BB_Basse'], line=dict(color='rgba(231,76,60,0.6)', dash='dash', width=1),
                             name="BB Basse", hovertemplate="BB Basse: %{y:,.2f}$<extra></extra>"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df['Date'], y=df['BB_Haute'], line=dict(color='rgba(46,204,113,0.6)', dash='dash', width=1),
                             name="BB Haute", fill='tonexty', fillcolor='rgba(100,100,100,0.05)',
                             hovertemplate="BB Haute: %{y:,.2f}$<extra></extra>"), row=1, col=1)

    # VWAP
    fig.add_trace(go.Scatter(x=df['Date'], y=df['VWAP_20'], line=dict(color='yellow', width=1, dash='dot'),
                             name="VWAP 20j", hovertemplate="VWAP: %{y:,.2f}$<extra></extra>"), row=1, col=1)

    # Fibonacci
    fib_colors = ['rgba(255,255,255,0.3)', 'rgba(46,204,113,0.3)', 'rgba(46,204,113,0.4)',
                  'rgba(241,196,15,0.4)', 'rgba(231,76,60,0.4)', 'rgba(231,76,60,0.3)', 'rgba(255,255,255,0.3)']
    for (label, level), color in zip(niveaux_fib.items(), fib_colors):
        fig.add_hline(y=level, line_dash="dot", line_color=color, annotation_text=f"Fib {label}",
                      annotation_position="right", row=1, col=1)

    # Supports / Résistances
    for i, sup in enumerate(liste_supports):
        fig.add_hline(y=sup, line_dash="dot", line_color="rgba(46,204,113,0.5)",
                      annotation_text=f"S{i+1}", row=1, col=1)
    for i, res in enumerate(liste_resistances):
        fig.add_hline(y=res, line_dash="dot", line_color="rgba(231,76,60,0.5)",
                      annotation_text=f"R{i+1}", row=1, col=1)

    # Volume
    colors_vol = ['rgba(46,204,113,0.5)' if c >= o else 'rgba(231,76,60,0.5)'
                  for c, o in zip(df['Close'], df['Open'])]
    fig.add_trace(go.Bar(x=df['Date'], y=df['Volume'], name="Volume",
                         marker_color=colors_vol, opacity=0.7), row=2, col=1)
    fig.add_trace(go.Scatter(x=df['Date'], y=df['Vol_MA_20'], line=dict(color='white', width=1),
                             name="Vol MA20"), row=2, col=1)

    fig.update_layout(xaxis_rangeslider_visible=False, template="plotly_dark",
                      height=650, margin=dict(l=10, r=10, t=30, b=10), hovermode="x unified",
                      showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=1.02))
    st.plotly_chart(fig, use_container_width=True)


with tab_oscillateurs:
    fig_osc = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.05,
                            subplot_titles=("RSI (14) & Stochastic RSI", "MACD", "ADX"))

    # RSI
    fig_osc.add_trace(go.Scatter(x=df['Date'], y=df['RSI'], line=dict(color='#8e44ad', width=1.5),
                                 name="RSI"), row=1, col=1)
    fig_osc.add_trace(go.Scatter(x=df['Date'], y=df['StochRSI_K'], line=dict(color='#3498db', width=1),
                                 name="StochRSI %K"), row=1, col=1)
    fig_osc.add_trace(go.Scatter(x=df['Date'], y=df['StochRSI_D'], line=dict(color='#e67e22', width=1, dash='dash'),
                                 name="StochRSI %D"), row=1, col=1)
    fig_osc.add_hline(y=70, line_dash="dash", line_color="rgba(231,76,60,0.5)", row=1, col=1)
    fig_osc.add_hline(y=30, line_dash="dash", line_color="rgba(46,204,113,0.5)", row=1, col=1)

    # MACD
    macd_colors = ['rgba(46,204,113,0.7)' if v >= 0 else 'rgba(231,76,60,0.7)' for v in df['MACD_Hist']]
    fig_osc.add_trace(go.Bar(x=df['Date'], y=df['MACD_Hist'], name="MACD Hist",
                             marker_color=macd_colors), row=2, col=1)
    fig_osc.add_trace(go.Scatter(x=df['Date'], y=df['MACD'], line=dict(color='#3498db', width=1.5),
                                 name="MACD"), row=2, col=1)
    fig_osc.add_trace(go.Scatter(x=df['Date'], y=df['MACD_Signal'], line=dict(color='#e67e22', width=1),
                                 name="Signal"), row=2, col=1)

    # ADX
    fig_osc.add_trace(go.Scatter(x=df['Date'], y=df['ADX'], line=dict(color='white', width=2),
                                 name="ADX"), row=3, col=1)
    fig_osc.add_trace(go.Scatter(x=df['Date'], y=df['Plus_DI'], line=dict(color='#2ecc71', width=1),
                                 name="+DI"), row=3, col=1)
    fig_osc.add_trace(go.Scatter(x=df['Date'], y=df['Minus_DI'], line=dict(color='#e74c3c', width=1),
                                 name="-DI"), row=3, col=1)
    fig_osc.add_hline(y=25, line_dash="dash", line_color="rgba(255,255,255,0.3)", row=3, col=1,
                      annotation_text="Seuil tendance")

    fig_osc.update_layout(template="plotly_dark", height=700, hovermode="x unified",
                          margin=dict(l=10, r=10, t=30, b=10))
    st.plotly_chart(fig_osc, use_container_width=True)


with tab_ichimoku:
    fig_ichi = go.Figure()
    fig_ichi.add_trace(go.Candlestick(x=df['Date'], open=df['Open'], high=df['High'],
                                       low=df['Low'], close=df['Close'], name="Prix", hoverinfo="none"))
    fig_ichi.add_trace(go.Scatter(x=df['Date'], y=df['Tenkan'], line=dict(color='#3498db', width=1),
                                  name="Tenkan (9)"))
    fig_ichi.add_trace(go.Scatter(x=df['Date'], y=df['Kijun'], line=dict(color='#e74c3c', width=1),
                                  name="Kijun (26)"))
    fig_ichi.add_trace(go.Scatter(x=df['Date'], y=df['Senkou_A'], line=dict(color='rgba(46,204,113,0.5)', width=0.5),
                                  name="Senkou A"))
    fig_ichi.add_trace(go.Scatter(x=df['Date'], y=df['Senkou_B'], line=dict(color='rgba(231,76,60,0.5)', width=0.5),
                                  name="Senkou B", fill='tonexty', fillcolor='rgba(100,100,100,0.1)'))

    fig_ichi.update_layout(template="plotly_dark", height=500, hovermode="x unified",
                           xaxis_rangeslider_visible=False, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig_ichi, use_container_width=True)

    # Interprétation Ichimoku
    ichi_signals = []
    if prix > infos['Tenkan'] and prix > infos['Kijun']:
        ichi_signals.append("✅ Prix au-dessus du Tenkan et du Kijun → biais haussier.")
    elif prix < infos['Tenkan'] and prix < infos['Kijun']:
        ichi_signals.append("🔴 Prix sous le Tenkan et le Kijun → biais baissier.")
    if not pd.isna(infos.get('Senkou_A')) and not pd.isna(infos.get('Senkou_B')):
        if prix > max(infos['Senkou_A'], infos['Senkou_B']):
            ichi_signals.append("✅ Prix au-dessus du nuage → tendance haussière confirmée.")
        elif prix < min(infos['Senkou_A'], infos['Senkou_B']):
            ichi_signals.append("🔴 Prix dans/sous le nuage → tendance baissière ou neutre.")
    if ichi_signals:
        for sig in ichi_signals:
            st.write(sig)


with tab_volume:
    fig_vol = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05,
                            subplot_titles=("On-Balance Volume (OBV)", "Quote Volume ($)"))

    fig_vol.add_trace(go.Scatter(x=df['Date'], y=df['OBV'], line=dict(color='#3498db', width=1.5),
                                 name="OBV"), row=1, col=1)
    fig_vol.add_trace(go.Scatter(x=df['Date'], y=df['OBV_MA'], line=dict(color='orange', width=1, dash='dash'),
                                 name="OBV MA20"), row=1, col=1)

    fig_vol.add_trace(go.Bar(x=df['Date'], y=df['Quote_volume'], name="Volume $",
                             marker_color='rgba(52,152,219,0.5)'), row=2, col=1)

    fig_vol.update_layout(template="plotly_dark", height=500, hovermode="x unified",
                          margin=dict(l=10, r=10, t=30, b=10))
    st.plotly_chart(fig_vol, use_container_width=True)

    # Interprétation OBV
    if infos['OBV'] > infos['OBV_MA']:
        st.write("✅ OBV au-dessus de sa moyenne → flux acheteur dominant (accumulation).")
    else:
        st.write("🔴 OBV sous sa moyenne → flux vendeur dominant (distribution).")


# ══════════════════════════════════════════════════════════════════════════════
# 11. TABLEAU DE BORD DÉRIVÉS
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("---")
st.header("⚡ Marché des Dérivés")

d1, d2, d3, d4 = st.columns(4)
d1.metric("Open Interest", f"{open_interest_usd:,.0f} $")
d2.metric("Funding Rate (8h)", f"{funding:.4f}%",
          delta="Surchauffe leviers" if funding > 0.05 else ("Shorts paient" if funding < -0.01 else "Neutre"),
          delta_color="inverse" if funding > 0.05 else "normal")
d3.metric("Long/Short Ratio (Top Traders)", f"{ls_ratio:.2f}",
          delta="Majorité Long" if ls_ratio > 1.2 else ("Majorité Short" if ls_ratio < 0.85 else "Équilibré"))
d4.metric("Δ OI 24h", f"{oi_var_24h:+.1f}%",
          delta="Flush récent" if oi_var_24h < -5 else ("Buildup" if oi_var_24h > 5 else "Stable"),
          delta_color="normal" if oi_var_24h < -5 else ("inverse" if oi_var_24h > 5 else "off"))

with st.expander("📖 Lecture des dérivés"):
    st.markdown("""
**Funding Rate** : coût payé toutes les 8h entre longs et shorts. >0.05% = surchauffe acheteuse (malus appliqué). <−0.01% = shorts en souffrance (potentiel squeeze).

**Long/Short Ratio** : <0.85 signifie majorité de shorts chez les top traders → carburant pour un short squeeze. >1.2 = excès de complaisance acheteuse.

**Δ OI 24h** : une chute brutale (< −5%) indique des liquidations massives récentes → le nettoyage a peut-être déjà eu lieu.
    """)

# ══════════════════════════════════════════════════════════════════════════════
# 12. CONTEXTE MACRO & MARCHÉ GLOBAL
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("---")
st.header("🌐 Contexte Macro & Marché Global")

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Fear & Greed", f"{fng_valeur}/100", delta=fng_statut,
          delta_color="inverse" if fng_valeur < 30 else ("normal" if fng_valeur > 70 else "off"))

if global_data:
    m2.metric("BTC Dominance", f"{global_data.get('btc_dominance', 0):.1f}%")
    m3.metric("Market Cap Total", f"${global_data.get('total_market_cap', 0)/1e12:.2f}T",
              delta=f"{global_data.get('market_cap_change_24h_pct', 0):.1f}% (24h)")
    m4.metric("Volume Global 24h", f"${global_data.get('total_volume_24h', 0)/1e9:.0f}B")
    m5.metric("ETH Dominance", f"{global_data.get('eth_dominance', 0):.1f}%")

# Historique Fear & Greed (mini-graphique)
if fng_historique:
    fng_vals = [v for v, _ in fng_historique]
    fng_fig = go.Figure()
    fng_fig.add_trace(go.Scatter(y=fng_vals[::-1], mode='lines+markers',
                                  line=dict(color='#f39c12', width=2),
                                  marker=dict(size=3), name="FNG"))
    fng_fig.add_hline(y=30, line_dash="dash", line_color="rgba(46,204,113,0.5)", annotation_text="Peur extrême")
    fng_fig.add_hline(y=70, line_dash="dash", line_color="rgba(231,76,60,0.5)", annotation_text="Avidité extrême")
    fng_fig.update_layout(template="plotly_dark", height=200, margin=dict(l=10, r=10, t=10, b=10),
                          xaxis_title="Jours (30j)", yaxis_title="FNG", showlegend=False)
    st.plotly_chart(fng_fig, use_container_width=True)

with st.expander("📖 Grille de lecture macro"):
    st.markdown("""
**Fear & Greed < 25** : Peur extrême historiquement corrélée aux points bas locaux. Signal d'accumulation.

**BTC Dominance en hausse** : Les capitaux quittent les altcoins pour le BTC → phase de « flight to quality ». Défavorable aux altcoins.

**BTC Dominance en baisse** : Capital qui ruisselle vers les altcoins → phase d'alt-season potentielle.

**Corrélations clés** : BTC est inversement corrélé au DXY (dollar fort = BTC faible) et positivement corrélé à la liquidité M2 globale. En période de hausse des taux réels, les actifs risqués (crypto incluse) souffrent.
    """)

# ══════════════════════════════════════════════════════════════════════════════
# 13. FICHE FONDAMENTALE DE L'ACTIF
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("---")
st.header(f"📋 Fiche Fondamentale — {choix}")

# Données CoinGecko
if cg_data:
    fg1, fg2, fg3, fg4 = st.columns(4)
    fg1.metric("Market Cap", f"${cg_data.get('market_cap', 0)/1e9:.1f}B")
    fg2.metric("Volume 24h", f"${cg_data.get('total_volume_24h', 0)/1e9:.1f}B")

    max_s = cg_data.get('max_supply')
    circ_s = cg_data.get('circulating_supply', 0)
    if max_s and max_s > 0:
        fg3.metric("Supply Circulante", f"{circ_s/max_s*100:.1f}% du max")
    else:
        fg3.metric("Supply Circulante", f"{circ_s:,.0f}")

    fg4.metric("Distance ATH", f"{cg_data.get('ath_change_pct', 0):.1f}%",
               delta=f"ATH: {cg_data.get('ath', 0):,.2f}$")

    # Performance multi-timeframe
    st.subheader("📈 Performance")
    perf1, perf2, perf3, perf4 = st.columns(4)
    perf1.metric("24h", f"{cg_data.get('price_change_24h_pct', 0):+.1f}%")
    perf2.metric("7j", f"{cg_data.get('price_change_7d_pct', 0):+.1f}%")
    perf3.metric("30j", f"{cg_data.get('price_change_30d_pct', 0):+.1f}%")
    perf4.metric("1 an", f"{cg_data.get('price_change_1y_pct', 0):+.1f}%")

# Fiches texte
f_col1, f_col2, f_col3 = st.columns(3)
f_col1.markdown(f"### 📊 Tokenomics\n{fiche['tokenomics']}")
f_col2.markdown(f"### 🗺️ Roadmap\n{fiche['roadmap']}")
f_col3.markdown(f"### 📈 Sensibilité\n{fiche['sensibilite']}")

# ══════════════════════════════════════════════════════════════════════════════
# 14. RÉSUMÉ TECHNIQUE RAPIDE
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("---")
st.header("🔍 Résumé Technique Express")

resume_col1, resume_col2 = st.columns(2)

with resume_col1:
    st.subheader("Signaux Techniques")
    signals = []

    # Tendance
    if prix > infos['MA_50']:
        signals.append(("Prix > MA50", "Haussier", "✅"))
    else:
        signals.append(("Prix < MA50", "Baissier", "🔴"))

    if not pd.isna(infos.get('MA_200')):
        if prix > infos['MA_200']:
            signals.append(("Prix > MA200", "Haussier", "✅"))
        else:
            signals.append(("Prix < MA200", "Baissier", "🔴"))

    # Golden/Death cross
    if not pd.isna(infos.get('MA_200')) and not pd.isna(infos.get('MA_50')):
        if infos['MA_50'] > infos['MA_200']:
            signals.append(("MA50 > MA200", "Golden Cross", "✅"))
        else:
            signals.append(("MA50 < MA200", "Death Cross", "🔴"))

    # RSI
    if infos['RSI'] < 30:
        signals.append((f"RSI = {infos['RSI']:.0f}", "Survendu", "✅"))
    elif infos['RSI'] > 70:
        signals.append((f"RSI = {infos['RSI']:.0f}", "Suracheté", "🔴"))
    else:
        signals.append((f"RSI = {infos['RSI']:.0f}", "Neutre", "⚪"))

    # MACD
    if infos['MACD'] > infos['MACD_Signal']:
        signals.append(("MACD > Signal", "Haussier", "✅"))
    else:
        signals.append(("MACD < Signal", "Baissier", "🔴"))

    # ADX
    if infos['ADX'] > 25:
        signals.append((f"ADX = {infos['ADX']:.0f}", "Tendance forte", "✅"))
    else:
        signals.append((f"ADX = {infos['ADX']:.0f}", "Range/Faible", "⚪"))

    # Bollinger
    if prix <= infos['BB_Basse']:
        signals.append(("Prix ≤ BB Basse", "Survendu statistique", "✅"))
    elif prix >= infos['BB_Haute']:
        signals.append(("Prix ≥ BB Haute", "Suracheté statistique", "🔴"))

    for label, interpretation, emoji in signals:
        st.write(f"{emoji} **{label}** → {interpretation}")


with resume_col2:
    st.subheader("Niveaux Clés")
    st.write(f"🔹 **VWAP 20j** : {infos['VWAP_20']:,.2f} $")
    st.write(f"🔹 **BB Basse** : {infos['BB_Basse']:,.2f} $")
    st.write(f"🔹 **BB Haute** : {infos['BB_Haute']:,.2f} $")
    st.write(f"🔹 **MA50** : {infos['MA_50']:,.2f} $")
    if not pd.isna(infos.get('MA_200')):
        st.write(f"🔹 **MA200** : {infos['MA_200']:,.2f} $")
    st.markdown("**Fibonacci :**")
    for label, level in niveaux_fib.items():
        st.write(f"  · {label} : {level:,.2f} $")

# ══════════════════════════════════════════════════════════════════════════════
# 15. ACTUALITÉS
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("---")
st.header(f"📰 Actualités — {choix.split()[0]}")

articles = charger_actualites(fiche['ticker_news'])
if not articles:
    articles = fiche["fallback_news"]
    st.caption("🔄 Flux de secours : documentation permanente.")

cols_news = st.columns(min(len(articles), 5))
for idx, art in enumerate(articles):
    with cols_news[idx]:
        st.markdown(f"**{art.get('title', 'Article')[:80]}**")
        body = art.get('body', '')[:150]
        st.caption(body + "..." if len(art.get('body', '')) > 150 else body)
        if art.get('url'):
            st.link_button("Lire ↗", art['url'])

# ══════════════════════════════════════════════════════════════════════════════
# 16. LEXIQUE COMPLET
# ══════════════════════════════════════════════════════════════════════════════

with st.expander("📖 Lexique Complet des Indicateurs"):
    st.markdown("""
**RSI (Relative Strength Index)** : Oscillateur 0–100. <30 = survendu. >70 = suracheté. Calculé ici avec le lissage de Wilder.

**MACD** : Différence entre EMA12 et EMA26. Croisement au-dessus de la ligne de signal = momentum haussier. L'histogramme montre l'accélération.

**Bandes de Bollinger** : Enveloppe à ±2 écarts-types de la MA20. Prix sous la bande basse = excès statistique baissier.

**ATR (Average True Range)** : Mesure la volatilité moyenne en valeur absolue. ATR% = ATR/Prix. Plus il est élevé, plus les stops doivent être larges.

**ADX** : Mesure la force de la tendance, pas sa direction. >25 = tendance prononcée. <20 = range. +DI > −DI = tendance haussière. Inverse = baissière.

**Stochastic RSI** : RSI appliqué à lui-même. %K et %D en zone basse (<20) = RSI lui-même est survendu → signal fort.

**OBV (On-Balance Volume)** : Cumul du volume signé. OBV montant + prix stable = accumulation cachée. OBV descendant + prix stable = distribution.

**Ichimoku** : Système complet. Prix au-dessus du nuage = haussier. Tenkan > Kijun = momentum positif. Nuage vert (Senkou A > B) = tendance haussière.

**Fibonacci** : Niveaux de retracement calculés sur le swing haut/bas des 100 dernières bougies. 61.8% et 38.2% sont les zones de rebond les plus fréquentes.

**VWAP** : Prix moyen pondéré par le volume. Référence institutionnelle. Prix sous le VWAP = on achète « moins cher que la moyenne du marché ».

**Funding Rate** : Coût payé toutes les 8h entre longs et shorts sur les perpétuels. >0.05% = surchauffe acheteuse.

**Long/Short Ratio** : Ratio des positions longues/courtes des top traders. <0.85 = carburant de short squeeze.

**Δ OI** : Variation de l'Open Interest. Chute brutale = liquidations passées (purge saine).
    """)

# ── Footer ──
st.markdown("---")
st.caption(f"Terminal Crypto Pro v2 — Dernière mise à jour : {datetime.now().strftime('%d/%m/%Y %H:%M')} — Données : Binance, CoinGecko, CryptoCompare, Alternative.me")
st.caption("⚠️ Cet outil est un support d'analyse. Il ne constitue en aucun cas un conseil financier.")
