"""FastAPI application for the AusLawExam-Bench Evaluator."""

from __future__ import annotations

import argparse
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .api import router
from .config import get_config

app = FastAPI(
    title="AusLawExam-Bench Evaluator",
    description="Web UI for running and inspecting the AusLawExam-Bench benchmark.",
    version="0.1.0",
)

# CORS: same-origin by default (frontend mounted at /).
# When exposing on a network, add allow_origins or use auth.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

app.include_router(router)

# Mount the web client.  A local build in frontend/dist wins, and otherwise the
# built copy that ships with the package is served, so Node.js is not needed.
from pathlib import Path

import auslex.publish

FRONTEND_DIST = Path(__file__).resolve().parents[1] / "frontend" / "dist"
PACKAGED_CLIENT = Path(auslex.publish.__file__).resolve().parent / "assets"
CLIENT_DIR = FRONTEND_DIST if FRONTEND_DIST.exists() else PACKAGED_CLIENT
if CLIENT_DIR.exists():
    app.mount("/", StaticFiles(directory=str(CLIENT_DIR), html=True), name="frontend")


def main() -> None:
    import uvicorn

    parser = argparse.ArgumentParser(description="Run the AusLawExam-Bench UI server.")
    parser.add_argument("--host", default="127.0.0.1", help="Bind address (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=None, help="Port (default: AUSLEX_UI_PORT or 8000)")
    args = parser.parse_args()

    cfg = get_config()
    port = int(os.environ.get("AUSLEX_UI_PORT", args.port or cfg.get("port", 8000)))
    uvicorn.run("backend.app:app", host=args.host, port=port, reload=False)


if __name__ == "__main__":
    main()
