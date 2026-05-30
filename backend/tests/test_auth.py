"""Integration tests for authentication and token management."""

import pytest
from fastapi.testclient import TestClient


class TestAuthEndpoints:
    """Integration tests for /api/v1/auth."""

    def test_get_token_demo_mode(self, client, human_entity):
        """In demo mode, anyone can get a token."""
        response = client.post(
            "/api/v1/auth/token",
            params={"entity_id": human_entity.id},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "Bearer"
        assert data["mode"] == "demo"

    def test_get_token_nonexistent_entity_demo(self, client):
        """In demo mode, token works even for non-existent entity."""
        response = client.post(
            "/api/v1/auth/token",
            params={"entity_id": "nonexistent-id"},
        )
        # Demo mode allows this
        assert response.status_code == 200

    def test_token_contains_entity_id(self, client, human_entity):
        """Token response should include entity_id for reference."""
        response = client.post(
            "/api/v1/auth/token",
            params={"entity_id": human_entity.id},
        )
        assert response.status_code == 200
        assert response.json()["entity_id"] == human_entity.id


class TestEntityService:
    """Integration tests for entity service layer."""

    def test_create_entity_via_service(self, client):
        """Test entity creation with proper validation."""
        response = client.post(
            "/api/v1/entities",
            json={"entity_type": "human", "name": "ServiceUser"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "ServiceUser"
        assert data["status"] == "active"

    def test_create_entity_with_invalid_type(self, client):
        """Invalid entity type should return 400."""
        response = client.post(
            "/api/v1/entities",
            json={"entity_type": "dragon", "name": "NotValid"},
        )
        assert response.status_code == 400

    def test_list_entities_with_filter(self, client):
        """Test entity filtering."""
        # Create different entity types
        client.post("/api/v1/entities", json={"entity_type": "human", "name": "Human1"})
        client.post("/api/v1/entities", json={"entity_type": "human", "name": "Human2"})
        client.post("/api/v1/entities", json={"entity_type": "agent", "name": "Bot1"})

        # Filter by type
        response = client.get("/api/v1/entities?entity_type=human")
        assert response.status_code == 200
        humans = [e for e in response.json() if e["entity_type"] == "human"]
        assert len(humans) >= 2

    def test_get_entity_not_found(self, client):
        response = client.get("/api/v1/entities/nonexistent-id")
        assert response.status_code == 404


class TestHealthEndpoint:
    """Integration tests for /health."""

    def test_health_check(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "pocp-ai-commons"
        assert data["database_status"] == "connected"

    def test_health_has_version(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert "version" in response.json()


class TestRateLimiting:
    """Integration tests for rate limiting middleware."""

    def test_normal_requests_pass(self, client):
        """Normal request volume should pass."""
        for _ in range(5):
            response = client.get("/health")
            assert response.status_code == 200


class TestEdgeCases:
    """Edge case and error handling tests."""

    def test_create_task_without_sponsor(self, client, human_entity):
        """Task can be created without sponsor."""
        response = client.post(
            "/api/v1/tasks",
            json={"title": "No Sponsor Task"},
        )
        assert response.status_code == 201

    def test_contribution_to_nonexistent_task(self, client, human_entity):
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

    def test_verify_nonexistent_contribution(self, client):
        response = client.post(
            "/api/v1/contributions/nonexistent/verify",
            json={"model_provider": "deepseek", "score": 0.9},
        )
        assert response.status_code == 404

    def test_approve_nonexistent_contribution(self, client, human_entity):
        response = client.post(
            "/api/v1/contributions/nonexistent/approve",
            json={"reviewer_id": human_entity.id},
        )
        assert response.status_code == 404

    def test_reject_nonexistent_contribution(self, client, human_entity):
        response = client.post(
            "/api/v1/contributions/nonexistent/reject",
            json={"reviewer_id": human_entity.id},
        )
        assert response.status_code == 404

    def test_pagination_skip_limit(self, client):
        """Test pagination with skip and limit."""
        # Create entities
        for i in range(5):
            client.post("/api/v1/entities", json={"entity_type": "human", "name": f"User{i}"})

        # Test limit
        response = client.get("/api/v1/entities?limit=2")
        assert response.status_code == 200
        assert len(response.json()) <= 2

        # Test skip
        response = client.get("/api/v1/entities?skip=3")
        assert response.status_code == 200

    def test_wallet_balance_starts_at_zero_for_non_human(self, client):
        """Non-human entities don't get registration credits."""
        # Create human first (needed as owner)
        human_resp = client.post("/api/v1/entities", json={"entity_type": "human", "name": "Owner"})
        owner_id = human_resp.json()["id"]

        # Create agent
        response = client.post(
            "/api/v1/entities",
            json={"entity_type": "agent", "name": "Bot", "owner_id": owner_id},
        )
        assert response.status_code == 201
        agent_id = response.json()["id"]

        # Agent should not have a wallet with credits
        wallets = client.get("/api/v1/wallets").json()
        agent_wallet = next((w for w in wallets if w["entity_id"] == agent_id), None)
        # Agent wallet may not exist or should have 0 credits
        if agent_wallet:
            assert agent_wallet["ai_credits"] == 0
            assert agent_wallet["cp_balance"] == 0
