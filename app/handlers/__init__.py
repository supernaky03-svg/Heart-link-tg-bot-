from aiogram import Router

from app.handlers import admin, common, complaint, discover, onboarding, premium, profile


def setup_routers() -> Router:
    router = Router(name="root")
    router.include_router(common.router)
    router.include_router(onboarding.router)
    router.include_router(discover.router)
    router.include_router(profile.router)
    router.include_router(premium.router)
    router.include_router(complaint.router)
    router.include_router(admin.router)
    return router
