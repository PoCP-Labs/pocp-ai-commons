"""Capability Internet Protocol model proposal.

Adapt this file to the repository's existing SQLAlchemy/Base style before runtime import.
This file is intentionally a proposal/skeleton so it does not break the current Genesis Loop.
"""

from __future__ import annotations
import enum

class CapabilityEntityType(str, enum.Enum):
    human = "human"
    agent = "agent"
    llm = "llm"
    skill = "skill"
    tool = "tool"
    dataset = "dataset"
    workflow = "workflow"
    compute_node = "compute_node"
    verifier_node = "verifier_node"
    reviewer_node = "reviewer_node"
    organization = "organization"
    community = "community"
    sponsor = "sponsor"
    protocol_treasury = "protocol_treasury"
    relay_node = "relay_node"
    indexer_node = "indexer_node"
    governance_node = "governance_node"

class NodeType(str, enum.Enum):
    light = "light"
    service = "service"
    compute = "compute"
    verifier = "verifier"
    reviewer = "reviewer"
    relay = "relay"
    indexer = "indexer"
    governance = "governance"
    treasury = "treasury"

class InvocationStatus(str, enum.Enum):
    created = "created"
    accepted = "accepted"
    running = "running"
    completed = "completed"
    proof_submitted = "proof_submitted"
    verified = "verified"
    settled = "settled"
    failed = "failed"
    disputed = "disputed"
