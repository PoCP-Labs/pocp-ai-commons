"""Locale discovery and negotiation for bilingual clients."""

from fastapi import APIRouter, Header, Query, Request

from services.i18n import (
    DEFAULT_LOCALE,
    SUPPORTED_LOCALES,
    locale_from_request,
    ontology_document_for_locale,
)

router = APIRouter(prefix="/api/v1/locale", tags=["locale"])


@router.get("")
def get_locale_config(
    request: Request,
    locale: str | None = Query(default=None, description="Override: en | zh"),
    accept_language: str | None = Header(default=None, alias="Accept-Language"),
):
    """Supported locales and effective locale for this request."""
    resolved = locale_from_request(accept_language, locale)
    return {
        "supported": list(SUPPORTED_LOCALES),
        "default": DEFAULT_LOCALE,
        "locale": resolved,
        "canonical_locale": DEFAULT_LOCALE,
        "negotiation": {
            "query_param": "locale",
            "header": "Accept-Language",
            "frontend_storage_key": "pocp_locale",
        },
        "policy": "docs/LANGUAGE-POLICY.md",
    }


@router.get("/preview-ontology")
def preview_localized_ontology(
    locale: str | None = Query(default=None),
    accept_language: str | None = Header(default=None, alias="Accept-Language"),
):
    """Sample of how entity ontology fields resolve for a locale (for UI smoke tests)."""
    from intelligence.entity_ontology import ontology_document

    resolved = locale_from_request(accept_language, locale)
    doc = ontology_document()
    return ontology_document_for_locale(doc, resolved)
