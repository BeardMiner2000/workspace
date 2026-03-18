from decimal import Decimal
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .config import DEFAULT_SEASON_ID
from .db import get_conn
from .engine import mark_to_market, submit_order
from .season import reset_season

app = FastAPI(title='Paper Trader League Trade Engine')


class OrderRequest(BaseModel):
    season_id: str = DEFAULT_SEASON_ID
    bot_id: str
    symbol: str
    side: str
    order_type: str = 'market'
    quantity: float = Field(gt=0)
    price: float | None = Field(default=None, gt=0)
    rationale: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class BootstrapRequest(BaseModel):
    season_id: str = DEFAULT_SEASON_ID
    starting_btc: float = Field(default=0.05, gt=0)


class MarkRequest(BaseModel):
    season_id: str = DEFAULT_SEASON_ID
    marks: dict[str, float]


@app.get('/health')
def health():
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT 1 AS ok')
                cur.fetchone()
        return {'ok': True, 'service': 'trade_engine'}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post('/season/bootstrap')
def bootstrap_season(payload: BootstrapRequest):
    return reset_season(payload.season_id, Decimal(str(payload.starting_btc)))


@app.post('/orders')
def create_order(order: OrderRequest):
    try:
        return submit_order(
            season_id=order.season_id,
            bot_id=order.bot_id,
            symbol=order.symbol,
            side=order.side,
            order_type=order.order_type,
            quantity=Decimal(str(order.quantity)),
            price=Decimal(str(order.price)) if order.price is not None else None,
            rationale=order.rationale,
            metadata=order.metadata,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post('/marks')
def update_marks(payload: MarkRequest):
    if not payload.marks:
        raise HTTPException(status_code=400, detail='marks payload cannot be empty')
    try:
        decimal_marks = {symbol.upper(): Decimal(str(price)) for symbol, price in payload.marks.items()}
        return mark_to_market(payload.season_id, decimal_marks)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8088)
