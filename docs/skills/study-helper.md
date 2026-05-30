# Study Helper Skill — Specification

> **Purpose:** Help learners organize, structure, and master study materials through verified contribution.
>
> **Type:** PoCP Skill Entity
> **Status:** Draft Specification
> **Version:** 1.0.0
> **Skill ID:** `skill:study-helper:v1`

---

## 1. Overview

The **Study Helper Skill** is a PoCP Skill Entity that assists humans and agents in transforming raw study materials (notes, lectures, textbooks) into structured, verified knowledge artifacts.

In the PoCP ecosystem, the Study Helper Skill occupies a unique position:

- It is **used by** humans (as the primary contributor) and agents (as executors)
- It **produces** contribution events with traceable evidence
- Its output can be **verified** by AI verifiers and **approved** by human reviewers
- It accumulates **reputation** as a Skill Entity over time

---

## 2. Purpose

The Study Helper Skill exists to answer:

> "How can a learner turn scattered study material into a verifiable contribution — earning AI Credits while improving their own understanding?"

### Primary Goals

1. **Knowledge Structuring** — Transform raw study material into organized, consumable formats (notes, summaries, flashcards, mind maps)
2. **Comprehension Verification** — Generate self-assessment questions and practice exercises that prove the contributor understands the material
3. **Contribution Enablement** — Structure output so it can be submitted as a PoCP contribution event, verified by AI, and approved by humans
4. **Reproducibility** — Produce artifacts that other learners can use, review, or build upon

---

## 3. Entity Relationship

```text
Human (Creator)
  │  owns / uses
  ├── StudyAgent (Agent Entity)
  │     │  invokes
  │     └── Study Helper Skill (Skill Entity)
  │           │  calls
  │           └── LLM (e.g. DeepSeek, GPT-4o)
  │
  ▼
Contribution Event
  ├── Primary Entity: Human
  ├── Participants: Agent (executor), Skill (skill_provider), LLM (model_provider)
  └── Status: submitted → ai_verified → approved/rejected
```

### Entity Types Involved

| Entity | Role in Contribution | Weight Range |
|--------|---------------------|-------------|
| Human | Creator — authors, refines, submits | 0.35–0.50 |
| Agent | Executor — organizes, formats, structures | 0.20–0.35 |
| Skill | Skill Provider — provides template, rubric | 0.10–0.20 |
| LLM | Model Provider — generates reasoning | < 0.10 |
| Human Reviewer | Final approver | advisory |

---

## 4. Inputs

The Study Helper Skill accepts the following inputs:

### Required Inputs

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `study_material` | text | The raw content to be structured | Lecture notes, textbook chapter, article |
| `subject` | string | Academic subject or domain | "R Language Programming", "Linear Algebra" |
| `output_format` | enum | Desired output structure | `study_notes`, `flashcards`, `summary`, `mind_map`, `practice_questions` |

### Optional Inputs

| Field | Type | Description | Default |
|-------|------|-------------|---------|
| `difficulty` | enum | `beginner`, `intermediate`, `advanced` | `intermediate` |
| `language` | string | Output language | `en` |
| `max_length` | integer | Maximum output length (words) | 2000 |
| `focus_areas` | string[] | Specific topics to emphasize | `["matrix()", "apply()", "%*%"]` |
| `include_examples` | boolean | Include runnable code examples | `true` |

### Input Validation Rules

- `study_material`: Minimum 100 characters, maximum 50,000 characters
- `output_format`: Must be one of the defined enum values
- `focus_areas`: Maximum 10 items
- `study_material` must be in a detectable language (ISO 639-1)

---

## 5. Outputs

The Study Helper Skill produces structured outputs ready for contribution submission.

### Standard Output Structure

```json
{
  "metadata": {
    "skill_id": "skill:study-helper:v1",
    "version": "1.0.0",
    "generated_at": "2026-05-30T00:00:00Z",
    "input_summary": {
      "subject": "R Language Programming",
      "output_format": "study_notes",
      "material_length": 3421
    }
  },
  "content": {
    "title": "R Matrix Operations — Study Notes",
    "sections": [
      {
        "heading": "Creating Matrices",
        "body": "Use `matrix()` to create matrices...",
        "code_examples": [
          "matrix(1:9, nrow = 3, byrow = TRUE)"
        ],
        "key_concepts": ["matrix() function", "dim parameter", "byrow"]
      }
    ],
    "summary": "Covers matrix creation, indexing, and arithmetic operations..."
  },
  "assessment": {
    "practice_questions": [
      {
        "question": "What function creates a matrix from a vector?",
        "answer": "matrix()",
        "difficulty": "easy"
      }
    ],
    "self_check_prompts": [
      "Can you explain the difference between `*` and `%*%`?"
    ]
  },
  "contribution_evidence": {
    "estimated_effort": "2 hours",
    "originality_score": 0.75,
    "coverage": ["matrix_creation", "indexing", "arithmetic", "apply_functions"],
    "quality_flags": []
  }
}
```

### Output Quality Guarantees

| Criterion | Requirement |
|-----------|------------|
| Accuracy | All code examples must be syntactically valid |
| Structure | Output must follow the defined schema |
| Completeness | All key concepts from input must be covered |
| Clarity | Language must be accessible at the target difficulty level |
| Attribution | Sources must be cited where applicable |

---

## 6. Verification Rubric

When a contribution using the Study Helper Skill is submitted, AI verifiers and human reviewers evaluate it against the following rubric.

### AI Verifier Rubric (Score 0.0–1.0)

| Criterion | Weight | What to Evaluate |
|-----------|--------|-----------------|
| Task Match | 0.15 | Does the output match the requested `output_format` and `subject`? |
| Accuracy | 0.25 | Are facts, code, and concepts correct? No hallucinations? |
| Completeness | 0.20 | Does it cover the key topics from the input material? |
| Structure | 0.10 | Is the output well-organized with clear headings and logical flow? |
| Originality | 0.10 | Does the contributor add their own explanation, not just copy-paste? |
| Readability | 0.10 | Is the language appropriate for the target difficulty level? |
| Evidence Quality | 0.10 | Are code examples runnable? Are sources cited? |

**AI Verifier Decision:**

| Score Range | Recommendation |
|-------------|---------------|
| 0.80–1.00 | ✅ Recommend approve |
| 0.60–0.79 | ⚠️ Recommend approve with minor improvements suggested |
| 0.40–0.59 | 🔄 Request revision with specific feedback |
| 0.00–0.39 | ❌ Recommend reject — insufficient quality |

### Human Reviewer Rubric (Binary: Approve / Reject)

| Check | Question | Must Pass? |
|-------|----------|------------|
| Authenticity | Is this clearly the contributor's own work? | ✅ Yes |
| Value | Does this help other learners? | ✅ Yes |
| Accuracy (Spot Check) | Random test: are 3 key claims correct? | ✅ Yes |
| AI Agreement | Do you agree with the AI verifier's score (±0.15)? | Recommended |
| Bad Faith | Any signs of gaming, plagiarism, or low effort? | ✅ Must be clean |
| Coverage Gap | Does the output miss important concepts from the input? | ⚠️ Flag if gap > 30% |

### Rubric for Reviewers

```text
APPROVE if:
  - Work is authentic and adds genuine learning value
  - AI score >= 0.60 (or reviewer independently judges quality)
  - No signs of bad faith or gaming

REJECT if:
  - Plagiarism or AI-generated without human refinement
  - Multiple factual errors (more than 2)
  - Clearly low effort relative to the task description
  - AI score < 0.40 and reviewer agrees

REQUEST REVISION if:
  - Work is genuine but incomplete or unclear
  - AI score 0.40–0.59 and reviewer sees potential
```

---

## 7. Example Contribution Flow

### Step 1: Human selects task

> **Task:** "Organize R Language Matrix Study Notes"
> **Skill Used:** Study Helper Skill
> **Agent:** StudyAgent

### Step 2: Skill processes input

- Input: Raw lecture notes on R matrix operations (~3000 chars)
- Output: Structured study notes with code examples + practice questions

### Step 3: Human refines and submits

- Human reviews, adds personal explanations, fixes inaccuracies
- Submits as a ContributionEvent with full participant mapping

### Step 4: AI verifier scores

- Score: 0.88 → "Notes cover key matrix concepts with accurate R syntax. Ready for human review."

### Step 5: Human reviewer approves

- Feedback: "Excellent structure. Approved for CP and AI Credits."
- CP and AI Credits are distributed per participant weights

---

## 8. Initial Seed Configuration

For MVP seeding, the Study Helper Skill should be created as:

```json
{
  "entity": {
    "entity_type": "skill",
    "name": "Study Helper Skill",
    "description": "Learning companion skill for organizing study materials, generating practice questions, and creating verifiable knowledge contributions."
  },
  "skill": {
    "version": "1.0.0",
    "prompt_template": "You are a Study Helper Skill. Given study material on {subject}, organize it into {output_format}. Target difficulty: {difficulty}. Output in {language}. Focus areas: {focus_areas}.",
    "maintainer_id": "pocp-entity-lumen-0"
  },
  "task": {
    "title": "[Study] {subject} — Create {output_format}",
    "description": "Use the Study Helper Skill to organize study materials on {subject} into {output_format}. This is a verified contribution task."
  }
}
```

---

## 9. Future Extensions (V0.2+)

| Feature | Description |
|---------|-------------|
| Multi-language output | Support for automatic translation alongside original |
| Collaborative mode | Multiple humans contribute to the same study artifact |
| Version history | Track how study notes evolve across revisions |
| Peer review | Allow other learners to rate usefulness of study artifacts |
| Spaced repetition integration | Auto-generate Anki/Quizlet-compatible flashcards |
| Cross-skill composition | Combine with Data Analysis Skill or Code Review Skill |

---

## 10. Verification Example: Pass / Fail Scenarios

### ✅ PASS Scenario

A learner studying **R programming**:
1. Uploads raw lecture notes (3,000 chars) on matrix operations
2. Study Helper Skill → produces structured notes with code examples
3. Learner adds personal commentary: "I found that `sweep()` is useful for centering data"
4. AI verifier score: 0.88
5. Human reviewer: "Excellent. Approved."

### ❌ FAIL Scenario

A learner copies from a textbook:
1. Uploads 500 chars of copied text
2. Output is verbatim reproduction with no original explanation
3. AI verifier score: 0.25 — flags low originality, possible plagiarism
4. Human reviewer: "Rejected. No evidence of original contribution."

### 🔄 REVISION Scenario

A learner tries but falls short:
1. Creates notes that are accurate but very sparse (only 3 bullet points)
2. AI verifier score: 0.52 — "Covers basics but lacks depth"
3. Human reviewer: "Request revision — please expand with examples and practice questions"
4. Learner revises and resubmits → approved

---

> **Skill Entity ID:** `skill:study-helper:v1`
> **Maintainer:** PoCP AI Commons
> **Status:** Draft — open for community review
