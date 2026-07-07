from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Lecture Exam Coach Agent"
    app_version: str = "0.1.0"
    environment: str = "local"

    port: int = 3000
    openai_api_key: str | None = None
    openai_chat_model: str = "gpt-4o-mini"
    llm_temperature: float = 0.2
    langchain_api_key: str | None = None
    langchain_tracing_v2: bool = False
    langchain_project: str = "lecture-exam-coach-agent"

    pdf_dir: str = "data/pdfs"
    vector_store_path: str = "data/vector_store/index.json"
    embedding_model: str = "text-embedding-3-small"
    rag_chunk_size: int = 1000
    rag_chunk_overlap: int = 150
    rag_top_k: int = 4

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
