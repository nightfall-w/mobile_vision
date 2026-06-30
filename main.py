"""
@FileName：main.py
@Description：
@Author：baojun.wang
@Time：2026/4/16 12:35
"""
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from starlette.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles

from api import router as api_router
from core.config import REPORT_URL, MEDIA_ROOT, PROJECT_ROOT
from core.exception import unified_exception_handler

# 尝试导入 Redis，如果失败则忽略
try:
    from core.redis import redis_cache
    REDIS_AVAILABLE = True
except Exception as e:
    print(f"Redis 不可用: {e}")
    REDIS_AVAILABLE = False


# 定义生命周期事件处理器
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时执行（替代 startup 事件）
    if REDIS_AVAILABLE:
        try:
            redis_cache.init_pool()
            print("Redis 连接池初始化成功")
        except Exception as e:
            print(f"Redis 连接池初始化失败: {e}")

    yield  # 程序运行期间会停在这里
    # 关闭时执行（替代 shutdown 事件）
    if REDIS_AVAILABLE and hasattr(redis_cache, 'pool') and redis_cache.pool:
        redis_cache.pool.disconnect()
        print("Redis 连接池已关闭")


app = FastAPI(lifespan=lifespan)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有HTTP方法
    allow_headers=["*"],  # 允许所有请求头
    expose_headers=["new_token"],  # 暴露 new_token 响应头
)

# 注册异常处理器：
# 1. 处理参数验证错误（RequestValidationError）
app.add_exception_handler(RequestValidationError, unified_exception_handler)
# 3. 处理所有其他未捕获的异常（Exception 基类）
app.add_exception_handler(Exception, unified_exception_handler)

# 挂载路由
app.include_router(api_router)
# 挂载静态目录：将 /media 路由映射到本地 media 文件夹
# 第一个参数是路由前缀，directory 是本地静态文件目录（相对/绝对路径均可）
app.mount(
    REPORT_URL,  # 访问前缀：http://localhost:8000/media/xxx.png
    StaticFiles(directory=MEDIA_ROOT),  # 本地静态文件目录
    name="media"  # 路由名称（可选，用于反向生成URL）
)

# 挂载 YOLO 输出目录
YOLO_OUTPUT_ROOT = PROJECT_ROOT / 'models' / 'yolo' / 'output'
YOLO_OUTPUT_ROOT.mkdir(exist_ok=True)
app.mount(
    '/yolo_output',  # 访问前缀
    StaticFiles(directory=str(YOLO_OUTPUT_ROOT)),
    name='yolo_output'
)


@app.middleware("http")
async def add_new_token_header(request: Request, call_next):
    """中间件：在响应头中添加 new_token"""
    response = await call_next(request)

    # 如果在请求处理过程中生成了 new_token，则添加到响应头
    if hasattr(request.state, 'new_token') and request.state.new_token:
        print("new_token", request.state.new_token)
        response.headers["new_token"] = request.state.new_token

    return response


# 启动服务
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080, reload=False)
