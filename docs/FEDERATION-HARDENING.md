# 强化多节点联邦 — 从单点运营到分布式互认

如何从「一个 maintainer + 一个数据库」演进到真正的多节点、低单点依赖。

See also: [FEDERATION-v0.1.md](./FEDERATION-v0.1.md) · [FEDERATION-DEMO.md](./FEDERATION-DEMO.md)

---

## 1. 问题：单点运营的风险

| 单点 | 风险 |
|------|------|
| 单一 Postgres | 数据主权集中在运营者 |
| 单一 maintainer | 治理权集中 |
| 单一 API 域名 | 关停即网络消失 |
| 信任列表写死在 env | 换 peer 要 redeploy |

**目标：** 任何学校、社区、企业都能跑一个节点；节点之间互认**经签名、可验证**的贡献，而不是服从某个中心。

---

## 2. 已实现的强化能力（v0.2+）

### A. 远程账本校验（导入前）

导入 proof 前，向源节点请求：

```http
GET /api/v1/ledger/verify   → 必须 valid: true
GET /api/v1/ledger/anchor   → tip_hash 与 proof 一致
```

环境变量：`POCP_VERIFY_REMOTE_LEDGER=true`（默认开启）

### B. 节点健康探测

```http
GET /api/v1/federation/peers/health
```

返回每个 `POCP_TRUSTED_NODES` 的可达性、ledger 有效性、anchor Merkle root。

### C. 一键联邦同步

```http
POST /api/v1/federation/sync
```

从所有可信节点拉取 `ledger/export` → 逐条取 `proof` → 本地 `import-proof`（写声誉 + 联邦账本）。

CLI 等价：

```bash
POCP_MIRROR_SOURCES='[{"base_url":"http://node-a:8100","node_id":"node-a"}]' \
python backend/scripts/federation_sync.py
```

### D. 启动时自动同步

```bash
POCP_FEDERATION_SYNC_ON_STARTUP=true
```

节点 B 启动后自动从可信列表同步（见 `docker-compose.federation.yml` 中 backend-b）。

### E. 签名 + 锚定 + Git 镜像

- proof 包 Ed25519 签名（`federation.signature`）
- 每日 `ledger/anchor` Merkle root → `anchors/{node_id}/`
- GitHub Action：`.github/workflows/ledger-anchor.yml`、`federation-mirror.yml`

---

## 3. 推荐部署拓扑

```text
                    ┌─────────────────┐
                    │  anchors/ (Git)  │  ← 公共只读记忆
                    └────────▲────────┘
                             │ daily anchor
        ┌────────────────────┼────────────────────┐
        │                    │                    │
   Node A (社区)        Node B (学校)        Node C (镜像只读)
   Rain 运营            信任 A               信任 A+B
   签名 proof           sync on startup      无写权限
```

**原则：**

1. **至少 2 个独立运营者** 各跑一节点（不同 Postgres、不同 `POCP_NODE_ID`、不同密钥）
2. **互配 `POCP_TRUSTED_NODES` + public_key**，强制 `POCP_REQUIRE_IMPORT_SIGNATURE=true`
3. **镜像节点** 只跑 sync + 只读 API，不持有唯一数据源
4. **锚定文件进 Git**，第三方无需信任运营者即可核对 Merkle root

---

## 4. 分阶段路线图

| 阶段 | 能力 | 状态 |
|------|------|------|
| **P0** | 哈希链账本 + proof 导出 | ✅ |
| **P1** | import-proof + 签名验签 | ✅ |
| **P2** | peers/health + sync + 远程 ledger 校验 | ✅ |
| **P3** | 信任列表 YAML + ledger 记录 | ✅ `config/trusted_nodes.yaml` |
| **P4** | 只读镜像节点 `POCP_NODE_MODE=read_only_mirror` | ✅ middleware |
| **P5** | 多 maintainer 治理（CODEOWNERS + 贡献投票） | 🔜 |
| **P6** | 链下锚定 → IPFS / 多 Git 远程 | 🔜 |

---

## 5. P3–P6 具体怎么做

### P3 信任列表上链下共识（不必上真链）

```text
config/trusted_nodes.yaml  ← PR 修改，多 maintainer review
  ↓
节点启动加载 YAML + env 覆盖
  ↓
ledger 记录 trust_list_updated 事件
```

### P4 只读镜像节点

- 环境变量 `POCP_NODE_MODE=read_only_mirror`
- 禁用 `POST /contributions`、`POST /approve`
- 仅保留 `GET /graph`、`GET /proof`、`GET /reputation`、`POST /sync`

### P5 治理去中心化

- 协议参数变更走 GitHub Proposal Issue 模板
- 高影响变更需 N 个 Reviewer 实体签名（Ed25519）
- `GOVERNANCE.md` 演进为贡献加权投票

### P6 外部锚定冗余

- 同一 `merkle_root` 推送到：本 repo `anchors/`、IPFS CID、可选 calldata
- 第三方验证：任意两个源 root 一致即可

---

## 6. 运维检查清单

```bash
# 1. 本节点账本 OK？
curl -s localhost:8101/api/v1/ledger/verify

# 2. 可信节点 OK？
curl -s localhost:8101/api/v1/federation/peers/health

# 3. 手动同步
curl -X POST localhost:8101/api/v1/federation/sync

# 4. 跨节点声誉
curl -s "localhost:8101/api/v1/federation/reputation?portable_id=dev:rain@example.com"
```

---

## 7. 与「属于全人类」的关系

| 机制 | 削弱单点 |
|------|----------|
| 多节点 + 互认 | 无唯一数据库 owner |
| 签名 proof | 无唯一叙事 owner |
| Git 锚定 | 无唯一历史 owner |
| sync 自动化 | 镜像节点可替代源节点只读服务 |
| 远程 ledger 校验 | 导入不盲信 HTTP 响应 |

**maintainer 仍会存在一段时间**（合并 PR、引导 Genesis），但协议记忆与声誉逐步分布在**多个可验证节点 + 公共 Git 锚定**上——这才是从单点运营走向「属于全人类」的工程路径。

---

*PoCP Federation Hardening · v0.2*
