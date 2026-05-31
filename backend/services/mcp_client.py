"""Minimal MCP JSON-RPC client — stdio and HTTP transports (v0.2)."""

from __future__ import annotations

import asyncio
import json
import os
import time
import uuid
from typing import Any

import httpx

MCP_PROTOCOL_VERSION = "2024-11-05"
CLIENT_INFO = {"name": "pocp-ai-commons", "version": "0.2"}
DEFAULT_STDIO_TIMEOUT = float(os.getenv("MCP_STDIO_TIMEOUT", "60"))
DEFAULT_HTTP_TIMEOUT = float(os.getenv("MCP_HTTP_TIMEOUT", "60"))


class McpClientError(Exception):
    """MCP wire protocol or tool execution failure."""


def _json_rpc_request(req_id: int | str, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"jsonrpc": "2.0", "id": req_id, "method": method}
    if params is not None:
        payload["params"] = params
    return payload


def _json_rpc_notification(method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"jsonrpc": "2.0", "method": method}
    if params is not None:
        payload["params"] = params
    return payload


def _parse_json_line(line: bytes) -> dict[str, Any] | None:
    text = line.decode(errors="replace").strip()
    if not text:
        return None
    return json.loads(text)


def _extract_tool_result(message: dict[str, Any]) -> dict[str, Any]:
    if "error" in message:
        err = message["error"]
        raise McpClientError(err.get("message") or str(err))
    result = message.get("result")
    if not isinstance(result, dict):
        raise McpClientError(f"Unexpected tools/call result: {result!r}")
    if result.get("isError"):
        content = result.get("content") or []
        text = " ".join(
            block.get("text", "")
            for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        )
        raise McpClientError(text or "MCP tool returned isError=true")
    return result


async def _read_json_rpc_response(
    reader: asyncio.StreamReader,
    req_id: int | str,
    *,
    timeout: float,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise McpClientError(f"Timed out waiting for MCP response id={req_id}")
        line = await asyncio.wait_for(reader.readline(), timeout=remaining)
        if not line:
            raise McpClientError("MCP server closed stdout before responding")
        parsed = _parse_json_line(line)
        if parsed is None:
            continue
        if parsed.get("id") == req_id:
            return parsed


async def call_tool_stdio(
    transport: dict[str, Any],
    *,
    tool_name: str,
    arguments: dict[str, Any],
    timeout: float | None = None,
) -> dict[str, Any]:
    """Spawn MCP server subprocess and call tools/call over newline-delimited JSON-RPC."""
    command = transport.get("command")
    if not command:
        raise McpClientError("stdio transport requires 'command'")

    args = [str(a) for a in (transport.get("args") or [])]
    env = {**os.environ, **{str(k): str(v) for k, v in (transport.get("env") or {}).items()}}
    proc_timeout = timeout if timeout is not None else DEFAULT_STDIO_TIMEOUT

    proc = await asyncio.create_subprocess_exec(
        str(command),
        *args,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
    )
    if proc.stdin is None or proc.stdout is None:
        raise McpClientError("Failed to open MCP subprocess pipes")

    async def _send(message: dict[str, Any]) -> None:
        proc.stdin.write((json.dumps(message) + "\n").encode())
        await proc.stdin.drain()

    try:
        init_id = 1
        call_id = 2
        await _send(
            _json_rpc_request(
                init_id,
                "initialize",
                {
                    "protocolVersion": MCP_PROTOCOL_VERSION,
                    "capabilities": {},
                    "clientInfo": CLIENT_INFO,
                },
            )
        )
        init_resp = await _read_json_rpc_response(proc.stdout, init_id, timeout=proc_timeout)
        if "error" in init_resp:
            raise McpClientError(init_resp["error"].get("message") or "initialize failed")

        await _send(_json_rpc_notification("notifications/initialized"))
        await _send(
            _json_rpc_request(
                call_id,
                "tools/call",
                {"name": tool_name, "arguments": arguments},
            )
        )
        call_resp = await _read_json_rpc_response(proc.stdout, call_id, timeout=proc_timeout)
        return _extract_tool_result(call_resp)
    finally:
        if proc.stdin and not proc.stdin.is_closing():
            proc.stdin.close()
        try:
            await asyncio.wait_for(proc.wait(), timeout=5)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()


async def call_tool_http(
    transport: dict[str, Any],
    *,
    tool_name: str,
    arguments: dict[str, Any],
    timeout: float | None = None,
) -> dict[str, Any]:
    """POST JSON-RPC tools/call to an MCP HTTP endpoint (Streamable HTTP compatible)."""
    url = transport.get("url")
    if not url:
        raise McpClientError("http transport requires 'url'")

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        **{str(k): str(v) for k, v in (transport.get("headers") or {}).items()},
    }
    req_timeout = timeout if timeout is not None else DEFAULT_HTTP_TIMEOUT
    session_id = str(uuid.uuid4())
    headers.setdefault("Mcp-Session-Id", session_id)

    init_body = _json_rpc_request(
        1,
        "initialize",
        {
            "protocolVersion": MCP_PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": CLIENT_INFO,
        },
    )
    call_body = _json_rpc_request(
        2,
        "tools/call",
        {"name": tool_name, "arguments": arguments},
    )

    async with httpx.AsyncClient(timeout=req_timeout) as client:
        init_resp = await client.post(url, json=init_body, headers=headers)
        if init_resp.status_code >= 400:
            raise McpClientError(f"MCP HTTP initialize failed ({init_resp.status_code}): {init_resp.text[:300]}")
        init_data = _parse_http_json_rpc(init_resp)
        if init_data and "error" in init_data:
            raise McpClientError(init_data["error"].get("message") or "initialize failed")

        call_resp = await client.post(url, json=call_body, headers=headers)
        if call_resp.status_code >= 400:
            raise McpClientError(f"MCP HTTP tools/call failed ({call_resp.status_code}): {call_resp.text[:300]}")
        call_data = _parse_http_json_rpc(call_resp)
        if call_data is None:
            raise McpClientError("MCP HTTP response was not JSON-RPC")
        return _extract_tool_result(call_data)


def _parse_http_json_rpc(response: httpx.Response) -> dict[str, Any] | None:
    content_type = response.headers.get("content-type", "")
    text = response.text.strip()
    if not text:
        return None
    if "application/json" in content_type or text.startswith("{"):
        data = response.json()
        if isinstance(data, dict):
            return data
    # SSE: take last data: line containing JSON
    if "text/event-stream" in content_type or text.startswith("event:") or text.startswith("data:"):
        for line in reversed(text.splitlines()):
            line = line.strip()
            if line.startswith("data:"):
                payload = line[5:].strip()
                if payload and payload != "[DONE]":
                    parsed = json.loads(payload)
                    if isinstance(parsed, dict) and parsed.get("jsonrpc") == "2.0":
                        return parsed
    return None


async def call_mcp_tool(
    transport: dict[str, Any],
    *,
    tool_name: str,
    arguments: dict[str, Any],
    timeout: float | None = None,
) -> dict[str, Any]:
    kind = transport.get("transport", "stdio")
    if kind == "http":
        return await call_tool_http(transport, tool_name=tool_name, arguments=arguments, timeout=timeout)
    if kind == "stdio":
        return await call_tool_stdio(transport, tool_name=tool_name, arguments=arguments, timeout=timeout)
    raise McpClientError(f"Unsupported MCP transport: {kind}")
