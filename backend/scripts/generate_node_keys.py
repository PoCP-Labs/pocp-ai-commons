"""Generate Ed25519 keypair for a PoCP federation node."""

import sys

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


def main() -> None:
    node_id = sys.argv[1] if len(sys.argv) > 1 else "pocp-node"
    key = Ed25519PrivateKey.generate()
    private_hex = key.private_bytes_raw().hex()
    public_hex = key.public_key().public_bytes_raw().hex()
    print(f"# Keys for {node_id}")
    print(f"POCP_NODE_ID={node_id}")
    print(f"POCP_NODE_PRIVATE_KEY={private_hex}")
    print(f"POCP_NODE_PUBLIC_KEY={public_hex}")


if __name__ == "__main__":
    main()
