# API Endpoint Plan

## Entity

```http
GET /api/v1/entities
POST /api/v1/entities
GET /api/v1/entities/{id}
```

## Capability

```http
GET /api/v1/capabilities
POST /api/v1/capabilities
POST /api/v1/capabilities/{id}/invoke
```

## Routing

```http
POST /api/v1/tasks/{id}/route
GET /api/v1/tasks/{id}/execution-plan
```

## Invocation

```http
GET /api/v1/invocations/{id}
GET /api/v1/entities/{id}/invocations
```

## Token Measurement

```http
GET /api/v1/wallets/{entity_id}
GET /api/v1/token-accounts/{entity_id}
```

## Settlement

```http
POST /api/v1/settlements
GET /api/v1/settlements/{id}
```

## Graph

```http
GET /api/v1/graph/network
GET /api/v1/graph/entities/{id}
```
