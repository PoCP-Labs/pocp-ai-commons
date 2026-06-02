# PoCP Confirmation Spec

## Purpose

Bitcoin has block confirmations. PoCP needs contribution and settlement confirmations.

## Confirmation Levels

```text
0-confirmation: event submitted
1-confirmation: event accepted by peers / mempool
2-confirmation: proof verified
3-confirmation: settlement proposed
4-confirmation: challenge window passed
5-confirmation: settlement finalized
```

## Suggested Use

```text
Small AIC settlement: 2-confirmation
Normal CP settlement: 3-confirmation
Compute Credits settlement: 4-confirmation
High-value PT_INTERNAL settlement: 5-confirmation + reviewer quorum
```
