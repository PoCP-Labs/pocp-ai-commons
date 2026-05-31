# Gitcoin / Deep Funding → PoCP Mapping

**Status:** evaluating · **Registry slug:** `gitcoin`

---

## Borrow (advisory only)

| Gitcoin / Deep Funding | PoCP module |
|------------------------|-------------|
| Dependency graph for funding allocation | `graph_analytics.py` review priority hints |
| AI model competition + human spot checks | `multi_verifier.py` template |
| Public goods narrative | CHAOSS + inspiration transparency reports |

---

## Reject

| Pattern | Reason |
|---------|--------|
| Grant voting as finalization | PoCP uses contribution proof + policy finalization |
| Graph score auto-approves | [DISTRIBUTED-INTELLIGENCE-BENCHMARK.md](../DISTRIBUTED-INTELLIGENCE-BENCHMARK.md) advisory-only rule |
| Token-first QF rounds as CP substitute | NO-TOKEN-FIRST |

---

## PoCP differentiator

Gitcoin **funds** public goods. PoCP **executes** the loop:

```text
contribute → verify → CP/AI Credits → use AI/compute → contribute again
```

Deep Funding dependency graphs may inform **which contributions need human review first**, never whether they pass.
