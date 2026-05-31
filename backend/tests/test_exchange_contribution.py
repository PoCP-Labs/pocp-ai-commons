"""Tests for exchange → contribution upgrade (Phase 4)."""

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models.contribution import ContributionEvent
from models.entity import Entity, EntityStatus, EntityType
from models.task import Task, TaskStatus
from models.wallet import CreditTransaction, CreditType, Wallet
from services.compute_receipt import build_compute_receipt
from services.compute_settlement import settle_bilateral
from services.exchange_contribution import publish_contribution_from_exchange


class ExchangeContributionTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        self.db.add_all(
            [
                Entity(
                    id="human-1",
                    entity_type=EntityType.human,
                    name="Consumer",
                    status=EntityStatus.active,
                ),
                Entity(
                    id="llm-1",
                    entity_type=EntityType.llm,
                    name="Provider",
                    status=EntityStatus.active,
                ),
            ]
        )
        self.db.add(
            Task(
                id="task-1",
                title="Promote exchange work",
                description="Test task",
                sponsor_id="human-1",
                status=TaskStatus.open,
            )
        )
        consumer = Wallet(entity_id="human-1", cp_balance=0, ai_credits=100)
        provider = Wallet(entity_id="llm-1", cp_balance=0, ai_credits=0)
        self.db.add(consumer)
        self.db.add(provider)
        self.db.flush()
        self.db.add(
            CreditTransaction(
                wallet_id=consumer.id,
                amount=-10,
                credit_type=CreditType.ai_credits,
                reason="compute_consumed:test",
            )
        )
        self.db.commit()

        receipt = build_compute_receipt(
            provider_entity_id="llm-1",
            provider_node_id="node-a",
            capability="llm_inference",
            adapter="mock",
            initiator_entity_id="human-1",
            job_id="job-promote",
            extra={
                "usage": {
                    "metering_mode": "token",
                    "pocp_tokens": 10,
                }
            },
        )
        result = settle_bilateral(self.db, receipt, consumer_entity_id="human-1")
        self.db.commit()
        self.exchange_id = result["exchange_id"]

    def tearDown(self):
        self.db.close()

    def test_publish_contribution_from_exchange(self):
        contribution = publish_contribution_from_exchange(
            self.db,
            exchange_id=self.exchange_id,
            human_entity_id="human-1",
            task_id="task-1",
            description="Promoted GPU inference notes",
        )
        self.db.commit()

        self.assertEqual(contribution.primary_entity_id, "human-1")
        self.assertEqual(contribution.task_id, "task-1")
        upgrade = (contribution.evidence or {}).get("exchange_upgrade") or {}
        self.assertEqual(upgrade.get("exchange_id"), self.exchange_id)
        self.assertEqual(upgrade.get("exchange_kind"), "compute")
        self.assertTrue(contribution.participants)
        roles = {p.role.value for p in contribution.participants}
        self.assertIn("creator", roles)
        self.assertIn("model_provider", roles)
        self.assertIn("witness", roles)
        self.assertTrue((contribution.evidence or {}).get("witness_required"))
        self.assertEqual((contribution.evidence or {}).get("contribution_path"), "exchange_upgrade")

    def test_publish_adds_graph_edges(self):
        contribution = publish_contribution_from_exchange(
            self.db,
            exchange_id=self.exchange_id,
            human_entity_id="human-1",
            task_id="task-1",
        )
        self.db.commit()

        from services.graph import build_contribution_graph

        graph = build_contribution_graph(self.db)
        ex_node = f"exchange:{self.exchange_id}"
        hub_node = f"contribution:{contribution.id}"
        node_ids = {n["id"] for n in graph["nodes"]}
        self.assertIn(ex_node, node_ids)
        self.assertIn(hub_node, node_ids)
        promoted = [
            e
            for e in graph["edges"]
            if e["relation"] == "promoted_to" and e["source"] == ex_node and e["target"] == hub_node
        ]
        self.assertEqual(len(promoted), 1)
        settled = [
            e
            for e in graph["edges"]
            if e["relation"] == "settled_exchange" and e["source"] == "human-1"
        ]
        self.assertEqual(len(settled), 1)

    def test_publish_idempotent_conflict(self):
        publish_contribution_from_exchange(
            self.db,
            exchange_id=self.exchange_id,
            human_entity_id="human-1",
            task_id="task-1",
        )
        self.db.commit()

        with self.assertRaises(Exception) as ctx:
            publish_contribution_from_exchange(
                self.db,
                exchange_id=self.exchange_id,
                human_entity_id="human-1",
                task_id="task-1",
            )
        self.assertEqual(getattr(ctx.exception, "status_code", None), 409)

        count = self.db.query(ContributionEvent).count()
        self.assertEqual(count, 1)


if __name__ == "__main__":
    unittest.main()
