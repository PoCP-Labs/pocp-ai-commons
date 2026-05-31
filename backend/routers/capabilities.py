"""Capability import and catalog — integrate OpenClaw, AgentSkills, MCP, and native abilities."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from models.entity import Entity, EntityType
from models.user_account import UserAccount
from routers.auth import require_current_user
from services.capability_execute import attach_receipt_to_result, execute_agent, execute_skill
from services.capability_import import (
    activate_capability,
    bind_runtime,
    import_agent_manifest,
    import_skill_from_skill_md,
    list_capability_catalog,
    list_capability_sources,
    load_capability_sources,
    sync_bundled_capabilities,
)
from services.mcp_import import (
    import_mcp_from_manifest_file,
    import_mcp_server,
    list_mcp_catalog,
    parse_mcp_servers_config,
    sync_bundled_mcp_capabilities,
)
from services.mcp_invoke import invoke_mcp_tool

router = APIRouter(prefix="/api/v1/capabilities", tags=["capabilities"])


class AgentSkillsImportIn(BaseModel):
    source: str = "agentskills"
    skill_md: str
    external_id: str | None = None
    version: str = "1.0.0"
    runtime: dict[str, Any] = Field(default_factory=dict)
    activate: bool | None = None


class AgentImportIn(BaseModel):
    source: str
    external_id: str
    name: str
    description: str | None = None
    capabilities: list[str] = Field(default_factory=list)
    service_endpoints: dict[str, str] = Field(default_factory=dict)
    runtime: dict[str, Any] = Field(default_factory=dict)
    activate: bool | None = None


class McpServerImportIn(BaseModel):
    external_id: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    transport: dict[str, Any] = Field(
        description="stdio: {command, args, env} or http: {url, headers}"
    )
    tools: list[dict[str, Any]] = Field(default_factory=list)
    import_tools: bool = True
    activate: bool | None = None


class McpConfigImportIn(BaseModel):
    """Cursor/Claude-style mcpServers JSON object."""
    mcpServers: dict[str, dict[str, Any]]
    activate: bool | None = None


class McpToolInvokeIn(BaseModel):
    arguments: dict[str, Any] = Field(default_factory=dict)
    agent_entity_id: str | None = None
    task_id: str | None = None
    contribution_id: str | None = None
    include_receipt: bool = False
    external_result: dict[str, Any] | None = Field(
        default=None,
        description="Result from an out-of-band MCP runtime (records external invoke mode)",
    )
    invoke_mode: str | None = Field(
        default=None,
        description="Force stub, live, or peer; default follows env/runtime policy",
    )


class RuntimeBindIn(BaseModel):
    runtime: dict[str, Any] = Field(default_factory=dict)


class SkillExecuteIn(BaseModel):
    input: str = Field(min_length=1)
    context: dict[str, Any] = Field(default_factory=dict)
    agent_entity_id: str | None = None
    llm_entity_id: str | None = None
    llm_provider: str | None = None
    llm_model: str | None = None
    task_id: str | None = None
    contribution_id: str | None = None
    include_receipt: bool = False


class AgentExecuteIn(BaseModel):
    input: str = Field(min_length=1)
    context: dict[str, Any] = Field(default_factory=dict)
    skill_entity_id: str | None = None
    llm_entity_id: str | None = None
    llm_provider: str | None = None
    task_id: str | None = None
    contribution_id: str | None = None
    submit_contribution: bool = False
    include_receipt: bool = False


@router.get("/sources")
def capability_sources():
    data = load_capability_sources()
    return {
        "spec_version": data.get("spec_version"),
        "principle": data.get("principle"),
        "import_policy": data.get("import_policy"),
        "sources": list_capability_sources(),
    }


@router.get("/catalog")
def capability_catalog(
    source: str | None = None,
    entity_type: str | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
):
    items = list_capability_catalog(
        db,
        source=source,
        entity_type=entity_type,
        status=status,
    )
    return {"count": len(items), "items": items}


@router.get("/directory")
def capability_directory(
    exchange_kind: str | None = Query(default=None, description="compute | capability | hybrid"),
    capability_type: str | None = Query(default=None),
    availability: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """Public marketplace directory — compute + AI capabilities by provider Entity."""
    from services.node_manifest import list_provider_directory

    if exchange_kind and exchange_kind not in ("compute", "capability", "hybrid"):
        raise HTTPException(status_code=400, detail="exchange_kind must be compute, capability, or hybrid")
    return list_provider_directory(
        db,
        exchange_kind=exchange_kind,
        capability_type=capability_type,
        availability=availability,
        limit=limit,
    )


@router.post("/skills/{skill_entity_id}/execute")
async def execute_skill_endpoint(
    skill_entity_id: str,
    body: SkillExecuteIn,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(require_current_user),
):
    """Directly execute a registered Skill entity (native LLM or OpenClaw gateway)."""
    result = await execute_skill(
        db,
        human_entity_id=current_user.entity_id,
        skill_entity_id=skill_entity_id,
        user_input=body.input,
        context=body.context,
        agent_entity_id=body.agent_entity_id,
        llm_entity_id=body.llm_entity_id,
        llm_provider=body.llm_provider,
        llm_model=body.llm_model,
        task_id=body.task_id,
        contribution_id=body.contribution_id,
    )
    if body.include_receipt:
        attach_receipt_to_result(db, result)
    db.commit()
    return result


@router.post("/agents/{agent_entity_id}/execute")
async def execute_agent_endpoint(
    agent_entity_id: str,
    body: AgentExecuteIn,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(require_current_user),
):
    """Directly execute a registered Agent entity (StudyAgent graph or generic orchestration)."""
    result = await execute_agent(
        db,
        human_entity_id=current_user.entity_id,
        agent_entity_id=agent_entity_id,
        user_input=body.input,
        context=body.context,
        skill_entity_id=body.skill_entity_id,
        llm_entity_id=body.llm_entity_id,
        llm_provider=body.llm_provider,
        task_id=body.task_id,
        contribution_id=body.contribution_id,
        submit_contribution=body.submit_contribution,
    )
    if body.include_receipt and result.get("trace_id"):
        attach_receipt_to_result(db, result)
    db.commit()
    return result


@router.get("/catalog/mcp")
def mcp_catalog(db: Session = Depends(get_db)):
    """MCP servers and tools registered as Tool entities."""
    items = list_mcp_catalog(db)
    return {"count": len(items), "items": items}


@router.post("/import/mcp", status_code=201)
def import_mcp_server_endpoint(
    body: McpServerImportIn,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(require_current_user),
):
    try:
        result = import_mcp_server(
            db,
            external_id=body.external_id,
            name=body.name,
            description=body.description,
            maintainer_id=current_user.entity_id,
            transport=body.transport,
            tools=body.tools,
            activate=body.activate,
            import_tools=body.import_tools,
        )
        db.commit()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return result


@router.post("/import/mcp/config", status_code=201)
def import_mcp_config(
    body: McpConfigImportIn,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(require_current_user),
):
    """Import multiple MCP servers from a standard mcpServers config object."""
    try:
        rows = parse_mcp_servers_config(body.model_dump())
        results = []
        for row in rows:
            results.append(
                import_mcp_server(
                    db,
                    external_id=row["external_id"],
                    name=row["name"],
                    description=row.get("description"),
                    maintainer_id=current_user.entity_id,
                    transport=row["transport"],
                    tools=row.get("tools") or [],
                    activate=body.activate,
                )
            )
        db.commit()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"imported": len(results), "servers": results}


@router.post("/sync/mcp-bundled")
def sync_mcp_bundled(
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(require_current_user),
):
    """Import bundled MCP demo manifests (pending until /activate)."""
    results = sync_bundled_mcp_capabilities(db, maintainer_id=current_user.entity_id, activate=False)
    db.commit()
    return {"imported": len(results), "items": results}


@router.post("/mcp/{tool_entity_id}/invoke")
async def invoke_mcp_tool_endpoint(
    tool_entity_id: str,
    body: McpToolInvokeIn,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(require_current_user),
):
    """Stub-invoke an MCP tool entity and record InvocationTrace (v0.1 — no live MCP wire protocol)."""
    result = await invoke_mcp_tool(
        db,
        human_entity_id=current_user.entity_id,
        tool_entity_id=tool_entity_id,
        arguments=body.arguments,
        agent_entity_id=body.agent_entity_id,
        task_id=body.task_id,
        contribution_id=body.contribution_id,
        external_result=body.external_result,
        force_mode=body.invoke_mode,
    )
    if body.include_receipt:
        attach_receipt_to_result(db, result)
    db.commit()
    return result


@router.post("/import/agentskills", status_code=201)
def import_agentskills_skill(
    body: AgentSkillsImportIn,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(require_current_user),
):
    sources = {s["slug"] for s in list_capability_sources()}
    if body.source not in sources:
        raise HTTPException(status_code=400, detail=f"Unknown capability source: {body.source}")

    try:
        result = import_skill_from_skill_md(
            db,
            source=body.source,
            skill_md=body.skill_md,
            external_id=body.external_id,
            maintainer_id=current_user.entity_id,
            version=body.version,
            runtime=body.runtime,
            activate=body.activate,
        )
        db.commit()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return result


@router.post("/import/agent", status_code=201)
def import_agent(
    body: AgentImportIn,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(require_current_user),
):
    sources = {s["slug"] for s in list_capability_sources()}
    if body.source not in sources:
        raise HTTPException(status_code=400, detail=f"Unknown capability source: {body.source}")

    try:
        result = import_agent_manifest(
            db,
            source=body.source,
            external_id=body.external_id,
            name=body.name,
            description=body.description,
            maintainer_id=current_user.entity_id,
            capabilities=body.capabilities,
            service_endpoints=body.service_endpoints,
            runtime=body.runtime,
            activate=body.activate,
        )
        db.commit()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return result


@router.post("/{entity_id}/runtime")
def bind_capability_runtime(
    entity_id: str,
    body: RuntimeBindIn,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(require_current_user),
):
    entity = db.get(Entity, entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    if entity.owner_id and entity.owner_id != current_user.entity_id:
        raise HTTPException(status_code=403, detail="Only the capability maintainer may bind runtime")

    try:
        updated = bind_runtime(db, entity_id=entity_id, runtime=body.runtime)
        db.commit()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "entity_id": updated.id,
        "status": updated.status.value,
        "runtime": (updated.metadata_ or {}).get("runtime") or {},
    }


@router.post("/{entity_id}/activate")
def activate_imported_capability(
    entity_id: str,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(require_current_user),
):
    entity = db.get(Entity, entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    if entity.entity_type not in (EntityType.skill, EntityType.agent, EntityType.tool):
        raise HTTPException(status_code=400, detail="Only skill, agent, or tool capabilities can be activated")
    if entity.owner_id and entity.owner_id != current_user.entity_id:
        raise HTTPException(status_code=403, detail="Only the capability maintainer may activate")

    try:
        updated = activate_capability(db, entity_id)
        db.commit()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"entity_id": updated.id, "status": updated.status.value}


@router.post("/sync/bundled")
def sync_bundled(
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(require_current_user),
):
    """Import bundled example skills (OpenClaw-compatible SKILL.md) for the catalog."""
    results = sync_bundled_capabilities(db, maintainer_id=current_user.entity_id)
    db.commit()
    return {"imported": len(results), "items": results}
