"""
@FileName：database.py
@Description：
@Author：baojun.wang
@Time：2025/10/27 13:45
"""
import asyncio
import os
from contextlib import asynccontextmanager, contextmanager
from threading import local

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

from utils.custom_logging import logger

load_dotenv()

DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "root1234")
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME", "mobile_vision")

SYNC_DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
ASYNC_DATABASE_URL = f"mysql+aiomysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

SYNC_ENGINE = create_engine(SYNC_DATABASE_URL,
                            pool_size=100,
                            max_overflow=200,
                            pool_pre_ping=True,
                            pool_recycle=3600,
                            echo=False
                            )
SYNC_SESSION = sessionmaker(bind=SYNC_ENGINE,
                            autocommit=False,
                            autoflush=True,
                            expire_on_commit=False
                            )

ASYNC_ENGINE = create_async_engine(ASYNC_DATABASE_URL,
                                   pool_size=20,
                                   max_overflow=10,
                                   pool_pre_ping=True,
                                   pool_recycle=1800,
                                   echo=False
                                   )
ASYNC_SESSION = async_sessionmaker(bind=ASYNC_ENGINE,
                                   class_=AsyncSession,
                                   expire_on_commit=False,
                                   autocommit=False,
                                   autoflush=False
                                   )


@contextmanager
def _get_db_session() -> Session:
    """内部使用的同步数据库会话上下文管理器"""
    session = SYNC_SESSION()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        raise
    finally:
        session.close()


def get_sync_db() -> Session:
    """供 FastAPI 依赖注入的同步会话生成器"""
    with _get_db_session() as session:
        yield session


@asynccontextmanager
async def _async_db_context() -> AsyncSession:
    """异步数据库会话上下文管理器"""
    async with ASYNC_SESSION() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            raise


async def get_async_db() -> AsyncSession:
    """供 FastAPI 依赖注入的异步会话生成器"""
    async with _async_db_context() as session:
        yield session


thread_local = local()


def get_engine():
    """获取当前线程的引擎"""
    if not hasattr(thread_local, 'engine'):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        engine = create_engine(
            SYNC_DATABASE_URL,
            pool_size=20,
            max_overflow=5,
            pool_recycle=1800,
            pool_pre_ping=True
        )

        thread_local.engine = engine
        thread_local.loop = loop

    return thread_local.engine


def get_session_factory():
    """获取当前线程的会话工厂"""
    engine = get_engine()

    if not hasattr(thread_local, 'session_factory'):
        thread_local.session_factory = sessionmaker(
            engine,
            class_=Session,
            expire_on_commit=False
        )

    return thread_local.session_factory


@asynccontextmanager
async def get_db_for_multithreading():
    """提供当前线程的数据库会话"""
    session_factory = get_session_factory()

    with session_factory() as session:
        try:
            logger.debug(f"会话开始 - ID: {id(session)}")
            yield session
            session.commit()
        except Exception as e:
            logger.warning(f"会话回滚 - 错误: {str(e)}")
            session.rollback()
            raise
        finally:
            logger.debug(f"会话关闭 - ID: {id(session)}")
            session.close()


Base = declarative_base()
