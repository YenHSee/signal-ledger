import os
import json
import urllib.request
from dataclasses import dataclass
from enum import Enum


class ModelTier(Enum):
    SMART = "smart"     # Highest-quality model
    NORMAL = "normal"   # Cost-effective hosted model
    LOCAL = "local"     # Local model


@dataclass(frozen=True)
class ModelSpec:
    provider: str
    tier: ModelTier
    requested_model: str
    temperature: float = 0.1
    response_format: str = "json"


def get_model_spec(
    tier: ModelTier = ModelTier.NORMAL,
    temperature: float = 0.1,
) -> ModelSpec:
    if tier == ModelTier.SMART:
        return ModelSpec(
            provider="openai",
            tier=tier,
            requested_model=os.getenv("OPENAI_MODEL", "gpt-4o"),
            temperature=temperature,
        )
    if tier == ModelTier.NORMAL:
        return ModelSpec(
            provider="deepseek",
            tier=tier,
            requested_model=os.getenv("DEEPSEEK_MODEL", "deepseek-v4-pro"),
            temperature=temperature,
        )
    return ModelSpec(
        provider="ollama",
        tier=tier,
        requested_model=os.getenv("OLLAMA_MODEL", "qwen2.5:7b"),
        temperature=temperature,
    )


def get_llm(
    tier: ModelTier = ModelTier.NORMAL,
    temperature: float = 0.1,
    spec: ModelSpec | None = None,
):
    """Return the configured model for the requested tier."""
    spec = spec or get_model_spec(tier=tier, temperature=temperature)
    if spec.provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=spec.requested_model,
            api_key=os.getenv("OPENAI_API_KEY"),
            temperature=spec.temperature,
        )
    if spec.provider == "deepseek":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=spec.requested_model,
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url="https://api.deepseek.com",
            temperature=spec.temperature,
        )
    from langchain_ollama import ChatOllama
    return ChatOllama(
        model=spec.requested_model,
        temperature=spec.temperature,
        format="json",
    )


def preflight_model(spec: ModelSpec) -> str | None:
    """Verify the requested hosted model, or return the local Ollama digest."""
    if spec.provider in {"deepseek", "openai"}:
        from openai import OpenAI

        kwargs = {
            "api_key": os.getenv(
                "DEEPSEEK_API_KEY" if spec.provider == "deepseek" else "OPENAI_API_KEY"
            )
        }
        if spec.provider == "deepseek":
            kwargs["base_url"] = "https://api.deepseek.com"
        client = OpenAI(**kwargs)
        supported = {item.id for item in client.models.list().data}
        if spec.requested_model not in supported:
            raise RuntimeError(
                f"Requested {spec.provider} model {spec.requested_model!r} is not returned "
                "by the provider /models endpoint."
            )
        return None

    base_url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
    with urllib.request.urlopen(f"{base_url}/api/tags", timeout=10) as response:
        payload = json.load(response)
    for model in payload.get("models", []):
        if model.get("name") == spec.requested_model or model.get("model") == spec.requested_model:
            digest = model.get("digest")
            if not digest:
                raise RuntimeError(f"Ollama did not return a digest for {spec.requested_model}.")
            return digest
    raise RuntimeError(f"Ollama model {spec.requested_model!r} is not installed.")
