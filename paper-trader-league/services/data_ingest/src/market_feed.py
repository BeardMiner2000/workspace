"""
Real market data feed via Coinbase Advanced Trade API.

Unauthenticated: public spot ticker prices (no key needed).
Authenticated (CB_API_KEY + CB_API_SECRET set): signed requests for
  deeper data — order book, candles, account products, etc.

Coinbase CDP keys use ES256 JWT signing.
Symbol mapping: internal XYZUSDT <-> Coinbase XYZ-USD
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
import uuid
from typing import Any

# ── symbol mapping ────────────────────────────────────────────────────────────
SYMBOL_MAP: dict[str, str] = {
    "BTCUSDT":  "BTC-USD",
    "ETHUSDT":  "ETH-USD",
    "SOLUSDT":  "SOL-USD",
    "DOGEUSDT": "DOGE-USD",
}

COINBASE_ADV_BASE = "https://api.coinbase.com"
COINBASE_EX_BASE  = "https://api.exchange.coinbase.com"   # public fallback

_HEADERS = {
    "User-Agent": "paper-trader-league/1.0",
    "Accept":     "application/json",
    "Content-Type": "application/json",
}


# ── JWT auth ──────────────────────────────────────────────────────────────────
def _build_jwt(api_key: str, private_key_pem: str, method: str, path: str) -> str:
    """Build a Coinbase CDP ES256 JWT for the given request."""
    import jwt  # PyJWT[crypto]
    from cryptography.hazmat.primitives.serialization import load_pem_private_key

    # Normalise escaped newlines that may come from .env
    pem = private_key_pem.replace("\\n", "\n").encode()
    private_key = load_pem_private_key(pem, password=None)

    uri = f"{method} {COINBASE_ADV_BASE.replace('https://', '')}{path}"
    payload = {
        "sub":  api_key,
        "iss":  "cdp",
        "nbf":  int(time.time()),
        "exp":  int(time.time()) + 120,
        "uri":  uri,
    }
    return jwt.encode(
        payload,
        private_key,
        algorithm="ES256",
        headers={"kid": api_key, "nonce": uuid.uuid4().hex},
    )


def _get_authed(path: str, api_key: str, private_key_pem: str, timeout: float = 8.0) -> dict:
    token = _build_jwt(api_key, private_key_pem, "GET", path)
    headers = {**_HEADERS, "Authorization": f"Bearer {token}"}
    req = urllib.request.Request(f"{COINBASE_ADV_BASE}{path}", headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _get_public(url: str, timeout: float = 8.0) -> dict:
    req = urllib.request.Request(url, headers=_HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


# ── price fetching ────────────────────────────────────────────────────────────
def _fetch_via_advanced_trade(cb_sym: str, api_key: str, private_key_pem: str) -> float:
    """Fetch best bid/ask midpoint via authenticated Advanced Trade API."""
    path = f"/api/v3/brokerage/market/products/{cb_sym}"
    data = _get_authed(path, api_key, private_key_pem)
    price = data.get("price") or data.get("best_bid") or data.get("best_ask")
    if price is None:
        raise RuntimeError(f"No price field in response for {cb_sym}: {list(data.keys())}")
    return float(price)


def _fetch_via_public_exchange(cb_sym: str) -> float:
    """Unauthenticated fallback via Coinbase Exchange public REST."""
    data = _get_public(f"{COINBASE_EX_BASE}/products/{cb_sym}/ticker")
    return float(data["price"])


def fetch_coinbase_prices(
    symbols: list[str],
    api_key: str | None = None,
    private_key_pem: str | None = None,
) -> dict[str, float]:
    """
    Fetch current spot prices from Coinbase.
    Uses authenticated Advanced Trade API when credentials are available,
    otherwise falls back to the unauthenticated Exchange public endpoint.
    Returns {internal_symbol: price_float}.
    """
    use_auth = bool(api_key and private_key_pem)
    prices: dict[str, float] = {}
    errors: list[str] = []

    for internal_sym in symbols:
        cb_sym = SYMBOL_MAP.get(internal_sym)
        if not cb_sym:
            errors.append(f"No Coinbase mapping for {internal_sym}")
            continue
        try:
            if use_auth:
                price = _fetch_via_advanced_trade(cb_sym, api_key, private_key_pem)
            else:
                price = _fetch_via_public_exchange(cb_sym)
            prices[internal_sym] = price
        except Exception as exc:
            # Try public fallback if auth fails
            if use_auth:
                try:
                    price = _fetch_via_public_exchange(cb_sym)
                    prices[internal_sym] = price
                    continue
                except Exception:
                    pass
            errors.append(f"{internal_sym} ({cb_sym}): {exc}")

    if errors:
        raise RuntimeError("Coinbase fetch errors: " + "; ".join(errors))

    return prices


def fetch_coinbase_prices_safe(
    symbols: list[str],
    api_key: str | None = None,
    private_key_pem: str | None = None,
    fallback: dict[str, float] | None = None,
    log_fn=None,
) -> dict[str, float] | None:
    """Safe wrapper — returns fallback (or None) instead of raising."""
    # Read from env if not passed directly
    if api_key is None:
        api_key = os.getenv("CB_API_KEY") or None
    if private_key_pem is None:
        private_key_pem = os.getenv("CB_API_SECRET") or None

    try:
        return fetch_coinbase_prices(symbols, api_key=api_key, private_key_pem=private_key_pem)
    except Exception as exc:
        msg = f"[market_feed] Coinbase fetch failed: {exc}"
        if log_fn:
            log_fn(msg)
        else:
            print(msg, flush=True)
        return fallback
