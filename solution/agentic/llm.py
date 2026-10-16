"""Factory helpers for chat and embedding models."""
from functools import lru_cache

from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from agentic.config import CHAT_MODEL, EMBEDDING_MODEL


@lru_cache(maxsize=None)
def get_llm(temperature: float = 0.0) -> ChatOpenAI:
    return ChatOpenAI(model=CHAT_MODEL, temperature=temperature)


@lru_cache(maxsize=None)
def get_embeddings() -> OpenAIEmbeddings:
    return OpenAIEmbeddings(model=EMBEDDING_MODEL)
