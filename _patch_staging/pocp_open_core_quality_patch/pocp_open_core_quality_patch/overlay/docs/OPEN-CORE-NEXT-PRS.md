# Open Core Next PRs

Recommended PR sequence after this patch.

## PR 1 — Public Core Quality

```text
Improve public open-source core quality and boundaries
```

Includes:

- quality docs;
- PR template;
- issue templates;
- health check script;
- formatter config;
- CI scaffold;
- README public-core section.

## PR 2 — Format Backend Source

```text
Format backend Python source files
```

Includes:

- restore line breaks;
- run Black;
- run Ruff;
- preserve business logic;
- ensure smoke test still works.

## PR 3 — README Consistency

```text
Fix README links and clarify reference implementation status
```

Includes:

- link check;
- target architecture wording;
- current implementation wording.

## PR 4 — Security and Data Consent

```text
Add security reporting and data consent process
```

Includes:

- SECURITY;
- DATA-CONSENT;
- ANTI-ABUSE-POLICY;
- README links.

## PR 5 — License Review

```text
Add license migration proposal
```

Includes:

- current license review;
- proposed Apache-2.0 for code;
- proposed CC BY 4.0 for protocol docs;
- contributor implications.

## PR 6 — Public Basic Interfaces

```text
Add public basic service interfaces
```

Includes:

- anti_abuse/base.py;
- routing/base.py;
- reputation/base.py;
- settlement/base.py;
- compute/base.py;
- basic/mock implementations only.

PoCP begins with contribution.
