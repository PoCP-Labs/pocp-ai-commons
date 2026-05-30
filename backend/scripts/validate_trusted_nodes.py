"""Validate trusted_nodes.yaml structure."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.trust_config import _CONFIG_PATH, load_trusted_nodes_from_yaml, trust_list_hash


def main() -> None:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else _CONFIG_PATH
    if not path.exists():
        print(f"Missing config: {path}", file=sys.stderr)
        sys.exit(1)

    import yaml

    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if "trusted_nodes" not in data:
        print("trusted_nodes key required", file=sys.stderr)
        sys.exit(1)

    nodes = load_trusted_nodes_from_yaml(path)
    print(f"OK {len(nodes)} trusted node(s), hash={trust_list_hash(nodes)}")


if __name__ == "__main__":
    main()
