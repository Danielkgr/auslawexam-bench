"""FastAPI application for the AusLawExam-Bench Evaluator."""

from __future__ import annotations

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

# Mount the frontend build output if it exists.
import os
from pathlib import Path

FRONTEND_DIST = Path(__file__).resolve().parents[1] / "frontend" / "dist"
if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")


def main() -> None:
    import uvicorn
    cfg = get_config()
    port = int(os.environ.get("AUSLEX_UI_PORT", cfg.get("port", 8000)))
    uvicorn.run("backend.app:app", host="0.0.0.0", port=port, reload=False)


if __name__ == "__main__":
    main()
