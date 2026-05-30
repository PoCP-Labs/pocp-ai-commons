"""PoCP Capability Layer kernel — unified orchestration for all intelligence engines."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session, joinedload

from intelligence import engines
from intelligence.protocol import (
    CAPABILITY_LAYER_VERSION,
    UNIFIED_PRINCIPLE,
    UNIFIED_PRINCIPLE_ZH,
    contribution_packet_header,
)
from models.contribution import ContributionEvent


class CapabilityLayer:
    """Entity-centric intelligence kernel. Automation-first; finalization is traceable in proof/ledger."""

    version = CAPABILITY_LAYER_VERSION
    principle = UNIFIED_PRINCIPLE
    principle_zh = UNIFIED_PRINCIPLE_ZH

    def protocol(self) -> dict[str, Any]:
        header = contribution_packet_header()
        header["modules"] = engines.module_registry()
        header["stack"] = self.protocol_stack()
        return header

    def protocol_stack(self) -> dict[str, Any]:
        from intelligence.protocol import protocol_stack

        return protocol_stack()

    def status(self) -> dict[str, Any]:
        modules = engines.module_registry()
        active = sum(1 for m in modules if m.get("status") == "active")
        return {
            "capability_layer_version": self.version,
            "principle": self.principle,
            "principle_zh": self.principle_zh,
            "modules_total": len(modules),
            "modules_active": active,
            "modules": modules,
        }

    async def verify_contribution(self, db: Session, contribution: ContributionEvent) -> dict:
        return await engines.run_verification(db, contribution)

    def governance_summary(self, db: Session) -> dict[str, Any]:
        return engines.run_governance(db)

    def contribution_graph(self, db: Session) -> dict:
        return engines.run_graph(db)

    def graph_analytics(self, db: Session, *, review_limit: int = 20) -> dict[str, Any]:
        return engines.run_graph_analytics(db, review_limit=review_limit)

    def dedup_check(
        self,
        db: Session,
        *,
        entity_id: str | None,
        description: str | None,
        evidence: dict | None,
        exclude_contribution_id: str | None = None,
    ) -> dict[str, Any]:
        return engines.run_dedup_check(
            db,
            entity_id=entity_id,
            description=description,
            evidence=evidence,
            exclude_contribution_id=exclude_contribution_id,
        )

    def precheck_submission(self, db: Session, *, entity_id: str, evidence: dict | None) -> None:
        engines.run_anti_abuse_precheck(db, entity_id=entity_id, evidence=evidence)

    def match_capabilities(
        self,
        db: Session,
        *,
        task_id: str | None = None,
        contribution_type: str | None = None,
        limit: int = 5,
    ) -> dict[str, Any]:
        return engines.run_matching(
            db,
            task_id=task_id,
            contribution_type=contribution_type,
            limit=limit,
        )

    def register_entity(
        self,
        db: Session,
        *,
        entity_type: str,
        name: str,
        description: str | None,
        tags: list[str],
        capabilities: list[str],
        owner_id: str | None,
        creator_id: str | None,
    ):
        from intelligence.entity_registry import register_contribution_entity

        return register_contribution_entity(
            db,
            entity_type=entity_type,
            name=name,
            description=description,
            tags=tags,
            capabilities=capabilities,
            owner_id=owner_id,
            creator_id=creator_id,
        )

    def federation_export(self, db: Session, contribution_id: str, *, node_id: str | None = None):
        from intelligence.federation_intel import export_federation_intelligence_packet

        return export_federation_intelligence_packet(db, contribution_id, node_id=node_id)

    def federation_ingest_summary(self, packet: dict):
        from intelligence.federation_intel import summarize_federation_ingest

        return summarize_federation_ingest(packet)

    def entity_profile(self, db: Session, entity_id: str) -> dict | None:
        return engines.entity_intelligence_profile(db, entity_id)

    def intelligence_packet(self, db: Session, contribution_id: str) -> dict | None:
        packet = engines.build_intelligence_packet(db, contribution_id)
        if packet is None:
            return None
        return {**contribution_packet_header(), **packet}

    def load_contribution(self, db: Session, contribution_id: str) -> ContributionEvent | None:
        return (
            db.query(ContributionEvent)
            .options(
                joinedload(ContributionEvent.task),
                joinedload(ContributionEvent.participants),
            )
            .filter(ContributionEvent.id == contribution_id)
            .first()
        )

    async def run_study_agent(self, db: Session, **kwargs) -> dict:
        """Agent runtime — capability layer; emits InvocationTrace + optional protocol evidence."""
        return await engines.run_study_agent(db, **kwargs)

    def list_compute_providers(
        self,
        db: Session,
        *,
        capability: str | None = None,
        status: str = "active",
        initiator_entity_id: str | None = None,
        organization_entity_id: str | None = None,
        mesh_filter: bool = False,
    ) -> dict:
        return engines.run_list_compute_providers(
            db,
            capability=capability,
            status=status,
            initiator_entity_id=initiator_entity_id,
            organization_entity_id=organization_entity_id,
            mesh_filter=mesh_filter,
        )

    def register_compute_profile(
        self,
        db: Session,
        *,
        entity_id: str,
        profile: dict,
        owner_entity_id: str | None,
    ):
        return engines.run_register_compute_profile(
            db,
            entity_id=entity_id,
            profile=profile,
            owner_entity_id=owner_entity_id,
        )

    def heartbeat_compute_profile(
        self,
        db: Session,
        *,
        entity_id: str,
        status: str,
        owner_entity_id: str | None,
    ):
        return engines.run_heartbeat_compute_profile(
            db,
            entity_id=entity_id,
            status=status,
            owner_entity_id=owner_entity_id,
        )

    def schedule_compute_job(
        self,
        db: Session,
        *,
        capability: str,
        initiator_entity_id: str | None,
        contribution_id: str | None = None,
        task_id: str | None = None,
        constraints: dict | None = None,
    ) -> dict:
        return engines.run_schedule_compute_job(
            db,
            capability=capability,
            initiator_entity_id=initiator_entity_id,
            contribution_id=contribution_id,
            task_id=task_id,
            constraints=constraints,
        )

    def get_compute_job(self, db: Session, job_id: str) -> dict:
        return engines.run_get_compute_job(db, job_id)


capability_layer = CapabilityLayer()
