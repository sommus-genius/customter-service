from langchain_openai import ChatOpenAI
from langchain_core.language_models import BaseChatModel

from src.conf.config import settings


print(settings)
"""
如果没有BaseChatModel，可能需要每次都写一套配置
"""

llm: BaseChatModel = ChatOpenAI(
    model=settings.llm_model,
    base_url=settings.llm_base_url,
    api_key=settings.llm_api_key,
    temperature = 0.6
)

if __name__ == '__main__':
    print(llm.invoke("你好").content)
