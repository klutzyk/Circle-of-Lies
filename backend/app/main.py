from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_game import router as game_router
from app.db.database import init_db


def create_app() -> FastAPI:
    app = FastAPI(title="Circle of Lies API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    def startup_event() -> None:
        init_db()

    app.include_router(game_router)
    return app


app = create_app()
