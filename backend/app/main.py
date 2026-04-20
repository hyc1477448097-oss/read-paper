from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db.postgres import engine, Base
from app.db.milvus import init_milvus, close_milvus
from app.db.redis import init_redis, close_redis
from app.api.papers import router as papers_router
from app.api.ai import router as ai_router
from app.api.analysis import router as analysis_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- startup ---
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    init_milvus()
    await init_redis()
    yield
    # --- shutdown ---
    await engine.dispose()
    close_milvus()
    await close_redis()


app = FastAPI(
    title="ReadMei API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(papers_router, prefix="/api/papers", tags=["papers"])
app.include_router(ai_router, prefix="/api/papers", tags=["ai"])
app.include_router(analysis_router, prefix="/api/papers", tags=["analysis"])


@app.get("/api/health")
async def health():
    return {"status": "ok"}
