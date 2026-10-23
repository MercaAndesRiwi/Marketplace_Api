"""FastAPI application entry point for marketplace."""

from fastapi import FastAPI

from marketplace.presentation.fastapi.routes import marketplace as marketplace_routes

app = FastAPI(
    title="Marketplace Events Producer (F4)",
    version="1.0.0",
    description="Generates marketplace order lifecycle events with fault injection.",
)

app.include_router(marketplace_routes.router)


@app.get("/", tags=["health"])
def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "api-marketplace", "version": "1.0.0"}
