"""FlowMind AI FastAPI application entrypoint."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api import automation, chat, documents, evaluation, search, stats
from app.core.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="FlowMind AI",
    description="Personal Knowledge & Automation Assistant (RAG + local LLM).",
    version=__version__,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    # Allow any localhost port so the Vite dev server works regardless of the port.
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documents.router)
app.include_router(search.router)
app.include_router(chat.router)
app.include_router(stats.router)
app.include_router(evaluation.router)
app.include_router(automation.router)


@app.get("/")
def root():
    return {"name": "FlowMind AI", "version": __version__, "docs": "/docs"}
