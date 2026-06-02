from __future__ import annotations
import hashlib

def _sha256(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()

class MerkleService:
    def merkle_root(self, hashes: list[str]) -> str:
        if not hashes:
            return _sha256("")
        layer = hashes[:]
        while len(layer) > 1:
            if len(layer) % 2 == 1:
                layer.append(layer[-1])
            layer = [_sha256(layer[i] + layer[i + 1]) for i in range(0, len(layer), 2)]
        return layer[0]
