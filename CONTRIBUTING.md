# Contributing to PoCP AI Commons

Thank you for considering a contribution to **PoCP AI Commons**.

PoCP AI Commons is an open-source contribution proof network for the age of AI.

Our first loop is:

```text
Contribution → Verification → CP → AI Credits → AI Use → More Contribution
```

We are building a system where humans, agents, skills, tools, datasets, workflows, and organizations can participate in contribution tasks, receive verification, build reputation, and earn AI access.

## What We Believe

- AI access should not depend only on money, geography, or platform control.
- Real contribution should be visible, verifiable, and rewarded.
- AI should be a witness and assistant, not the final ruler.
- Human reviewers remain responsible for final approval.
- Reputation must be earned, not bought.
- Contributors should share in the value they help create.

## Ways to Contribute

You can contribute as a:

| Role | What You Can Do |
|---|---|
| Core Developer | Build backend, frontend, wallet, ledger, verification, graph |
| AI Verifier Builder | Build OpenAI, DeepSeek, Claude, Gemini, local LLM verifiers |
| Skill Builder | Create reusable Skills such as Study Helper, Code Review, Resume Helper |
| Task Designer | Design contribution tasks for learning, open-source, public-good, and community work |
| Human Reviewer | Review contributions and improve verification rubrics |
| Researcher | Improve CP/Credits rules, reputation, governance, anti-abuse, human-agent collaboration |
| Community Builder | Translate docs, welcome new contributors, organize discussions and build sessions |

## Code Contribution Is Not Limited to Writing Code

Code contribution is not limited to writing code. Requirements, issues, prompts, tests, reviews, documentation, skills, agents, and human judgment are all part of the code contribution chain.

See the [Code Contribution Commons](./CODE-CONTRIBUTION-COMMONS.md) package:

- [GENESIS-CODE-CONTRIBUTORS.md](./GENESIS-CODE-CONTRIBUTORS.md)
- [DEV-TASKS.md](./DEV-TASKS.md)
- [ISSUE-WRITING-GUIDE.md](./ISSUE-WRITING-GUIDE.md)
- [AI-ASSISTED-CODING-GUIDE.md](./AI-ASSISTED-CODING-GUIDE.md)
- [REVIEW-GUIDE.md](./REVIEW-GUIDE.md)
- [docs/CODE-COMMONS-LAUNCH.md](./docs/CODE-COMMONS-LAUNCH.md)

Pick a GitHub issue template (`code_contribution_task`, `issue_spec_task`, `test_task`, `skill_task`, `review_task`) that matches your role. AI may advise; humans remain responsible for final review and merge.

## Good First Contributions

Start here:

- Improve README clarity
- Polish GENESIS.md translations (see [docs/genesis/README.md](docs/genesis/README.md))
- Add architecture diagrams
- Improve the frontend AI Chat tab
- Add OpenAI Verifier tests
- Add DeepSeek Verifier tests
- Create a Study Helper Skill
- Create a Code Review Skill
- Improve Contribution Graph UI
- Write anti-abuse test cases
- Write FAQ: Is PoCP a token project?
- Write FAQ: Why AI Credits first?

See [`GOOD_FIRST_ISSUES.md`](GOOD_FIRST_ISSUES.md).

## Development Setup

Please refer to the repository README for current backend/frontend setup.

Typical local flow:

```bash
# backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# frontend
cd frontend
npm install
npm run dev
```

## Contribution Workflow

1. Fork the repository.
2. Create a branch:

```bash
git checkout -b feature/your-contribution-name
```

3. Make your changes.
4. Run tests or smoke tests if available.
5. Open a Pull Request.
6. Explain:
   - What you changed
   - Why it matters
   - How to test it
   - Whether it affects CP, AI Credits, verification, ledger, or reputation

## Pull Request Requirements

A good PR should include:

- A clear title
- A short summary
- Screenshots for UI changes
- Test notes
- Risk notes if relevant
- Documentation updates if behavior changes

## AI Assistance Disclosure

You may use AI tools to help with contributions.

Please disclose AI assistance when relevant, especially for:

- Generated code
- Generated docs
- Generated tests
- Translations
- Verification prompts
- Research summaries

Example:

> This PR was drafted with assistance from an AI coding assistant and reviewed by the human contributor before submission.

## Human Review Principle

PoCP uses AI for advisory review, but human maintainers remain responsible for final decisions.

For this project:

- AI can suggest.
- AI can summarize.
- AI can score.
- AI can detect risks.
- Human reviewers approve or reject.

## Code of Conduct

All contributors must follow [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md).

## Genesis Contributors

Early contributors may be listed in [`GENESIS-CONTRIBUTORS.md`](GENESIS-CONTRIBUTORS.md), based on verified meaningful contributions.

PoCP begins with contribution.
