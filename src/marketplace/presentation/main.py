"""Alternative direct entry point to run the application."""

from __future__ import annotations

import uvicorn

from marketplace.infrastructure.config import API_HOST, API_PORT


def main() -> None:
    """Start the marketplace API server."""
    print(f"Starting marketplace API on {API_HOST}:{API_PORT}")
    print(f"Documentation available at http://{API_HOST}:{API_PORT}/docs")

    uvicorn.run(
        "marketplace.presentation.fastapi.main:app",
        host=API_HOST,
        port=API_PORT,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()
