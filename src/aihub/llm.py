"""LLM factory (Module 3: LangChain + LLM providers). Swap provider here only."""
from .config import Settings
from .errors import ConfigError


def build_llm(settings: Settings, temperature: float = 0.0):
    if not settings.groq_api_key:
        raise ConfigError("GROQ_API_KEY is not set. Copy .env.example to .env and add your key.")
    from langchain_groq import ChatGroq

    return ChatGroq(
        model=settings.llm_model,
        api_key=settings.groq_api_key,
        temperature=temperature,
        max_retries=2,
        timeout=60,
    )


def text_of(message) -> str:
    """Normalise an LLM response (AIMessage or str) to plain text."""
    return (getattr(message, "content", message) or "").strip()
