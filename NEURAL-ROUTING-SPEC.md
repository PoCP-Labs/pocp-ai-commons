# Neural Routing Spec

## Purpose

The Neural Routing Layer is the task routing brain of PoCP Neural Commons Network.

It maps tasks to capabilities.

## Input

A task may include title, description, task type, required output, acceptance criteria, budget, urgency, privacy requirements, preferred entities, excluded entities, and risk tolerance.

## Output

The router returns an Execution Plan.

```json
{
  "task_id": "task_001",
  "recommended_path": [
    {
      "step": 1,
      "entity_type": "agent",
      "capability": "task_planning",
      "entity_id": "agent_001"
    },
    {
      "step": 2,
      "entity_type": "skill",
      "capability": "code_review",
      "entity_id": "skill_001"
    },
    {
      "step": 3,
      "entity_type": "llm",
      "capability": "reasoning",
      "entity_id": "llm_001"
    },
    {
      "step": 4,
      "entity_type": "compute_node",
      "capability": "gpu_inference",
      "entity_id": "compute_001"
    },
    {
      "step": 5,
      "entity_type": "reviewer",
      "capability": "human_review",
      "entity_id": "human_002"
    }
  ],
  "estimated_cost": {
    "AIC": 20,
    "CC": 10,
    "PT": 0
  },
  "risk_level": "medium",
  "explanation": "Selected based on task type, reputation, cost, and availability."
}
```

## Routing Factors

The router should consider task type, capability match, price, availability, reputation, risk, past success rate, latency, privacy requirement, governance policy, sponsor pool, and user preference.

## Routing Modes

```text
manual
rule_based
ai_assisted
market_based
reputation_weighted
sponsored
governance_constrained
```

## MVP Routing

Initial implementation can be rule-based.

Examples:

```text
task_type=code → CodeAgent + CodeReviewSkill + LLM + HumanReviewer
task_type=study → StudyAgent + StudySkill + LLM
task_type=compute → ComputeNode + VerifierNode
task_type=translation → TranslationSkill + LLM + Reviewer
```

## Routing Logs

Every routing decision should be logged:

- task id;
- candidate capabilities;
- selected capabilities;
- estimated cost;
- risk score;
- rationale;
- rejected candidates;
- final outcome.

## Feedback Loop

After task completion:

- update success rate;
- update entity reputation;
- update capability reputation;
- update cost estimates;
- update routing policy.

## Principle

Routing is not only optimization.

Routing is value coordination across intelligent entities.

PoCP begins with contribution.
