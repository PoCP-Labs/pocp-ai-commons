import os

from services.verifiers.openai_verifier import OpenAIVerifier


class DeepSeekVerifier(OpenAIVerifier):
    provider_name = "deepseek"

    def __init__(self):
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        self.model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        self.base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/")
