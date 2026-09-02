from fastapi import APIRouter
from app.api.auth import router as auth_router
from app.api.articles import router as articles_router
from app.api.verification import router as verification_router
from app.api.admin import router as admin_router
from app.api.public import router as public_router

router = APIRouter()

# Public endpoint — no auth required — mounted FIRST to avoid any route ambiguity
router.include_router(public_router, prefix="/public", tags=["public"])

router.include_router(auth_router, prefix="/auth", tags=["auth"])
router.include_router(articles_router, prefix="/articles", tags=["articles"])
router.include_router(verification_router, prefix="/articles", tags=["verification"])
router.include_router(admin_router, prefix="/admin", tags=["admin"])
