from __future__ import annotations

import json
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # DeepSeek
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    deepseek_llm_model: str = "deepseek-chat"
    deepseek_embed_model: str = "deepseek-embedding"

    # Baidu Translate (general VIP API)
    baidu_translate_appid: str = ""
    baidu_translate_appkey: str = ""
    baidu_translate_url: str = "https://fanyi-api.baidu.com/api/trans/vip/translate"
    baidu_translate_from: str = "auto"
    baidu_translate_to: str = "zh"
    # 百度对未认证/标准版常有 QPS 限制；54003 Invalid Access Limit 时需加大间隔
    baidu_translate_min_interval_sec: float = 1.05

    # PostgreSQL
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "readmei"
    postgres_password: str = "readmei123"
    postgres_db: str = "readmei"

    # Milvus
    milvus_host: str = "localhost"
    milvus_port: int = 19530

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0

    # RAG / 上下文答疑
    rag_top_k: int = 5

    # App
    upload_dir: str = "./uploads"
    cors_origins: str = '["http://localhost:3000","http://localhost:5173"]'

    @property
    def postgres_dsn(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @property
    def cors_origin_list(self) -> list[str]:
        return json.loads(self.cors_origins)

    @property
    def upload_path(self) -> Path:
        p = Path(self.upload_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p


settings = Settings()
