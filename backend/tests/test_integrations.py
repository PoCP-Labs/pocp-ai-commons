import unittest

from services.agent_receipt import compute_receipt_hash, verify_agent_receipt
from services.provenance import attach_provenance_to_evidence, build_provenance_envelope, provenance_from_evidence
from services.code_attribution_bridge import build_code_attribution_context
from services.verifier_registry import load_verifier_providers


class ProvenanceTests(unittest.TestCase):
    def test_attach_provenance_roundtrip(self):
        evidence = attach_provenance_to_evidence(
            {"url": "https://example.com"},
            declared_by_entity_id="entity-1",
            creation_mode="ai_assisted",
            ai_tools_used=["cursor"],
            human_experts_cited=["github:rain"],
        )
        envelope = provenance_from_evidence(evidence)
        self.assertEqual(envelope["creation_mode"], "ai_assisted")
        self.assertEqual(envelope["envelope_version"], "octp-compatible-v0.1")
        self.assertIn("integrity", envelope)

    def test_build_provenance_envelope(self):
        envelope = build_provenance_envelope(
            declared_by_entity_id="entity-1",
            creation_mode="human_written",
        )
        self.assertEqual(envelope["declared_by_entity_id"], "entity-1")


class AgentReceiptTests(unittest.TestCase):
    def test_receipt_hash_stable(self):
        payload = {
            "spec_version": "pocp.agent_receipt.v0.1",
            "trace_id": "t1",
            "steps": [],
        }
        self.assertEqual(compute_receipt_hash(payload), compute_receipt_hash(payload))

    def test_unsigned_receipt_verify_false(self):
        receipt = {
            "spec_version": "pocp.agent_receipt.v0.1",
            "trace_id": "t1",
            "steps": [],
            "integrity": {
                "receipt_hash": "abc",
                "signature": "def",
                "signer_public_key": "00",
            },
        }
        self.assertFalse(verify_agent_receipt(receipt))


class VerifierRegistryTests(unittest.TestCase):
    def test_load_builtin_mock_verifier(self):
        providers = load_verifier_providers()
        names = {p.provider_name for p in providers}
        self.assertIn("mock", names)

    def test_genesis_witnesses_loaded_by_default(self):
        providers = load_verifier_providers()
        names = {p.provider_name for p in providers}
        self.assertIn("lumen-0", names)
        self.assertIn("desui", names)
        self.assertIn("clarion-0", names)


class ClarionUnifiedTests(unittest.TestCase):
    def test_score_context_for_verifier(self):
        from services.clarion import score_context_for_verifier

        scored = score_context_for_verifier(
            {
                "task": {"title": "Docs", "description": "Write setup guide"},
                "contribution": {
                    "description": "Added setup guide for beginners",
                    "evidence": {"url": "https://example.com/guide"},
                },
                "participants": [{"entity_id": "e1", "role": "creator"}],
            }
        )
        self.assertGreater(scored["avg_score"], 0.0)
        self.assertIn("rationale", scored)


class EvidenceGitTests(unittest.TestCase):
    def test_extract_empty_evidence(self):
        from services.evidence_git import validate_git_commits

        report = validate_git_commits({})
        self.assertEqual(report["checked_count"], 0)


class AttributionMerkleTests(unittest.TestCase):
    def test_build_and_verify_merkle_proof(self):
        from services.attribution_merkle import build_attribution_merkle_proof, verify_attribution_merkle_proof

        proof = build_attribution_merkle_proof({"artifact": "backend/services/proof.py"})
        if proof["leaf_count"] == 0:
            self.skipTest("no builders matched in this environment")
        slug = proof["builders"][0]["slug"]
        self.assertTrue(verify_attribution_merkle_proof(proof, slug))


class ReviewQueueTests(unittest.TestCase):
    def test_review_queue_import(self):
        from services.review_queue import list_human_review_queue

        self.assertTrue(callable(list_human_review_queue))


class CodeAttributionBridgeTests(unittest.TestCase):
    def test_matches_backend_path_hint(self):
        context = build_code_attribution_context({"artifact": "backend/services/proof.py"})
        self.assertTrue(context["path_hints"])
        self.assertTrue(context["builders_involved"] or context["matched_paths"])


class PortableReputationTests(unittest.TestCase):
    def test_validate_evidence_full_shape(self):
        from services.evidence_validate import validate_evidence_full

        report = validate_evidence_full({"url": "https://example.com"})
        self.assertIn("urls", report)
        self.assertIn("git", report)


class ProvenanceClaimsTests(unittest.TestCase):
    def test_verification_claims_in_envelope(self):
        evidence = attach_provenance_to_evidence(
            {"url": "https://example.com"},
            declared_by_entity_id="entity-1",
            verification_claims=[{"claim_type": "self_reviewed", "details": "demo"}],
        )
        envelope = provenance_from_evidence(evidence)
        self.assertEqual(len(envelope.get("verification_claims") or []), 1)


class ExternalInspirationTests(unittest.TestCase):
    def test_registry_loads_inspirations(self):
        from services.external_inspiration import list_inspirations, load_registry

        data = load_registry()
        self.assertEqual(data.get("registry"), "external_inspirations")
        inspirations = list_inspirations()
        slugs = {i["slug"] for i in inspirations}
        self.assertIn("octp", slugs)
        self.assertIn("meritocrab", slugs)
        self.assertIn("sourcecred", slugs)
        self.assertIn("poc-protocol-core", slugs)
        self.assertIn("mcp", slugs)

    def test_match_provenance_module(self):
        from services.external_inspiration import match_inspirations_for_module

        matches = match_inspirations_for_module("backend/services/provenance.py")
        slugs = {m["slug"] for m in matches}
        self.assertIn("octp", slugs)

    def test_build_context_includes_registry_summary(self):
        from services.external_inspiration import build_external_inspirations_context

        context = build_external_inspirations_context(
            {"_pocp": {"modules": ["backend/services/provenance.py"]}}
        )
        self.assertEqual(context["spec_version"], "pocp.external_inspirations.v0.1")
        self.assertTrue(context["matched_from_evidence"])
        self.assertGreater(len(context["registry_summary"]), 0)

    def test_inspiration_report_shape(self):
        from services.external_inspiration import build_inspiration_report

        report = build_inspiration_report()
        self.assertGreater(report["inspiration_count"], 0)
        self.assertGreater(report["contribution_count"], 0)
        self.assertIn("octp", report["inspirations"])
        self.assertIn("chaoss", report["inspirations"])
        self.assertIn("sourcecred", report["inspirations"])
        evaluating = [s for s, i in report["inspirations"].items() if i.get("status") == "evaluating"]
        self.assertIn("mcp", evaluating)

    def test_find_inspiration_by_entity_id(self):
        from services.external_inspiration import find_inspiration_by_entity_id

        item = find_inspiration_by_entity_id("pocp-insp-octp")
        self.assertIsNotNone(item)
        self.assertEqual(item["slug"], "octp")

    def test_build_context_with_module_hints(self):
        from services.external_inspiration import build_external_inspirations_context

        context = build_external_inspirations_context(
            None,
            module_hints=["backend/services/federation_sync.py"],
        )
        slugs = {m["slug"] for m in context["matched_from_evidence"]}
        self.assertIn("forgefed", slugs)


class FederationCommunityTests(unittest.TestCase):
    def test_peer_entity_id_stable(self):
        from services.federation_community import peer_entity_id

        self.assertEqual(peer_entity_id("node-a"), "pocp-entity-federation-peer-node-a")
        self.assertTrue(peer_entity_id("community/b").startswith("pocp-entity-federation-peer-"))

    def test_local_entity_id(self):
        from services.federation_community import local_federation_entity_id

        self.assertEqual(local_federation_entity_id(), "pocp-entity-federation-local")

    def test_federation_import_hub_id(self):
        from services.federation_community import federation_import_hub_id

        self.assertTrue(federation_import_hub_id("abc").startswith("federation-import:"))


class CommunityPartnerTests(unittest.TestCase):
    def test_registry_loads_partners(self):
        from services.community_partner import list_partners, load_registry

        data = load_registry()
        self.assertEqual(data.get("registry"), "community_partners")
        slugs = {p["slug"] for p in list_partners()}
        self.assertIn("forgefed", slugs)
        self.assertIn("ollama", slugs)
        self.assertIn("akash", slugs)

    def test_benchmark_inspirations_registered(self):
        from services.external_inspiration import get_inspiration, list_inspirations

        slugs = {i["slug"] for i in list_inspirations()}
        for slug in ("gensyn", "akash", "gitcoin", "mcp", "provenancekit", "io-net"):
            self.assertIn(slug, slugs)
        self.assertIsNotNone(get_inspiration("akash"))
        declined = {i["slug"] for i in list_inspirations(include_declined=True) if i.get("declined")}
        self.assertIn("bittensor", declined)
        self.assertIn("virtuals-protocol", declined)

    def test_match_witness_partners(self):
        from services.community_partner import match_partners_for_capability

        offers = match_partners_for_capability("witness")
        slugs = {p["slug"] for p in offers}
        self.assertTrue(len(offers) > 0)
        self.assertTrue("chaoss" in slugs or "meritocrab" in slugs)

    def test_match_training_partners(self):
        from services.community_partner import match_partners_for_capability

        offers = match_partners_for_capability("training")
        slugs = {p["slug"] for p in offers}
        self.assertIn("gensyn", slugs)

    def test_outreach_report_shape(self):
        from services.community_partner import build_outreach_report

        report = build_outreach_report()
        self.assertGreater(report["partner_count"], 0)
        self.assertIn("by_status", report)
        self.assertIn("high_priority_prospects", report)

    def test_build_community_partner_context(self):
        from types import SimpleNamespace

        from services.community_partner import build_community_partner_context

        contribution = SimpleNamespace(
            id="c1",
            primary_entity_id="e1",
            contribution_type="documentation",
            evidence={"_pocp": {"tags": ["verify", "research"]}},
            task=SimpleNamespace(title="Research doc", description="Write guide"),
        )
        ctx = build_community_partner_context(None, contribution, contribution.evidence)
        self.assertEqual(ctx["spec_version"], "pocp.community_partner_context.v0.1")
        self.assertIn("capability_discovery", ctx)

    def test_build_federation_import_context_shape(self):
        from services.federation_community import build_federation_import_context

        ctx = build_federation_import_context(
            None,
            contribution_id="c1",
            primary_entity_id="e1",
        )
        self.assertEqual(ctx["spec_version"], "pocp.federation_import_context.v0.1")
        self.assertEqual(ctx["contribution_id"], "c1")

    def test_outreach_event_types(self):
        from services.community_partner import VALID_OUTREACH_EVENTS

        self.assertIn("contact_sent", VALID_OUTREACH_EVENTS)
        self.assertIn("status_advanced", VALID_OUTREACH_EVENTS)

    def test_outreach_status_survives_entity_refresh(self):
        from database import SessionLocal, init_db
        from models.entity import Entity
        from services.community_partner import (
            build_outreach_report,
            ensure_partner_entities,
            get_partner,
            record_partner_outreach,
        )

        init_db()
        db = SessionLocal()
        try:
            ensure_partner_entities(db)
            record_partner_outreach(
                db,
                "forgefed",
                event_type="contact_sent",
                notes="test outreach",
                new_status="in_conversation",
            )
            db.commit()
            ensure_partner_entities(db)
            entity_id = get_partner("forgefed")["entity_id"]
            entity = db.get(Entity, entity_id)
            self.assertEqual((entity.metadata_ or {}).get("partnership_status"), "in_conversation")
            report = build_outreach_report(db)
            self.assertEqual(report["partners"]["forgefed"]["partnership_status"], "in_conversation")
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
