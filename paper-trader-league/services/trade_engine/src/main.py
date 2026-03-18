from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="Paper Trader League Trade Engine")


class Order(BaseModel):
    bot_id: str
    symbol: str
    side: str
    order_type: str
    quantity: float
    price: float | None = None
    rationale: dict = {}


@app.get("/health")
def health():
    return {"ok": True, "service": "trade_engine"}


@app.post("/orders")
def submit_order(order: Order):
    return {
        "accepted": True,
        "message": "Stub only; matching/fees/slippage not implemented yet.",
        "order": order.model_dump(),
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8088)
