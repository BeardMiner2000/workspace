from fastapi import FastAPI
import uvicorn

app = FastAPI(title="Paper Trader League Scoring API")


@app.get("/health")
def health():
    return {"ok": True, "service": "scoring_api"}


@app.get("/leaderboard")
def leaderboard():
    return {
        "season": "draft",
        "message": "Stub only; database-backed scoring not implemented yet.",
        "bots": [],
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8090)
