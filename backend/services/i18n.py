"""Locale resolution and bilingual field selection (English canonical, zh secondary).

See docs/I18N-GUIDE.md and docs/LANGUAGE-POLICY.md.
"""

from __future__ import annotations

import copy
from typing import Any

SUPPORTED_LOCALES = ("en", "zh")
DEFAULT_LOCALE = "en"
_LOCALE_HEADER = "accept-language"
_QUERY_PARAM = "locale"


def normalize_locale(value: str | None) -> str:
    """Map BCP-47 tags to PoCP locale codes: en | zh."""
    if not value or not str(value).strip():
        return DEFAULT_LOCALE
    tag = str(value).strip().lower().replace("_", "-")
    if tag in SUPPORTED_LOCALES:
        return tag
    if tag.startswith("zh"):
        return "zh"
    return DEFAULT_LOCALE


def locale_from_request(
    accept_language: str | None = None,
    query_locale: str | None = None,
) -> str:
    """Prefer explicit ?locale= over Accept-Language."""
    if query_locale:
        return normalize_locale(query_locale)
    if not accept_language:
        return DEFAULT_LOCALE
    # Accept-Language: zh-CN,zh;q=0.9,en;q=0.8
    for part in accept_language.split(","):
        token = part.split(";")[0].strip()
        loc = normalize_locale(token)
        if loc == "zh":
            return "zh"
    return DEFAULT_LOCALE


def pick_localized(
    record: dict[str, Any],
    field: str,
    locale: str,
    *,
    zh_suffix: str = "_zh",
) -> Any:
    """Return English field, or Chinese override when locale is zh."""
    if locale != "zh":
        return record.get(field)
    zh_key = f"{field}{zh_suffix}"
    zh_val = record.get(zh_key)
    if zh_val is not None and zh_val != "":
        return zh_val
    return record.get(field)


def localize_flat_record(
    record: dict[str, Any],
    locale: str,
    fields: tuple[str, ...],
) -> dict[str, Any]:
    """Copy record and replace listed fields with localized text."""
    out = dict(record)
    for field in fields:
        if field in out or f"{field}_zh" in record:
            out[field] = pick_localized(record, field, locale)
    if locale == "zh":
        for key in list(out.keys()):
            if key.endswith("_zh"):
                del out[key]
    return out


def localize_nested_specs(
    specs: dict[str, dict[str, Any]],
    locale: str,
    text_fields: tuple[str, ...] = ("label", "description", "name"),
) -> dict[str, dict[str, Any]]:
    """Localize entity type / role spec maps keyed by id."""
    if locale != "zh":
        return specs
    return {
        key: localize_flat_record(spec, locale, text_fields)
        for key, spec in specs.items()
    }


def localize_tree(node: Any, locale: str) -> Any:
    """Walk dict/list trees; swap base keys from *_zh siblings when locale is zh."""
    if locale != "zh":
        if isinstance(node, dict):
            return {k: localize_tree(v, locale) for k, v in node.items() if not k.endswith("_zh")}
        if isinstance(node, list):
            return [localize_tree(item, locale) for item in node]
        return node

    if isinstance(node, list):
        return [localize_tree(item, locale) for item in node]
    if not isinstance(node, dict):
        return node

    out: dict[str, Any] = {}
    for key, value in node.items():
        if key.endswith("_zh"):
            continue
        zh_key = f"{key}_zh"
        if zh_key in node and isinstance(node.get(key), str):
            out[key] = node[zh_key]
        elif isinstance(value, (dict, list)):
            out[key] = localize_tree(value, locale)
        else:
            out[key] = value
    return out


def ontology_document_for_locale(doc: dict[str, Any], locale: str) -> dict[str, Any]:
    """Return ontology API payload with display strings for the requested locale."""
    payload = copy.deepcopy(doc)
    payload["locale"] = locale
    payload["canonical_locale"] = DEFAULT_LOCALE
    if locale == "zh":
        payload["principle"] = pick_localized(payload, "principle", locale)
        payload["entity_types"] = localize_nested_specs(payload.get("entity_types") or {}, locale)
        roles = payload.get("participant_roles") or {}
        if isinstance(roles, dict):
            payload["participant_roles"] = localize_nested_specs(roles, locale)
    return payload
