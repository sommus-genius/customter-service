
from fastapi import FastAPI
from pydantic_settings import BaseSettings

from pydantic_settings import SettingsConfigDict
from pathlib import Path
ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    #llm 相关
    llm_model: str = "glm-4.5-air"
    llm_base_url: str = "https://open.bigmodel.cn/api/paas/v4/"
    llm_api_key: str = "18928b4ca04c40939c78222397b322a0.TIvzB1AZgxkOL0KH"

    #电商API配置
    commerce_api_base_url: str = "http://127.0.0.1:18081"

    #数据库配置
    database_url: str

    #应用配置
    app_host: str = "127.0.0.1"
    app_port: int = 18082

    model_config = SettingsConfigDict(env_file=ENV_FILE, env_file_encoding="utf-8", extra="ignore")


settings = Settings()

if __name__=='main':
    print(settings.database_url)