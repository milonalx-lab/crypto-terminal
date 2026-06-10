"""
Terminal Crypto Pro v2.1 — Confluence Multi-Dimensionnelle
-----------------------------------------------------------
NOUVEAUTÉS v2.1 (audit du 10/06/2026) :
  1. 💼 SECTION PORTEFEUILLE : lit portfolio.csv (à la racine du repo), croise
     avec les prix live et affiche P&L réel, marges avant Dead Line / Stop,
     potentiel vers Take Profit, alertes, et progression vers l'objectif 15K$.
     -> POURQUOI : le terminal analysait un actif générique ; ta vraie question
        quotidienne est "MES positions sont-elles menacées / à renforcer ?".
  2. 📅 RÉGIME WEEKLY : EMA21 hebdo (bull market support band, standard, pas
     exotique). Règle : renforcer uniquement si Daily ET Weekly sont alignés.
     Un setup long en weekly baissier prend -1.5 au score (affiché et expliqué).
     -> POURQUOI : un régime haussier daily DANS un baissier weekly est le
        piège classique du swing à horizon plusieurs mois.
  3. 🎯 ATH RÉEL : le garde-fou macro utilise désormais l'ATH CoinGecko (vrai
     plus haut historique) et non plus le max sur 1 an de données.
     -> POURQUOI : "proche de l'ATH" déclenchait/ratait le veto à tort.
  4. ➕ CRO et The Graph (GRT) ajoutés (16 actifs) : tout ton portefeuille
     suivi est désormais couvert par le terminal.
  5. 🧹 NETTOYAGES : historique prix 730j (MA200 daily complète + weekly
     possible), graphiques limités aux 365 derniers jours pour la lisibilité,
     paramètre mort retiré de score_breakout, footer corrigé.

Fichiers requis à la racine du repo :
  app.py, data_fetch.py, terminal_fixes.py, portfolio.csv
"""

import requests
import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

# --- Modules de correction (fichiers à la racine du repo) ---
from data_fetch import fetch_hyperliquid_derivs, fetch_btc_macro
from terminal_fixes import last_broken_resistance, validate_breakout, apply_macro_guardrail

# ══════════════════════════════════════════════════════════════════════════════
# 1. INITIALISATION
# ══════════════════════════════════════════════════════════════════════════════
st.set_page_config(page_title="Terminal Crypto Pro v2.1", layout="wide")
st.title("🛡️ Terminal Crypto Professionnel v2.1 — Confluence Multi-Dimensionnelle")

# Objectif de portefeuille (modifie ici si l'objectif évolue)
OBJECTIF_PORTEFEUILLE = 15000

# ══════════════════════════════════════════════════════════════════════════════
# 2. RÉPERTOIRE FONDAMENTAL ÉTENDU (16 actifs)
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
    },
    "Hyperliquid (HYPE)": {
        "coingecko_id": "hyperliquid",
        "contract_mult": 1,
        "index_id": "HYPE",
        "tokenomics": "Offre max 1Md. Rachats et burn agressifs financés par les revenus du DEX (circulation passée sous 300M). Pas de capital-risque early extractif.",
        "roadmap": "L1 perpétuels on-chain (200k ordres/s) + HyperEVM. Expansion vers spot, lending, RWA. Recherche de clarté réglementaire US sur les perp.",
        "sensibilite": "Token de DEX à fort bêta. Très lié aux revenus de la plateforme et aux volumes de trading de dérivés. Sensible au narratif 'perp DEX'. ⚠️ Déblocage mensuel (cliff) à surveiller chaque ~6 du mois.",
        "ticker_news": "HYPE",
        "lien_x": "https://x.com/HyperliquidX",
        "fallback_news": [
            {"title": "Hyperliquid Docs", "body": "Architecture HyperBFT et L1 perpétuels.", "url": "https://hyperliquid.gitbook.io/hyperliquid-docs"},
            {"title": "Hyperliquid sur CoinGecko", "body": "Données de marché et écosystème.", "url": "https://www.coingecko.com/en/coins/hyperliquid"}
        ]
    },
    "Jupiter (JUP)": {
        "coingecko_id": "jupiter-exchange-solana",
        "contract_mult": 1,
        "index_id": "JUP",
        "tokenomics": "Token de gouvernance du 1er agrégateur DEX de Solana. Politique de rachat : 50% des frais protocole rachètent et bloquent du JUP pendant 3 ans.",
        "roadmap": "Expansion produit : Jupiter Lend, Ultra V3, vérification de tokens. >50% du volume DEX Solana. Devenu 2e validateur du réseau.",
        "sensibilite": "Proxy de l'activité DeFi sur Solana. Corrélé à SOL et aux volumes de swap/perp. Bêta élevé.",
        "ticker_news": "JUP",
        "lien_x": "https://x.com/JupiterExchange",
        "fallback_news": [
            {"title": "Jupiter Station", "body": "Documentation et produits Jupiter.", "url": "https://station.jup.ag/"},
            {"title": "Jupiter sur CoinGecko", "body": "Données de marché JUP.", "url": "https://www.coingecko.com/en/coins/jupiter"}
        ]
    },
    "Aave (AAVE)": {
        "coingecko_id": "aave",
        "contract_mult": 1,
        "index_id": "AAVE",
        "tokenomics": "Offre max 16M. Token de gouvernance + 'safety module' (staking qui assure le protocole). Rachats activés via les revenus du protocole.",
        "roadmap": "Aave V4 (architecture unifiée de liquidité). GHO (stablecoin natif). Expansion multi-chain. Leader du lending DeFi par TVL.",
        "sensibilite": "Blue chip DeFi. Corrélé à l'ETH et à la TVL DeFi globale. Bêta modéré pour un altcoin.",
        "ticker_news": "AAVE",
        "lien_x": "https://x.com/aave",
        "fallback_news": [
            {"title": "Aave Docs", "body": "Protocole de prêt décentralisé.", "url": "https://docs.aave.com/"},
            {"title": "Aave sur CoinGecko", "body": "Données de marché AAVE.", "url": "https://www.coingecko.com/en/coins/aave"}
        ]
    },
    "Polygon (POL)": {
        "coingecko_id": "polygon-ecosystem-token",
        "contract_mult": 1,
        "index_id": "POL",
        "tokenomics": "Token de nouvelle génération (ex-MATIC). Offre 10Md, légèrement inflationniste. Re-staking natif : sécuriser plusieurs chaînes ZK avec un seul token.",
        "roadmap": "AggLayer (couche d'agrégation cross-chain ZK). Migration MATIC→POL finalisée. Focus sur les paiements et les RWA.",
        "sensibilite": "Infrastructure L2 Ethereum. Corrélé à l'adoption des rollups et à l'ETH. Concurrence forte (Arbitrum, Base).",
        "ticker_news": "POL",
        "lien_x": "https://x.com/0xPolygon",
        "fallback_news": [
            {"title": "Polygon Docs", "body": "AggLayer et chaînes ZK.", "url": "https://docs.polygon.technology/"},
            {"title": "Polygon sur CoinGecko", "body": "Données de marché POL.", "url": "https://www.coingecko.com/en/coins/polygon-ecosystem-token"}
        ]
    },
    "Lido DAO (LDO)": {
        "coingecko_id": "lido-dao",
        "contract_mult": 1,
        "index_id": "LDO",
        "tokenomics": "Token de gouvernance du plus gros protocole de liquid staking ETH. Offre 1Md. La valeur dépend des frais prélevés sur les récompenses de staking.",
        "roadmap": "Maintien de la position dominante sur le staking ETH (stETH). Diversification des validateurs. Enjeux de décentralisation.",
        "sensibilite": "Proxy du staking Ethereum. Très corrélé à l'ETH et aux flux de staking. Sensible aux débats réglementaires sur le staking.",
        "ticker_news": "LDO",
        "lien_x": "https://x.com/LidoFinance",
        "fallback_news": [
            {"title": "Lido Docs", "body": "Liquid staking Ethereum.", "url": "https://docs.lido.fi/"},
            {"title": "Lido sur CoinGecko", "body": "Données de marché LDO.", "url": "https://www.coingecko.com/en/coins/lido-dao"}
        ]
    },
    "Fetch.ai (FET)": {
        "coingecko_id": "fetch-ai",
        "contract_mult": 1,
        "index_id": "FET",
        "tokenomics": "Token de l'Artificial Superintelligence Alliance (fusion Fetch.ai, SingularityNET, Ocean). Utilisé pour les agents IA autonomes et l'accès aux services du réseau.",
        "roadmap": "Construction d'une plateforme d'agents IA décentralisés. Fusion ASI en cours d'intégration des écosystèmes.",
        "sensibilite": "Token thématique 'IA + crypto'. Très spéculatif, fort bêta. Réagit aux narratifs IA (annonces OpenAI, Nvidia, etc.).",
        "ticker_news": "FET",
        "lien_x": "https://x.com/Fetch_ai",
        "fallback_news": [
            {"title": "Fetch.ai Docs", "body": "Agents IA autonomes décentralisés.", "url": "https://fetch.ai/docs"},
            {"title": "Fetch.ai sur CoinGecko", "body": "Données de marché FET.", "url": "https://www.coingecko.com/en/coins/fetch-ai"}
        ]
    },
    "Arbitrum (ARB)": {
        "coingecko_id": "arbitrum",
        "contract_mult": 1,
        "index_id": "ARB",
        "tokenomics": "Token de gouvernance du principal rollup optimiste d'Ethereum. Offre 10Md avec déblocages programmés (attention à la dilution).",
        "roadmap": "Stylus (smart contracts multi-langages). Orbit (chaînes L3 personnalisées). Maintien du leadership TVL sur les L2.",
        "sensibilite": "Infrastructure L2 Ethereum. Corrélé à l'ETH et à l'activité DeFi. Sensible aux déblocages de tokens (vesting).",
        "ticker_news": "ARB",
        "lien_x": "https://x.com/arbitrum",
        "fallback_news": [
            {"title": "Arbitrum Docs", "body": "Rollup optimiste Ethereum.", "url": "https://docs.arbitrum.io/"},
            {"title": "Arbitrum sur CoinGecko", "body": "Données de marché ARB.", "url": "https://www.coingecko.com/en/coins/arbitrum"}
        ]
    },
    "NEAR Protocol (NEAR)": {
        "coingecko_id": "near",
        "contract_mult": 1,
        "index_id": "NEAR",
        "tokenomics": "L1 avec sharding (Nightshade). Inflation ~5%, 70% des frais brûlés. Staking yield significatif.",
        "roadmap": "Positionnement comme couche d'abstraction de chaînes + infrastructure pour l'IA décentralisée. Chain Signatures (contrôle cross-chain).",
        "sensibilite": "L1 alternatif à fort bêta. Réagit aux narratifs IA et abstraction de compte. Corrélé au sentiment altcoin global.",
        "ticker_news": "NEAR",
        "lien_x": "https://x.com/NEARProtocol",
        "fallback_news": [
            {"title": "NEAR Docs", "body": "L1 à sharding et abstraction de chaînes.", "url": "https://docs.near.org/"},
            {"title": "NEAR sur CoinGecko", "body": "Données de marché NEAR.", "url": "https://www.coingecko.com/en/coins/near"}
        ]
    },
    "Sui (SUI)": {
        "coingecko_id": "sui",
        "contract_mult": 1,
        "index_id": "SUI",
        "tokenomics": "L1 utilisant le langage Move (ex-équipe Meta/Diem). Offre max 10Md avec déblocages. Staking et frais de gas en SUI.",
        "roadmap": "Exécution parallèle pour haut débit. Focus gaming, DeFi et objets on-chain. Écosystème en croissance rapide.",
        "sensibilite": "L1 récent à très fort bêta. Très spéculatif, sensible aux déblocages de tokens et au narratif 'Solana killer'.",
        "ticker_news": "SUI",
        "lien_x": "https://x.com/SuiNetwork",
        "fallback_news": [
            {"title": "Sui Docs", "body": "L1 à langage Move et exécution parallèle.", "url": "https://docs.sui.io/"},
            {"title": "Sui sur CoinGecko", "body": "Données de marché SUI.", "url": "https://www.coingecko.com/en/coins/sui"}
        ]
    },
    # ── NOUVEAU v2.1 : couverture complète du portefeuille ──
    "Cronos (CRO)": {
        "coingecko_id": "crypto-com-chain",
        "contract_mult": 1,
        "index_id": "CRO",
        "tokenomics": "Token de l'exchange Crypto.com et de la chaîne Cronos. ⚠️ Gouvernance centralisée : les 70Md de CRO brûlés en 2021 ont été ré-émis en 2025 (dilution massive, controverse). Risque spécifique élevé.",
        "roadmap": "Cronos zkEVM (L2 Ethereum), intégrations paiements/carte Crypto.com, écosystème DeFi Cronos. La valeur dépend de la santé commerciale de l'exchange.",
        "sensibilite": "Token d'exchange : corrélé aux volumes et au marketing de Crypto.com plus qu'aux fondamentaux on-chain. Bêta moyen-élevé. À traiter en moonbag : pas de DCA, pas de renforcement.",
        "ticker_news": "CRO",
        "lien_x": "https://x.com/cronos_chain",
        "fallback_news": [
            {"title": "Cronos Docs", "body": "Chaîne EVM de l'écosystème Crypto.com.", "url": "https://docs.cronos.org/"},
            {"title": "CRO sur CoinGecko", "body": "Données de marché CRO.", "url": "https://www.coingecko.com/en/coins/cronos"}
        ]
    },
    "The Graph (GRT)": {
        "coingecko_id": "the-graph",
        "contract_mult": 1,
        "index_id": "GRT",
        "tokenomics": "Protocole d'indexation de données blockchain ('le Google du Web3'). Offre ~10.8Md, inflation ~3%/an pour rémunérer les indexeurs, burn partiel des frais de requêtes.",
        "roadmap": "Indexation multi-chain, Substreams (flux de données temps réel), positionnement 'données pour agents IA'. Adoption mesurable via le volume de requêtes payantes.",
        "sensibilite": "Infrastructure data à fort bêta, longue sous-performance vs le marché. Réagit au narratif IA + données. Position 'espoir' : ne renforcer que sur signaux techniques clairs, jamais par moyenne à la baisse émotionnelle.",
        "ticker_news": "GRT",
        "lien_x": "https://x.com/graphprotocol",
        "fallback_news": [
            {"title": "The Graph Docs", "body": "Protocole d'indexation décentralisé.", "url": "https://thegraph.com/docs/"},
            {"title": "GRT sur CoinGecko", "body": "Données de marché GRT.", "url": "https://www.coingecko.com/en/coins/the-graph"}
        ]
    },
}

options_cryptos = {
    "Bitcoin (BTC)": "BTCUSDT",
    "Ethereum (ETH)": "ETHUSDT",
    "Solana (SOL)": "SOLUSDT",
    "Chainlink (LINK)": "LINKUSDT",
    "Avalanche (AVAX)": "AVAXUSDT",
    "Hyperliquid (HYPE)": "HYPEUSDT",
    "Jupiter (JUP)": "JUPUSDT",
    "Aave (AAVE)": "AAVEUSDT",
    "Polygon (POL)": "POLUSDT",
    "Lido DAO (LDO)": "LDOUSDT",
    "Fetch.ai (FET)": "FETUSDT",
    "Arbitrum (ARB)": "ARBUSDT",
    "NEAR Protocol (NEAR)": "NEARUSDT",
    "Sui (SUI)": "SUIUSDT",
    "Cronos (CRO)": "CROUSDT",
    "The Graph (GRT)": "GRTUSDT",
}

# ══════════════════════════════════════════════════════════════════════════════
# 3. FONCTIONS DE CHARGEMENT SÉCURISÉES
# ══════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=300)
def charger_donnees_prix(coingecko_id, ticker_cc=None):
    """Charge 730 vraies bougies JOURNALIÈRES via CryptoCompare (priorité),
    fallback CoinGecko si CryptoCompare échoue.
    POURQUOI 730 et plus 365 : il faut ~2 ans de daily pour construire un
    régime WEEKLY fiable (EMA21W) et une MA200 daily complète dès le début.
    ticker_cc : ticker CryptoCompare (ex: 'BTC', 'ETH'). Si None, on tente seulement CoinGecko.
    v2.1.1 : retourne (df, source) pour pouvoir AVERTIR quand on tourne en mode
    dégradé (fallback CoinGecko 4j -> MA200/régime daily incalculables).
    + retry avec pause : les IP Streamlit Cloud sont partagées et CryptoCompare
    les rate-limite par vagues — un 2e essai passe souvent.
    """
    # ── Source 1 : CryptoCompare histoday (730 vraies bougies J, 2 essais) ──
    if ticker_cc:
        for tentative in range(2):
            try:
                url = (f"https://min-api.cryptocompare.com/data/v2/histoday"
                       f"?fsym={ticker_cc}&tsym=USD&limit=730")
                rep = requests.get(url, timeout=12).json()
                if isinstance(rep, dict) and rep.get('Response') == 'Error':
                    raise RuntimeError(rep.get('Message', 'CryptoCompare error'))
                data = rep.get('Data', {}).get('Data', [])
                if data and len(data) >= 200:
                    df = pd.DataFrame(data)
                    df['Date'] = pd.to_datetime(df['time'], unit='s')
                    df = df.rename(columns={
                        'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close',
                        'volumefrom': 'Volume', 'volumeto': 'Quote_volume'
                    })
                    df['Trades'] = 0
                    df = df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume', 'Quote_volume', 'Trades']].copy()
                    for col in ['Open', 'High', 'Low', 'Close', 'Volume', 'Quote_volume']:
                        df[col] = pd.to_numeric(df[col])
                    # CryptoCompare renvoie des bougies à 0 avant la naissance de l'actif
                    # (ex: HYPE n'existe que depuis fin 2024) -> on les retire.
                    df = df[df['Close'] > 0].copy()
                    if len(df) >= 200:
                        return df.reset_index(drop=True), "cryptocompare"
                break  # réponse valide mais trop courte -> inutile de réessayer
            except Exception:
                import time
                time.sleep(1.5)

    # ── Source 2 : CoinGecko OHLC (fallback, granularité 4j sur 365 jours) ──
    try:
        jours = 365
        url = f"https://api.coingecko.com/api/v3/coins/{coingecko_id}/ohlc?vs_currency=usd&days={jours}"
        rep = requests.get(url, timeout=12)
        rep.raise_for_status()
        data = rep.json()
        df = pd.DataFrame(data, columns=['Timestamp', 'Open', 'High', 'Low', 'Close'])
        df['Date'] = pd.to_datetime(df['Timestamp'], unit='ms')
        for col in ['Open', 'High', 'Low', 'Close']:
            df[col] = pd.to_numeric(df[col])
        url_vol = f"https://api.coingecko.com/api/v3/coins/{coingecko_id}/market_chart?vs_currency=usd&days={jours}&interval=daily"
        rep_vol = requests.get(url_vol, timeout=12).json()
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
        return df, "coingecko"
    except Exception as e:
        st.error(f"Erreur de chargement des prix ({coingecko_id}) : {e}")
        return pd.DataFrame(), "aucune"


# ── NOUVEAU v2.1 : prix multi-actifs pour le portefeuille ──
# Mapping symbole -> id CoinGecko (source de SECOURS si CryptoCompare rate-limite
# l'IP partagée de Streamlit Cloud — la cause des 'N/A' constatés le 10/06).
PORTFOLIO_CG_IDS = {
    "BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana", "HYPE": "hyperliquid",
    "JUP": "jupiter-exchange-solana", "CRO": "crypto-com-chain", "GRT": "the-graph",
    "NEAR": "near", "ARB": "arbitrum", "MEME": "memecoin-2", "PENGU": "pudgy-penguins",
    "GRASS": "grass", "USDC": "usd-coin", "USDT": "tether", "LINK": "chainlink",
    "AVAX": "avalanche-2", "AAVE": "aave", "POL": "polygon-ecosystem-token",
    "LDO": "lido-dao", "FET": "fetch-ai", "SUI": "sui",
}


@st.cache_data(ttl=120)
def charger_prix_portfolio(symbols_tuple):
    """Prix spot USD de toutes les positions. Double source :
      1. CryptoCompare pricemulti (1 appel) — AVEC détection du JSON d'erreur :
         un 'Response: Error' (rate-limit ou symbole inconnu) renvoyait avant
         un dict vide silencieux -> tout le tableau affichait N/A.
      2. CoinGecko simple/price (1 appel) pour TOUS les symboles encore manquants.
    Renvoie {symbole: prix ou None}. Un symbole sans prix sur les 2 sources
    reste None et est listé comme exclu sous le tableau (jamais de prix inventé)."""
    out = {s: None for s in symbols_tuple}

    # ── Source 1 : CryptoCompare ──
    try:
        fsyms = ",".join(symbols_tuple)
        url = f"https://min-api.cryptocompare.com/data/pricemulti?fsyms={fsyms}&tsyms=USD"
        rep = requests.get(url, timeout=10).json()
        if isinstance(rep, dict) and rep.get('Response') != 'Error':
            for s in symbols_tuple:
                v = rep.get(s)
                if isinstance(v, dict) and v.get('USD'):
                    out[s] = float(v['USD'])
    except Exception:
        pass

    # ── Source 2 : CoinGecko pour les manquants ──
    manquants = [s for s in symbols_tuple if out[s] is None and s in PORTFOLIO_CG_IDS]
    if manquants:
        try:
            ids = ",".join(PORTFOLIO_CG_IDS[s] for s in manquants)
            rep = requests.get("https://api.coingecko.com/api/v3/simple/price",
                               params={"ids": ids, "vs_currencies": "usd"}, timeout=10).json()
            for s in manquants:
                v = (rep.get(PORTFOLIO_CG_IDS[s], {}) or {}).get('usd')
                if v:
                    out[s] = float(v)
        except Exception:
            pass

    return out


def charger_portfolio_csv():
    """Lit portfolio.csv à la racine du repo. Colonnes attendues :
    crypto, quantite, avg_buy, dead_line, stop_loss, take_profit, statut, note.
    Les niveaux vides (dead_line/stop/tp) sont autorisés (positions dust/cash)."""
    try:
        pf = pd.read_csv('portfolio.csv')
        pf.columns = [c.strip().lower() for c in pf.columns]
        pf['crypto'] = pf['crypto'].astype(str).str.strip().str.upper()
        for col in ['quantite', 'avg_buy', 'dead_line', 'stop_loss', 'take_profit']:
            if col in pf.columns:
                pf[col] = pd.to_numeric(pf[col], errors='coerce')
        return pf
    except Exception:
        return None


@st.cache_data(ttl=300)
def charger_derives_coingecko(index_id):
    """Funding Rate + Open Interest via l'agrégateur CoinGecko (accessible depuis tout serveur)."""
    funding, oi_usd, vol_24h = 0.0, 0.0, 0.0
    try:
        url = "https://api.coingecko.com/api/v3/derivatives"
        rep = requests.get(url, timeout=12).json()
        candidats = []
        for t in rep:
            if t.get('index_id') == index_id and t.get('contract_type') == 'perpetual':
                oi = t.get('open_interest') or 0
                fr = t.get('funding_rate')
                v = t.get('volume_24h') or 0
                if oi and fr is not None:
                    candidats.append((float(oi), float(fr), float(v)))
        if candidats:
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
    """Données fondamentales via /coins/markets (endpoint léger) avec retry.
    NB v2.1 : le champ 'ath' alimente désormais le garde-fou macro (ATH RÉEL)."""
    url = ("https://api.coingecko.com/api/v3/coins/markets"
           f"?vs_currency=usd&ids={coin_id}"
           "&price_change_percentage=24h,7d,30d,1y")
    for tentative in range(3):
        try:
            rep = requests.get(url, timeout=12)
            if rep.status_code == 429:
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
                   "LINK": "chainlink", "AVAX": "avalanche", "CRO": "cronos",
                   "GRT": "the graph"}.get(ticker, ticker.lower())
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

    def nettoyer_html(txt):
        txt = _re.sub(r'<[^>]+>', '', txt or '')
        txt = _re.sub(r'\s+', ' ', txt)
        return txt.strip()

    bruts = []

    feeds = [
        ("CoinTelegraph", "https://cointelegraph.com/rss"),
        ("CoinDesk", "https://www.coindesk.com/arc/outboundfeeds/rss/"),
        ("Decrypt", "https://decrypt.co/feed"),
        ("Bitcoin Magazine", "https://bitcoinmagazine.com/feed"),
    ]

    ecosystem_kw = {
        "BTC": ["bitcoin", "btc", "satoshi", "halving", "lightning network", "ordinals", "blackrock spot etf",
                "michael saylor", "microstrategy", "miner", "hash rate"],
        "ETH": ["ethereum", "eth", "vitalik", "buterin", "ether", "ethereum 2", "merge", "shanghai",
                "dencun", "pectra", "evm", "smart contract", "ethereum etf", "lido", "staking eth"],
        "SOL": ["solana", "sol", "anatoly", "yakovenko", "firedancer", "jito", "phantom wallet",
                "marinade", "solana mobile", "saga phone", "memecoin solana"],
        "LINK": ["chainlink", "link", "ccip", "oracle", "sergey nazarov", "data feed", "cross-chain link"],
        "AVAX": ["avalanche", "avax", "subnet", "ava labs", "emin gun sirer", "avalanche9000", "core wallet"],
        "HYPE": ["hyperliquid", "hype", "hyperbft", "hyperevm", "hypercore", "perp dex", "hyperliquid dex"],
        "JUP": ["jupiter", "jup", "jupiter exchange", "jupiter dex", "dex aggregator solana", "jupiter lend", "jupiter perps"],
        "AAVE": ["aave", "ghо", "gho stablecoin", "aave v4", "lending defi", "safety module", "stani kulechov"],
        "POL": ["polygon", "pol", "matic", "agglayer", "polygon zk", "polygon pos", "polygon labs"],
        "LDO": ["lido", "ldo", "steth", "liquid staking", "lido dao", "lido finance", "staked eth"],
        "FET": ["fetch.ai", "fetch ai", "fet", "artificial superintelligence", "asi alliance", "singularitynet", "ocean protocol", "ai agent"],
        "ARB": ["arbitrum", "arb", "arbitrum one", "stylus", "orbit chain", "offchain labs", "rollup optimiste"],
        "NEAR": ["near protocol", "near", "nightshade", "chain signatures", "near foundation", "illia polosukhin"],
        "SUI": ["sui", "sui network", "move language", "mysten labs", "sui blockchain", "walrus"],
        "CRO": ["cronos", "cro", "crypto.com", "cronos zkevm", "kris marszalek", "crypto com"],
        "GRT": ["the graph", "grt", "subgraph", "graph protocol", "substreams", "indexing protocol"],
    }
    kw_list = ecosystem_kw.get(ticker, [ticker.lower(), nom_complet])

    def score_pertinence(titre, desc):
        titre_l = titre.lower()
        desc_l = desc.lower()
        score = 0
        if ticker.lower() in titre_l or nom_complet in titre_l:
            score += 10
        for kw in kw_list:
            if kw in titre_l:
                score += 5
                break
        for kw in kw_list:
            if kw in desc_l:
                score += 1
                break
        return score

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
                sc = score_pertinence(titre, desc)
                if sc >= 5:
                    bruts.append({"title": titre, "body": desc[:300], "url": lien,
                                  "source": source, "date": pub[:16], "_score": sc})
        except Exception:
            continue

    bruts.sort(key=lambda x: x.get('_score', 0), reverse=True)

    if len(bruts) < 4:
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
                        "_score": 8,
                    })
        except Exception:
            pass

    vus = set()
    uniques = []
    for art in bruts:
        cle = art['title'][:60].lower()
        if cle not in vus:
            vus.add(cle)
            uniques.append(art)
    bruts = uniques

    articles = []
    for art in bruts[:6]:
        articles.append({
            "title": traduire_fr(art["title"]),
            "body": traduire_fr(art["body"]),
            "url": art["url"],
            "source": art["source"],
            "date": art["date"],
        })

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


def detecter_supports_resistances(df, window=15, nb=3, lookback=270):
    """Niveaux pivots RELATIFS AU PRIX : supports sous le prix, résistances au-dessus.
    v2.1 : lookback=270 ajouté. POURQUOI : avec 730j d'historique, sans borne,
    des pivots vieux de 2 ans ressortiraient. 9 mois = pertinent pour du swing.
    Convention conservée : liste_supports[-1] et liste_resistances[-1] = le plus proche."""
    data = df.tail(lookback)
    if len(data) < window * 2 + 2:
        return [], []
    prix = float(data['Close'].iloc[-1])
    conf = data.iloc[:-window]  # exclut les bougies non confirmées
    if len(conf) < window:
        return [], []
    is_min = conf['Low'] == conf['Low'].rolling(window=window, center=True).min()
    is_max = conf['High'] == conf['High'].rolling(window=window, center=True).max()
    lows = conf[is_min]['Low'].tolist()
    highs = conf[is_max]['High'].tolist()
    supports = sorted([l for l in lows if l < prix])[-nb:]
    resistances = sorted([h for h in highs if h > prix], reverse=True)[-nb:]
    return supports, resistances


def appliquer_analyse_technique(df):
    """Applique l'ensemble des indicateurs techniques au DataFrame."""
    df['EMA_12'] = df['Close'].ewm(span=12, adjust=False).mean()
    df['EMA_26'] = df['Close'].ewm(span=26, adjust=False).mean()
    df['MA_20'] = df['Close'].rolling(20).mean()
    df['MA_50'] = df['Close'].rolling(50).mean()
    df['MA_100'] = df['Close'].rolling(100).mean()
    df['MA_200'] = df['Close'].rolling(200).mean()

    df['STD_20'] = df['Close'].rolling(20).std()
    df['BB_Haute'] = df['MA_20'] + (2 * df['STD_20'])
    df['BB_Basse'] = df['MA_20'] - (2 * df['STD_20'])
    df['BB_Width'] = (df['BB_Haute'] - df['BB_Basse']) / df['MA_20'] * 100

    df['RSI'] = calculer_rsi_wilder(df['Close'], 14)
    df['StochRSI_K'], df['StochRSI_D'] = calculer_stochastic_rsi(df['RSI'])
    df['MACD'], df['MACD_Signal'], df['MACD_Hist'] = calculer_macd(df['Close'])
    df['ATR'] = calculer_atr(df, 14)
    df['ATR_Pct'] = (df['ATR'] / df['Close']) * 100
    df['ADX'], df['Plus_DI'], df['Minus_DI'] = calculer_adx(df, 14)
    df['OBV'] = calculer_obv(df)
    df['OBV_MA'] = df['OBV'].rolling(20).mean()
    df['VWAP_20'] = calculer_vwap_rolling(df, 20)
    df['Vol_MA_20'] = df['Volume'].rolling(20).mean()
    df['Tenkan'], df['Kijun'], df['Senkou_A'], df['Senkou_B'], df['Chikou'] = calculer_ichimoku(df)

    return df


# ══════════════════════════════════════════════════════════════════════════════
# 5. MOTEUR ADAPTATIF — RÉGIME DAILY + WEEKLY + 3 SETUPS
# ══════════════════════════════════════════════════════════════════════════════

def detecter_regime(df):
    """Détecte le régime de marché DAILY : Haussier / Baissier / Range.
    Retourne (label, emoji, pente_ma200_pct, details_dict)."""
    infos = df.iloc[-1]
    prix = infos['Close']
    ma50 = infos['MA_50']
    ma200 = infos['MA_200']
    adx = infos['ADX']

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


# ── NOUVEAU v2.1 : régime WEEKLY ──
def detecter_regime_weekly(df):
    """Régime HEBDOMADAIRE via la 'bull market support band' (SMA20W + EMA21W),
    la référence standard des cycles crypto. Pas d'indicateur exotique.

    POURQUOI : ton horizon est de plusieurs mois ; le weekly filtre le bruit
    du daily. COMMENT : on resample le daily en bougies hebdo, puis :
      • Clôture > bande ET EMA21W montante (5 sem.) -> Haussier
      • Clôture < bande ET EMA21W descendante      -> Baissier
      • Sinon -> Transition (le prix se bat avec la bande)
    Retourne (label, emoji, pente_ema21w_pct ou None)."""
    try:
        dfw = (df.set_index('Date')[['Open', 'High', 'Low', 'Close', 'Volume']]
                 .resample('W-SUN')
                 .agg({'Open': 'first', 'High': 'max', 'Low': 'min',
                       'Close': 'last', 'Volume': 'sum'})
                 .dropna())
        if len(dfw) < 30:
            return "Indéterminé (historique court)", "❔", None
        dfw['EMA21'] = dfw['Close'].ewm(span=21, adjust=False).mean()
        dfw['SMA20'] = dfw['Close'].rolling(20).mean()
        close = float(dfw['Close'].iloc[-1])
        ema = float(dfw['EMA21'].iloc[-1])
        sma = float(dfw['SMA20'].iloc[-1]) if not pd.isna(dfw['SMA20'].iloc[-1]) else ema
        ema_passe = float(dfw['EMA21'].iloc[-6]) if len(dfw) >= 6 else ema
        pente_w = ((ema - ema_passe) / ema_passe) * 100 if ema_passe > 0 else 0.0
        bande_haute, bande_basse = max(ema, sma), min(ema, sma)
        if close > bande_haute and pente_w > 0:
            return "Haussier", "📈", pente_w
        if close < bande_basse and pente_w < 0:
            return "Baissier", "📉", pente_w
        return "Transition", "↔️", pente_w
    except Exception:
        return "Indéterminé", "❔", None


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

    if not pd.isna(infos['MA_200']) and prix > infos['MA_200']:
        score += 2.0
        signaux.append(("✅", "Tendance de fond haussière (prix > MA200)"))
    else:
        signaux.append(("⛔", "Pas de tendance haussière de fond — setup peu fiable"))
        return 0.0, signaux, None

    near_ma50 = _proche(prix, infos['MA_50'], 4)
    near_vwap = _proche(prix, infos['VWAP_20'], 3)
    if near_ma50 or near_vwap:
        score += 2.5
        ref = "MA50" if near_ma50 else "VWAP"
        signaux.append(("✅", f"Repli sur support dynamique ({ref}) — zone d'achat"))
    elif prix > infos['MA_50']:
        score += 0.5
        signaux.append(("⚪", "Prix au-dessus du support, pas encore de repli net"))

    if 38 <= infos['RSI'] <= 55:
        score += 2.0
        signaux.append(("✅", f"RSI en zone de rebond ({infos['RSI']:.0f}) — pas suracheté"))
        if infos['RSI'] > prec['RSI']:
            score += 0.5
            signaux.append(("✅", "RSI qui remonte — momentum se rétablit"))
    elif infos['RSI'] < 38:
        score += 1.0
        signaux.append(("⚪", f"RSI bas ({infos['RSI']:.0f}) — repli profond, surveiller le rebond"))

    if infos['MACD_Hist'] > prec['MACD_Hist']:
        score += 1.5
        signaux.append(("✅", "MACD se retourne à la hausse — pression vendeuse qui faiblit"))

    for label in ["38.2%", "50%", "61.8%"]:
        if label in niveaux_fib and _proche(prix, niveaux_fib[label], 2.5):
            score += 1.5
            signaux.append(("✅", f"Rebond sur Fibonacci {label} — zone technique forte"))
            break

    zone = f"{min(infos['MA_50'], infos['VWAP_20']):,.2f} – {prix:,.2f} $"
    return min(10.0, score), signaux, zone


def score_breakout(df):
    """SETUP 2 — Cassure / momentum. Pour suivre une vague en cours.
    v2.1 : paramètre 'liste_resistances' retiré (il n'était jamais utilisé ;
    la détection passe par last_broken_resistance + validate_breakout).
    Retourne (score/10, signaux, zone_entree)."""
    infos = df.iloc[-1]
    prix = infos['Close']
    score = 0.0
    signaux = []

    resistance_cassee = None
    df_lc = df.rename(columns={'High': 'high', 'Low': 'low'})
    niveau_casse = last_broken_resistance(df_lc, prix)
    bk = validate_breakout(prix, niveau_casse, max_extension_pct=8.0)
    if bk['valid']:
        score += 3.0
        resistance_cassee = niveau_casse
        signaux.append(("✅", f"Cassure crédible de {niveau_casse:,.2f} $ (+{bk['extension_pct']:.1f}%)"))
    elif niveau_casse is not None and bk.get('extension_pct') is not None and bk['extension_pct'] > 8.0:
        signaux.append(("⛔", f"Cassure de {niveau_casse:,.2f} $ déjà dépassée de {bk['extension_pct']:.0f}% — chasse, attendre un repli"))
    else:
        signaux.append(("⚪", "Pas de cassure nette récente"))

    if infos['Volume'] > 1.3 * infos['Vol_MA_20']:
        score += 2.5
        signaux.append(("✅", "Volume de confirmation présent — cassure crédible"))
    else:
        signaux.append(("⚪", "Volume insuffisant — risque de faux signal (fakeout)"))

    if infos['ADX'] > 22 and infos['Plus_DI'] > infos['Minus_DI']:
        score += 2.5
        signaux.append(("✅", f"Tendance qui se renforce (ADX {infos['ADX']:.0f}, +DI dominant)"))
    elif infos['Plus_DI'] > infos['Minus_DI']:
        score += 1.0
        signaux.append(("⚪", "Direction haussière mais tendance encore faible"))

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

    if infos['RSI'] < 30:
        score += 2.5
        signaux.append(("✅", f"RSI en survente extrême ({infos['RSI']:.0f})"))
    elif infos['RSI'] < 38:
        score += 1.0
        signaux.append(("⚪", f"RSI bas ({infos['RSI']:.0f})"))

    if prix <= infos['BB_Basse']:
        score += 2.0
        signaux.append(("✅", "Prix sous la bande de Bollinger basse — excès statistique"))

    if infos['Volume'] > 1.5 * infos['Vol_MA_20']:
        score += 2.0
        signaux.append(("✅", "Volume climax — possible capitulation vendeuse"))

    if fng_valeur < 25:
        score += 1.5
        signaux.append(("✅", f"Peur extrême (Fear & Greed {fng_valeur})"))
    if funding < 0:
        score += 1.0
        signaux.append(("✅", "Funding négatif — shorts dominants, pression de rachat"))
    if ls_ratio is not None and ls_ratio < 0.85:
        score += 0.5
        signaux.append(("✅", "Majorité de shorts — carburant de short squeeze"))

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
    candidats = []

    if regime == "Tendance Haussière":
        candidats.append(("Pullback (repli en tendance)", s_pull, "Modéré"))
        candidats.append(("Breakout (momentum)", s_break, "Modéré"))
        candidats.append(("Reversal (contrarian)", s_rev * 0.6, "Élevé"))
    elif regime == "Tendance Baissière":
        candidats.append(("Reversal (contrarian)", s_rev, "Très élevé"))
        candidats.append(("Breakout (momentum)", s_break * 0.5, "Élevé"))
    else:
        candidats.append(("Reversal (bas de range)", s_rev, "Élevé"))
        candidats.append(("Breakout (haut de range)", s_break, "Modéré"))
        candidats.append(("Pullback (repli)", s_pull * 0.8, "Modéré"))

    candidats.sort(key=lambda x: x[1], reverse=True)
    nom, score, risque = candidats[0]

    if score >= 6.5:
        verdict, couleur = "ENTRÉE ENVISAGEABLE", "success"
    elif score >= 4.5:
        verdict, couleur = "SURVEILLER DE PRÈS", "warning"
    else:
        verdict, couleur = "S'ABSTENIR POUR L'INSTANT", "error"

    return nom, score, verdict, couleur, risque


# ══════════════════════════════════════════════════════════════════════════════
# 6. 💼 MON PORTEFEUILLE — VUE D'ENSEMBLE (NOUVEAU v2.1)
# ══════════════════════════════════════════════════════════════════════════════

def _fmt_prix(v):
    """Format adaptatif : BTC à 2 décimales, MEME à 6."""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "N/A"
    if v >= 1000:
        return f"{v:,.0f}"
    if v >= 100:
        return f"{v:,.2f}"
    if v >= 1:
        return f"{v:,.3f}"
    if v >= 0.01:
        return f"{v:.4f}"
    return f"{v:.6f}"


st.markdown("## 💼 Mon Portefeuille — vue d'ensemble")
pf = charger_portfolio_csv()

if pf is None:
    st.info("📄 Ajoute un fichier **portfolio.csv** à la racine du repo (mêmes colonnes que le modèle fourni : "
            "crypto, quantite, avg_buy, dead_line, stop_loss, take_profit, statut, note) pour activer le suivi de positions.")
else:
    symbols = tuple(pf['crypto'].tolist())
    prix_map = charger_prix_portfolio(symbols)

    lignes, alertes = [], []
    total_valeur, total_pnl, cash_valeur, sans_prix = 0.0, 0.0, 0.0, []

    for _, row in pf.iterrows():
        sym = row['crypto']
        qte = row.get('quantite')
        avg = row.get('avg_buy')
        px = prix_map.get(sym)
        # Filet de sécurité stables : si l'API ne renvoie rien, 1$ est la bonne approximation
        if px is None and sym in ('USDC', 'USDT', 'DAI'):
            px = 1.0
        if px is None or pd.isna(qte):
            sans_prix.append(sym)
            valeur, pnl_pct = None, None
        else:
            valeur = float(qte) * float(px)
            total_valeur += valeur
            if sym in ('USDC', 'USDT', 'DAI'):
                cash_valeur += valeur
            if not pd.isna(avg) and avg > 0:
                pnl = (px - avg) * qte
                total_pnl += pnl
                pnl_pct = (px - avg) / avg * 100
            else:
                pnl_pct = None  # airdrops (coût 0) : pas de % pertinent

        dl = row.get('dead_line')
        slv = row.get('stop_loss')
        tp = row.get('take_profit')

        # Marge avant Dead Line : de combien le prix peut baisser avant le niveau critique
        marge_dl = ((px - dl) / px * 100) if (px and not pd.isna(dl) and dl > 0) else None
        # Potentiel vers Take Profit
        pot_tp = ((tp - px) / px * 100) if (px and not pd.isna(tp) and tp > 0) else None

        # ── ALERTES (du plus grave au moins grave, une seule par ligne) ──
        if px is not None:
            if not pd.isna(slv) and slv > 0 and px <= slv:
                alertes.append(("error", f"🚨 **{sym}** : STOP LOSS franchi ({_fmt_prix(px)} ≤ {_fmt_prix(slv)} $) — niveau d'action, décision requise"))
            elif not pd.isna(dl) and dl > 0 and px <= dl:
                alertes.append(("error", f"🔴 **{sym}** : DEAD LINE franchie ({_fmt_prix(px)} ≤ {_fmt_prix(dl)} $) — réévaluer la conviction maintenant"))
            elif marge_dl is not None and marge_dl <= 5:
                alertes.append(("warning", f"⚠️ **{sym}** : à {marge_dl:.1f}% de la dead line ({_fmt_prix(dl)} $) — surveiller de près"))
            if not pd.isna(tp) and tp > 0 and px >= tp:
                alertes.append(("success", f"🎯 **{sym}** : TAKE PROFIT atteint ({_fmt_prix(px)} ≥ {_fmt_prix(tp)} $) — alléger selon plan"))
            elif pot_tp is not None and 0 < pot_tp <= 5:
                alertes.append(("success", f"🎯 **{sym}** : à {pot_tp:.1f}% du take profit ({_fmt_prix(tp)} $) — préparer l'allègement"))

        lignes.append({
            "Crypto": sym,
            "Qté": float(qte) if not pd.isna(qte) else None,
            "Avg $": _fmt_prix(avg) if not pd.isna(avg) else "—",
            "Prix $": _fmt_prix(px),
            "Valeur $": round(valeur, 2) if valeur is not None else None,
            "P&L %": round(pnl_pct, 1) if pnl_pct is not None else None,
            "Marge → DL %": round(marge_dl, 1) if marge_dl is not None else None,
            "Potentiel → TP %": round(pot_tp, 1) if pot_tp is not None else None,
            "Statut": row.get('statut', ''),
        })

    # ── Bandeau de synthèse ──
    pcol1, pcol2, pcol3, pcol4 = st.columns(4)
    pcol1.metric("Valeur totale", f"{total_valeur:,.0f} $",
                 delta=f"{total_pnl:+,.0f} $ latent",
                 delta_color="normal" if total_pnl >= 0 else "inverse",
                 help="Somme de toutes les positions au prix live (CryptoCompare). Le delta = P&L latent total vs tes prix moyens d'achat. POURQUOI : c'est LA donnée de pilotage quotidienne — la valeur réelle, pas un capital théorique.")
    reste = OBJECTIF_PORTEFEUILLE - total_valeur
    pct_obj = total_valeur / OBJECTIF_PORTEFEUILLE * 100 if OBJECTIF_PORTEFEUILLE > 0 else 0
    pcol2.metric(f"Objectif {OBJECTIF_PORTEFEUILLE/1000:.0f}K $", f"{pct_obj:.0f}%",
                 delta=f"reste {reste:,.0f} $" if reste > 0 else "ATTEINT ✅",
                 delta_color="off",
                 help="Progression vers l'objectif. RAPPEL FRANC : combler l'écart dépend surtout du bêta de marché (scénario Base = ~11.5K, Bull = 15K+). Ne sur-trade pas pour forcer ce chiffre — c'est la 1ère cause de destruction d'un portefeuille de cette taille.")
    pcol3.metric("Cash (stables)", f"{cash_valeur:,.0f} $",
                 delta=f"{cash_valeur/total_valeur*100:.0f}% du portefeuille" if total_valeur > 0 else None,
                 delta_color="off",
                 help="USDC + USDT disponibles = munitions pour les DCA planifiés (BTC ~55K) et les setups validés par le terminal. Un cash à 0% = aucune capacité à saisir une capitulation.")
    nb_alertes = sum(1 for a in alertes if a[0] in ("error", "warning"))
    pcol4.metric("Alertes actives", f"{nb_alertes}",
                 delta="RAS" if nb_alertes == 0 else "action/surveillance requise",
                 delta_color="off" if nb_alertes == 0 else "inverse",
                 help="Nombre de positions ayant franchi (ou approchant à <5%) leur stop loss ou dead line. Niveaux définis dans portfolio.csv — c'est TOI qui les fixes, le terminal les surveille.")

    st.progress(min(1.0, max(0.0, pct_obj / 100)))

    # ── Alertes détaillées ──
    if alertes:
        for typ, msg in alertes:
            if typ == "error":
                st.error(msg)
            elif typ == "warning":
                st.warning(msg)
            else:
                st.success(msg)
    else:
        st.caption("✅ Aucune alerte : aucun niveau critique franchi ou approché (marge > 5% partout).")

    # ── Tableau des positions (triées par poids décroissant) ──
    df_pf = pd.DataFrame(lignes).sort_values("Valeur $", ascending=False, na_position='last')
    st.dataframe(
        df_pf, use_container_width=True, hide_index=True,
        column_config={
            "Qté": st.column_config.NumberColumn(format="%.4f"),
            "Valeur $": st.column_config.NumberColumn(format="%.2f"),
            "P&L %": st.column_config.NumberColumn(format="%+.1f%%",
                help="Plus/moins-value latente vs ton prix moyen d'achat. '—' pour les airdrops (coût 0)."),
            "Marge → DL %": st.column_config.NumberColumn(format="%.1f%%",
                help="De combien le prix peut encore baisser avant ta DEAD LINE (niveau de réévaluation de conviction). <5% = alerte."),
            "Potentiel → TP %": st.column_config.NumberColumn(format="%+.1f%%",
                help="Hausse restante jusqu'à ton TAKE PROFIT. Négatif = TP déjà dépassé."),
        }
    )
    if sans_prix:
        st.caption(f"⚠️ Prix indisponible pour : {', '.join(sans_prix)} — exclu(s) du total. Vérifie le ticker dans portfolio.csv.")
    st.caption("💡 **Comment mettre à jour** : après chaque trade, modifie portfolio.csv directement sur GitHub "
               "(quantité / avg / niveaux) → l'app se redéploie seule. Le journal détaillé reste dans ton Excel ; "
               "ce CSV est l'état NET courant que le terminal surveille.")

st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# 7. INTERFACE — SÉLECTION & CHARGEMENT
# ══════════════════════════════════════════════════════════════════════════════

choix = st.selectbox("Sélectionne un actif :", list(options_cryptos.keys()))
symbole_api = options_cryptos[choix]
fiche = repo_fondamental[choix]

df, source_px = charger_donnees_prix(fiche['coingecko_id'], fiche['ticker_news'])
if df.empty:
    st.stop()
if source_px == "coingecko":
    st.warning("⚠️ **Mode dégradé** : CryptoCompare indisponible (rate-limit probable de l'IP Streamlit Cloud) — "
               "fallback CoinGecko en bougies de **4 jours**. Conséquences : MA200 et régime DAILY incalculables, "
               "pivots/oscillateurs moins fiables. **Ne prends pas de décision d'entrée sur ces données** ; "
               "recharge la page dans 2-3 minutes pour retrouver le daily complet.")

_d = fetch_hyperliquid_derivs(fiche['index_id'])
if 'error' not in _d:
    funding = _d['funding_8h_pct']
    open_interest_usd = _d['open_interest_usd']
    deriv_volume = _d['volume_24h_usd']
else:
    funding, open_interest_usd, deriv_volume = charger_derives_coingecko(fiche['index_id'])
ls_ratio = charger_long_short_ratio(symbole_api)
oi_var_24h = None
fng_valeur, fng_statut, fng_historique = charger_fear_and_greed()
cg_data = charger_donnees_coingecko(fiche['coingecko_id'])
global_data = charger_dominance_btc()

# Analyse technique (sur l'historique COMPLET 730j — les indicateurs gagnent en précision)
df = appliquer_analyse_technique(df)
infos = df.iloc[-1]
prix = infos['Close']

# v2.1 : les graphiques n'affichent que les 365 derniers jours pour la lisibilité,
# mais tous les calculs (MA200, régimes, pivots) utilisent l'historique complet.
df_plot = df.tail(365).reset_index(drop=True)

liste_supports, liste_resistances = detecter_supports_resistances(df)
niveaux_fib = calculer_fibonacci(df)

# ══════════════════════════════════════════════════════════════════════════════
# 8. BARRE LATÉRALE — RISK MANAGEMENT + FONDAMENTAL
# ══════════════════════════════════════════════════════════════════════════════

st.sidebar.header("🧮 Gestion du Risque")
capital = st.sidebar.number_input("Capital total ($)", value=8200, step=100,
                                  help="Mets ta valeur de portefeuille réelle (affichée en haut de page) pour un sizing cohérent.")
risque_pct = st.sidebar.slider("Risque par trade (%)", 0.5, 5.0, 1.0, 0.5)
stop_loss_suggere = liste_supports[-1] if liste_supports else prix * 0.95
stop_loss = st.sidebar.number_input("Stop Loss ($)", value=float(stop_loss_suggere))

risque_dollars = capital * (risque_pct / 100)
distance_sl = ((prix - stop_loss) / prix) * 100
taille_position = risque_dollars / (distance_sl / 100) if distance_sl > 0 else 0
unites = taille_position / prix if prix > 0 else 0

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
# 9. MOTEUR DE DÉCISION — RÉGIMES + SETUPS + GARDE-FOUS
# ══════════════════════════════════════════════════════════════════════════════

regime, regime_emoji, pente_ma200, regime_details = detecter_regime(df)
regime_w, regime_w_emoji, pente_w = detecter_regime_weekly(df)   # NOUVEAU v2.1
s_pull, sig_pull, zone_pull = score_pullback(df, niveaux_fib)
s_break, sig_break, zone_break = score_breakout(df)
s_rev, sig_rev, zone_rev = score_reversal(df, funding, fng_valeur, ls_ratio)

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

if "Pullback" in nom_setup:
    signaux_reco, zone_reco = sig_pull, zone_pull
elif "Breakout" in nom_setup:
    signaux_reco, zone_reco = sig_break, zone_break
else:
    signaux_reco, zone_reco = sig_rev, zone_rev

# ── GARDE-FOU MACRO / BÊTA : la corrélation BTC peut primer sur le setup ──
_macro = fetch_btc_macro()
_btc_chg = _macro.get('btc_change_24h') if 'error' not in _macro else None
_btc_below_ma = _macro.get('btc_below_key_ma', False)

# v2.1 : ATH RÉEL (CoinGecko) et non plus le max sur l'historique chargé.
# POURQUOI : 'proche de l'ATH' (>-8%) déclenchait le malus/veto sur un faux ATH.
_ath_cg = cg_data.get('ath', 0) if cg_data else 0
_ath = float(_ath_cg) if _ath_cg and _ath_cg > 0 else float(df['High'].max())
_dist_ath = (prix - _ath) / _ath * 100 if _ath > 0 else 0.0

_beta = 1.0 if fiche['index_id'] == 'BTC' else None  # None => prudence haut bêta
_setup_type = ('breakout' if 'Breakout' in nom_setup
               else 'pullback' if 'Pullback' in nom_setup else 'reversal')

score_final, raisons_macro, veto_macro = apply_macro_guardrail(
    raw_score=score_setup,
    btc_change_24h=_btc_chg,
    fng_index=fng_valeur,
    dist_from_ath_pct=_dist_ath,
    asset_beta=_beta,
    btc_below_key_ma=_btc_below_ma,
    funding_rate=funding,
    setup_type=_setup_type,
)
score_setup = score_final

# ── NOUVEAU v2.1 : ALIGNEMENT WEEKLY ──
# Règle : un setup LONG de continuation (pullback/breakout) en régime weekly
# baissier prend -1.5. Le Reversal n'est pas pénalisé : sa prémisse est
# justement d'acheter la capitulation (même logique que le carve-out du F&G).
penalite_weekly = 0.0
if regime_w == "Baissier" and _setup_type != "reversal":
    penalite_weekly = 1.5
    score_setup = max(0.0, score_setup - penalite_weekly)
    raisons_macro.append(
        f"Régime WEEKLY baissier (pente EMA21W {pente_w:+.1f}%) : "
        f"renforcement contre-tendance de fond — pénalité −1.5"
    )
elif regime_w == "Haussier" and regime == "Tendance Haussière":
    raisons_macro.append("Daily et Weekly alignés haussiers ✅ — contexte de fond favorable au setup")

# ── Verdict final (recalculé APRÈS garde-fou macro ET filtre weekly) ──
if veto_macro:
    verdict, couleur = "ENTRÉE DÉCONSEILLÉE (garde-fou macro)", "error"
elif score_setup >= 6.5:
    verdict, couleur = "ENTRÉE ENVISAGEABLE", "success"
elif score_setup >= 4.5:
    verdict, couleur = "SURVEILLER DE PRÈS", "warning"
else:
    verdict, couleur = "S'ABSTENIR POUR L'INSTANT", "error"

for _r in raisons_macro:
    _ico = "⛔" if veto_macro else ("✅" if "alignés" in _r else "⚠️")
    signaux_reco.append((_ico, _r))

# ══════════════════════════════════════════════════════════════════════════════
# 10. AFFICHAGE PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════

st.markdown(f"# 💰 {choix.split()[0]} : **{prix:,.2f} USD**")

# ── Bandeau RÉGIMES (daily + weekly) ──
reg_col1, reg_col2, reg_col3, reg_col4 = st.columns(4)
reg_col1.metric("Régime DAILY", f"{regime_emoji} {regime}",
                help="📈 HAUSSIER : prix > MA200 ET MA50 > MA200 ET pente de fond positive. On achète les replis (setup Pullback prioritaire).\n📉 BAISSIER : prix < MA200 ET MA50 < MA200. On évite d'acheter ; seul le Reversal contrarian est envisageable, à haut risque.\n↔️ RANGE : signaux mixtes. On joue les bornes : achat près du bas du range, vente près du haut.")
reg_col2.metric("Régime WEEKLY", f"{regime_w_emoji} {regime_w}",
                delta=f"pente EMA21W {pente_w:+.1f}%" if pente_w is not None else None,
                delta_color="normal" if (pente_w or 0) > 0 else "inverse",
                help="POURQUOI : ton horizon est de plusieurs mois — le weekly est le filtre de fond qui élimine le bruit du daily.\nCOMMENT : clôture hebdo vs bande SMA20W/EMA21W ('bull market support band', la référence des cycles crypto) + pente de l'EMA21W sur 5 semaines.\nRÈGLE : renforcer une position uniquement si Daily ET Weekly sont alignés haussiers. Weekly baissier = -1.5 sur tout setup long de continuation (le Reversal contrarian reste exempté).")
reg_col3.metric("Pente MA200 (20j)", f"{pente_ma200:+.1f}%",
                delta="Fond porteur" if pente_ma200 > 0 else "Fond fragile",
                delta_color="normal" if pente_ma200 > 0 else "inverse",
                help="Inclinaison de la moyenne mobile 200 jours sur les 20 derniers jours.\n• > +2% : structure haussière solide, on peut surpondérer le long.\n• 0 à +2% : fond stable, biais haussier modéré.\n• -2% à 0 : fond qui s'essouffle, prudence sur les achats.\n• < -2% : tendance de fond clairement baissière, éviter les longs hors capitulation.")
reg_col4.metric("Force tendance (ADX)", f"{infos['ADX']:.0f}",
                delta="Directionnel" if infos['ADX'] > 25 else "Sans direction",
                delta_color="normal" if infos['ADX'] > 25 else "off",
                help="Mesure la FORCE de la tendance (pas la direction).\n• > 40 : tendance très forte (suivre, ne pas contre-trader).\n• 25–40 : tendance saine et exploitable, breakouts fiables.\n• 20–25 : tendance faible, à confirmer.\n• < 20 : marché en range, le RSI et les supports/résistances priment sur les MA.")

# ── Métriques principales ──
c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Prix", f"{prix:,.2f} $",
          delta=f"{cg_data.get('price_change_24h_pct', 0):.1f}% (24h)" if cg_data else None,
          help="Prix actuel et variation sur 24h. La couleur du delta (vert/rouge) donne l'humeur du jour.")

rsi_v = infos['RSI']
rsi_action = ("Survente extrême — guetter divergence haussière ou capitulation" if rsi_v < 30
              else "Zone de rebond — entrée potentielle en tendance haussière" if 30 <= rsi_v < 45
              else "Momentum équilibré — neutre" if 45 <= rsi_v < 60
              else "Momentum haussier — sain en début de hausse" if 60 <= rsi_v < 70
              else "Suracheté — risque de correction, prudence pour entrer")
c2.metric("RSI (14j)", f"{rsi_v:.1f}",
          help=f"Force relative 0–100, période 14j (Wilder).\n• 0–30 : SURVENTE — capitulation, rebond statistique probable.\n• 30–45 : ZONE DE REBOND — idéal pour acheter un repli en tendance haussière.\n• 45–60 : neutre, attendre une direction.\n• 60–70 : momentum haussier sain.\n• 70–100 : SURACHETÉ — risque de correction.\n\nLecture actuelle : {rsi_action}.")

macd_v = infos['MACD']
macd_h = infos['MACD_Hist']
macd_h_prev = df['MACD_Hist'].iloc[-2]
if macd_h > 0 and macd_h_prev <= 0:
    macd_action = "Croisement haussier FRAIS — signal d'entrée fort"
elif macd_h > 0 and macd_h > macd_h_prev:
    macd_action = "Momentum haussier qui s'accélère — tendance en place"
elif macd_h > 0 and macd_h < macd_h_prev:
    macd_action = "Momentum haussier qui décélère — surveiller le retournement"
elif macd_h < 0 and macd_h_prev >= 0:
    macd_action = "Croisement baissier FRAIS — sortir ou éviter d'entrer"
elif macd_h < 0 and macd_h > macd_h_prev:
    macd_action = "Pression vendeuse qui faiblit — possible retournement en cours"
else:
    macd_action = "Momentum baissier qui s'amplifie — éviter d'entrer long"
c3.metric("MACD Hist", f"{macd_h:.2f}",
          delta="Haussier" if macd_h > 0 else "Baissier",
          delta_color="normal" if macd_h > 0 else "inverse",
          help=f"Histogramme MACD (différence MACD − Signal). Mesure l'accélération du momentum.\n• > 0 et CROISSANT : momentum haussier qui s'accélère (signal d'entrée).\n• > 0 et DÉCROISSANT : momentum haussier qui s'essouffle, retournement possible.\n• < 0 et CROISSANT : baisse qui s'épuise, possible reversal.\n• < 0 et DÉCROISSANT : panique vendeuse, éviter d'entrer.\n• Croisement de 0 vers le positif = signal d'achat classique.\n\nLecture actuelle : {macd_action}.")

atr_pct = infos['ATR_Pct']
atr_action = ("Très faible volatilité — compression, mouvement imminent" if atr_pct < 1.5
              else "Volatilité modérée — conditions normales" if atr_pct < 3
              else "Volatilité élevée — élargir les stops" if atr_pct < 5
              else "Volatilité extrême — taille de position réduite")
c4.metric("ATR (volatilité)", f"{infos['ATR']:.2f} ({atr_pct:.1f}%)",
          help=f"Amplitude moyenne d'une bougie sur 14j.\n• Stop loss recommandé : 1 à 1.5 × ATR sous l'entrée pour un swing standard.\n• ATR% < 1.5 : compression, breakout imminent souvent.\n• ATR% 1.5–3 : volatilité normale.\n• ATR% 3–5 : volatilité élevée, stops larges nécessaires.\n• ATR% > 5 : extrême, réduire la taille de position de moitié.\n\nLecture actuelle : {atr_action}.")

fund_action = ("Shorts dominants — pression de rachat, rebond possible" if funding < -0.01
               else "Sain — pas de déséquilibre marqué" if -0.01 <= funding <= 0.03
               else "Acheteurs un peu chauds — surveiller" if 0.03 < funding <= 0.05
               else "SURCHAUFFE — purge baissière probable (malus −1 sur score)")
c5.metric("Funding Rate", f"{funding:.4f}%" if funding != 0 else "N/A",
          delta="Surchauffe" if funding > 0.05 else ("Shorts paient" if funding < -0.01 else "Sain"),
          delta_color="inverse" if funding > 0.05 else "normal",
          help=f"Coût payé toutes les 8h entre traders à effet de levier sur les perpétuels.\n• < -0.01% : shorts paient les longs → carburant pour un rebond.\n• -0.01% à 0.03% : équilibre sain.\n• 0.03% à 0.05% : penchant haussier, début de chauffe.\n• > 0.05% : SURCHAUFFE acheteuse, risque de purge (long squeeze).\n\nLecture actuelle : {fund_action}.")

vwap = infos['VWAP_20']
ecart_vwap = ((prix - vwap) / vwap) * 100 if vwap > 0 else 0
vwap_action = ("Très sous le VWAP — achat à prix moyen avantageux" if ecart_vwap < -3
               else "Sous le VWAP — légère décote" if ecart_vwap < 0
               else "Sur le VWAP — prix au juste milieu" if ecart_vwap < 1
               else "Au-dessus du VWAP — premium léger" if ecart_vwap < 5
               else "Très au-dessus — extension à risque")
c6.metric("VWAP 20j", f"{vwap:,.2f} $",
          delta=f"{ecart_vwap:+.1f}% du prix",
          delta_color="normal" if ecart_vwap < 0 else "inverse",
          help=f"Prix moyen pondéré par le volume sur 20 jours = la 'juste valeur' selon le marché.\n• Prix < VWAP : tu achètes moins cher que la moyenne pondérée. Support clé en tendance haussière.\n• Prix > VWAP : prime payée. Résistance dynamique en tendance baissière.\n• Écart >5% : extension du prix, retour vers le VWAP probable.\n\nLecture actuelle : {vwap_action}.")

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
    st.caption(f"Régimes — Daily : {regime} · Weekly : {regime_w}")

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
# 11. GRAPHIQUE PRINCIPAL — PRIX + INDICATEURS (affichage : 365 derniers jours)
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("---")
tab_chart, tab_oscillateurs, tab_ichimoku, tab_volume = st.tabs(
    ["📈 Prix & Tendance", "📉 Oscillateurs", "☁️ Ichimoku", "📊 Volume & OBV"]
)

with tab_chart:
    with st.expander("📖 Comment lire ce graphique", expanded=False):
        st.markdown("""
**Chandeliers japonais** : chaque bougie = 1 jour. Verte = clôture > ouverture. Rouge = clôture < ouverture. La mèche montre les extrêmes.

**Ligne cyan (MA50)** : moyenne mobile 50 jours. Support/résistance dynamique en swing. Acheter sous MA50 en tendance haussière = entrée sur repli.

**Ligne orange (MA200)** : moyenne mobile 200 jours. Frontière entre régime haussier (prix au-dessus) et baissier (en-dessous). Référence des institutionnels.

**Bandes pointillées (Bollinger)** : enveloppe à ±2 écarts-types autour de la MA20.
• Prix sous la bande basse = excès baissier statistique (rebond probable).
• Prix sur la bande haute = excès haussier (correction probable).
• Bandes qui se resserrent = compression → mouvement explosif imminent.

**Ligne jaune pointillée (VWAP 20j)** : prix moyen pondéré par le volume. Support clé en tendance.

**Lignes Fibonacci** : niveaux de retracement statistiques. 38.2%, 50% et 61.8% sont les zones de rebond les plus fréquentes après une vague de hausse ou de baisse.

**Lignes S1/S2/S3 (vertes)** : supports détectés sur les creux locaux des 9 derniers mois. **R1/R2/R3 (rouges)** : résistances sur les sommets locaux.

**Histogramme inférieur (Volume)** : vert quand bougie haussière, rouge quand baissière. La ligne blanche = volume moyen 20j. Un volume > 1.5× la moyenne valide un mouvement.

*NB : le graphique affiche 365 jours, mais MA200, régimes et pivots sont calculés sur 730 jours d'historique (plus fiable).*
        """)

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03,
                        row_heights=[0.75, 0.25],
                        subplot_titles=("", "Volume"))

    fig.add_trace(go.Candlestick(
        x=df_plot['Date'], open=df_plot['Open'], high=df_plot['High'],
        low=df_plot['Low'], close=df_plot['Close'],
        name="Prix", hoverinfo="none"
    ), row=1, col=1)

    fig.add_trace(go.Scatter(x=df_plot['Date'], y=df_plot['MA_50'], line=dict(color='cyan', width=1.5),
                             name="MA50", hovertemplate="MA50: %{y:,.2f}$<extra></extra>"), row=1, col=1)
    if df_plot['MA_200'].notna().sum() > 0:
        fig.add_trace(go.Scatter(x=df_plot['Date'], y=df_plot['MA_200'], line=dict(color='orange', width=1.5),
                                 name="MA200", hovertemplate="MA200: %{y:,.2f}$<extra></extra>"), row=1, col=1)

    fig.add_trace(go.Scatter(x=df_plot['Date'], y=df_plot['BB_Basse'], line=dict(color='rgba(231,76,60,0.6)', dash='dash', width=1),
                             name="BB Basse", hovertemplate="BB Basse: %{y:,.2f}$<extra></extra>"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df_plot['Date'], y=df_plot['BB_Haute'], line=dict(color='rgba(46,204,113,0.6)', dash='dash', width=1),
                             name="BB Haute", fill='tonexty', fillcolor='rgba(100,100,100,0.05)',
                             hovertemplate="BB Haute: %{y:,.2f}$<extra></extra>"), row=1, col=1)

    fig.add_trace(go.Scatter(x=df_plot['Date'], y=df_plot['VWAP_20'], line=dict(color='yellow', width=1, dash='dot'),
                             name="VWAP 20j", hovertemplate="VWAP: %{y:,.2f}$<extra></extra>"), row=1, col=1)

    fib_colors = ['rgba(255,255,255,0.3)', 'rgba(46,204,113,0.3)', 'rgba(46,204,113,0.4)',
                  'rgba(241,196,15,0.4)', 'rgba(231,76,60,0.4)', 'rgba(231,76,60,0.3)', 'rgba(255,255,255,0.3)']
    for (label, level), color in zip(niveaux_fib.items(), fib_colors):
        fig.add_hline(y=level, line_dash="dot", line_color=color, annotation_text=f"Fib {label}",
                      annotation_position="right", row=1, col=1)

    for i, sup in enumerate(liste_supports):
        fig.add_hline(y=sup, line_dash="dot", line_color="rgba(46,204,113,0.5)",
                      annotation_text=f"S{i+1}", row=1, col=1)
    for i, res in enumerate(liste_resistances):
        fig.add_hline(y=res, line_dash="dot", line_color="rgba(231,76,60,0.5)",
                      annotation_text=f"R{i+1}", row=1, col=1)

    colors_vol = ['rgba(46,204,113,0.5)' if c >= o else 'rgba(231,76,60,0.5)'
                  for c, o in zip(df_plot['Close'], df_plot['Open'])]
    fig.add_trace(go.Bar(x=df_plot['Date'], y=df_plot['Volume'], name="Volume",
                         marker_color=colors_vol, opacity=0.7), row=2, col=1)
    fig.add_trace(go.Scatter(x=df_plot['Date'], y=df_plot['Vol_MA_20'], line=dict(color='white', width=1),
                             name="Vol MA20"), row=2, col=1)

    fig.update_layout(xaxis_rangeslider_visible=False, template="plotly_dark",
                      height=650, margin=dict(l=10, r=10, t=30, b=10), hovermode="x unified",
                      showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=1.02))
    st.plotly_chart(fig, use_container_width=True)


with tab_oscillateurs:
    with st.expander("📖 Comment lire ces oscillateurs", expanded=False):
        st.markdown("""
**RSI (Relative Strength Index)** — violet : oscillateur 0–100.
• < 30 = survente (rebond statistique probable).
• 30–45 = zone de rebond idéale en tendance haussière.
• 45–60 = neutre.
• 60–70 = momentum haussier sain.
• > 70 = suracheté (correction probable).
Méthode Wilder appliquée (lissage exponentiel correct).

**Stochastic RSI** — bleu (%K) et orange (%D) : RSI appliqué à lui-même.
• Croisement %K au-dessus de %D en zone basse (<20) = signal d'achat fort.
• Plus réactif que le RSI brut, idéal pour timing fin d'entrée/sortie.

**MACD** — bleu (ligne MACD) et orange (signal). Barres = histogramme.
• MACD coupe le signal vers le haut → signal d'achat.
• MACD coupe le signal vers le bas → signal de vente.
• Histogramme positif et croissant = momentum haussier qui s'accélère.
• Histogramme négatif et croissant = pression vendeuse qui faiblit (reversal possible).

**ADX** — blanc : force de la tendance (pas la direction).
• > 25 = tendance forte et exploitable.
• < 20 = marché en range, éviter les stratégies de suivi.
**+DI** (vert) > **-DI** (rouge) = direction haussière. Inverse = baissière.
        """)

    fig_osc = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.05,
                            subplot_titles=("RSI (14) & Stochastic RSI", "MACD", "ADX"))

    fig_osc.add_trace(go.Scatter(x=df_plot['Date'], y=df_plot['RSI'], line=dict(color='#8e44ad', width=1.5),
                                 name="RSI"), row=1, col=1)
    fig_osc.add_trace(go.Scatter(x=df_plot['Date'], y=df_plot['StochRSI_K'], line=dict(color='#3498db', width=1),
                                 name="StochRSI %K"), row=1, col=1)
    fig_osc.add_trace(go.Scatter(x=df_plot['Date'], y=df_plot['StochRSI_D'], line=dict(color='#e67e22', width=1, dash='dash'),
                                 name="StochRSI %D"), row=1, col=1)
    fig_osc.add_hline(y=70, line_dash="dash", line_color="rgba(231,76,60,0.5)", row=1, col=1)
    fig_osc.add_hline(y=30, line_dash="dash", line_color="rgba(46,204,113,0.5)", row=1, col=1)

    macd_colors = ['rgba(46,204,113,0.7)' if v >= 0 else 'rgba(231,76,60,0.7)' for v in df_plot['MACD_Hist']]
    fig_osc.add_trace(go.Bar(x=df_plot['Date'], y=df_plot['MACD_Hist'], name="MACD Hist",
                             marker_color=macd_colors), row=2, col=1)
    fig_osc.add_trace(go.Scatter(x=df_plot['Date'], y=df_plot['MACD'], line=dict(color='#3498db', width=1.5),
                                 name="MACD"), row=2, col=1)
    fig_osc.add_trace(go.Scatter(x=df_plot['Date'], y=df_plot['MACD_Signal'], line=dict(color='#e67e22', width=1),
                                 name="Signal"), row=2, col=1)

    fig_osc.add_trace(go.Scatter(x=df_plot['Date'], y=df_plot['ADX'], line=dict(color='white', width=2),
                                 name="ADX"), row=3, col=1)
    fig_osc.add_trace(go.Scatter(x=df_plot['Date'], y=df_plot['Plus_DI'], line=dict(color='#2ecc71', width=1),
                                 name="+DI"), row=3, col=1)
    fig_osc.add_trace(go.Scatter(x=df_plot['Date'], y=df_plot['Minus_DI'], line=dict(color='#e74c3c', width=1),
                                 name="-DI"), row=3, col=1)
    fig_osc.add_hline(y=25, line_dash="dash", line_color="rgba(255,255,255,0.3)", row=3, col=1,
                      annotation_text="Seuil tendance")

    fig_osc.update_layout(template="plotly_dark", height=700, hovermode="x unified",
                          margin=dict(l=10, r=10, t=30, b=10))
    st.plotly_chart(fig_osc, use_container_width=True)


with tab_ichimoku:
    with st.expander("📖 Comment lire l'Ichimoku", expanded=False):
        st.markdown("""
L'Ichimoku Kinko Hyo est un système complet qui donne tendance, momentum, supports et signaux dans un seul graphique.

**Tenkan (bleu, période 9)** : signal court terme.
**Kijun (rouge, période 26)** : référence moyen terme, support/résistance dynamique.
• Tenkan > Kijun = momentum positif (signal d'achat).
• Tenkan < Kijun = momentum négatif (signal de vente).

**Nuage (Senkou A et B)** : zone de support/résistance projetée 26 jours en avant.
• Prix au-dessus du nuage = tendance HAUSSIÈRE confirmée.
• Prix dans le nuage = zone neutre, indécision.
• Prix sous le nuage = tendance BAISSIÈRE confirmée.
• Nuage vert (Senkou A > B) = biais haussier. Rouge = biais baissier.
• Épaisseur du nuage = force du support/résistance.

**Signal d'achat complet** : prix au-dessus du nuage + Tenkan > Kijun + nuage vert = configuration idéale pour entrer long.
        """)

    fig_ichi = go.Figure()
    fig_ichi.add_trace(go.Candlestick(x=df_plot['Date'], open=df_plot['Open'], high=df_plot['High'],
                                       low=df_plot['Low'], close=df_plot['Close'], name="Prix", hoverinfo="none"))
    fig_ichi.add_trace(go.Scatter(x=df_plot['Date'], y=df_plot['Tenkan'], line=dict(color='#3498db', width=1),
                                  name="Tenkan (9)"))
    fig_ichi.add_trace(go.Scatter(x=df_plot['Date'], y=df_plot['Kijun'], line=dict(color='#e74c3c', width=1),
                                  name="Kijun (26)"))
    fig_ichi.add_trace(go.Scatter(x=df_plot['Date'], y=df_plot['Senkou_A'], line=dict(color='rgba(46,204,113,0.5)', width=0.5),
                                  name="Senkou A"))
    fig_ichi.add_trace(go.Scatter(x=df_plot['Date'], y=df_plot['Senkou_B'], line=dict(color='rgba(231,76,60,0.5)', width=0.5),
                                  name="Senkou B", fill='tonexty', fillcolor='rgba(100,100,100,0.1)'))

    fig_ichi.update_layout(template="plotly_dark", height=500, hovermode="x unified",
                           xaxis_rangeslider_visible=False, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig_ichi, use_container_width=True)

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
    with st.expander("📖 Comment lire le volume et l'OBV", expanded=False):
        st.markdown("""
Le volume confirme (ou invalide) tout mouvement de prix. Un mouvement sans volume est suspect.

**OBV (On-Balance Volume)** — bleu : volume cumulé signé (+ si bougie haussière, − si baissière).
• OBV qui monte alors que le prix stagne = ACCUMULATION discrète (signal d'achat institutionnel).
• OBV qui baisse alors que le prix stagne = DISTRIBUTION discrète (vendeurs invisibles).
• Divergence OBV/Prix : si le prix fait un nouveau plus haut sans que l'OBV suive, la hausse est artificielle.

**OBV MA20** — orange : moyenne mobile de l'OBV. L'OBV au-dessus de sa MA = flux acheteur dominant.

**Quote Volume ($)** — barres bleues : volume échangé en dollars sur 24h. Permet de comparer la liquidité réelle entre périodes (mieux que le volume en unités, biaisé par le prix).

**Lecture rapide** :
• Cassure + volume élevé = mouvement crédible, à suivre.
• Cassure + volume faible = fakeout probable, attendre confirmation.
• Volume climax (> 2× la moyenne) après une longue baisse = signal de capitulation, plancher possible.
        """)

    fig_vol = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05,
                            subplot_titles=("On-Balance Volume (OBV)", "Quote Volume ($)"))

    fig_vol.add_trace(go.Scatter(x=df_plot['Date'], y=df_plot['OBV'], line=dict(color='#3498db', width=1.5),
                                 name="OBV"), row=1, col=1)
    fig_vol.add_trace(go.Scatter(x=df_plot['Date'], y=df_plot['OBV_MA'], line=dict(color='orange', width=1, dash='dash'),
                                 name="OBV MA20"), row=1, col=1)

    fig_vol.add_trace(go.Bar(x=df_plot['Date'], y=df_plot['Quote_volume'], name="Volume $",
                             marker_color='rgba(52,152,219,0.5)'), row=2, col=1)

    fig_vol.update_layout(template="plotly_dark", height=500, hovermode="x unified",
                          margin=dict(l=10, r=10, t=30, b=10))
    st.plotly_chart(fig_vol, use_container_width=True)

    if infos['OBV'] > infos['OBV_MA']:
        st.write("✅ OBV au-dessus de sa moyenne → flux acheteur dominant (accumulation).")
    else:
        st.write("🔴 OBV sous sa moyenne → flux vendeur dominant (distribution).")


# ══════════════════════════════════════════════════════════════════════════════
# 12. TABLEAU DE BORD DÉRIVÉS
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("---")
st.header("⚡ Marché des Dérivés")

d1, d2, d3, d4 = st.columns(4)
d1.metric("Open Interest", f"{open_interest_usd/1e9:.2f}B $" if open_interest_usd > 0 else "N/A",
          help="Montant total engagé sur les contrats à terme. En hausse = nouveaux capitaux entrent. Chute brutale = liquidations/débouclage de positions.")
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
              help="Donnée indisponible depuis le serveur US (source Bybit géo-restreinte). Ce champ n'impacte pas le score quand il est absent — le Reversal perd au plus 0.5 pt de signal.")

with st.expander("📖 Lecture des dérivés"):
    st.markdown("""
**Open Interest** : capital total engagé sur les contrats perpétuels. En forte hausse avec un prix qui monte = tendance saine. Chute brutale = liquidations.

**Funding Rate** : coût payé toutes les 8h entre longs et shorts. >0.05% = surchauffe acheteuse (malus appliqué au score). <−0.01% = shorts en souffrance (potentiel squeeze haussier).

**Volume Dérivés** : confirme la conviction. Un mouvement de prix sur fort volume dérivés est plus fiable.

**Ratio Long/Short** : <0.85 = majorité de shorts → carburant pour un short squeeze. >1.2 = excès d'optimisme.

*Note : source primaire = API native Hyperliquid (HYPE et actifs listés), sinon agrégateur CoinGecko (tous exchanges confondus).*
    """)

# ══════════════════════════════════════════════════════════════════════════════
# 13. CONTEXTE MACRO & MARCHÉ GLOBAL
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
# 14. FICHE FONDAMENTALE DE L'ACTIF
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("---")
st.header(f"📋 Fiche Fondamentale — {choix}")

def fmt_milliards(v):
    return f"${v/1e9:.1f}B" if v and v > 0 else "N/A"

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
               help="Écart par rapport au plus haut historique RÉEL (All-Time High, source CoinGecko — c'est aussi cette valeur qui alimente le garde-fou macro). −80% = l'actif a perdu 80% depuis son sommet.")

    st.subheader("📈 Performance")
    perf1, perf2, perf3, perf4 = st.columns(4)
    perf1.metric("24h", f"{cg_data.get('price_change_24h_pct', 0):+.1f}%")
    perf2.metric("7 jours", f"{cg_data.get('price_change_7d_pct', 0):+.1f}%")
    perf3.metric("30 jours", f"{cg_data.get('price_change_30d_pct', 0):+.1f}%")
    perf4.metric("1 an", f"{cg_data.get('price_change_1y_pct', 0):+.1f}%")
else:
    st.warning("⏳ Données fondamentales temporairement indisponibles (limite de requêtes CoinGecko). Rafraîchis la page dans 1 minute.")

f_col1, f_col2, f_col3 = st.columns(3)
f_col1.markdown(f"### 📊 Tokenomics\n{fiche['tokenomics']}")
f_col2.markdown(f"### 🗺️ Roadmap\n{fiche['roadmap']}")
f_col3.markdown(f"### 📈 Sensibilité\n{fiche['sensibilite']}")

# ══════════════════════════════════════════════════════════════════════════════
# 15. RÉSUMÉ TECHNIQUE RAPIDE
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("---")
st.header("🔍 Synthèse Technique")

nb_bull, nb_bear, nb_neutre = 0, 0, 0
analyses = {"tendance": [], "momentum": [], "volatilite": [], "force": []}

if prix > infos['MA_50']:
    analyses["tendance"].append(("✅", "Prix > MA50", "soutenu court terme"))
    nb_bull += 1
else:
    analyses["tendance"].append(("🔴", "Prix < MA50", "sous pression court terme"))
    nb_bear += 1

if not pd.isna(infos.get('MA_200')):
    if prix > infos['MA_200']:
        analyses["tendance"].append(("✅", "Prix > MA200", "régime de fond haussier"))
        nb_bull += 1
    else:
        analyses["tendance"].append(("🔴", "Prix < MA200", "régime de fond baissier"))
        nb_bear += 1
    if infos['MA_50'] > infos['MA_200']:
        analyses["tendance"].append(("✅", "Golden Cross (MA50 > MA200)", "structure haussière confirmée"))
        nb_bull += 1
    else:
        analyses["tendance"].append(("🔴", "Death Cross (MA50 < MA200)", "structure baissière confirmée"))
        nb_bear += 1

# v2.1 : le régime weekly entre dans la synthèse — c'est le filtre de fond
if regime_w == "Haussier":
    analyses["tendance"].append(("✅", "Weekly haussier (EMA21W)", "cycle de fond porteur"))
    nb_bull += 1
elif regime_w == "Baissier":
    analyses["tendance"].append(("🔴", "Weekly baissier (EMA21W)", "cycle de fond hostile aux longs"))
    nb_bear += 1
elif regime_w == "Transition":
    analyses["tendance"].append(("⚪", "Weekly en transition", "le prix se bat avec la bande 20/21W"))
    nb_neutre += 1

if infos['RSI'] < 30:
    analyses["momentum"].append(("✅", f"RSI {infos['RSI']:.0f}", "survendu, rebond probable"))
    nb_bull += 1
elif infos['RSI'] > 70:
    analyses["momentum"].append(("🔴", f"RSI {infos['RSI']:.0f}", "suracheté, correction probable"))
    nb_bear += 1
elif 40 <= infos['RSI'] <= 60:
    analyses["momentum"].append(("⚪", f"RSI {infos['RSI']:.0f}", "neutre"))
    nb_neutre += 1
else:
    analyses["momentum"].append(("⚪", f"RSI {infos['RSI']:.0f}", "zone intermédiaire"))
    nb_neutre += 1

if infos['MACD'] > infos['MACD_Signal']:
    analyses["momentum"].append(("✅", "MACD > Signal", "momentum haussier"))
    nb_bull += 1
else:
    analyses["momentum"].append(("🔴", "MACD < Signal", "momentum baissier"))
    nb_bear += 1

if prix <= infos['BB_Basse']:
    analyses["volatilite"].append(("✅", "Prix ≤ Bollinger Basse", "excès baissier statistique"))
    nb_bull += 1
elif prix >= infos['BB_Haute']:
    analyses["volatilite"].append(("🔴", "Prix ≥ Bollinger Haute", "excès haussier statistique"))
    nb_bear += 1
else:
    analyses["volatilite"].append(("⚪", "Prix dans les bandes", "volatilité normale"))
    nb_neutre += 1

if infos['ADX'] > 25:
    if infos['Plus_DI'] > infos['Minus_DI']:
        analyses["force"].append(("✅", f"ADX {infos['ADX']:.0f}", "tendance haussière forte"))
        nb_bull += 1
    else:
        analyses["force"].append(("🔴", f"ADX {infos['ADX']:.0f}", "tendance baissière forte"))
        nb_bear += 1
else:
    analyses["force"].append(("⚪", f"ADX {infos['ADX']:.0f}", "marché sans direction"))
    nb_neutre += 1

total = nb_bull + nb_bear + nb_neutre
pct_bull = (nb_bull / total) * 100 if total else 0
if pct_bull >= 65:
    synthese_emoji, synthese_couleur = "📈", "success"
    synthese_txt = f"**Configuration majoritairement HAUSSIÈRE** — {nb_bull} signaux verts sur {total} ({pct_bull:.0f}%). Les indicateurs convergent vers un biais acheteur. Aligné avec le setup recommandé : **{nom_setup}**."
elif pct_bull <= 35:
    synthese_emoji, synthese_couleur = "📉", "error"
    synthese_txt = f"**Configuration majoritairement BAISSIÈRE** — {nb_bear} signaux rouges sur {total} ({(nb_bear/total)*100:.0f}%). Les indicateurs convergent vers un biais vendeur. Prudence pour entrer long."
else:
    synthese_emoji, synthese_couleur = "↔️", "warning"
    synthese_txt = f"**Configuration MIXTE** — {nb_bull} haussiers / {nb_bear} baissiers / {nb_neutre} neutres. Aucune conviction nette, marché en transition. Attendre un signal plus tranché ou jouer en taille réduite."

if synthese_couleur == "success":
    st.success(f"{synthese_emoji} {synthese_txt}")
elif synthese_couleur == "warning":
    st.warning(f"{synthese_emoji} {synthese_txt}")
else:
    st.error(f"{synthese_emoji} {synthese_txt}")

st.caption("ℹ️ Rappel : cette synthèse décrit l'ÉTAT du marché ; le score de setup mesure la QUALITÉ d'une opportunité. "
           "Un Reversal 9/10 dans une photo majoritairement baissière n'est pas une contradiction — ce sont deux dimensions indépendantes.")

syn_col1, syn_col2 = st.columns(2)
with syn_col1:
    st.markdown("#### 📊 Tendance")
    for emoji, label, desc in analyses["tendance"]:
        st.markdown(f"{emoji} **{label}** — {desc}")
    st.markdown("#### ⚡ Momentum")
    for emoji, label, desc in analyses["momentum"]:
        st.markdown(f"{emoji} **{label}** — {desc}")

with syn_col2:
    st.markdown("#### 📐 Volatilité & Force")
    for emoji, label, desc in analyses["volatilite"] + analyses["force"]:
        st.markdown(f"{emoji} **{label}** — {desc}")

    st.markdown("#### 🎯 Niveaux Clés")
    st.markdown(f"• **VWAP 20j** : {infos['VWAP_20']:,.2f} $ — support/résistance dynamique")
    st.markdown(f"• **MA50** : {infos['MA_50']:,.2f} $ — moyenne court/moyen terme")
    if not pd.isna(infos.get('MA_200')):
        st.markdown(f"• **MA200** : {infos['MA_200']:,.2f} $ — frontière régime")
    st.markdown(f"• **Bollinger** : {infos['BB_Basse']:,.2f} $ ↔ {infos['BB_Haute']:,.2f} $")
    if liste_supports:
        st.markdown(f"• **Support le plus proche** : {liste_supports[-1]:,.2f} $")
    if liste_resistances:
        st.markdown(f"• **Résistance la plus proche** : {liste_resistances[-1]:,.2f} $")

# ══════════════════════════════════════════════════════════════════════════════
# 16. ACTUALITÉS
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
# 17. LEXIQUE COMPLET
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

**Bull Market Support Band (weekly)** : zone entre la SMA20 et l'EMA21 HEBDOMADAIRES. Tant que la clôture hebdo tient au-dessus, le cycle haussier de fond est intact ; une perte confirmée de la bande marque historiquement les bascules de cycle.

**Funding Rate** : Coût payé toutes les 8h entre longs et shorts sur les perpétuels. >0.05% = surchauffe acheteuse.

**Long/Short Ratio** : Ratio des positions longues/courtes des top traders. <0.85 = carburant de short squeeze.

**Dead Line (portefeuille)** : TON niveau de réévaluation de conviction, défini dans portfolio.csv. Franchi = on rouvre le dossier (thèse cassée ?), pas forcément on vend. Le Stop Loss, lui, est un niveau d'ACTION.
    """)

# ── Footer ──
st.markdown("---")
st.caption(f"Terminal Crypto Pro v2.1 — Dernière mise à jour : {datetime.now().strftime('%d/%m/%Y %H:%M')} — Données : CryptoCompare, CoinGecko, Hyperliquid, Alternative.me")
st.caption("⚠️ Cet outil est un support d'analyse. Il ne constitue en aucun cas un conseil financier.")
