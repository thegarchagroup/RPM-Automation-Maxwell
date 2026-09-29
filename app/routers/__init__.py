from app.routers.rpm import router as rpm_router
from app.routers.auth import router as auth_router
from app.routers.templates import router as templates_router
from app.routers.inspections import router as inspections_router
from app.routers.dropbox import router as dropbox_router

__all__ = [
    "rpm_router",
    "auth_router",
    "templates_router",
    "inspections_router",
    "dropbox_router",
]
