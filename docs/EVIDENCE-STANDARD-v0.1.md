# PoCP Evidence Standard v0.1

PoCP evidence is a JSON object attached to a contribution. The original fields
remain contributor-controlled, while PoCP reserves `_pocp` for portable metadata.

## Metadata

`backend/services/evidence.py` enriches submitted evidence with:

| Field | Meaning |
|---|---|
| `_pocp.content_hash` | SHA-256 hash of the canonical evidence object, excluding `_pocp` |
| `_pocp.spec_version` | PoCP evidence metadata version |
| `_pocp.evidence_standard` | Evidence type standard version |
| `_pocp.evidence_types` | Sorted list of detected standard evidence types |

Metadata is excluded from the content hash so nodes can add standard metadata
without changing the hash of the contributor-provided evidence.

## Standard Types

Evidence keys are normalized into these review types:

| Type | Common keys |
|---|---|
| `artifact` | `artifact`, `artifacts` |
| `commit` | `commit`, `commits` |
| `content_preview` | `content`, `content_preview` |
| `diff` | `diff`, `patch` |
| `pull_request` | `pull_request`, `pr` |
| `screenshot` | `screenshot`, `screenshots` |
| `url` | `url`, `urls`, `link`, `links`, `source` |
| `other` | Any non-empty evidence key not listed above |

## Review Items

Clarion-0 and proof tooling may expose evidence as typed items:

```json
{
  "type": "url",
  "key": "links",
  "label": "Links",
  "value": ["https://example.org/work"]
}
```

The typed item is a review convenience, not a governance decision. Clarion-0 may
score and summarize these items, but it must not approve, reject, or otherwise
change contribution status.
