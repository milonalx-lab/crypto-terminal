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
        "contract_mult": 1,
        "index_id": "BTC",
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
        "contract_mult": 1,
        "index_id": "ETH",
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
        "contract_mult": 1,
        "index_id": "SOL",
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
        "index_id": "LINK",
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
        "index_id": "AVAX",
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


@st.cache_data(ttl=300)
def charger_derives_coingecko(index_id):
    """Funding Rate + Open Interest via l'agrégateur CoinGecko (accessible depuis tout serveur).
    index_id : 'BTC', 'ETH', 'SOL', 'LINK', 'AVAX'.
    """
    funding, oi_usd, vol_24h = 0.0, 0.0, 0.0
    try:
        url = "https://api.coingecko.com/api/v3/derivatives"
        rep = requests.get(url, timeout=12).json()
        # On garde les perpétuels du bon index, et on choisit le marché le plus liquide
        candidats = []
        for t in rep:
            if t.get('index_id') == index_id and t.get('contract_type') == 'perpetual':
                oi = t.get('open_interest') or 0
                fr = t.get('funding_rate')
                v = t.get('volume_24h') or 0
                if oi and fr is not None:
                    candidats.append((float(oi), float(fr), float(v)))
        if candidats:
            # Marché le plus liquide = référence funding ; OI sommé sur tous les marchés
            candidats.sort(key=lambda x: x[0], reverse=True)
            funding = candidats[0][1]                    # déjà en %
            oi_usd = sum(c[0] for c in candidats)        # somme OI (USD)
            vol_24h = sum(c[2] for c in candidats)       # somme volume 24h
    except Exception:
        pass
    return funding, oi_usd, vol_24h


@st.cache_data(ttl=300)
def charger_long_short_ratio(symbole):
    """Tentative Bybit (peut échouer depuis serveur US) — sinon N/A (None)."""
    try:
        url = f"https://api.bybit.com/v5/market/account-ratio?category=linear&symbol={symbole}&period=1h&limit=1"
        rep = requests.get(url, timeout=6).json()
        liste = rep.get('result', {}).get('list', [])
        if liste:
            buy = float(liste[0].get('buyRatio', 0))
            sell = float(liste[0].get('sellRatio', 0))
            if sell > 0:
                return buy / sell
    except Exception:
        pass
    return None


@st.cache_data(ttl=600)
def charger_donnees_coingecko(coin_id):
    """Données fondamentales via /coins/markets (endpoint léger) avec retry."""
    url = ("https://api.coingecko.com/api/v3/coins/markets"
           f"?vs_currency=usd&ids={coin_id}"
           "&price_change_percentage=24h,7d,30d,1y")
    for tentative in range(3):
        try:
            rep = requests.get(url, timeout=12)
            if rep.status_code == 429:  # rate-limit → on attend et on réessaie
                import time
                time.sleep(2 * (tentative + 1))
                continue
            rep.raise_for_status()
            data = rep.json()
            if not data:
                return {}
            m = data[0]
            return {
                "market_cap": m.get('market_cap', 0) or 0,
                "total_volume_24h": m.get('total_volume', 0) or 0,
                "circulating_supply": m.get('circulating_supply', 0) or 0,
                "total_supply": m.get('total_supply', 0) or 0,
                "max_supply": m.get('max_supply', None),
                "ath": m.get('ath', 0) or 0,
                "ath_date": m.get('ath_date', ''),
                "ath_change_pct": m.get('ath_change_percentage', 0) or 0,
                "price_change_24h_pct": m.get('price_change_percentage_24h_in_currency', 0) or 0,
                "price_change_7d_pct": m.get('price_change_percentage_7d_in_currency', 0) or 0,
                "price_change_30d_pct": m.get('price_change_percentage_30d_in_currency', 0) or 0,
                "price_change_1y_pct": m.get('price_change_percentage_1y_in_currency', 0) or 0,
                "fully_diluted_valuation": m.get('fully_diluted_valuation', 0) or 0,
            }
        except Exception:
            import time
            time.sleep(1)
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


@st.cache_data(ttl=86400)
def traduire_fr(texte):
    """Traduit un texte EN→FR via l'endpoint public Google Translate. Fallback : texte original."""
    if not texte or not texte.strip():
        return texte
    try:
        url = "https://translate.googleapis.com/translate_a/single"
        params = {"client": "gtx", "sl": "en", "tl": "fr", "dt": "t", "q": texte[:1500]}
        rep = requests.get(url, params=params, timeout=8)
        if rep.status_code == 200:
            data = rep.json()
            # data[0] = liste de segments traduits
            return "".join(seg[0] for seg in data[0] if seg[0])
    except Exception:
        pass
    return texte


@st.cache_data(ttl=600)
def charger_actualites(ticker, coingecko_id):
    """Actualités via flux RSS (fiables, publics) puis CryptoCompare, traduites en FR."""
    import xml.etree.ElementTree as ET
    import re as _re

    nom_complet = {"BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana",
                   "LINK": "chainlink", "AVAX": "avalanche"}.get(ticker, ticker.lower())
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

    def nettoyer_html(txt):
        txt = _re.sub(r'<[^>]+>', '', txt or '')
        txt = _re.sub(r'\s+', ' ', txt)
        return txt.strip()

    bruts = []  # articles non traduits, on filtre par pertinence

    # ── Source 1 : flux RSS généralistes crypto ──
    feeds = [
        ("CoinTelegraph", "https://cointelegraph.com/rss"),
        ("CoinDesk", "https://www.coindesk.com/arc/outboundfeeds/rss/"),
        ("Decrypt", "https://decrypt.co/feed"),
        ("Bitcoin Magazine", "https://bitcoinmagazine.com/feed"),
    ]
    for source, url in feeds:
        try:
            rep = requests.get(url, headers=headers, timeout=8)
            if rep.status_code != 200:
                continue
            root = ET.fromstring(rep.content)
            for item in root.iter('item'):
                titre = (item.findtext('title') or '').strip()
                desc = nettoyer_html(item.findtext('description') or '')
                lien = (item.findtext('link') or '').strip()
                pub = (item.findtext('pubDate') or '').strip()
                # Filtre de pertinence : ticker ou nom complet dans le titre/desc
                texte_low = (titre + ' ' + desc).lower()
                pertinent = (ticker.lower() in texte_low) or (nom_complet in texte_low)
                # Pour BTC/ETH on accepte aussi les news macro générales
                if pertinent:
                    bruts.append({"title": titre, "body": desc[:300], "url": lien,
                                  "source": source, "date": pub[:16]})
        except Exception:
            continue

    # ── Source 2 : CryptoCompare (si peu de résultats RSS) ──
    if len(bruts) < 3:
        try:
            url = f"https://min-api.cryptocompare.com/data/v2/news/?categories={ticker}&lang=EN&sortOrder=popular"
            rep = requests.get(url, headers=headers, timeout=8)
            if rep.status_code == 200:
                for art in rep.json().get('Data', [])[:6]:
                    bruts.append({
                        "title": art.get('title', ''),
                        "body": (art.get('body', '') or '')[:300],
                        "url": art.get('url', ''),
                        "source": art.get('source_info', {}).get('name', 'CryptoCompare'),
                        "date": datetime.fromtimestamp(art.get('published_on', 0)).strftime('%d/%m/%Y %H:%M') if art.get('published_on') else '',
                    })
        except Exception:
            pass

    # ── Traduction FR des 6 articles les plus récents ──
    articles = []
    for art in bruts[:6]:
        articles.append({
            "title": traduire_fr(art["title"]),
            "body": traduire_fr(art["body"]),
            "url": art["url"],
            "source": art["source"],
            "date": art["date"],
        })

    # ── Source 3 : liens directs si tout a échoué ──
    if not articles:
        tl = ticker.lower()
        articles = [
            {"title": f"Actualités {ticker} — CoinDesk", "body": "Dernières analyses et breaking news.", "url": f"https://www.coindesk.com/tag/{tl}/", "source": "CoinDesk", "date": "En direct"},
            {"title": f"Analyses {ticker} — CoinTelegraph", "body": "Couverture quotidienne et analyses de prix.", "url": f"https://cointelegraph.com/tags/{tl}", "source": "CoinTelegraph", "date": "En direct"},
            {"title": f"Flux X — #{ticker}", "body": "Discussions de la communauté en temps réel.", "url": f"https://x.com/search?q=%23{ticker}+crypto&f=live", "source": "X", "date": "Live"},
        ]

    return articles


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
# 5. MOTEUR ADAPTATIF — RÉGIME DE MARCHÉ + 3 SETUPS
# ══════════════════════════════════════════════════════════════════════════════

def detecter_regime(df):
    """Détecte le régime de marché : Haussier / Baissier / Range.
    Retourne (label, emoji, pente_ma200_pct, details_dict).
    """
    infos = df.iloc[-1]
    prix = infos['Close']
    ma50 = infos['MA_50']
    ma200 = infos['MA_200']
    adx = infos['ADX']

    # Pente de la MA200 sur 20 jours (en %)
    pente = 0.0
    if df['MA_200'].notna().sum() > 20:
        ma200_passe = df['MA_200'].iloc[-21]
        if not pd.isna(ma200_passe) and ma200_passe > 0:
            pente = ((ma200 - ma200_passe) / ma200_passe) * 100

    details = {
        "prix_vs_ma200": "au-dessus" if (not pd.isna(ma200) and prix > ma200) else "en-dessous",
        "ma50_vs_ma200": "MA50 > MA200" if (not pd.isna(ma200) and ma50 > ma200) else "MA50 < MA200",
        "pente_ma200": pente,
        "adx": adx,
    }

    if pd.isna(ma200):
        return "Indéterminé", "❔", pente, details

    haussier = prix > ma200 and ma50 > ma200 and pente > -1
    baissier = prix < ma200 and ma50 < ma200 and pente < 1

    if haussier:
        return "Tendance Haussière", "📈", pente, details
    elif baissier:
        return "Tendance Baissière", "📉", pente, details
    else:
        return "Range / Transition", "↔️", pente, details


def _proche(a, b, tolerance_pct):
    """True si a est à moins de tolerance_pct de b."""
    if b == 0:
        return False
    return abs(a - b) / b * 100 <= tolerance_pct


def score_pullback(df, niveaux_fib):
    """SETUP 1 — Achat de repli en tendance haussière. Le plus haute-probabilité.
    Retourne (score/10, liste de signaux actifs, zone_entree)."""
    infos = df.iloc[-1]
    prec = df.iloc[-2]
    prix = infos['Close']
    score = 0.0
    signaux = []

    # Gate : régime haussier (prix > MA200)
    if not pd.isna(infos['MA_200']) and prix > infos['MA_200']:
        score += 2.0
        signaux.append(("✅", "Tendance de fond haussière (prix > MA200)"))
    else:
        signaux.append(("⛔", "Pas de tendance haussière de fond — setup peu fiable"))
        return 0.0, signaux, None

    # Repli vers support dynamique (MA50 ou VWAP)
    near_ma50 = _proche(prix, infos['MA_50'], 4)
    near_vwap = _proche(prix, infos['VWAP_20'], 3)
    if near_ma50 or near_vwap:
        score += 2.5
        ref = "MA50" if near_ma50 else "VWAP"
        signaux.append(("✅", f"Repli sur support dynamique ({ref}) — zone d'achat"))
    elif prix > infos['MA_50']:
        score += 0.5
        signaux.append(("⚪", "Prix au-dessus du support, pas encore de repli net"))

    # RSI en zone de rebond (revient de survente sans euphorie)
    if 38 <= infos['RSI'] <= 55:
        score += 2.0
        signaux.append(("✅", f"RSI en zone de rebond ({infos['RSI']:.0f}) — pas suracheté"))
        if infos['RSI'] > prec['RSI']:
            score += 0.5
            signaux.append(("✅", "RSI qui remonte — momentum se rétablit"))
    elif infos['RSI'] < 38:
        score += 1.0
        signaux.append(("⚪", f"RSI bas ({infos['RSI']:.0f}) — repli profond, surveiller le rebond"))

    # MACD histogramme qui se retourne à la hausse
    if infos['MACD_Hist'] > prec['MACD_Hist']:
        score += 1.5
        signaux.append(("✅", "MACD se retourne à la hausse — pression vendeuse qui faiblit"))

    # Proximité d'un niveau Fibonacci de rebond
    for label in ["38.2%", "50%", "61.8%"]:
        if label in niveaux_fib and _proche(prix, niveaux_fib[label], 2.5):
            score += 1.5
            signaux.append(("✅", f"Rebond sur Fibonacci {label} — zone technique forte"))
            break

    zone = f"{min(infos['MA_50'], infos['VWAP_20']):,.2f} – {prix:,.2f} $"
    return min(10.0, score), signaux, zone


def score_breakout(df, liste_resistances):
    """SETUP 2 — Cassure / momentum. Pour suivre une vague en cours.
    Retourne (score/10, signaux, zone_entree)."""
    infos = df.iloc[-1]
    prix = infos['Close']
    score = 0.0
    signaux = []

    # Cassure d'une résistance récente
    resistance_cassee = None
    if liste_resistances:
        res_proche = min(liste_resistances, key=lambda r: abs(r - prix))
        if prix >= res_proche * 0.99:  # à 1% ou au-dessus
            score += 3.0
            resistance_cassee = res_proche
            signaux.append(("✅", f"Cassure de résistance ({res_proche:,.2f} $)"))
        elif prix >= res_proche * 0.97:
            score += 1.0
            signaux.append(("⚪", f"Approche de résistance ({res_proche:,.2f} $) — guetter la cassure"))

    # Volume de confirmation
    if infos['Volume'] > 1.3 * infos['Vol_MA_20']:
        score += 2.5
        signaux.append(("✅", "Volume de confirmation présent — cassure crédible"))
    else:
        signaux.append(("⚪", "Volume insuffisant — risque de faux signal (fakeout)"))

    # ADX en hausse + DI haussier
    if infos['ADX'] > 22 and infos['Plus_DI'] > infos['Minus_DI']:
        score += 2.5
        signaux.append(("✅", f"Tendance qui se renforce (ADX {infos['ADX']:.0f}, +DI dominant)"))
    elif infos['Plus_DI'] > infos['Minus_DI']:
        score += 1.0
        signaux.append(("⚪", "Direction haussière mais tendance encore faible"))

    # RSI momentum sain
    if 50 <= infos['RSI'] <= 72:
        score += 2.0
        signaux.append(("✅", f"RSI en momentum sain ({infos['RSI']:.0f})"))
    elif infos['RSI'] > 72:
        signaux.append(("⚠️", f"RSI suracheté ({infos['RSI']:.0f}) — cassure tardive, risque accru"))

    zone = f"{prix:,.2f} $ (sur confirmation de clôture)" if resistance_cassee else None
    return min(10.0, score), signaux, zone


def score_reversal(df, funding, fng_valeur, ls_ratio):
    """SETUP 3 — Retournement / capitulation. Contrarian, HAUT RISQUE.
    Retourne (score/10, signaux, zone_entree)."""
    infos = df.iloc[-1]
    prix = infos['Close']
    score = 0.0
    signaux = []

    # RSI en survente profonde
    if infos['RSI'] < 30:
        score += 2.5
        signaux.append(("✅", f"RSI en survente extrême ({infos['RSI']:.0f})"))
    elif infos['RSI'] < 38:
        score += 1.0
        signaux.append(("⚪", f"RSI bas ({infos['RSI']:.0f})"))

    # Prix sous la bande de Bollinger basse
    if prix <= infos['BB_Basse']:
        score += 2.0
        signaux.append(("✅", "Prix sous la bande de Bollinger basse — excès statistique"))

    # Volume climax (capitulation)
    if infos['Volume'] > 1.5 * infos['Vol_MA_20']:
        score += 2.0
        signaux.append(("✅", "Volume climax — possible capitulation vendeuse"))

    # Sentiment / dérivés extrêmes
    if fng_valeur < 25:
        score += 1.5
        signaux.append(("✅", f"Peur extrême (Fear & Greed {fng_valeur})"))
    if funding < 0:
        score += 1.0
        signaux.append(("✅", "Funding négatif — shorts dominants, pression de rachat"))
    if ls_ratio is not None and ls_ratio < 0.85:
        score += 0.5
        signaux.append(("✅", "Majorité de shorts — carburant de short squeeze"))

    # Divergence haussière simplifiée (prix plus bas, RSI plus haut sur 10j)
    if len(df) > 11:
        prix_bas_recent = df['Close'].iloc[-1] < df['Close'].iloc[-11]
        rsi_plus_haut = df['RSI'].iloc[-1] > df['RSI'].iloc[-11]
        if prix_bas_recent and rsi_plus_haut:
            score += 1.5
            signaux.append(("✅", "Divergence haussière RSI — affaiblissement de la baisse"))

    if not signaux:
        signaux.append(("⛔", "Aucun signe de capitulation — pas de setup contrarian"))

    zone = f"{infos['BB_Basse']:,.2f} – {prix:,.2f} $" if score >= 4 else None
    return min(10.0, score), signaux, zone


def recommander(regime, s_pull, s_break, s_rev):
    """Sélectionne le setup à privilégier selon le régime et renvoie la reco finale.
    Retourne (nom_setup, score, verdict, couleur, niveau_risque)."""
    # Validité des setups selon le régime
    candidats = []  # (nom, score, risque)

    if regime == "Tendance Haussière":
        candidats.append(("Pullback (repli en tendance)", s_pull, "Modéré"))
        candidats.append(("Breakout (momentum)", s_break, "Modéré"))
        candidats.append(("Reversal (contrarian)", s_rev * 0.6, "Élevé"))  # downweighté
    elif regime == "Tendance Baissière":
        # En tendance baissière, on n'achète PAS les replis. Seul le reversal vaut, mais risqué.
        candidats.append(("Reversal (contrarian)", s_rev, "Très élevé"))
        candidats.append(("Breakout (momentum)", s_break * 0.5, "Élevé"))
    else:  # Range / Transition
        candidats.append(("Reversal (bas de range)", s_rev, "Élevé"))
        candidats.append(("Breakout (haut de range)", s_break, "Modéré"))
        candidats.append(("Pullback (repli)", s_pull * 0.8, "Modéré"))

    candidats.sort(key=lambda x: x[1], reverse=True)
    nom, score, risque = candidats[0]

    # Verdict basé sur le meilleur score valide
    if score >= 6.5:
        verdict, couleur = "ENTRÉE ENVISAGEABLE", "success"
    elif score >= 4.5:
        verdict, couleur = "SURVEILLER DE PRÈS", "warning"
    else:
        verdict, couleur = "S'ABSTENIR POUR L'INSTANT", "error"

    return nom, score, verdict, couleur, risque


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

funding, open_interest_usd, deriv_volume = charger_derives_coingecko(fiche['index_id'])
ls_ratio = charger_long_short_ratio(symbole_api)
oi_var_24h = None  # variation OI 24h indisponible via agrégateur gratuit
fng_valeur, fng_statut, fng_historique = charger_fear_and_greed()
cg_data = charger_donnees_coingecko(fiche['coingecko_id'])
global_data = charger_dominance_btc()

# Analyse technique
df = appliquer_analyse_technique(df)
infos = df.iloc[-1]
prix = infos['Close']

# Open Interest déjà en USD via CoinGecko derivatives

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
# 8. MOTEUR DE DÉCISION — RÉGIME + SETUPS
# ══════════════════════════════════════════════════════════════════════════════

regime, regime_emoji, pente_ma200, regime_details = detecter_regime(df)
s_pull, sig_pull, zone_pull = score_pullback(df, niveaux_fib)
s_break, sig_break, zone_break = score_breakout(df, liste_resistances)
s_rev, sig_rev, zone_rev = score_reversal(df, funding, fng_valeur, ls_ratio)

# Bonus/malus fondamental manuel appliqué au setup retenu
ajust_fonda = 0.0
if "Favorable" in statut_roadmap:
    ajust_fonda += 0.5
elif "Défavorable" in statut_roadmap:
    ajust_fonda -= 1.0
if "Favorable" in statut_politique:
    ajust_fonda += 0.5
elif "Défavorable" in statut_politique:
    ajust_fonda -= 1.0

nom_setup, score_setup, verdict, couleur, niveau_risque = recommander(regime, s_pull, s_break, s_rev)
score_setup = max(0.0, min(10.0, score_setup + ajust_fonda))

# Associer les signaux et la zone au setup recommandé
if "Pullback" in nom_setup:
    signaux_reco, zone_reco = sig_pull, zone_pull
elif "Breakout" in nom_setup:
    signaux_reco, zone_reco = sig_break, zone_break
else:
    signaux_reco, zone_reco = sig_rev, zone_rev

# ══════════════════════════════════════════════════════════════════════════════
# 9. AFFICHAGE PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════

st.markdown(f"# 💰 {choix.split()[0]} : **{prix:,.2f} USD**")

# ── Bandeau RÉGIME ──
reg_col1, reg_col2, reg_col3 = st.columns(3)
reg_col1.metric("Régime de marché", f"{regime_emoji} {regime}",
                help="Le contexte qui détermine quelle stratégie est valide. Haussier = on achète les replis. Baissier = on évite d'acheter (sauf contrarian). Range = on joue les extrêmes.")
reg_col2.metric("Pente MA200 (20j)", f"{pente_ma200:+.1f}%",
                delta="Fond porteur" if pente_ma200 > 0 else "Fond fragile",
                delta_color="normal" if pente_ma200 > 0 else "inverse",
                help="Inclinaison de la tendance de fond. Positive = structure haussière saine. Négative = méfiance, le fond se dégrade.")
reg_col3.metric("Force tendance (ADX)", f"{infos['ADX']:.0f}",
                delta="Directionnel" if infos['ADX'] > 25 else "Sans direction",
                delta_color="normal" if infos['ADX'] > 25 else "off",
                help=">25 = vraie tendance, les suivis de momentum fonctionnent. <20 = range, on privilégie les rebonds entre bornes.")

# ── Métriques principales ──
c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Prix", f"{prix:,.2f} $",
          delta=f"{cg_data.get('price_change_24h_pct', 0):.1f}% (24h)" if cg_data else None,
          help="Prix actuel et variation sur 24h.")
c2.metric("RSI (14j)", f"{infos['RSI']:.1f}",
          help="Force relative 0–100. <30 = survendu. >70 = suracheté. 40–55 = zone de rebond saine en tendance.")
c3.metric("MACD Hist", f"{infos['MACD_Hist']:.2f}",
          delta="Haussier" if infos['MACD_Hist'] > 0 else "Baissier",
          delta_color="normal" if infos['MACD_Hist'] > 0 else "inverse",
          help="Momentum. Positif et croissant = accélération haussière. Retournement à la hausse = signal d'entrée.")
c4.metric("ATR (volatilité)", f"{infos['ATR']:.2f} ({infos['ATR_Pct']:.1f}%)",
          help="Volatilité moyenne. Plus c'est haut, plus ton stop doit être large.")
c5.metric("Funding Rate", f"{funding:.4f}%" if funding != 0 else "N/A",
          delta="Surchauffe" if funding > 0.05 else ("Shorts paient" if funding < -0.01 else "Sain"),
          delta_color="inverse" if funding > 0.05 else "normal",
          help="Coût du levier (8h). >0.05% = euphorie acheteuse (risque de purge). Négatif = shorts dominants (rebond possible).")
c6.metric("VWAP 20j", f"{infos['VWAP_20']:,.2f} $",
          help="Prix moyen pondéré par le volume. Sous le VWAP = on achète moins cher que la moyenne du marché. Support clé en tendance.")

# ── DÉCISION : setup recommandé ──
st.markdown("---")
st.subheader("🎯 Décision de trading")

col_verdict, col_signaux = st.columns([1, 1.4])

with col_verdict:
    libelle = f"{verdict} — {score_setup:.1f}/10"
    if couleur == "success":
        st.success(f"**{libelle}**")
    elif couleur == "warning":
        st.warning(f"**{libelle}**")
    else:
        st.error(f"**{libelle}**")

    st.markdown(f"**Setup retenu :** {nom_setup}")
    risque_emoji = {"Modéré": "🟢", "Élevé": "🟠", "Très élevé": "🔴"}.get(niveau_risque, "⚪")
    st.markdown(f"**Niveau de risque :** {risque_emoji} {niveau_risque}")
    if zone_reco:
        st.markdown(f"**Zone d'entrée :** {zone_reco}")
    st.caption(f"Scores bruts — Pullback {s_pull:.1f} · Breakout {s_break:.1f} · Reversal {s_rev:.1f}")

with col_signaux:
    st.markdown("**Lecture du setup :**")
    for emoji, txt in signaux_reco:
        st.markdown(f"{emoji} {txt}")

with st.expander("🔍 Comparer les 3 setups en détail"):
    tab_p, tab_b, tab_r = st.tabs([f"Pullback ({s_pull:.1f})", f"Breakout ({s_break:.1f})", f"Reversal ({s_rev:.1f})"])
    with tab_p:
        st.caption("Achat de repli en tendance haussière — le plus haute-probabilité.")
        for emoji, txt in sig_pull:
            st.markdown(f"{emoji} {txt}")
    with tab_b:
        st.caption("Cassure de résistance avec confirmation de volume — pour suivre une vague.")
        for emoji, txt in sig_break:
            st.markdown(f"{emoji} {txt}")
    with tab_r:
        st.caption("Retournement contrarian en capitulation — haut risque, à réserver aux extrêmes.")
        for emoji, txt in sig_rev:
            st.markdown(f"{emoji} {txt}")

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
d1.metric("Open Interest", f"{open_interest_usd/1e9:.2f}B $" if open_interest_usd > 0 else "N/A",
          help="Montant total engagé sur les contrats à terme (agrégé tous exchanges via CoinGecko). En hausse = nouveaux capitaux entrent. Chute brutale = liquidations/débouclage de positions.")
d2.metric("Funding Rate", f"{funding:.4f}%" if funding != 0 else "N/A",
          delta="Surchauffe leviers" if funding > 0.05 else ("Shorts paient" if funding < -0.01 else "Neutre"),
          delta_color="inverse" if funding > 0.05 else "normal",
          help="Coût du levier toutes les 8h. >0.05% = excès d'acheteurs (malus de −1 sur le score). <−0.01% = shorts en souffrance → carburant pour un rebond.")
d3.metric("Volume Dérivés 24h", f"{deriv_volume/1e9:.1f}B $" if deriv_volume > 0 else "N/A",
          help="Volume échangé sur les contrats à terme sur 24h. Un volume élevé confirme l'intérêt des traders à effet de levier et la liquidité du marché.")
if ls_ratio is not None:
    d4.metric("Ratio Long/Short", f"{ls_ratio:.2f}",
              delta="Majorité Long" if ls_ratio > 1.2 else ("Majorité Short" if ls_ratio < 0.85 else "Équilibré"),
              help="Comptes longs ÷ comptes courts. <0.85 = beaucoup de shorts → un short squeeze peut propulser le prix. >1.2 = excès d'optimisme, risque de correction.")
else:
    d4.metric("Ratio Long/Short", "N/A",
              help="Donnée temporairement indisponible (source restreinte depuis le serveur). Ce champ n'impacte pas le score quand il est absent.")

with st.expander("📖 Lecture des dérivés"):
    st.markdown("""
**Open Interest** : capital total engagé sur les contrats perpétuels. En forte hausse avec un prix qui monte = tendance saine. Chute brutale = liquidations.

**Funding Rate** : coût payé toutes les 8h entre longs et shorts. >0.05% = surchauffe acheteuse (malus appliqué au score). <−0.01% = shorts en souffrance (potentiel squeeze haussier).

**Volume Dérivés** : confirme la conviction. Un mouvement de prix sur fort volume dérivés est plus fiable.

**Ratio Long/Short** : <0.85 = majorité de shorts → carburant pour un short squeeze. >1.2 = excès d'optimisme.

*Note : les données dérivés sont agrégées via CoinGecko (tous exchanges confondus) pour rester accessibles depuis n'importe quel serveur.*
    """)

# ══════════════════════════════════════════════════════════════════════════════
# 12. CONTEXTE MACRO & MARCHÉ GLOBAL
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("---")
st.header("🌐 Contexte Macro & Marché Global")

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Fear & Greed", f"{fng_valeur}/100", delta=fng_statut,
          delta_color="inverse" if fng_valeur < 30 else ("normal" if fng_valeur > 70 else "off"),
          help="Indice de sentiment 0–100. <25 = peur extrême (historiquement de bons points d'achat). >75 = avidité extrême (prudence, sommet possible). Contrarian : on achète dans la peur.")

if global_data and global_data.get('btc_dominance', 0) > 0:
    m2.metric("Dominance BTC", f"{global_data.get('btc_dominance', 0):.1f}%",
              help="Part du BTC dans la capitalisation crypto totale. En hausse = capitaux qui fuient les altcoins vers le BTC (défavorable aux alts). En baisse = potentielle 'alt-season'.")
    m3.metric("Cap. Marché Totale", f"${global_data.get('total_market_cap', 0)/1e12:.2f}T",
              delta=f"{global_data.get('market_cap_change_24h_pct', 0):.1f}% (24h)",
              help="Capitalisation de tout le marché crypto. Sa tendance globale donne le climat : marché haussier (risk-on) ou baissier (risk-off).")
    m4.metric("Volume Global 24h", f"${global_data.get('total_volume_24h', 0)/1e9:.0f}B",
              help="Volume total échangé sur 24h, tous actifs confondus. Un volume en hausse confirme la conviction derrière un mouvement de marché.")
    m5.metric("Dominance ETH", f"{global_data.get('eth_dominance', 0):.1f}%",
              help="Part de l'Ethereum dans la capitalisation totale. Une hausse signale souvent un appétit pour la DeFi et les altcoins de qualité.")
else:
    m2.metric("Dominance BTC", "N/A")
    m3.metric("Cap. Marché Totale", "N/A")
    m4.metric("Volume Global 24h", "N/A")
    m5.metric("Dominance ETH", "N/A")

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

def fmt_milliards(v):
    return f"${v/1e9:.1f}B" if v and v > 0 else "N/A"

# Données CoinGecko
if cg_data and cg_data.get('market_cap', 0) > 0:
    fg1, fg2, fg3, fg4 = st.columns(4)
    fg1.metric("Market Cap", fmt_milliards(cg_data.get('market_cap', 0)),
               help="Capitalisation totale = prix × offre en circulation. Mesure la taille de l'actif. >100B = large cap (BTC, ETH), <1B = small cap plus volatil.")
    fg2.metric("Volume 24h", fmt_milliards(cg_data.get('total_volume_24h', 0)),
               help="Montant échangé sur 24h. Un volume élevé = forte liquidité et intérêt. Un ratio Volume/MarketCap élevé peut signaler un mouvement imminent.")

    max_s = cg_data.get('max_supply')
    circ_s = cg_data.get('circulating_supply', 0)
    if max_s and max_s > 0:
        fg3.metric("Offre en circulation", f"{circ_s/max_s*100:.1f}% du max",
                   help="Part de l'offre maximale déjà émise. Proche de 100% = peu d'inflation future (ex: BTC). Faible = risque de dilution par émission de nouveaux jetons.")
    else:
        fg3.metric("Offre en circulation", f"{circ_s:,.0f}" if circ_s else "N/A",
                   help="Nombre de jetons actuellement en circulation. Sans offre maximale, l'actif peut être inflationniste.")

    fg4.metric("Distance à l'ATH", f"{cg_data.get('ath_change_pct', 0):.1f}%",
               delta=f"ATH: {cg_data.get('ath', 0):,.2f}$",
               help="Écart par rapport au plus haut historique (All-Time High). −80% = l'actif a perdu 80% depuis son sommet. Indique le potentiel de récupération vs le risque.")

    st.subheader("📈 Performance")
    perf1, perf2, perf3, perf4 = st.columns(4)
    perf1.metric("24h", f"{cg_data.get('price_change_24h_pct', 0):+.1f}%")
    perf2.metric("7 jours", f"{cg_data.get('price_change_7d_pct', 0):+.1f}%")
    perf3.metric("30 jours", f"{cg_data.get('price_change_30d_pct', 0):+.1f}%")
    perf4.metric("1 an", f"{cg_data.get('price_change_1y_pct', 0):+.1f}%")
else:
    st.warning("⏳ Données fondamentales temporairement indisponibles (limite de requêtes CoinGecko). Rafraîchis la page dans 1 minute.")

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

articles = charger_actualites(fiche['ticker_news'], fiche['coingecko_id'])

for art in articles:
    with st.container():
        col_txt, col_btn = st.columns([4, 1])
        with col_txt:
            src_tag = f"  ·  {art.get('source', '')}" if art.get('source') else ""
            date_tag = f"  ·  {art.get('date', '')}" if art.get('date') else ""
            st.markdown(f"**{art.get('title', 'Article')[:120]}**")
            body = art.get('body', '')[:250]
            st.caption(f"{body}...{src_tag}{date_tag}" if len(art.get('body', '')) > 250 else f"{body}{src_tag}{date_tag}")
        with col_btn:
            if art.get('url'):
                st.link_button("Lire ↗", art['url'])
    st.markdown("<hr style='margin:4px 0; border-color: rgba(255,255,255,0.05)'>", unsafe_allow_html=True)

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
