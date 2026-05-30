# PoCP Federation v0.1

**多节点互认草案 — 让协议不属于单一运营者**

See also: [PROTOCOL.md](./PROTOCOL.md) · [OPENNESS-AND-ANTI-MONOPOLY.md](./OPENNESS-AND-ANTI-MONOPOLY.md) · [PROTOCOL-SPEC-v0.1.md](../PROTOCOL-SPEC-v0.1.md) · [PORTABLE-PROOF-FEDERATION.md](./PORTABLE-PROOF-FEDERATION.md)

---

## 1. 目标

| 问题 | 联邦层回答 |
|------|-----------|
| 数据锁在单一 Postgres | 节点导出账本 / 图谱，他方只读镜像 |
| 身份只在本地 UUID 有效 | `portable_id`（如 `github:rain`）跨节点引用 |
| 声誉不可移植 | 互认已签名的 `approved` 贡献事件 |
| 规则属于某次 deploy | `config/pocp_rewards.yaml` 版本化参数 |

V0.1 联邦 API 为**骨架**；完整 import 计划在 v0.2。

---

## 2. 信任模型

每个节点声明：

```json
{
  "node_id": "pocp-node-abc123",
  "spec_version": "0.1",
  "public_endpoints": [
    "https://node.example/api/v1/ledger/export",
    "https://node.example/api/v1/entities/{id}/portable",
    "https://node.example/api/v1/ledger/verify"
  ]
}
```

环境变量 `POCP_TRUSTED_NODES`（JSON 数组）列出可信节点：

```json
[
  {
    "node_id": "school-a",
    "base_url": "https://pocp.school-a.edu",
    "public_key": "optional-ed25519-hex"
  }
]
```

**互认规则（计划）：**

1. 只导入 `approved` 且账本哈希链验证通过的事件  
2. 贡献证据 `content_hash` 必须匹配  
3. 实体以 `portable_id` 对齐，而非本地 UUID  
4. 各节点保留自己的 AI Credits 池；CP/声誉可按信任权重合并  

---

## 3. 可移植身份

Human 实体在 OAuth 登录后写入 metadata：

```json
{
  "portable_id": "github:rain",
  "external_ids": { "github": "rain" },
  "provider": "github",
  "provider_user_id": "12345"
}
```

`GET /api/v1/entities/{id}/portable` 导出完整可移植包（实体 + 钱包摘要 + 声誉）。

---

## 4. 账本完整性

每条 `ledger_records` 行包含：

- `prev_hash` — 上一条记录哈希  
- `record_hash` — SHA-256(prev_hash | event_type | payload | created_at)

```http
GET /api/v1/ledger/verify   → { valid, count, first_broken_id }
GET /api/v1/ledger/export   → 按时间升序导出（可镜像）
```

---

## 5. 联邦 API（V0.1 已实现 / 计划）

| 方法 | 路径 | 状态 |
|------|------|------|
| GET | `/api/v1/federation/node` | ✅ 节点元信息 |
| GET | `/api/v1/federation/trust` | ✅ 信任列表 |
| POST | `/api/v1/federation/import` | ✅ 事件导入（声誉互认，不发 Credits） |
| POST | `/api/v1/federation/import-proof` | ✅ 从 proof 包导入 |
| GET | `/api/v1/federation/imports` | ✅ 已导入记录 |
| GET | `/api/v1/federation/reputation?portable_id=` | ✅ 声誉聚合 |
| GET | `/api/v1/ledger/export` | ✅ |
| GET | `/api/v1/ledger/verify` | ✅ |
| GET | `/api/v1/entities/{id}/portable` | ✅ |

### Import 载荷草案（v0.2）

```json
{
  "source_node_id": "school-a",
  "contribution_id": "uuid",
  "task_title": "Write R tutorial",
  "primary_entity_portable_id": "github:rain",
  "contribution_type": "knowledge",
  "evidence": { "url": "...", "_pocp": { "content_hash": "..." } },
  "participants": [
    { "entity_portable_id": "github:rain", "role": "creator", "weight": 0.4 }
  ],
  "ledger_record_hash": "abc...",
  "signature": "optional"
}
```

---

## 6. 分阶段落地

| 阶段 | 能力 |
|------|------|
| **V0.1** | 哈希链账本、证据哈希、导出 API、联邦骨架 |
| **V0.2** | import、Ed25519 验签、声誉查询、镜像脚本、账本锚定 |
| **P2** | peers/health + sync + 远程 ledger 校验（见 [FEDERATION-HARDENING.md](./FEDERATION-HARDENING.md)） |
| **V1.0** | 多节点生产互认、信任列表治理、只读镜像节点 |

---

## 7. 部署多个节点

```bash
# 节点 A
POCP_NODE_ID=community-a BACKEND_URL=https://a.example docker compose up

# 节点 B（信任 A）
POCP_NODE_ID=school-b \
POCP_TRUSTED_NODES='[{"node_id":"community-a","base_url":"https://a.example"}]' \
docker compose up
```

同一套 `PROTOCOL-SPEC-v0.1.md` + 各自 Postgres = 协议自然存在于网络上，而非属于某一个部署者。

**本地双节点演示：** [FEDERATION-DEMO.md](./FEDERATION-DEMO.md)  
**强化单点 → 多节点：** [FEDERATION-HARDENING.md](./FEDERATION-HARDENING.md)

## 8. Ed25519 签名（v0.2）

源节点配置 `POCP_NODE_PRIVATE_KEY` 后，proof 包自动附带：

```json
"federation": {
  "node_id": "node-a",
  "public_key": "...",
  "signature": "...",
  "signed_field": "integrity.proof_hash"
}
```

导入节点在 `POCP_TRUSTED_NODES` 中配置对应 `public_key`。  
设置 `POCP_REQUIRE_IMPORT_SIGNATURE=true` 可强制验签。

生成密钥：`python scripts/generate_node_keys.py <node-id>`

## 9. 镜像脚本

从可信节点拉取已批准贡献的 proof 并导入本地：

```bash
cd backend
# 目标节点需设置 POCP_ALLOW_UNTRUSTED_IMPORT=true（开发）或将源节点加入 POCP_TRUSTED_NODES
python scripts/mirror_trusted_node.py http://source:8000 source-node-id http://localhost:8000
```

多源同步（CI / cron）：

```bash
POCP_MIRROR_SOURCES='[{"base_url":"http://node-a:8100","node_id":"node-a"}]' \
POCP_MIRROR_TARGET=http://localhost:8101 \
python scripts/federation_sync.py
```

---

*PoCP Federation · v0.2*
