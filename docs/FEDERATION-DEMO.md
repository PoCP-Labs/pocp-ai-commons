# PoCP 双节点联邦演示

两个独立 PoCP 节点，演示「协议不属于单一运营者」：

- **Node A**（源节点）— `http://localhost:8100`
- **Node B**（镜像节点）— `http://localhost:8101`，信任 Node A 的公钥

## 启动

```bash
docker compose -f docker-compose.federation.yml up --build
```

## 流程

### 1. 在 Node A 完成贡献闭环

```bash
# 登录
curl -s -X POST http://localhost:8100/api/v1/auth/dev-login \
  -H "Content-Type: application/json" \
  -d '{"username":"rain","email":"rain@example.com"}'

# 用返回的 token 创建任务、提交贡献、auto-verify、approve
# （或使用 scripts/smoke_test.py http://localhost:8100）
```

### 2. 查看 Node A 的签名 proof

```bash
curl -s http://localhost:8100/api/v1/contributions/{id}/proof | jq .federation
```

应包含 `node_id`、`public_key`、`signature`（Ed25519 签名 `integrity.proof_hash`）。

### 3. 镜像到 Node B

```bash
cd backend
python scripts/mirror_trusted_node.py http://localhost:8100 node-a http://localhost:8101
```

Node B 会验证签名、导入声誉（不发 AI Credits）。

### 4. 查询跨节点声誉

```bash
curl -s "http://localhost:8101/api/v1/federation/reputation?portable_id=dev:rain@example.com"
```

### 5. 导出账本锚定

**API：** `GET /api/v1/ledger/anchor`

**本地（有数据库）：**

```bash
cd backend
DATABASE_URL=postgresql+psycopg://pocp:pocp@localhost:5433/pocp_a \
POCP_NODE_ID=node-a \
python scripts/anchor_ledger.py ../anchors
```

**远程（无数据库）：**

```bash
python scripts/fetch_anchor.py http://localhost:8100 ../anchors
```

生成 `anchors/{node_id}/ledger-anchor-YYYYMMDD.json`（Merkle root，可选 Ed25519 签名）。

## GitHub Actions 自动化

在仓库 Settings → Secrets 配置：

| Secret | 用途 |
|--------|------|
| `POCP_ANCHOR_NODE_URL` | 锚定工作流拉取的节点 URL |
| `POCP_MIRROR_SOURCES` | JSON：`[{"base_url":"...","node_id":"..."}]` |
| `POCP_MIRROR_TARGET` | 镜像目标节点 URL |

可选 Variables：

| Variable | 说明 |
|----------|------|
| `POCP_ANCHOR_ENABLED` | 设为 `false` 禁用每日锚定 |
| `POCP_MIRROR_ENABLED` | 设为 `false` 禁用联邦镜像 |

工作流：

- `.github/workflows/ledger-anchor.yml` — 每日 UTC 0:00 提交锚定文件到 `anchors/`
- `.github/workflows/federation-mirror.yml` — 每 6 小时从可信源镜像 proof

手动触发：`Actions → Ledger Anchor → Run workflow`

锚定文件说明见 [anchors/README.md](../anchors/README.md)。

## 生成新节点密钥

```bash
python scripts/generate_node_keys.py my-node
```

将 `public_key` 加入他节点的 `POCP_TRUSTED_NODES`。

## 环境变量

| 变量 | 说明 |
|------|------|
| `POCP_NODE_PRIVATE_KEY` | Ed25519 私钥（hex） |
| `POCP_NODE_PUBLIC_KEY` | 公钥（hex，可仅从私钥推导） |
| `POCP_TRUSTED_NODES` | JSON 信任列表 |
| `POCP_REQUIRE_IMPORT_SIGNATURE` | `true` 时强制验证签名 |
| `POCP_ALLOW_UNTRUSTED_IMPORT` | 开发用，跳过信任列表 |

---

See also: [FEDERATION-v0.1.md](./FEDERATION-v0.1.md)
