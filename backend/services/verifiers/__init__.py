from services.verifiers.base import BaseVerifier, VerifierResult
from services.verifiers.mock_verifier import MockVerifier
from services.verifiers.openai_verifier import OpenAIVerifier
from services.verifiers.deepseek_verifier import DeepSeekVerifier
from services.verifiers.ollama_verifier import OllamaVerifier


def __getattr__(name: str):
    if name == "MultiVerifierService":
        from services.verifiers.multi_verifier import MultiVerifierService

        return MultiVerifierService
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "BaseVerifier",
    "VerifierResult",
    "MockVerifier",
    "OpenAIVerifier",
    "DeepSeekVerifier",
    "OllamaVerifier",
    "MultiVerifierService",
]
