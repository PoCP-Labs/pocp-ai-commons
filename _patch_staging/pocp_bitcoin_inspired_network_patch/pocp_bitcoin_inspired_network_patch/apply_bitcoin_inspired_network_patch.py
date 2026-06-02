from pathlib import Path
import shutil

ROOT = Path.cwd()
PATCH_DIR = Path(__file__).resolve().parent
OVERLAY = PATCH_DIR / "overlay"

if not OVERLAY.exists():
    raise SystemExit(f"Overlay folder not found: {OVERLAY}")

for item in OVERLAY.rglob("*"):
    rel = item.relative_to(OVERLAY)
    target = ROOT / rel
    if item.is_dir():
        target.mkdir(parents=True, exist_ok=True)
        continue
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        backup = target.with_suffix(target.suffix + ".bak")
        shutil.copy2(target, backup)
        print(f"Backed up existing file: {target} -> {backup}")
    shutil.copy2(item, target)
    print(f"Wrote: {target}")

print("\\nPoCP Bitcoin-inspired network patch applied.")
print("Next: paste CURSOR_APPLY_PROMPT.md into Cursor.")
print("Then run: python backend/scripts/bitcoin_inspired_network_smoke.py")
