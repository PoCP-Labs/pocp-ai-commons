"""A2A JSON-RPC task bridge — maps SendMessage / GetTask to PoCP Contributions (BI-1.5)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from models.contribution import ContributionEvent, ContributionStatus, ParticipantRole
from models.entity import Entity, EntityType
from models.task import Task, TaskStatus
from models.user_account import UserAccount
from services.a2a_agent_card import A2A_PROTOCOL_VERSION, POCP_A2A_EXTENSION_URI, build_entity_agent_card
from services.contribution_submit import submit_contribution_event
from services.evidence import POCP_META_KEY, enrich_evidence

A2A_ERROR_TASK_NOT_FOUND = -32001
A2A_ERROR_UNSUPPORTED = -32004
A2A_ERROR_INVALID_PARAMS = -32602
A2A_ERROR_INTERNAL = -32603

_SUPPORTED_METHODS = frozenset(
    {
        "SendMessage",
        "GetTask",
        "ListTasks",
        "GetAgentCard",
    }
)

_ENTITY_ROLE_MAP: dict[EntityType, ParticipantRole] = {
    EntityType.agent: ParticipantRole.executor,
    EntityType.skill: ParticipantRole.skill_provider,
    EntityType.llm: ParticipantRole.model_provider,
    EntityType.tool: ParticipantRole.tool_provider,
    EntityType.dataset: ParticipantRole.data_provider,
    EntityType.workflow: ParticipantRole.coordinator,
}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _meta_get(meta: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in meta and meta[key] is not None:
            return meta[key]
    return None


def _contribution_a2a_meta(contribution: ContributionEvent) -> dict[str, Any]:
    evidence = contribution.evidence or {}
    pocp = evidence.get(POCP_META_KEY) or {}
    a2a = pocp.get("a2a") or {}
    return a2a if isinstance(a2a, dict) else {}


def map_contribution_status_to_a2a_state(status: ContributionStatus) -> str:
    mapping = {
        ContributionStatus.draft: "TASK_STATE_SUBMITTED",
        ContributionStatus.submitted: "TASK_STATE_SUBMITTED",
        ContributionStatus.ai_verified: "TASK_STATE_WORKING",
        ContributionStatus.approved: "TASK_STATE_COMPLETED",
        ContributionStatus.rejected: "TASK_STATE_REJECTED",
    }
    return mapping.get(status, "TASK_STATE_WORKING")


def _status_message_for_contribution(contribution: ContributionEvent) -> str:
    state = map_contribution_status_to_a2a_state(contribution.status)
    if state == "TASK_STATE_WORKING" and contribution.status == ContributionStatus.ai_verified:
        return "Witness quorum passed — policy auto-finalization in progress (entity-equal delegate)."
    if state == "TASK_STATE_COMPLETED":
        return "Contribution finalized and recorded on ledger."
    if state == "TASK_STATE_REJECTED":
        return "Contribution rejected during verification or policy finalization."
    return "Contribution submitted — awaiting witness verification."


def _message_parts_from_text(text: str) -> list[dict[str, Any]]:
    return [{"kind": "text", "text": text}]


def extract_message_text(message: dict[str, Any] | None) -> str:
    if not message:
        return ""
    if isinstance(message.get("text"), str):
        return message["text"].strip()
    content = message.get("content")
    if isinstance(content, str):
        return content.strip()
    parts = message.get("parts") or []
    chunks: list[str] = []
    for part in parts:
        if not isinstance(part, dict):
            continue
        if part.get("kind") == "text" or part.get("type") == "text":
            text = part.get("text")
            if isinstance(text, str) and text.strip():
                chunks.append(text.strip())
    return "\n".join(chunks).strip()


def contribution_to_a2a_task(
    contribution: ContributionEvent,
    *,
    include_history: bool = False,
) -> dict[str, Any]:
    a2a_meta = _contribution_a2a_meta(contribution)
    state = map_contribution_status_to_a2a_state(contribution.status)
    description = contribution.description or ""
    evidence = contribution.evidence or {}
    preview = evidence.get("content_preview") or description[:500]

    task: dict[str, Any] = {
        "id": contribution.id,
        "contextId": a2a_meta.get("context_id") or contribution.task_id,
        "status": {
            "state": state,
            "message": {
                "role": "ROLE_AGENT",
                "parts": _message_parts_from_text(_status_message_for_contribution(contribution)),
                "messageId": str(uuid.uuid4()),
                "contextId": a2a_meta.get("context_id") or contribution.task_id,
            },
            "timestamp": _utc_now_iso(),
        },
        "artifacts": [
            {
                "artifactId": f"contribution-{contribution.id}",
                "name": "contribution_evidence",
                "parts": _message_parts_from_text(str(preview)),
            }
        ],
        "metadata": {
            "pocpContributionId": contribution.id,
            "pocpTaskId": contribution.task_id,
            "pocpStatus": contribution.status.value,
            "pocpContributionType": contribution.contribution_type,
            "humanFinalizationRequired": False,
            "autoFinalizationEnabled": True,
            "contributionApi": f"/api/v1/contributions/{contribution.id}",
            "autoVerifyApi": f"/api/v1/contributions/{contribution.id}/auto-verify",
        },
    }
    if a2a_meta.get("target_entity_id"):
        task["metadata"]["pocpTargetEntityId"] = a2a_meta["target_entity_id"]
    if include_history:
        task["history"] = [
            {
                "role": "ROLE_USER",
                "parts": _message_parts_from_text(description),
                "messageId": a2a_meta.get("message_id") or str(uuid.uuid4()),
                "contextId": task["contextId"],
            }
        ]
    return task


def _resolve_or_create_task(
    db: Session,
    *,
    human_entity_id: str,
    metadata: dict[str, Any],
    message_text: str,
) -> Task:
    task_id = _meta_get(metadata, "pocpTaskId", "taskId", "task_id")
    if task_id:
        task = db.query(Task).filter(Task.id == str(task_id)).first()
        if task:
            return task
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")

    title = _meta_get(metadata, "taskTitle", "task_title") or (message_text[:120] or "A2A task")
    description = _meta_get(metadata, "taskDescription", "task_description") or message_text[:2000]
    sponsor_id = _meta_get(metadata, "sponsorId", "sponsor_id") or human_entity_id
    task = Task(
        title=str(title)[:255],
        description=str(description)[:4000] if description else None,
        sponsor_id=str(sponsor_id),
        status=TaskStatus.open,
    )
    db.add(task)
    db.flush()
    return task


def _participants_for_target(
    db: Session,
    *,
    human_entity_id: str,
    target_entity_id: str | None,
    metadata: dict[str, Any],
) -> list[dict[str, Any]]:
    participants: list[dict[str, Any]] = [
        {"entity_id": human_entity_id, "role": ParticipantRole.creator.value, "weight": 0.5},
    ]
    target_id = target_entity_id or _meta_get(metadata, "targetEntityId", "target_entity_id")
    if not target_id:
        return participants

    target = db.get(Entity, str(target_id))
    if target is None:
        raise HTTPException(status_code=404, detail=f"Target entity not found: {target_id}")

    role = _ENTITY_ROLE_MAP.get(target.entity_type, ParticipantRole.executor)
    participants.append(
        {"entity_id": target.id, "role": role.value, "weight": 0.3},
    )
    return participants


def send_message_to_contribution(
    db: Session,
    *,
    user: UserAccount,
    params: dict[str, Any],
    target_entity_id: str | None = None,
) -> ContributionEvent:
    if not user.entity_id:
        raise HTTPException(status_code=403, detail="Authenticated user has no linked Entity")

    message = params.get("message") or {}
    metadata = params.get("metadata") or {}
    if not isinstance(metadata, dict):
        metadata = {}

    message_text = extract_message_text(message)
    if not message_text:
        raise HTTPException(status_code=400, detail="SendMessage requires non-empty message text")

    task = _resolve_or_create_task(
        db,
        human_entity_id=user.entity_id,
        metadata=metadata,
        message_text=message_text,
    )

    contribution_type = str(
        _meta_get(metadata, "contributionType", "contribution_type") or "knowledge"
    )
    description = _meta_get(metadata, "description") or message_text[:4000]
    context_id = _meta_get(metadata, "contextId", "context_id") or str(uuid.uuid4())
    message_id = _meta_get(message, "messageId", "message_id") or str(uuid.uuid4())

    evidence = enrich_evidence(
        {
            "content_preview": message_text[:800],
            "a2a_message": {
                "message_id": message_id,
                "context_id": context_id,
                "role": message.get("role") or "ROLE_USER",
            },
        }
    )
    a2a_record = {
        "context_id": context_id,
        "message_id": message_id,
        "target_entity_id": target_entity_id or _meta_get(metadata, "targetEntityId", "target_entity_id"),
        "skill_id": _meta_get(metadata, "skillId", "skill_id"),
        "protocol_version": A2A_PROTOCOL_VERSION,
        "extension_uri": POCP_A2A_EXTENSION_URI,
    }

    participants = _participants_for_target(
        db,
        human_entity_id=user.entity_id,
        target_entity_id=target_entity_id,
        metadata=metadata,
    )

    contribution = submit_contribution_event(
        db,
        human_entity_id=user.entity_id,
        task_id=task.id,
        contribution_type=contribution_type,
        description=str(description),
        evidence=evidence,
        participants=participants,
    )
    stored = dict(contribution.evidence or {})
    pocp_meta = dict(stored.get(POCP_META_KEY) or {})
    pocp_meta["a2a"] = a2a_record
    stored[POCP_META_KEY] = pocp_meta
    contribution.evidence = stored
    db.flush()
    return contribution


def get_task_for_user(
    db: Session,
    *,
    user: UserAccount,
    task_id: str,
    history_length: int | None = None,
) -> dict[str, Any]:
    contribution = (
        db.query(ContributionEvent)
        .options(joinedload(ContributionEvent.participants))
        .filter(ContributionEvent.id == task_id)
        .first()
    )
    if contribution is None:
        raise KeyError(task_id)
    if contribution.primary_entity_id != user.entity_id:
        raise PermissionError(task_id)
    include_history = history_length is None or history_length > 0
    return contribution_to_a2a_task(contribution, include_history=include_history)


def list_tasks_for_user(
    db: Session,
    *,
    user: UserAccount,
    page_size: int = 20,
) -> dict[str, Any]:
    page_size = max(1, min(page_size, 100))
    rows = (
        db.query(ContributionEvent)
        .filter(ContributionEvent.primary_entity_id == user.entity_id)
        .order_by(ContributionEvent.created_at.desc())
        .limit(page_size)
        .all()
    )
    return {
        "tasks": [contribution_to_a2a_task(row) for row in rows],
        "totalCount": len(rows),
        "pageSize": page_size,
    }


def _jsonrpc_result(request_id: Any, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _jsonrpc_error(request_id: Any, code: int, message: str, data: Any = None) -> dict[str, Any]:
    err: dict[str, Any] = {"code": code, "message": message}
    if data is not None:
        err["data"] = data
    return {"jsonrpc": "2.0", "id": request_id, "error": err}


def handle_jsonrpc_call(
    db: Session,
    *,
    user: UserAccount,
    payload: dict[str, Any],
    target_entity_id: str | None = None,
) -> dict[str, Any]:
    if payload.get("jsonrpc") != "2.0":
        return _jsonrpc_error(payload.get("id"), -32600, "Invalid Request — jsonrpc must be '2.0'")

    request_id = payload.get("id")
    method = payload.get("method")
    params = payload.get("params") or {}

    if not isinstance(method, str) or method not in _SUPPORTED_METHODS:
        return _jsonrpc_error(request_id, -32601, f"Method not found: {method}")

    if not isinstance(params, dict):
        return _jsonrpc_error(request_id, A2A_ERROR_INVALID_PARAMS, "Invalid params — object expected")

    try:
        if method == "SendMessage":
            contribution = send_message_to_contribution(
                db,
                user=user,
                params=params,
                target_entity_id=target_entity_id,
            )
            db.commit()
            db.refresh(contribution)
            return _jsonrpc_result(
                request_id,
                {"task": contribution_to_a2a_task(contribution, include_history=True)},
            )

        if method == "GetTask":
            task_id = params.get("id") or params.get("taskId")
            if not task_id:
                return _jsonrpc_error(request_id, A2A_ERROR_INVALID_PARAMS, "GetTask requires id")
            history_length = params.get("historyLength")
            try:
                task = get_task_for_user(
                    db,
                    user=user,
                    task_id=str(task_id),
                    history_length=history_length,
                )
            except KeyError:
                return _jsonrpc_error(request_id, A2A_ERROR_TASK_NOT_FOUND, f"Task not found: {task_id}")
            except PermissionError:
                return _jsonrpc_error(request_id, A2A_ERROR_TASK_NOT_FOUND, f"Task not found: {task_id}")
            return _jsonrpc_result(request_id, task)

        if method == "ListTasks":
            page_size = int(params.get("pageSize") or params.get("page_size") or 20)
            listing = list_tasks_for_user(db, user=user, page_size=page_size)
            return _jsonrpc_result(request_id, listing)

        if method == "GetAgentCard":
            if target_entity_id:
                card = build_entity_agent_card(db, target_entity_id)
                if card is None:
                    return _jsonrpc_error(request_id, A2A_ERROR_TASK_NOT_FOUND, "Entity not found")
            else:
                from services.a2a_agent_card import build_node_agent_card

                card = build_node_agent_card(db)
            return _jsonrpc_result(request_id, {"agentCard": card})

        return _jsonrpc_error(request_id, A2A_ERROR_UNSUPPORTED, f"Unsupported method: {method}")
    except HTTPException as exc:
        code = A2A_ERROR_INVALID_PARAMS if exc.status_code < 500 else A2A_ERROR_INTERNAL
        return _jsonrpc_error(request_id, code, str(exc.detail))
    except Exception as exc:
        db.rollback()
        return _jsonrpc_error(request_id, A2A_ERROR_INTERNAL, str(exc))
