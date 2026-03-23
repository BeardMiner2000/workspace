"""
Real market data feed via Coinbase Advanced Trade API.

Provides price, candle, order-book, and best-bid/ask helpers with
automatic fallback to Coinbase Exchange public REST when authenticated
Advanced Trade credentials are unavailable.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone
from typing import Any, Iterable

COINBASE_ADV_BASE = "https://api.coinbase.com"
COINBASE_EX_BASE = "https://api.exchange.coinbase.com"   # public fallback

_HEADERS = {
    "User-Agent": "paper-trader-league/1.0",
    "Accept": "application/json",
    "Content-Type": "application/json",
}

_GRANULARITY_SECONDS = {
    "ONE_MINUTE": 60,
    "FIVE_MINUTE": 300,
    "FIFTEEN_MINUTE": 900,
    "ONE_HOUR": 3600,
}

_GRANULARITY_ALIASES = {
    "1M": "ONE_MINUTE",
    "1MIN": "ONE_MINUTE",
    "ONE_MIN": "ONE_MINUTE",
    "5M": "FIVE_MINUTE",
    "5MIN": "FIVE_MINUTE",
    "15M": "FIFTEEN_MINUTE",
    "15MIN": "FIFTEEN_MINUTE",
    "1H": "ONE_HOUR",
    "60M": "ONE_HOUR",
}


# ── JWT auth ──────────────────────────────────────────────────────────────────
def _build_jwt(api_key: str, private_key_pem: str, method: str, path: str) -> str:
    """Build a Coinbase CDP ES256 JWT for the given request."""
    import jwt  # PyJWT[crypto]
    from cryptography.hazmat.primitives.serialization import load_pem_private_key

    pem = private_key_pem.replace("\\n", "\n").encode()
    private_key = load_pem_private_key(pem, password=None)

    uri = f"{method} {COINBASE_ADV_BASE.replace('https://', '')}{path}"
    payload = {
        "sub": api_key,
        "iss": "cdp",
        "nbf": int(time.time()),
        "exp": int(time.time()) + 120,
        "uri": uri,
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


# ── symbol mapping ────────────────────────────────────────────────────────────
_DEFAULT_SYMBOL_MAP: dict[str, str] = {
    "BTCUSDT":   "BTC-USD",
    "ETHUSDT":   "ETH-USD",
    "SOLUSDT":   "SOL-USD",
    "DOGEUSDT":  "DOGE-USD",
    "SHIBUSDT":  "SHIB-USD",
    "PEPEUSDT":  "PEPE-USD",
    "WIFUSDT":   "WIF-USD",
    "BONKUSDT":  "BONK-USD",
    "FLOKIUSDT": "FLOKI-USD",
}


def _build_symbol_map() -> dict[str, str]:
    url = f"{COINBASE_EX_BASE}/products"
    try:
        data = _get_public(url)
    except Exception as exc:  # pragma: no cover - network failure
        print(
            f"[market_feed] failed to load Coinbase products ({exc}); using fallback symbols",
            flush=True,
        )
        return dict(_DEFAULT_SYMBOL_MAP)

    mapping: dict[str, str] = {}
    for product in data:
        quote = str(product.get("quote_currency", "")).upper()
        status = str(product.get("status", "")).lower()
        trading_disabled = bool(product.get("trading_disabled", False))
        if quote != "USD" or status != "online" or trading_disabled:
            continue
        product_id = product.get("id")
        base = str(product.get("base_currency", "")).upper()
        if not product_id or not base:
            continue
        internal_symbol = f"{base}USDT"
        mapping.setdefault(internal_symbol, product_id)

    if not mapping:
        print(
            "[market_feed] Coinbase products API returned no USD markets; using fallback symbols",
            flush=True,
        )
        return dict(_DEFAULT_SYMBOL_MAP)

    for symbol, product_id in _DEFAULT_SYMBOL_MAP.items():
        mapping.setdefault(symbol, product_id)

    print(
        f"[market_feed] loaded {len(mapping)} Coinbase USD products",
        flush=True,
    )
    return mapping


SYMBOL_MAP: dict[str, str] = _build_symbol_map()


def _ensure_list(value: str | Iterable[str]) -> list[str]:
    if isinstance(value, str):
        return [value]
    return list(value)


def _load_api_creds(api_key: str | None, private_key_pem: str | None) -> tuple[str | None, str | None]:
    return (
        api_key or os.getenv("CB_API_KEY") or None,
        private_key_pem or os.getenv("CB_API_SECRET") or None,
    )


def _resolve_granularity(granularity: str) -> tuple[str, int]:
    key = granularity.upper()
    if key in _GRANULARITY_SECONDS:
        return key, _GRANULARITY_SECONDS[key]
    alias = _GRANULARITY_ALIASES.get(key)
    if alias and alias in _GRANULARITY_SECONDS:
        return alias, _GRANULARITY_SECONDS[alias]
    raise ValueError(f"Unsupported granularity: {granularity}")


def _parse_time(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    try:
        return int(datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp())
    except Exception:
        return 0


def _normalize_adv_trade_candles(data: dict | list) -> list[dict[str, float]]:
    raw = data.get("candles", data) if isinstance(data, dict) else data
    normalized: list[dict[str, float]] = []
    for entry in raw:
        normalized.append(
            {
                "start": _parse_time(entry.get("start") or entry.get("start_time")),
                "open": float(entry.get("open")),
                "high": float(entry.get("high")),
                "low": float(entry.get("low")),
                "close": float(entry.get("close")),
                "volume": float(entry.get("volume")),
            }
        )
    return normalized


def _normalize_exchange_candles(rows: list[list[float]]) -> list[dict[str, float]]:
    normalized: list[dict[str, float]] = []
    for row in rows:
        # Coinbase Exchange returns [time, low, high, open, close, volume]
        ts, low, high, open_px, close_px, volume = row
        normalized.append(
            {
                "start": int(ts),
                "open": float(open_px),
                "high": float(high),
                "low": float(low),
                "close": float(close_px),
                "volume": float(volume),
            }
        )
    return normalized


def _normalize_book_levels(levels: Iterable[Any]) -> list[dict[str, float]]:
    normalized = []
    for level in levels:
        if isinstance(level, dict):
            price = float(level.get("price"))
            size = float(level.get("size")) if "size" in level else float(level.get("quantity", 0))
        else:
            price = float(level[0])
            size = float(level[1])
        normalized.append({"price": price, "size": size})
    return normalized


def fetch_coinbase_candles(
    product_id: str,
    granularity: str = "ONE_MINUTE",
    *,
    start: str | None = None,
    end: str | None = None,
    api_key: str | None = None,
    private_key_pem: str | None = None,
) -> list[dict[str, float]]:
    """Fetch OHLCV candles from Coinbase. Returns newest-to-oldest list."""
    api_key, private_key_pem = _load_api_creds(api_key, private_key_pem)
    granularity_key, seconds = _resolve_granularity(granularity)
    params = {"granularity": granularity_key}
    if start:
        params["start"] = start
    if end:
        params["end"] = end
    query = urllib.parse.urlencode(params)

    if api_key and private_key_pem:
        path = f"/api/v3/brokerage/market/products/{product_id}/candles?{query}"
        data = _get_authed(path, api_key, private_key_pem)
        return _normalize_adv_trade_candles(data)

    # Fallback to public Exchange REST which uses seconds for granularity
    url = f"{COINBASE_EX_BASE}/products/{product_id}/candles?granularity={seconds}"
    if start:
        url += f"&start={urllib.parse.quote(start)}"
    if end:
        url += f"&end={urllib.parse.quote(end)}"
    rows = _get_public(url)
    return _normalize_exchange_candles(rows)


def fetch_coinbase_orderbook(
    product_id: str,
    depth: int = 20,
    *,
    api_key: str | None = None,
    private_key_pem: str | None = None,
) -> dict[str, list[dict[str, float]]]:
    """Fetch order book (bids/asks) up to the requested depth."""
    api_key, private_key_pem = _load_api_creds(api_key, private_key_pem)
    limit = max(1, min(depth, 100))

    # Try public Exchange REST first (no auth required, reliable)
    try:
        url = f"{COINBASE_EX_BASE}/products/{product_id}/book?level=2"
        data = _get_public(url)
        return {
            "bids": _normalize_book_levels(data.get("bids", [])[:limit]),
            "asks": _normalize_book_levels(data.get("asks", [])[:limit]),
        }
    except Exception:
        pass

    # Fallback to authenticated Advanced Trade API
    if api_key and private_key_pem:
        try:
            path = f"/api/v3/brokerage/market/products/{product_id}/book?limit={limit}"
            data = _get_authed(path, api_key, private_key_pem)
            book = data.get("pricebook", data)
            return {
                "bids": _normalize_book_levels(book.get("bids", [])[:limit]),
                "asks": _normalize_book_levels(book.get("asks", [])[:limit]),
            }
        except Exception:
            pass

    return {"bids": [], "asks": []}


def fetch_coinbase_best_bid_ask(
    product_ids: str | Iterable[str],
    *,
    api_key: str | None = None,
    private_key_pem: str | None = None,
) -> dict[str, dict[str, float]]:
    """Fetch best bid/ask snapshots for one or more product_ids."""
    ids = _ensure_list(product_ids)
    api_key, private_key_pem = _load_api_creds(api_key, private_key_pem)

    result: dict[str, dict[str, float]] = {}
    if api_key and private_key_pem:
        # Fetch each product individually via the product ticker endpoint (most reliable)
        for pid in ids:
            try:
                path = f"/api/v3/brokerage/market/products/{pid}"
                data = _get_authed(path, api_key, private_key_pem)
                bid = float(data.get("best_bid") or data.get("price") or 0)
                ask = float(data.get("best_ask") or data.get("price") or 0)
                if bid > 0:
                    result[pid] = {
                        "best_bid": bid,
                        "best_ask": ask if ask > 0 else bid,
                        "bid_size": float(data.get("best_bid_size", 0) or 0),
                        "ask_size": float(data.get("best_ask_size", 0) or 0),
                    }
            except Exception:
                pass
        missing = [pid for pid in ids if pid not in result]
    else:
        missing = ids

    for pid in missing:
        url = f"{COINBASE_EX_BASE}/products/{pid}/ticker"
        try:
            data = _get_public(url)
        except Exception:
            continue
        result[pid] = {
            "best_bid": float(data.get("bid", data.get("best_bid", data.get("price", 0)))),
            "best_ask": float(data.get("ask", data.get("best_ask", data.get("price", 0)))),
            "bid_size": float(data.get("bid_size", 0)),
            "ask_size": float(data.get("ask_size", 0)),
        }
    return result


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


def _extract_base_currency(symbol: str) -> str | None:
    cb_sym = SYMBOL_MAP.get(symbol)
    if not cb_sym:
        return None
    return cb_sym.split('-', 1)[0].upper()


def _fetch_usd_exchange_rates() -> dict[str, float]:
    url = f"{COINBASE_ADV_BASE}/v2/exchange-rates?currency=USD"
    data = _get_public(url)
    rates = data.get('data', {}).get('rates', {}) if isinstance(data, dict) else {}
    inverted: dict[str, float] = {}
    for currency, raw_value in rates.items():
        try:
            value = float(raw_value)
        except (TypeError, ValueError):
            continue
        if value <= 0:
            continue
        inverted[currency.upper()] = 1.0 / value
    if not inverted:
        raise RuntimeError('no USD exchange rates returned')
    return inverted


def _fetch_prices_via_exchange_rates(symbols: Iterable[str]) -> dict[str, float]:
    rates = _fetch_usd_exchange_rates()
    prices: dict[str, float] = {}
    for symbol in symbols:
        base = _extract_base_currency(symbol)
        if not base:
            continue
        price = rates.get(base)
        if price:
            prices[symbol] = price
    return prices


def fetch_coinbase_prices(
    symbols: list[str],
    api_key: str | None = None,
    private_key_pem: str | None = None,
) -> dict[str, float]:
    """Fetch current spot prices from Coinbase."""
    api_key, private_key_pem = _load_api_creds(api_key, private_key_pem)
    use_auth = bool(api_key and private_key_pem)
    prices: dict[str, float] = {}
    errors: list[str] = []
    normalized: list[str] = []
    seen: set[str] = set()

    for internal_sym in symbols:
        cb_sym = SYMBOL_MAP.get(internal_sym)
        if not cb_sym:
            errors.append(f"No Coinbase mapping for {internal_sym}")
            continue
        if internal_sym not in seen:
            normalized.append(internal_sym)
            seen.add(internal_sym)

    remaining = list(normalized)

    if use_auth and remaining:
        still_missing: list[str] = []
        for internal_sym in remaining:
            cb_sym = SYMBOL_MAP[internal_sym]
            try:
                prices[internal_sym] = _fetch_via_advanced_trade(cb_sym, api_key, private_key_pem)
            except Exception:
                still_missing.append(internal_sym)
        remaining = still_missing

    exchange_rate_error: str | None = None
    if remaining:
        try:
            bulk_prices = _fetch_prices_via_exchange_rates(remaining)
            prices.update(bulk_prices)
        except Exception as exc:
            exchange_rate_error = f"exchange-rates fetch failed: {exc}"
        remaining = [sym for sym in remaining if sym not in prices]

    if remaining:
        still_missing: list[str] = []
        for internal_sym in remaining:
            cb_sym = SYMBOL_MAP.get(internal_sym)
            if not cb_sym:
                continue
            try:
                prices[internal_sym] = _fetch_via_public_exchange(cb_sym)
            except Exception as exc:
                errors.append(f"{internal_sym} ({cb_sym}): {exc}")
                still_missing.append(internal_sym)
        remaining = still_missing

    if remaining:
        errors.extend(f"{sym}: no price available after fallbacks" for sym in remaining)

    if errors:
        message = "Coinbase fetch errors: " + "; ".join(errors)
        if exchange_rate_error:
            message += f" | {exchange_rate_error}"
        raise RuntimeError(message)

    return prices


def fetch_coinbase_prices_safe(
    symbols: list[str],
    api_key: str | None = None,
    private_key_pem: str | None = None,
    fallback: dict[str, float] | None = None,
    log_fn=None,
) -> dict[str, float] | None:
    """Safe wrapper — returns fallback (or None) instead of raising."""
    if api_key is None or private_key_pem is None:
        api_key, private_key_pem = _load_api_creds(api_key, private_key_pem)

    try:
        return fetch_coinbase_prices(symbols, api_key=api_key, private_key_pem=private_key_pem)
    except Exception as exc:
        msg = f"[market_feed] Coinbase fetch failed: {exc}"
        if log_fn:
            log_fn(msg)
        else:
            print(msg, flush=True)
        return fallback
