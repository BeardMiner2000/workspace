"""
DexScreener integration for top trending Solana tokens.

Fetches boosted/trending Solana tokens from DexScreener API with
60-second caching. Returns normalized token data for pump_surfer bot.
"""
from __future__ import annotations

import json
import time
import urllib.request
from typing import Any

_BOOST_URL = "https://api.dexscreener.com/token-boosts/top/v1"
_LATEST_BOOST_URL = "https://api.dexscreener.com/token-boosts/latest/v1"
_SEARCH_URLS = (
    "https://api.dexscreener.com/latest/dex/search?q=solana%20pump",
    "https://api.dexscreener.com/latest/dex/search?q=pump",
)

_HEADERS = {
    "User-Agent": "paper-trader-league/1.0",
    "Accept": "application/json",
}

_cache_ts: float = 0.0
_cache_data: list[dict[str, Any]] = []
_CACHE_TTL = 60.0


def _get_json(url: str, timeout: float = 8.0) -> Any:
    req = urllib.request.Request(url, headers=_HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _parse_boost_response(data: Any) -> list[dict[str, Any]]:
    """Parse token-boosts/top/v1 response."""
    tokens = []
    if not isinstance(data, list):
        return tokens

    for item in data:
        try:
            chain_id = item.get("chainId", "")
            if chain_id != "solana":
                continue

            # Boost endpoint gives token info; we need pair price data
            symbol_raw = item.get("tokenAddress", "")[:8].upper()
            description = item.get("description") or ""
            # Try to extract a ticker from description or use address prefix
            name = item.get("url", "").split("/")[-1] if item.get("url") else symbol_raw
            # We'll treat the token address as our identifier
            address = item.get("tokenAddress", "")
            if not address:
                continue

            tokens.append({
                "symbol": f"{symbol_raw}USDT",
                "price_usd": 0.0,  # not available in boost endpoint directly
                "price_change_24h": float(item.get("totalAmount", 0)),  # use boost amount as proxy
                "volume_24h": float(item.get("totalAmount", 0)) * 1000,  # synthetic volume proxy
                "address": address,
                "name": name,
            })
        except Exception:
            continue

    return tokens


def _parse_pairs_response(data: Any) -> list[dict[str, Any]]:
    """Parse pairs search response from DexScreener."""
    tokens = []
    if not isinstance(data, dict):
        return tokens

    pairs = data.get("pairs") or []
    if not pairs:
        pairs = data.get("data", {}).get("pairs", []) if isinstance(data.get("data"), dict) else []

    seen_addresses = set()

    for pair in pairs:
        try:
            chain_id = pair.get("chainId", "")
            if chain_id != "solana":
                continue

            price_usd_raw = pair.get("priceUsd")
            try:
                price_usd = float(price_usd_raw)
                if price_usd <= 0:
                    continue
            except (TypeError, ValueError):
                continue

            base_token = pair.get("baseToken", {})
            address = base_token.get("address", "")
            if not address or address in seen_addresses:
                continue
            seen_addresses.add(address)

            symbol_raw = base_token.get("symbol", "UNKNOWN").upper()
            # Clean symbol: remove special chars, keep alphanumeric
            symbol_clean = "".join(c for c in symbol_raw if c.isalnum())[:12]
            name = base_token.get("name", symbol_clean)

            price_change_24h = 0.0
            price_change = pair.get("priceChange", {})
            if isinstance(price_change, dict):
                h24 = price_change.get("h24")
                if h24 is not None:
                    try:
                        price_change_24h = float(h24)
                    except (TypeError, ValueError):
                        pass

            volume_24h = 0.0
            volume = pair.get("volume", {})
            if isinstance(volume, dict):
                v24 = volume.get("h24")
                if v24 is not None:
                    try:
                        volume_24h = float(v24)
                    except (TypeError, ValueError):
                        pass

            tokens.append({
                "symbol": f"{symbol_clean}USDT",
                "price_usd": price_usd,
                "price_change_24h": price_change_24h,
                "volume_24h": volume_24h,
                "address": address,
                "name": name,
            })
        except Exception:
            continue

    return tokens


def fetch_top_solana_tokens(force: bool = False) -> list[dict[str, Any]]:
    """
    Fetch top trending Solana tokens from DexScreener.

    Returns up to 10 tokens sorted by 24h volume.
    Results are cached for 60 seconds.
    """
    global _cache_ts, _cache_data

    now = time.time()
    if not force and now - _cache_ts < _CACHE_TTL and _cache_data:
        return _cache_data

    tokens: list[dict[str, Any]] = []

    for url in _SEARCH_URLS:
        try:
            data = _get_json(url)
            tokens = _parse_pairs_response(data)
        except Exception:
            tokens = []
        if tokens:
            break

    if not tokens:
        for url in (_LATEST_BOOST_URL, _BOOST_URL):
            try:
                data = _get_json(url)
                tokens = _parse_boost_response(data)
            except Exception:
                tokens = []
            if tokens:
                break

    # If still nothing, return cached data or empty
    if not tokens:
        return _cache_data  # return stale cache if available

    # Filter: only tokens with parseable non-zero price
    tokens = [t for t in tokens if t.get("price_usd", 0) > 0]
    if not tokens:
        return _cache_data

    # Sort by volume_24h descending, take top 10
    tokens.sort(key=lambda t: t.get("volume_24h", 0), reverse=True)
    tokens = tokens[:10]

    _cache_ts = now
    _cache_data = tokens
    return tokens
