"""Federation protocol status — re-export for intelligence router."""

from services.protocol_federation_status.schemas import (
    federation_protocol_manifest,
    validate_federation_protocol_manifest,
)

__all__ = [
    "federation_protocol_manifest",
    "validate_federation_protocol_manifest",
]
