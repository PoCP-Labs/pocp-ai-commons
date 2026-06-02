# Cursor Prompt: Improve PoCP Public Open-Source Core Quality

You are working in:

`PoCP-Labs/pocp-ai-commons`

A quality patch has been applied.

## Strategic goal

PoCP's protocol skeleton should remain open source.

Commercial intelligence capabilities should be reserved.

Before splitting commercial modules, first make the public repository a high-quality open-source core.

## Main tasks

### 1. Fix Python source formatting

Inspect all backend Python files.

Priority files to check:

- `backend/main.py`
- `backend/routers/api.py`
- `backend/models/*.py`
- `backend/services/*.py`
- `backend/scripts/*.py`
- `backend/tests/*.py` if present

If any Python file is compressed into one long line or has broken formatting:

- restore readable Python formatting;
- preserve business logic;
- do not redesign the architecture in this PR;
- run formatting using Black if possible;
- run Ruff if possible.

Use `pyproject.toml` added by this patch.

### 2. Run health checks

Try:

```bash
python backend/scripts/health_check.py
```

If backend requirements are installed, also try:

```bash
python backend/scripts/smoke_test.py http://127.0.0.1:8000
```

If Docker is available:

```bash
docker compose up --build
```

Do not fail the PR only because optional local dependencies are missing; document what was tested.

### 3. Update README

Add a short section:

```markdown
## Public Open-Source Core

PoCP keeps its protocol skeleton, schemas, reference implementation, SDK-facing interfaces, and community tools open source.

The public repository is intended to remain readable, runnable, auditable, and contributor-friendly.

Commercial intelligence capabilities, including advanced anti-abuse intelligence, commercial neural routing, managed compute scheduling, enterprise governance, private deployment tooling, and advanced reputation / risk models may be implemented in separate commercial modules.

See:

- [Open Source Core Quality](OPEN-SOURCE-CORE-QUALITY.md)
- [Reference Implementation](REFERENCE-IMPLEMENTATION.md)
- [Public Core Boundary](PUBLIC-CORE-BOUNDARY.md)
- [Commercial Reserved Boundary](COMMERCIAL-RESERVED-BOUNDARY.md)
- [Repository Health Checklist](REPO-HEALTH-CHECKLIST.md)
```

Preserve existing README quick start, demo, API, and project positioning.

### 4. Clarify implementation status

If README lists target files or architecture that are not yet implemented, add wording like:

```markdown
Some architecture documents describe the target modular structure. The current reference implementation may still use aggregated routers or services while modularization is in progress.
```

### 5. Preserve license

Do not change the license automatically.

If a license migration is needed, open a separate PR later.

### 6. Keep sensitive commercial logic out

Do not add advanced anti-abuse scoring, private risk weights, commercial routing algorithms, compute scheduler optimization, enterprise customer logic, or secret-based private deployment scripts to the public repository.

### 7. Suggested commit

```text
Improve public open-source core quality and boundaries
```

## Success criteria

- Python files are readable and formatted.
- Basic health check script exists.
- README explains public-core vs commercial-reserved boundary.
- CI scaffold exists.
- PR template and issue templates exist.
- Existing demo is preserved.
