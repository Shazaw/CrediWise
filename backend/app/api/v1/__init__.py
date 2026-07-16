"""Versioned API router aggregation (PLAN §12.1 — base `/api/v1`)."""

from fastapi import APIRouter

from app.api.v1 import auth, documents, me

router = APIRouter(prefix="/api/v1")
router.include_router(auth.router)
router.include_router(me.router)
router.include_router(documents.router)
