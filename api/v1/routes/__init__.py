"""
@FileName：__init__.py.py
@Description：
@Author：baojun.wang
@Time：2026/4/16 12:38
"""
from fastapi import APIRouter
from api.v1.routes import dataset, annotation, train, model, device, workspace, user, llm, testcase, testtask, testplan, monitor

router = APIRouter(prefix="/v1")
router.include_router(dataset.router)
router.include_router(annotation.router)
router.include_router(train.router)
router.include_router(model.router)
router.include_router(device.router)
router.include_router(workspace.router)
router.include_router(user.router)
router.include_router(llm.router)
router.include_router(testcase.router)
router.include_router(testtask.router)
router.include_router(testplan.router)
router.include_router(monitor.router)


@router.get("/health")
async def health_check():
    """健康检查接口"""
    from core.response import api_response
    return api_response(data="ok")
