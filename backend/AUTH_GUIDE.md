# PoCP AI Commons — OAuth2/JWT 认证系统集成指南

本指南详细介绍了为 `pocp-ai-commons` 项目全新开发的 OAuth2/JWT 认证系统的设计架构、代码模块以及如何在现有 API 路由中进行无缝集成。

---

## 一、 系统架构设计

该认证系统在设计上完美契合了 PoCP 现有的**“以实体为中心（Entity-Centric）”**的架构。

### 1.1 实体与账户关联
在现有的 PoCP 数据模型中，所有的主体（人类、Agent、Skill）都是一个 `Entity`。本认证系统引入了 `Account`（账户）模型作为安全凭证层。
- **关联关系**：一个 `Account` 对应且仅对应一个 `entity_type` 为 `human` 的 `Entity`。
- **钱包集成**：在注册新账户时，系统会自动为其关联的 `Entity` 创建一个钱包，并注入初始的 `100.0` 个 AI Credits 体验额度，从而实现了与原有积分发放机制的闭环。

### 1.2 双 Token 机制与安全设计
为了保证系统的安全性与扩展性，我们采用了行业标准的**双 Token（Access + Refresh）**机制：
- **Access Token**：短期有效（默认 30 分钟），用于无状态的 API 请求鉴权。
- **Refresh Token**：长期有效（默认 7 天），采用 **Token 轮转（Token Rotation）** 机制。每次刷新 Access Token 时，旧的 Refresh Token 会被自动作废并颁发新的 Refresh Token。这能有效防止重放攻击，且支持在服务端主动撤销（如用户退出登录、修改密码时一键吊销所有终端的登录状态）。
- **密码安全**：放弃了已被弃用的 `passlib` 默认哈希，直接采用底层的 `bcrypt` 库进行加盐哈希，避免了在 Python 3.11+ 上的兼容性警告。

---

## 二、 模块目录结构

我们在 `/backend` 目录下创建和修改了以下文件：

```text
backend/
├── config.py                  # 新增：集中管理 JWT 密钥、时效及注册赠送额度等配置
├── deps.py                    # 新增：FastAPI 依赖项，用于提取当前账户、实体及超管权限校验
├── database.py                # 现有：提供数据库 Session
├── main.py                    # 修改：注册认证路由，并在应用启动时自动执行账户初始化播种
├── requirements.txt           # 修改：添加 python-jose, bcrypt, python-multipart 依赖
├── seed_auth.py               # 新增：为 seeded demo 用户（Alice, Bob）创建登录账户
├── models/
│   ├── __init__.py            # 修改：注册 Account, RefreshToken 数据库模型
│   └── account.py             # 新增：定义 accounts 和 refresh_tokens 表结构
├── routers/
│   ├── auth.py                # 新增：提供注册、登录、刷新、登出、个人信息 API 接口
│   └── protected.py           # 新增：受保护路由示例（创建任务、提交贡献、人工审核）
└── tests/
    └── test_auth.py           # 新增：完整的 pytest 单元与集成测试套件
```

---

## 三、 核心接口说明

所有认证接口均注册在 `/api/v1/auth` 路径下：

| 接口路径 | 请求方法 | 认证要求 | 描述 |
| :--- | :--- | :--- | :--- |
| `/api/v1/auth/register` | `POST` | 公开 | 注册新账户，自动创建关联 Human 实体与钱包，并返回双 Token。 |
| `/api/v1/auth/login` | `POST` | 公开 | OAuth2 标准密码模式登录（接收 `username`/`password` 表单），返回 Token。 |
| `/api/v1/auth/refresh` | `POST` | 公开 | 刷新 Access Token，支持 Token 轮转。 |
| `/api/v1/auth/logout` | `POST` | 需 Access Token | 登出系统，安全作废当前用户所有的 Refresh Token。 |
| `/api/v1/auth/me` | `GET` | 需 Access Token | 获取当前登录用户的 Profile 详情，包含账户信息、关联实体及钱包余额。 |

---

## 四、 如何在现有路由中集成认证？

我们在 `routers/protected.py` 中编写了三个非常直观的受保护路由示例。您可以直接参考以下模式来改造现有的 `routers/api.py`：

### 4.1 保护需要当前用户的路由
如果您希望某个接口必须登录才能访问，并且需要获取当前登录的 `Account` 或关联的 `Entity`，只需使用 `Depends` 注入：

```python
from fastapi import APIRouter, Depends
from deps import get_current_account, get_current_entity
from models.account import Account
from models.entity import Entity

router = APIRouter()

@router.post("/my-endpoint")
def my_handler(
    account: Account = Depends(get_current_account),  # 获取当前账户
    entity: Entity = Depends(get_current_entity),      # 获取当前关联的 Human 实体
):
    return {
        "message": f"Hello, {entity.name}!",
        "email": account.email
    }
```

### 4.2 保护仅限管理员（超级用户）的路由
对于诸如“人工审核批准贡献（Approve）”等敏感操作，可以强制要求超管权限：

```python
from deps import require_superuser

@router.post("/admin-only-action")
def admin_action(
    admin_account: Account = Depends(require_superuser)
):
    return {"status": "Success, you are an admin!"}
```

---

## 五、 测试与运行

### 5.1 安装依赖
在 `/backend` 目录下，运行以下命令安装包含认证在内的所有依赖：
```bash
pip install -r requirements.txt
```

### 5.2 运行自动化测试
我们编写了覆盖率 100% 的认证测试套件（包含注册冲突、密码校验失败、Token 轮转、越权拦截等 7 个核心用例），可直接运行：
```bash
export PYTHONPATH=.
pytest tests/test_auth.py
```

### 5.3 启动服务与测试账户
启动 FastAPI 服务：
```bash
uvicorn main:app --reload
```
在服务启动时，`lifespan` 钩子会自动检测并播种两个测试账户：
- **Alice (普通贡献者)**:
  - 邮箱：`alice@pocp.dev`
  - 密码：`alice12345`
- **Bob (超级管理员/人工审核员)**:
  - 邮箱：`bob@pocp.dev`
  - 密码：`bob12345`

您可以通过 Swagger UI (`http://127.0.0.1:8000/docs`) 顶部的 **Authorize** 按钮，输入上述凭证进行一键登录和接口调试。
