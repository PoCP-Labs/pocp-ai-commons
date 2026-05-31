"""Load GitHub neural-network technology registry (YAML)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "neural_network_sources.yaml"


@lru_cache(maxsize=1)
def load_neural_network_sources() -> dict:
    if not CONFIG_PATH.is_file():
        return {"spec_version": "0.1", "sources": {}, "declined": {}}
    with CONFIG_PATH.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def list_neural_sources(*, status: str | None = None, category: str | None = None) -> list[dict]:
    data = load_neural_network_sources()
    sources = data.get("sources") or {}
    rows: list[dict] = []
    for key, spec in sources.items():
        if not isinstance(spec, dict):
            continue
        if status and spec.get("status") != status:
            continue
        if category and spec.get("category") != category:
            continue
        rows.append({"slug": key, **spec})
    rows.sort(key=lambda r: (r.get("integration_round", 99), r.get("display_name", r["slug"])))
    return rows
