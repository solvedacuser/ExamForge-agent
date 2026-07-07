from langchain_openai import OpenAIEmbeddings

from app.core.config import get_settings


def get_embedding_model() -> OpenAIEmbeddings:
    settings = get_settings()
    return OpenAIEmbeddings(
        model=settings.embedding_model,
        api_key=settings.openai_api_key,
    )


def embed_documents(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    return get_embedding_model().embed_documents(texts)


def embed_query(text: str) -> list[float]:
    return get_embedding_model().embed_query(text)
