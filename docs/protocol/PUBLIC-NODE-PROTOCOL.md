# Public Node Protocol

## Public Node Manifest

```http
GET /.well-known/pocp-node.json
```

## Public Node API

```http
GET  /pocp/node
GET  /pocp/health
GET  /pocp/capabilities
POST /pocp/handshake
POST /pocp/invoke
POST /pocp/proofs
POST /pocp/settlements/ack
```

## Node Modes

```text
direct_public
reverse_proxy
relay
hosted
offline_light
```
