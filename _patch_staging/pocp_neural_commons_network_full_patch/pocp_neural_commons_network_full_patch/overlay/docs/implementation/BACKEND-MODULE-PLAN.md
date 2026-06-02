# Backend Module Plan

Recommended public backend modules:

```text
backend/services/capability/
backend/services/neural/
backend/services/token_measurement/
backend/services/settlement/
backend/services/compute/
backend/services/reputation/
```

Use:

```text
base.py
basic.py
mock.py
schemas.py
```

Avoid public files named:

```text
commercial_*.py
advanced_*.py
risk_weights.py
optimizer_private.py
```
