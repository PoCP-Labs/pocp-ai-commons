"""Adapter registry — slug → ComputeAdapter instance."""

from __future__ import annotations

from services.compute_adapters.akash import AkashComputeAdapter
from services.compute_adapters.base import ComputeAdapter
from services.compute_adapters.gensyn import GensynComputeAdapter
from services.compute_adapters.ionet import IoNetComputeAdapter
from services.compute_adapters.render import RenderComputeAdapter

_ADAPTERS: dict[str, ComputeAdapter] = {
    AkashComputeAdapter.slug: AkashComputeAdapter(),
    RenderComputeAdapter.slug: RenderComputeAdapter(),
    IoNetComputeAdapter.slug: IoNetComputeAdapter(),
    GensynComputeAdapter.slug: GensynComputeAdapter(),
}


def list_adapters() -> list[dict]:
    return [adapter.catalog_entry() for adapter in _ADAPTERS.values()]


def get_adapter(slug: str) -> ComputeAdapter:
    normalized = slug.strip().lower()
    adapter = _ADAPTERS.get(normalized)
    if adapter is None:
        raise ValueError(f"Unknown compute adapter: {slug}")
    return adapter
