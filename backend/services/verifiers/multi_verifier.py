import json
from statistics import median

from sqlalchemy.orm import Session

from models.contribution import AiVerifierResult, ContributionEvent, ContributionStatus
from services.llm_language import infer_context_language
from services.provenance import provenance_from_evidence
from services.verifier_registry import load_verifier_providers
from services.verifiers.mock_verifier import MockVerifier


class MultiVerifierService:
    def __init__(self):
        self.providers = load_verifier_providers()

    async def verify_contribution(self, db: Session, contribution: ContributionEvent) -> dict:
        task = contribution.task
        context = {
            "task": {
                "id": getattr(task, "id", None),
                "title": getattr(task, "title", None),
                "description": getattr(task, "description", None),
            },
            "contribution": {
                "id": contribution.id,
                "type": contribution.contribution_type,
                "description": contribution.description,
                "evidence": contribution.evidence,
                "content_hash": (contribution.evidence or {}).get("_pocp", {}).get("content_hash"),
                "primary_entity_id": contribution.primary_entity_id,
                "provenance": provenance_from_evidence(contribution.evidence),
            },
            "participants": [
                {
                    "entity_id": p.entity_id,
                    "role": p.role.value,
                    "weight": p.weight,
                    "evidence": p.evidence,
                }
                for p in contribution.participants
            ],
        }

        results = []
        for provider in self.providers:
            if hasattr(provider, "available") and not provider.available:
                continue
            try:
                results.append(await provider.verify(context))
            except Exception as exc:
                results.append(await MockVerifier().verify({**context, "provider_error": str(exc)}))

        if not results:
            results = [await MockVerifier().verify(context)]

        suggested_cp_values = [r.suggested_cp for r in results]
        suggested_credits_values = [r.suggested_credits for r in results]
        avg_quality = sum(r.quality for r in results) / len(results)
        avg_task_match = sum(r.task_match for r in results) / len(results)
        avg_originality = sum(r.originality for r in results) / len(results)
        avg_impact = sum(r.impact for r in results) / len(results)
        avg_evidence = sum(r.evidence_score for r in results) / len(results)
        avg_risk = sum(r.risk_score for r in results) / len(results)
        avg_score = (avg_quality + avg_task_match + avg_originality + avg_impact + avg_evidence) / 5
        disagreement_high = max(suggested_cp_values) - min(suggested_cp_values) > 30 if len(results) > 1 else False
        passed = avg_score >= 0.7 and avg_risk <= 0.5 and not disagreement_high

        provider_payload = [r.model_dump() for r in results]
        consensus = {
            "language_hint": infer_context_language(context),
            "avg_score": round(avg_score, 4),
            "avg_quality": round(avg_quality, 4),
            "avg_task_match": round(avg_task_match, 4),
            "avg_originality": round(avg_originality, 4),
            "avg_impact": round(avg_impact, 4),
            "avg_evidence": round(avg_evidence, 4),
            "avg_risk": round(avg_risk, 4),
            "suggested_cp": round(median(suggested_cp_values), 2),
            "suggested_credits": round(median(suggested_credits_values), 2),
            "disagreement_high": disagreement_high,
            "passed": passed,
            "provider_results": provider_payload,
        }

        db.add(
            AiVerifierResult(
                contribution_id=contribution.id,
                model_provider="multi_consensus",
                score=avg_score,
                feedback=json.dumps(consensus, ensure_ascii=False),
                passed=passed,
            )
        )
        for r in results:
            db.add(
                AiVerifierResult(
                    contribution_id=contribution.id,
                    model_provider=r.provider,
                    score=(r.task_match + r.quality + r.originality + r.impact + r.evidence_score) / 5,
                    feedback=json.dumps(r.model_dump(), ensure_ascii=False),
                    passed=r.risk_score <= 0.5 and r.quality >= 0.6,
                )
            )

        contribution.status = ContributionStatus.ai_verified if passed else ContributionStatus.submitted
        db.flush()
        return consensus
