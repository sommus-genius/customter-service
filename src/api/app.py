from fastapi import FastAPI

from api.routes.chat_router import router
from infrastructure.database import init_db_engine, close_db_engine

from contextlib import asynccontextmanager

from infrastructure.http_client import init_http_client, close_http_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    通过app.state 可以存储一些全局共享资源
    :param app:
    :return:
    """
    # 初始化数据库引擎
    print("初始化数据库引擎")
    init_db_engine() #自带连接池
    print("数据库引擎初始化完成")

    # 初始化http_client
    init_http_client()
    print("http_client初始化完成")
    yield

    await close_db_engine()
    print("数据库连接已关闭")
    await close_http_client()
    print("http_client已关闭")
app = FastAPI(description="电商小二AI只能客服系统", lifespan=lifespan)
app.include_router(router)