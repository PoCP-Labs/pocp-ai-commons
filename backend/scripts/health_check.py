from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"


def check_exists(path: Path, label: str) -> bool:
    if path.exists():
        print(f"[OK] {label}: {path.relative_to(ROOT)}")
        return True
    print(f"[WARN] Missing {label}: {path.relative_to(ROOT)}")
    return False


def check_python_files_readable() -> bool:
    print("\nChecking Python source readability...")
    ok = True
    for path in sorted(BACKEND.rglob("*.py")):
        text = path.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        rel = path.relative_to(ROOT)

        if not lines:
            print(f"[WARN] Empty Python file: {rel}")
            continue

        longest = max(len(line) for line in lines)

        if len(lines) <= 3 and longest > 300:
            print(
                f"[WARN] Possible compressed one-line Python file: {rel} "
                f"(lines={len(lines)}, longest_line={longest})"
            )
            ok = False
        elif longest > 500:
            print(f"[WARN] Very long line in {rel}: {longest} chars")
            ok = False
        else:
            print(f"[OK] {rel}")

    return ok


def check_docs_links() -> bool:
    print("\nChecking important docs...")
    required = [
        "README.md",
        "GENESIS.md",
        "AI-COMMONS.md",
        "PROTOCOL-SPEC-v0.1.md",
    ]
    ok = True
    for name in required:
        ok = check_exists(ROOT / name, name) and ok
    return ok


def check_backend_structure() -> bool:
    print("\nChecking backend structure...")
    paths = [
        ("backend/main.py", "FastAPI entrypoint"),
        ("backend/models", "models directory"),
        ("backend/services", "services directory"),
        ("backend/routers", "routers directory"),
        ("backend/scripts", "scripts directory"),
    ]
    ok = True
    for rel, label in paths:
        ok = check_exists(ROOT / rel, label) and ok
    return ok


def main() -> int:
    print("PoCP repository health check")
    print(f"Root: {ROOT}")

    ok = True
    ok = check_docs_links() and ok
    ok = check_backend_structure() and ok
    ok = check_python_files_readable() and ok

    print("\nSummary")
    if ok:
        print("[OK] Repository health check passed.")
        return 0

    print("[WARN] Repository health check completed with warnings.")
    print("Review warnings before inviting external contributors.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
