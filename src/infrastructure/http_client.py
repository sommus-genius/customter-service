import httpx
from httpx import AsyncClient
http_client :AsyncClient | None = None

# 初始化
def init_http_client():
    global http_client
    http_client = httpx.AsyncClient()

#关闭
async def close_http_client():
    if http_client is not None:
        await http_client.aclose()