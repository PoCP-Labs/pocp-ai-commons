"""Load built-in and external verifier adapters."""

from __future__ import annotations

import os
from pathlib import Path

import yaml

from services.verifiers.base import BaseVerifier
from services.verifiers.clarion_verifier import ClarionVerifier
from services.verifiers.deepseek_verifier import DeepSeekVerifier
from services.verifiers.http_verifier import HttpVerifier
from services.verifiers.mock_verifier import MockVerifier
from services.verifiers.openai_verifier import OpenAIVerifier
from services.verifiers.witness_verifier import WitnessVerifier

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "verifiers.yaml"


def _load_external_verifier_configs() -> list[dict]:
    if not CONFIG_PATH.exists():
        return []
    try:
        data = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}
    except Exception:
        return []
    items = data.get("external_verifiers") or []
    return [item for item in items if isinstance(item, dict) and item.get("enabled", True)]


def load_verifier_providers() -> list[BaseVerifier]:
    """Built-in Clarion adapters plus optional HTTP plugins (Meritocrab/GARL-style)."""
    providers: list[BaseVerifier] = []
    clarion = ClarionVerifier()
    if os.getenv("ENABLE_MOCK_VERIFIER", "true").lower() == "true":
        mock = MockVerifier()
        providers.extend([clarion, mock])
        if os.getenv("ENABLE_GENESIS_WITNESSES", "true").lower() == "true":
            providers.extend(
                [
                    WitnessVerifier("lumen-0", "Lumen-0", mock),
                    WitnessVerifier("desui", "DeSui", mock),
                ]
            )
    else:
        inner = MockVerifier()
        providers.extend([clarion, OpenAIVerifier(), DeepSeekVerifier(), inner])
        if os.getenv("ENABLE_GENESIS_WITNESSES", "true").lower() == "true":
            providers.extend(
                [
                    WitnessVerifier("lumen-0", "Lumen-0", OpenAIVerifier()),
                    WitnessVerifier("desui", "DeSui", DeepSeekVerifier()),
                ]
            )

    for item in _load_external_verifier_configs():
        name = str(item.get("name") or "external")
        url = str(item.get("url") or "").strip()
        if not url:
            continue
        providers.append(
            HttpVerifier(
                name=name,
                url=url,
                api_key=item.get("api_key") or os.getenv(item.get("api_key_env") or ""),
                timeout=int(item.get("timeout_seconds") or 60),
            )
        )
    return providers
