from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import analyses, auth, payments
from app.core.config import settings
from app.core.logging import setup_logging

setup_logging()

app = FastAPI(title=settings.app_name, version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(analyses.router)
app.include_router(payments.router)


@app.get("/api/health", tags=["misc"])
async def health() -> dict:
    return {"status": "ok", "env": settings.env}
