"""Valuation Platform API — FastAPI entry point."""
from fastapi import FastAPI

app = FastAPI(title="Valuation Platform API")


@app.get("/health")
def health():
    return {"status": "ok", "service": "valuation-platform-api"}
