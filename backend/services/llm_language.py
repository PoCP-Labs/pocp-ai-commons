"""Cursor-style conversational language policy for LLM calls (not UI i18n).

Multilingual understanding and reply language are delegated to the model.
This module only supplies system-prompt policy and optional audit hints.
"""

from __future__ import annotations

import os
import re
from typing import Literal

LanguageHint = Literal["en", "zh", "mixed", "unknown"]

_CJK_RE = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]")
_LATIN_RE = re.compile(r"[A-Za-z]{2,}")


def mirror_user_language_enabled() -> bool:
    forced = (os.getenv("POCP_LLM_REPLY_LOCALE") or "").strip().lower()
    if forced in ("en", "zh"):
        return False
    return os.getenv("POCP_LLM_MIRROR_USER_LANGUAGE", "true").lower() in ("1", "true", "yes")


def forced_reply_locale() -> str | None:
    forced = (os.getenv("POCP_LLM_REPLY_LOCALE") or "").strip().lower()
    if forced in ("en", "zh"):
        return forced
    return None


def detect_language_hint(text: str) -> LanguageHint:
    """Cheap hint for logs/telemetry — not used to route models."""
    if not text or not str(text).strip():
        return "unknown"
    sample = str(text)[:2000]
    cjk = len(_CJK_RE.findall(sample))
    latin = len(_LATIN_RE.findall(sample))
    if cjk >= 4 and latin == 0:
        return "zh"
    if latin >= 3 and cjk == 0:
        return "en"
    if cjk >= 2 and latin >= 2:
        return "mixed"
    if cjk >= 2:
        return "zh"
    if latin >= 2:
        return "en"
    return "unknown"


def conversational_language_instructions(*, domain: str = "ai_chat") -> str:
    """System-prompt block: Cursor-like mirror + protocol English boundary."""
    forced = forced_reply_locale()
    if forced == "en":
        return (
            "Language: Always reply in English unless quoting user text verbatim."
        )
    if forced == "zh":
        return (
            "Language: Always reply in Simplified Chinese unless quoting user text verbatim."
        )
    if not mirror_user_language_enabled():
        return (
            "Language: Reply in clear English. If the user writes in another language, "
            "you may acknowledge it but keep protocol-facing suggestions in English."
        )
    return (
        "Language (Cursor-style): Infer the user's language from their latest message and "
        "reply in that same language by default. Switch only when they ask. "
        "Keep code, file paths, entity IDs, and JSON field names in English as in the repo. "
        "When you propose protocol artifacts (contribution titles, proof summaries, API payloads), "
        "use English for canonical fields; you may add a short paraphrase in the user's language "
        "outside the structured payload. "
        f"Context: {domain}."
    )


def conversational_system_prompt(*, base: str, domain: str = "ai_chat") -> str:
    """Merge product base prompt with bilingual conversation policy."""
    base = (base or "").strip()
    lang = conversational_language_instructions(domain=domain)
    if not base:
        return lang
    return f"{base}\n\n{lang}"


def protocol_json_language_instructions() -> str:
    """Witness / verifier: English JSON keys; mirror language in string values only."""
    return (
        "Protocol JSON rules: Keep all JSON keys and numeric fields exactly as specified. "
        "Enum values such as recommended_status must stay in English "
        "(e.g. ready_for_policy_finalize, request_changes). "
        "Free-text string fields (rationale, concerns, reviewer_questions, proof_draft.summary, "
        "proof_draft.evidence items) should use the same language as the contributor's "
        "task/contribution text when mirror mode is on (Cursor-style). "
        "If task/contribution text is mixed, prefer the dominant language."
    )


def verifier_system_prompt(*, role_label: str = "an AI advisory verifier") -> str:
    """System message for witness / auto-verify LLM calls."""
    return conversational_system_prompt(
        base=f"You are {role_label} for PoCP AI Commons. Return JSON only.",
        domain="witness_verify",
    ) + "\n\n" + protocol_json_language_instructions()


def infer_context_language(context: dict) -> LanguageHint:
    """Detect dominant language from verification context (telemetry / UI hints)."""
    task = context.get("task") or {}
    contrib = context.get("contribution") or {}
    blob = "\n".join(
        [
            str(task.get("title") or ""),
            str(task.get("description") or ""),
            str(contrib.get("description") or ""),
        ]
    )
    return detect_language_hint(blob)
