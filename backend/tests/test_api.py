"""Integration tests for PoCP AI Commons API endpoints.

These tests use the full FastAPI app with an in-memory SQLite database.
"""


class TestEntityEndpoints:
    """Integration tests for /api/v1/entities."""

    def test_create_human_entity(self, client):
        response = client.post(
            "/api/v1/entities",
            json={"entity_type": "human", "name": "Alice"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Alice"
        assert data["entity_type"] == "human"

    def test_get_entity(self, client, human_entity):
        response = client.get(f"/api/v1/entities/{human_entity.id}")
        assert response.status_code == 200
        assert response.json()["name"] == "TestUser"

    def test_get_entity_not_found(self, client):
        response = client.get("/api/v1/entities/nonexistent")
        assert response.status_code == 404

    def test_list_entities(self, client):
        # Create a few entities
        for name in ["Alice", "Bob", "Charlie"]:
            client.post("/api/v1/entities", json={"entity_type": "human", "name": name})

        response = client.get("/api/v1/entities")
        assert response.status_code == 200
        assert len(response.json()) >= 3

    def test_create_agent_entity(self, client, human_entity):
        response = client.post(
            "/api/v1/entities",
            json={
                "entity_type": "agent",
                "name": "HelperBot",
                "owner_id": human_entity.id,
            },
        )
        assert response.status_code == 201
        assert response.json()["entity_type"] == "agent"

    def test_invalid_entity_type(self, client):
        response = client.post(
            "/api/v1/entities",
            json={"entity_type": "invalid_type", "name": "Bad"},
        )
        assert response.status_code == 400


class TestTaskEndpoints:
    """Integration tests for /api/v1/tasks."""

    def test_create_task(self, client, human_entity):
        response = client.post(
            "/api/v1/tasks",
            json={
                "title": "Write documentation",
                "description": "Improve the README",
                "sponsor_id": human_entity.id,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Write documentation"
        assert data["status"] == "open"

    def test_get_task(self, client, human_entity, test_task):
        response = client.get(f"/api/v1/tasks/{test_task.id}")
        assert response.status_code == 200
        assert response.json()["title"] == "Test Task"

    def test_get_task_not_found(self, client):
        response = client.get("/api/v1/tasks/nonexistent")
        assert response.status_code == 404


class TestContributionEndpoints:
    """Integration tests for /api/v1/contributions."""

    def test_submit_contribution(self, client, human_entity, test_task):
        response = client.post(
            "/api/v1/contributions",
            json={
                "task_id": test_task.id,
                "primary_entity_id": human_entity.id,
                "contribution_type": "knowledge",
                "description": "Test contribution",
                "evidence": {"url": "https://example.com"},
                "participants": [
                    {"entity_id": human_entity.id, "role": "creator", "weight": 1.0}
                ],
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "submitted"

    def test_submit_contribution_task_not_found(self, client, human_entity):
        response = client.post(
            "/api/v1/contributions",
            json={
                "task_id": "nonexistent",
                "primary_entity_id": human_entity.id,
                "contribution_type": "knowledge",
                "description": "Test",
                "participants": [],
            },
        )
        assert response.status_code == 404

    def test_full_contribution_loop(self, client, human_entity, reviewer_entity, test_task, agent_entity, skill_entity):
        """Test the full loop: submit → AI verify → human approve."""
        # 1. Submit
        response = client.post(
            "/api/v1/contributions",
            json={
                "task_id": test_task.id,
                "primary_entity_id": human_entity.id,
                "contribution_type": "knowledge",
                "description": "Full loop test",
                "evidence": {"content": "test"},
                "participants": [
                    {"entity_id": human_entity.id, "role": "creator", "weight": 0.4},
                    {"entity_id": agent_entity.id, "role": "executor", "weight": 0.25},
                    {"entity_id": skill_entity.id, "role": "skill_provider", "weight": 0.15},
                ],
            },
        )
        assert response.status_code == 201
        contrib_id = response.json()["id"]

        # 2. AI verify
        response = client.post(
            f"/api/v1/contributions/{contrib_id}/verify",
            json={"model_provider": "deepseek", "score": 0.9, "feedback": "Good"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "ai_verified"

        # 3. Human approve
        response = client.post(
            f"/api/v1/contributions/{contrib_id}/approve",
            json={"reviewer_id": reviewer_entity.id, "feedback": "Approved"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "approved"

        # 4. Verify rewards were issued
        wallets = client.get("/api/v1/wallets").json()
        human_wallet = next((w for w in wallets if w["entity_id"] == human_entity.id), None)
        assert human_wallet is not None
        assert human_wallet["cp_balance"] > 0
        assert human_wallet["ai_credits"] > 0

    def test_reject_contribution(self, client, human_entity, reviewer_entity, test_task):
        """Test contribution rejection."""
        # Submit
        response = client.post(
            "/api/v1/contributions",
            json={
                "task_id": test_task.id,
                "primary_entity_id": human_entity.id,
                "contribution_type": "knowledge",
                "description": "Reject test",
                "evidence": {},
                "participants": [
                    {"entity_id": human_entity.id, "role": "creator", "weight": 1.0}
                ],
            },
        )
        contrib_id = response.json()["id"]

        # Reject
        response = client.post(
            f"/api/v1/contributions/{contrib_id}/reject",
            json={"reviewer_id": reviewer_entity.id, "feedback": "Does not meet standards"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "rejected"

    def test_self_approval_blocked(self, client, human_entity, test_task):
        """Self-approval should be rejected."""
        # Submit → verify → try self-approve
        response = client.post(
            "/api/v1/contributions",
            json={
                "task_id": test_task.id,
                "primary_entity_id": human_entity.id,
                "contribution_type": "knowledge",
                "description": "Self-approval test",
                "evidence": {},
                "participants": [
                    {"entity_id": human_entity.id, "role": "creator", "weight": 1.0}
                ],
            },
        )
        contrib_id = response.json()["id"]

        # Verify
        client.post(
            f"/api/v1/contributions/{contrib_id}/verify",
            json={"model_provider": "deepseek", "score": 0.9, "feedback": "OK"},
        )

        # Self-approve should fail
        response = client.post(
            f"/api/v1/contributions/{contrib_id}/approve",
            json={"reviewer_id": human_entity.id, "feedback": "Self approve"},
        )
        assert response.status_code == 400


class TestWalletEndpoints:
    """Integration tests for wallets and ledger."""

    def test_new_human_gets_registration_credits(self, client):
        response = client.post(
            "/api/v1/entities",
            json={"entity_type": "human", "name": "NewUser"},
        )
        entity_id = response.json()["id"]

        wallets = client.get("/api/v1/wallets").json()
        wallet = next((w for w in wallets if w["entity_id"] == entity_id), None)
        assert wallet is not None
        assert wallet["ai_credits"] == 100.0

    def test_get_wallet_by_entity(self, client, human_entity):
        # Trigger wallet creation via entity endpoints
        response = client.get(f"/api/v1/wallets/{human_entity.id}")
        # Wallet may not exist yet if no credits granted
        assert response.status_code in (200, 404)

    def test_ledger_has_registration_entry(self, client):
        client.post(
            "/api/v1/entities",
            json={"entity_type": "human", "name": "LedgerTest"},
        )

        ledger = client.get("/api/v1/ledger").json()
        reg_entries = [e for e in ledger if e["event_type"] == "registration_grant"]
        assert len(reg_entries) >= 1


class TestGraphEndpoint:
    """Integration tests for /api/v1/graph."""

    def test_empty_graph(self, client):
        response = client.get("/api/v1/graph")
        assert response.status_code == 200
        data = response.json()
        assert "nodes" in data
        assert "edges" in data

    def test_graph_with_contributions(self, client, human_entity, reviewer_entity, test_task):
        # Create a contribution
        client.post(
            "/api/v1/contributions",
            json={
                "task_id": test_task.id,
                "primary_entity_id": human_entity.id,
                "contribution_type": "knowledge",
                "description": "Graph test",
                "evidence": {},
                "participants": [
                    {"entity_id": human_entity.id, "role": "creator", "weight": 1.0}
                ],
            },
        )

        response = client.get("/api/v1/graph")
        assert response.status_code == 200
        data = response.json()
        node_ids = [n["id"] for n in data["nodes"]]
        assert human_entity.id in node_ids
