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

print("\nPoCP Open Core Restructure patch applied.")
print("Next:")
print("1. Open Cursor.")
print("2. Paste CURSOR_APPLY_PROMPT.md.")
print("3. Let Cursor update README and preserve current quick start.")
print("4. Commit on branch: open-core-restructure.")
