from aiogram import Dispatcher

from app.handlers.admin.panel import router as admin_router
from app.handlers.errors import router as errors_router
from app.handlers.user.browse import router as browse_router
from app.handlers.user.matches import router as matches_router
from app.handlers.user.menu import router as menu_router
from app.handlers.user.profile import router as profile_router
from app.handlers.user.settings import router as settings_router
from app.handlers.user.start import router as start_router


def include_routers(dp: Dispatcher) -> None:
    dp.include_router(start_router)
    dp.include_router(profile_router)
    dp.include_router(settings_router)
    dp.include_router(browse_router)
    dp.include_router(matches_router)
    dp.include_router(admin_router)
    dp.include_router(menu_router)
    dp.include_router(errors_router)
