from fastapi import APIRouter

from api.v1.routes import router as v1_router

router = APIRouter(prefix="/api")  # 版本前缀
router.include_router(v1_router)