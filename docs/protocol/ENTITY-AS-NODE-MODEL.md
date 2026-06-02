# Entity 与 Node：如何把「本机以外的 Entity」变成网络节点

## 概念分层

| 层级 | 是什么 | 本机 DB 里有什么 |
|------|--------|------------------|
| **Node（节点）** | 一台对外提供 HTTPS 的 PoCP 实例（`POCP_NODE_ID` + `BACKEND_URL`） | 一个 **community** Entity：`pocp-entity-federation-peer-{node_id}` |
| **Entity（贡献主体）** | Skill、Agent、Human 等可被对话、证明、结算的对象 | 本机 **主本**；其它节点上是 **远程主本** |
| **镜像 Entity** | 远程主本在本机图谱上的只读影子 | `metadata.roles` 含 `federated_mirror`，`home_node_id` 指向对方节点 |

**要点**：不是「每一个远程 Entity 都等于一个 Node」，而是「每个受信 Node 暴露一批 Entity；本机把它们镜像进图谱，对话时按 `home_node_id` 转发」。

## 三步落地

### 1. 把对方实例登记为受信节点

在 `.env` 或 `trusted_nodes.yaml` 中配置：

```json
POCP_TRUSTED_NODES=[
  {
    "node_id": "node-b",
    "base_url": "https://peer.example.com",
    "trust_weight": 0.9
  }
]
BACKEND_URL=https://your-public-url
POCP_NODE_ID=node-a
POCP_DIALOGUE_PEER_ROUTE=true
```

启动后 `ensure_federation_peer_entities()` 会为每个 peer 创建 **节点壳** Entity（`federation_peer` / `federation_node` 角色）。

也可用 API 探测（镜像需已在信任列表中）：

```http
POST /api/v1/federation/peers/register
{
  "node_id": "node-b",
  "base_url": "https://peer.example.com",
  "mirror_entities": true
}
```

### 2. 拉取并镜像远程 Entity 目录

```http
POST /api/v1/federation/peers/node-b/mirror-entities
```

实现：`services/federation_entity_mirror.py`

- 从 peer 拉取 `GET /api/v1/entities?entity_type=skill`（及 agent、llm 等）
- 在本机创建稳定 UUID 影子行（`uuid5(node_id, remote_entity_id)`）
- `metadata` 写入 `home_node_id`、`remote_entity_id`、`portable_id`、`peer_base_url`

查询本机已镜像列表：

```http
GET /api/v1/federation/peers/node-b/remote-entities
```

### 3. 对本机图谱上的镜像发 Entity Dialogue

对用户/前端：照常选本地 `entity_id`（镜像行的 id）。

路由层（`dialogue_route.py`）会：

1. 识别 `federated_mirror`
2. 把 `to.node_id` 设为 `home_node_id`，`to.entity_id` 换成 `remote_entity_id`
3. `POST https://peer.../api/v1/federation/dialogue` 转发

也可在协议面板里手写 `to.node_id` + `portable_id`（见 `CROSS-NODE-INTERNET.md`）。

## 与现有联邦能力的关系

| 能力 | 用途 |
|------|------|
| `federation_community` | 节点壳 Entity、贡献图边 |
| `federation_entity_mirror` | **远程 Entity 目录同步**（新增） |
| `federation_import` | 证明包/事件导入（链上/结算向） |
| `entity_portable` | `portable_id` 跨节点解析 |
| `dialogue_route` | HTTPS 跨节点对话 |

导入证明与「镜像目录」互补：镜像用于 **发现与 invoke**；import 用于 **贡献与结算凭证**。

## 安全与运维

- 只镜像 **POCP_TRUSTED_NODES** 中的节点；未入信任列表的 `register` 只探测、不拉目录。
- 镜像默认 **不复制** 私钥、钱包、owner 关系；仅名称、类型、描述与路由元数据。
- 定期 `POST .../mirror-entities` 可刷新目录（同名 remote id 会 update）。
- 生产环境建议为 peer 的 `/api/v1/entities` 保留公开读或 mTLS；敏感 Entity 应在对方用 `inactive` 或网关过滤。

## 相关文件

- `backend/services/federation_entity_mirror.py`
- `backend/services/federation_community.py`
- `backend/services/network/dialogue_route.py`
- `docs/protocol/CROSS-NODE-INTERNET.md`
- `docs/protocol/ENTITY-DIALOGUE-PROTOCOL.md`
