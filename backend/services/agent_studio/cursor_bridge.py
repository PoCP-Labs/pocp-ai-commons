"""Execute Agent Studio handoffs via Cursor SDK (optional dependency)."""

from __future__ import annotations

import os
import subprocess
import sys
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from meta_agents_spec import META_AGENT_BY_ID, NEXUS_ID

_REPO_ROOT = Path(__file__).resolve().parents[3]
_PROMPTS_DIR = _REPO_ROOT / "agents" / "prompts"


def repo_root() -> Path:
    raw = os.getenv("POCP_REPO_ROOT", "").strip()
    if raw:
        return Path(raw).resolve()
    return _REPO_ROOT.resolve()


def cursor_api_key() -> str | None:
    key = (os.getenv("CURSOR_API_KEY") or os.getenv("POCP_CURSOR_API_KEY") or "").strip()
    return key or None


def python_supports_cursor_sdk() -> bool:
    """cursor-sdk uses os.get_blocking (Python 3.12+)."""
    return sys.version_info >= (3, 12)


def cursor_sdk_installed() -> bool:
    if not python_supports_cursor_sdk():
        return False
    try:
        import cursor_sdk  # noqa: F401

        return True
    except ImportError:
        return False


def cursor_runtime() -> str:
    return (os.getenv("POCP_CURSOR_RUNTIME") or "local").strip().lower()


def cursor_model() -> str:
    return (os.getenv("POCP_CURSOR_MODEL") or "composer-2.5").strip()


def automation_enabled() -> bool:
    if os.getenv("POCP_CURSOR_AUTOMATION", "false").lower() not in ("1", "true", "yes"):
        return False
    if not cursor_api_key():
        return False
    if not cursor_sdk_installed():
        return False
    return True


def automation_status() -> dict[str, Any]:
    import sys

    key = cursor_api_key()
    root = repo_root()
    py_ok = python_supports_cursor_sdk()
    active = automation_enabled()
    return {
        "enabled_flag": os.getenv("POCP_CURSOR_AUTOMATION", "false"),
        "automation_active": active,
        "sdk_installed": cursor_sdk_installed(),
        "api_key_configured": bool(key),
        "python_version_ok": py_ok,
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}",
        "runtime": cursor_runtime(),
        "model": cursor_model(),
        "repo_root": str(root),
        "repo_root_exists": root.is_dir(),
        "status_source": "backend_api",
        "install_hint": (
            "py -3.12 -m pip install cursor-sdk; set CURSOR_API_KEY in backend/.env; "
            "POCP_CURSOR_AUTOMATION=true; docker compose restart backend"
        ),
        "worker_hint": (
            "Windows host (recommended): .\\scripts\\run-studio-cursor-trial.ps1 "
            "or py -3.12 backend/scripts/check_studio_cursor.py"
        ),
        "inactive_reason": _automation_inactive_reason(py_ok, bool(key)),
    }


def _automation_inactive_reason(python_ok: bool, key_set: bool) -> str | None:
    if automation_enabled():
        return None
    if os.getenv("POCP_CURSOR_AUTOMATION", "false").lower() not in ("1", "true", "yes"):
        return "POCP_CURSOR_AUTOMATION is not true in backend/.env"
    if not key_set:
        return "CURSOR_API_KEY missing in backend/.env (restart backend after editing)"
    if not python_ok:
        return "Python 3.12+ required for cursor-sdk"
    if not cursor_sdk_installed():
        return "cursor-sdk not installed in backend image (rebuild: docker compose build backend)"
    return "unknown"


def _load_prompt_excerpt(slug: str, limit: int = 2400) -> str:
    path = _PROMPTS_DIR / f"{slug}.md"
    if not path.is_file():
        return ""
    text = path.read_text(encoding="utf-8")
    return text if len(text) <= limit else text[: limit - 3] + "..."


def build_handoff_prompt(
    *,
    handoff_id: str,
    to_agent_entity_id: str,
    scope: str | None,
    tests_run: str | None,
    mission_id: str | None,
    memory_context: str | None = None,
) -> str:
    spec = META_AGENT_BY_ID.get(to_agent_entity_id, {})
    slug = spec.get("slug", "")
    name = spec.get("name", to_agent_entity_id)
    roles = ", ".join(spec.get("roles") or [])
    capabilities = ", ".join(spec.get("capabilities") or [])
    writable = "\n".join(f"- {p}" for p in (spec.get("writable_paths") or [])[:12])
    prompt_excerpt = _load_prompt_excerpt(slug) if slug else ""

    return f"""# PoCP Meta Agent — automated handoff execution

You are **{name}** (`{to_agent_entity_id}`).
Act only within your roster writable paths and capabilities.

## Roles
{roles}

## Capabilities
{capabilities}

## Writable paths
{writable or "- (see agents/ROSTER.md)"}

## Agent Studio handoff
- handoff_id: {handoff_id}
- mission_id: {mission_id or "none"}
- scope: {scope or "No scope text — infer from mission plan."}
- tests_run: {tests_run or "Run relevant pytest/npm for your domain."}

## Playbook excerpt (`agents/prompts/{slug}.md`)
{prompt_excerpt or "(no prompt file)"}

## Memory vault (recent lessons)
{memory_context or "(memory context not loaded)"}

## Instructions
1. Implement the scope in this repository (`{repo_root()}`).
2. Run the tests listed in tests_run (or domain defaults).
3. Do NOT commit secrets, .env, or production credentials.
4. Do NOT finalize CP/AI Credits on live contributions.
5. End with a short summary: files changed, test commands run, pass/fail.

Global rules: `agents/prompts/_global.md`, NO-TOKEN-FIRST, Open Core boundary.

## Language
Mirror the language of the handoff scope / operator messages (Cursor-style).
Keep code, paths, and protocol JSON in English unless editing translation docs under `docs/genesis/`.
"""


def _agent_create_kwargs() -> tuple[dict[str, Any], str, str]:
    """Kwargs for Agent.create / Agent.prompt; returns (kwargs, runtime label, target path)."""
    from cursor_sdk import CloudAgentOptions, LocalAgentOptions

    api_key = cursor_api_key()
    if not api_key:
        raise RuntimeError("CURSOR_API_KEY or POCP_CURSOR_API_KEY not set")

    root = repo_root()
    runtime = cursor_runtime()
    model = cursor_model()

    opts_kwargs: dict[str, Any] = {
        "api_key": api_key,
        "model": model,
    }
    target = str(root)
    if runtime == "cloud":
        repo_url = os.getenv("POCP_CURSOR_CLOUD_REPO", "").strip()
        if not repo_url:
            raise RuntimeError(
                "POCP_CURSOR_RUNTIME=cloud requires POCP_CURSOR_CLOUD_REPO "
                "(e.g. https://github.com/PoCP-Labs/pocp-ai-commons)"
            )
        opts_kwargs["cloud"] = CloudAgentOptions(
            repos=[repo_url],
            auto_create_pr=os.getenv("POCP_CURSOR_AUTO_PR", "false").lower() == "true",
        )
        target = repo_url
    else:
        if not root.is_dir():
            raise RuntimeError(f"POCP_REPO_ROOT not a directory: {root}")
        opts_kwargs["local"] = LocalAgentOptions(cwd=str(root))

    return opts_kwargs, runtime, target


def _launch_bridge_threaded(workspace: str, *, timeout: float = 60) -> Any:
    """Windows-safe bridge launch (cursor-sdk uses select() on stderr, which fails on Win)."""
    from cursor_sdk._bridge import (
        Bridge,
        BridgeEndpoint,
        _bridge_subprocess_env,
        _terminate_process,
        parse_discovery_line,
    )
    from cursor_sdk._vendor import resolve_bridge_path
    from cursor_sdk.errors import CursorSDKError

    argv = [resolve_bridge_path(), "--workspace", workspace]
    process = subprocess.Popen(
        argv,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        env=_bridge_subprocess_env(),
    )
    discovery: dict[str, Any] = {}
    reader_errors: list[BaseException] = []
    done = threading.Event()

    def _read_stderr() -> None:
        try:
            if process.stderr is None:
                return
            for line in process.stderr:
                parsed = parse_discovery_line(line)
                if parsed is not None:
                    discovery.update(dict(parsed))
                    return
        except Exception as exc:
            reader_errors.append(exc)
        finally:
            done.set()

    threading.Thread(target=_read_stderr, daemon=True).start()
    if not done.wait(timeout):
        _terminate_process(process)
        raise CursorSDKError("Timed out waiting for cursor-sdk-bridge discovery")
    if reader_errors:
        _terminate_process(process)
        raise reader_errors[0]
    if not discovery:
        _terminate_process(process)
        raise CursorSDKError(
            f"Bridge exited before discovery with status {process.poll()}"
        )
    return Bridge(BridgeEndpoint.from_discovery(discovery), process)


@contextmanager
def _cursor_sdk_client() -> Iterator[Any]:
    """SDK client with a working bridge on Windows."""
    from cursor_sdk._client import Client

    if sys.platform == "win32":
        bridge = _launch_bridge_threaded(str(repo_root()))
        client = Client(bridge.endpoint, allow_api_key_env_fallback=True)
        try:
            yield client
        finally:
            bridge.close()
    else:
        from cursor_sdk._client import _default_client

        yield _default_client()


def bridge_launch_ok(*, timeout: float = 45) -> tuple[bool, str]:
    """Lightweight preflight: start bridge and shut down (no agent run)."""
    if not python_supports_cursor_sdk() or not cursor_sdk_installed():
        return False, "cursor-sdk not available"
    if sys.platform != "win32":
        return True, "native bridge launch"
    try:
        bridge = _launch_bridge_threaded(str(repo_root()), timeout=timeout)
        bridge.close()
        return True, "windows threaded bridge ok"
    except Exception as exc:
        return False, str(exc)


def _use_streaming_agent() -> bool:
    """Agent.create streaming fails on some Windows hosts (WinError 10038)."""
    if sys.platform == "win32":
        return os.getenv("POCP_CURSOR_STREAM", "false").lower() in ("1", "true", "yes")
    return os.getenv("POCP_CURSOR_STREAM", "true").lower() not in ("0", "false", "no")


def _stream_run_to_console(run: Any) -> None:
    """Print assistant/tool messages as they arrive."""
    from services.agent_studio.studio_console import log_step

    for message in run.messages():
        mtype = getattr(message, "type", None) or getattr(message, "role", "")
        if mtype == "assistant":
            msg = getattr(message, "message", message)
            content = getattr(msg, "content", None) or []
            for block in content:
                btype = getattr(block, "type", "")
                if btype == "text":
                    text = getattr(block, "text", "") or ""
                    if text:
                        print(text, end="", flush=True)
        elif mtype in ("tool", "tool_call", "tool_result"):
            name = getattr(message, "name", None) or mtype
            log_step(f"Cursor tool event: {name}")


def _execute_via_prompt(
    prompt: str,
    create_kwargs: dict[str, Any],
    *,
    verbose: bool,
    client: Any,
) -> Any:
    """One-shot Agent.prompt — reliable on Windows for handoff automation."""
    from cursor_sdk import Agent, AgentOptions

    from services.agent_studio.studio_console import log_block, log_step

    if verbose:
        log_step("Invoking Cursor (Agent.prompt one-shot)...")
        log_block("Prompt preview", prompt[:3500], max_lines=25)
        print("\n--- Waiting for Cursor (may take several minutes) ---\n", flush=True)
    return Agent.prompt(prompt, AgentOptions(**create_kwargs), client=client)


def _execute_via_streaming_agent(
    prompt: str,
    create_kwargs: dict[str, Any],
    *,
    verbose: bool,
    client: Any,
) -> Any:
    from cursor_sdk import Agent

    from services.agent_studio.studio_console import log_block, log_step

    if verbose:
        log_step("Creating Cursor agent session (streaming)...")
    with Agent.create(**create_kwargs, client=client) as agent:
        if verbose:
            agent_id = getattr(agent, "agent_id", None) or getattr(agent, "id", "?")
            log_step("Agent session ready", f"agent_id={agent_id}")
            log_step("Sending handoff prompt to Cursor...")
        run = agent.send(prompt)
        if verbose:
            run_id = getattr(run, "id", None) or getattr(run, "run_id", "?")
            log_step("Run started", f"run_id={run_id}")
            log_block("Prompt sent to Cursor (preview)", prompt[:3500], max_lines=25)
            print("\n--- Cursor assistant (live) ---\n", flush=True)
            _stream_run_to_console(run)
            print("\n\n--- Waiting for run to finish ---\n", flush=True)
        return run.wait()


def execute_handoff_prompt(prompt: str, *, verbose: bool = False) -> dict[str, Any]:
    """Run one Cursor agent prompt; returns structured result (no DB side effects)."""
    if not cursor_sdk_installed():
        raise RuntimeError("cursor-sdk not installed. pip install cursor-sdk")

    from cursor_sdk import CursorAgentError
    from cursor_sdk.errors import AuthenticationError

    from services.agent_studio.studio_console import log_step

    create_kwargs, runtime, target = _agent_create_kwargs()

    if verbose:
        log_step(
            "Cursor SDK",
            f"runtime={runtime} model={create_kwargs.get('model')} target={target}",
        )
        if sys.platform == "win32":
            log_step("Bridge", "using Windows threaded launcher")

    try:
        with _cursor_sdk_client() as client:
            if _use_streaming_agent():
                result = _execute_via_streaming_agent(
                    prompt, create_kwargs, verbose=verbose, client=client
                )
            else:
                result = _execute_via_prompt(
                    prompt, create_kwargs, verbose=verbose, client=client
                )
    except (CursorAgentError, AuthenticationError) as exc:
        if verbose:
            log_step("Cursor startup FAILED", str(exc))
        return {
            "ok": False,
            "startup_error": True,
            "message": str(exc),
            "retryable": getattr(exc, "is_retryable", False),
        }
    except OSError as exc:
        if verbose:
            log_step("Cursor OS error", str(exc))
        return {
            "ok": False,
            "startup_error": True,
            "message": str(exc),
            "retryable": False,
        }
    except Exception as exc:
        if verbose:
            log_step("Cursor error", str(exc))
        return {
            "ok": False,
            "startup_error": True,
            "message": str(exc),
            "retryable": False,
        }

    status = getattr(result, "status", None)
    text = getattr(result, "result", None) or ""
    run_id = getattr(result, "id", None)
    agent_id = getattr(result, "agent_id", None)

    if verbose:
        log_step("Run finished", f"status={status} run_id={run_id}")
        if text:
            log_block("Final result (excerpt)", str(text)[:3000], max_lines=30)

    return {
        "ok": status == "finished",
        "startup_error": False,
        "status": status,
        "run_id": run_id,
        "agent_id": agent_id,
        "summary": (text[:4000] if isinstance(text, str) else str(text)[:4000]),
        "retryable": status == "error",
    }
