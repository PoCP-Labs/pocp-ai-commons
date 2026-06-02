"""Console logging for Agent Studio trial runs (visible in terminal)."""

from __future__ import annotations

import os
import sys
from datetime import datetime


def configure_studio_stdio() -> None:
    """Avoid UnicodeEncodeError on Windows GBK consoles during verbose trials."""
    if sys.platform != "win32":
        return
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


def studio_verbose() -> bool:
    return os.getenv("POCP_STUDIO_VERBOSE", "false").lower() in ("1", "true", "yes")


def log_step(title: str, detail: str | None = None) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {title}"
    print(line, flush=True)
    if detail:
        for part in detail.strip().splitlines():
            print(f"         {part}", flush=True)


def log_banner(text: str) -> None:
    print("\n" + "=" * 60, flush=True)
    print(text, flush=True)
    print("=" * 60 + "\n", flush=True)


def log_block(label: str, body: str, max_lines: int = 40) -> None:
    print(f"\n--- {label} ---", flush=True)
    lines = body.splitlines()
    if len(lines) > max_lines:
        lines = lines[:max_lines] + [f"... ({len(body.splitlines()) - max_lines} more lines)"]
    print("\n".join(lines), flush=True)
    print("--- end ---\n", flush=True)
