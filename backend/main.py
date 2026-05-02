"""Valuation Platform API — FastAPI entry point."""
import os

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI
from supabase import Client, create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

app = FastAPI(title="Valuation Platform API")

# Instantiated once at startup so it's ready for table queries later.
# `None` if env vars are missing — /db-health surfaces that as a clear error.
supabase: Client | None = (
    create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
    if SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY
    else None
)


@app.get("/health")
def health():
    return {"status": "ok", "service": "valuation-platform-api"}


@app.get("/db-health")
def db_health():
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        return {
            "status": "error",
            "detail": "Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY in backend/.env",
        }
    try:
        resp = httpx.get(
            f"{SUPABASE_URL}/rest/v1/",
            headers={
                "apikey": SUPABASE_SERVICE_ROLE_KEY,
                "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
            },
            timeout=5.0,
        )
        if resp.status_code == 200:
            return {"status": "ok", "database": "connected"}
        return {
            "status": "error",
            "database": "unexpected_response",
            "http_status": resp.status_code,
        }
    except httpx.RequestError as e:
        return {
            "status": "error",
            "database": "connection_failed",
            "detail": str(e),
        }
