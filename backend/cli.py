"""CLI entry point for the Evaluator backend."""

from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="auslex-ui",
        description="Start the AusLawExam-Bench Evaluator web UI.",
    )
    parser.add_argument("--port", type=int, default=8000, help="Port to serve on (default: 8000)")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload (development)")
    args = parser.parse_args(argv)

    import os
    os.environ.setdefault("AUSLEX_UI_PORT", str(args.port))

    import uvicorn
    uvicorn.run(
        "backend.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
