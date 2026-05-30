"""Integration tests for the COMPLETE genesis loop.

GENESIS.md §4 defines the genesis cycle:
  Contribution → Verification → CP → AI Credits → AI Use → More Contribution

This test proves the entire loop works end-to-end:
1. Register human → get 100 AI Credits
2. Create task
3. Submit contribution → AI verify → human approve → earn more Credits
4. Spend Credits on AI chat → credits deducted → ledger written
5. Verify the loop is closed
"""


class TestGenesisLoop:
    """End-to-end test of the complete genesis cycle."""

    def test_full_genesis_loop(self, client):
        """Prove the genesis loop works: register → contribute → earn → spend → loop."""

        # Step 1: Register human → receives 100 AI Credits
        register_resp = client.post(
            "/api/v1/entities",
            json={"entity_type": "human", "name": "GenesisUser"},
        )
        assert register_resp.status_code == 201
        entity_id = register_resp.json()["id"]

        # Verify registration credits
        wallets = client.get("/api/v1/wallets").json()
        wallet = next(w for w in wallets if w["entity_id"] == entity_id)
        assert wallet["ai_credits"] == 100.0
        initial_credits = wallet["ai_credits"]

        # Step 2: Create a contribution task
        task_resp = client.post(
            "/api/v1/tasks",
            json={
                "title": "Genesis Loop Test Task",
                "description": "Prove the genesis loop works end-to-end",
                "sponsor_id": entity_id,
            },
        )
        assert task_resp.status_code == 201
        task_id = task_resp.json()["id"]

        # Step 3: Submit contribution
        contrib_resp = client.post(
            "/api/v1/contributions",
            json={
                "task_id": task_id,
                "primary_entity_id": entity_id,
                "contribution_type": "knowledge",
                "description": "Genesis loop integration test",
                "evidence": {"type": "integration_test", "result": "pass"},
                "participants": [
                    {"entity_id": entity_id, "role": "creator", "weight": 1.0}
                ],
            },
        )
        assert contrib_resp.status_code == 201
        contrib_id = contrib_resp.json()["id"]
        assert contrib_resp.json()["status"] == "submitted"

        # Step 4: AI verification
        verify_resp = client.post(
            f"/api/v1/contributions/{contrib_id}/verify",
            json={"model_provider": "deepseek", "score": 0.9, "feedback": "Genesis loop verified"},
        )
        assert verify_resp.status_code == 200
        assert verify_resp.json()["status"] == "ai_verified"

        # Step 5: Human approval → earns CP + AI Credits
        # Create a reviewer
        reviewer_resp = client.post(
            "/api/v1/entities",
            json={"entity_type": "human", "name": "GenesisReviewer"},
        )
        assert reviewer_resp.status_code == 201
        reviewer_id = reviewer_resp.json()["id"]

        approve_resp = client.post(
            f"/api/v1/contributions/{contrib_id}/approve",
            json={"reviewer_id": reviewer_id, "feedback": "Genesis loop approved"},
        )
        assert approve_resp.status_code == 200
        assert approve_resp.json()["status"] == "approved"

        # Verify rewards were issued
        wallets = client.get("/api/v1/wallets").json()
        wallet = next(w for w in wallets if w["entity_id"] == entity_id)
        assert wallet["cp_balance"] > 0
        assert wallet["ai_credits"] > initial_credits  # Earned more credits!
        credits_after_contribution = wallet["ai_credits"]

        # Step 6: AI Use — spend credits on AI chat (THE MISSING HALF)
        chat_resp = client.post(
            "/api/v1/ai/chat",
            params={"entity_id": entity_id, "prompt": "What is PoCP?"},
        )
        assert chat_resp.status_code == 200
        chat_data = chat_resp.json()
        assert chat_data["status"] == "completed"
        assert "response" in chat_data
        assert chat_data["credits_deducted"] > 0

        # Verify credits were deducted
        wallets = client.get("/api/v1/wallets").json()
        wallet = next(w for w in wallets if w["entity_id"] == entity_id)
        assert wallet["ai_credits"] < credits_after_contribution
        assert wallet["ai_credits"] > 0  # Still has some left

        # Step 7: Verify ledger has both contribution and usage records
        ledger = client.get("/api/v1/ledger").json()
        contrib_ledger = [e for e in ledger if e["event_type"] == "contribution_approved"]
        usage_ledger = [e for e in ledger if e["event_type"] == "ai_credits_spent"]
        assert len(contrib_ledger) >= 1
        assert len(usage_ledger) >= 1

        # Step 8: Verify AI usage history
        history = client.get(f"/api/v1/ai/chat/{entity_id}/history").json()
        assert len(history) >= 1
        assert history[0]["status"] == "completed"
        assert history[0]["credits_deducted"] > 0

        # Step 9: Verify usage stats
        stats = client.get(f"/api/v1/ai/chat/{entity_id}/stats").json()
        assert stats["total_queries"] >= 1
        assert stats["total_credits_spent"] > 0

        # GENESIS LOOP PROVEN:
        # register → earn credits → contribute → earn more → spend credits → loop continues
        print(f"✅ Genesis loop proven!")
        print(f"   Registration credits: {initial_credits}")
        print(f"   After contribution: {credits_after_contribution}")
        print(f"   After AI use: {wallet['ai_credits']}")
        print(f"   CP earned: {wallet['cp_balance']}")

    def test_insufficient_credits(self, client):
        """Test that AI chat fails gracefully when credits are insufficient."""
        # Create entity with no credits (agent)
        owner_resp = client.post(
            "/api/v1/entities",
            json={"entity_type": "human", "name": "Owner"},
        )
        owner_id = owner_resp.json()["id"]

        agent_resp = client.post(
            "/api/v1/entities",
            json={
                "entity_type": "agent",
                "name": "BrokeAgent",
                "owner_id": owner_id,
            },
        )
        agent_id = agent_resp.json()["id"]

        # Agent has no wallet with credits
        chat_resp = client.post(
            "/api/v1/ai/chat",
            params={"entity_id": agent_id, "prompt": "Hello"},
        )
        # Should fail - no wallet or insufficient credits
        assert chat_resp.status_code in (404, 402)

    def test_empty_prompt_rejected(self, client, human_entity):
        """Empty prompt should be rejected."""
        chat_resp = client.post(
            "/api/v1/ai/chat",
            params={"entity_id": human_entity.id, "prompt": "   "},
        )
        assert chat_resp.status_code == 400

    def test_credits_deducted_recorded_in_ledger(self, client, human_entity):
        """AI Credits spending must be recorded in Ledger Memory (Protocol Principle 8)."""
        # Initial ledger count
        ledger_before = client.get("/api/v1/ledger").json()
        usage_count_before = len([e for e in ledger_before if e["event_type"] == "ai_credits_spent"])

        # Use AI
        client.post(
            "/api/v1/ai/chat",
            params={"entity_id": human_entity.id, "prompt": "Test ledger recording"},
        )

        # Verify new ledger entry
        ledger_after = client.get("/api/v1/ledger").json()
        usage_count_after = len([e for e in ledger_after if e["event_type"] == "ai_credits_spent"])
        assert usage_count_after > usage_count_before

        # Verify ledger entry has correct payload
        usage_entries = [e for e in ledger_after if e["event_type"] == "ai_credits_spent"]
        latest = usage_entries[0]
        assert "entity_id" in latest["payload"]
        assert "credits_deducted" in latest["payload"]
        assert "remaining_balance" in latest["payload"]
        assert latest["payload"]["entity_id"] == human_entity.id
