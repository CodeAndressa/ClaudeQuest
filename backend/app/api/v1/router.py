from fastapi import APIRouter

from app.api.v1 import health
from app.domains.auth.router import router as auth_router
from app.domains.dashboard.router import router as dashboard_router
from app.domains.gamification.badges import badges_router
from app.domains.gamification.certificates import router as certificates_router
from app.domains.gamification.ranking import router as ranking_router
from app.domains.gamification.router import router as gamification_router
from app.domains.learning.router import router as learning_router

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(health.router)
api_v1_router.include_router(auth_router)
api_v1_router.include_router(dashboard_router)
api_v1_router.include_router(gamification_router)
api_v1_router.include_router(certificates_router)
api_v1_router.include_router(badges_router)
api_v1_router.include_router(ranking_router)
api_v1_router.include_router(learning_router)
