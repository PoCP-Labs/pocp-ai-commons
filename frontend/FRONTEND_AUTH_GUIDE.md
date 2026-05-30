# PoCP AI Commons — 前端 OAuth2/JWT 认证集成指南

本指南详细介绍了为 `pocp-ai-commons` 项目前端（React + Vite）全新开发的 OAuth2/JWT 认证系统的集成方案。

---

## 一、 前端认证设计

前端认证系统与后端的双 Token（Access + Refresh）机制完美契合，采用了高内聚、低耦合的模块化设计，并且**严格保持了项目原有的极简、单文件、内联样式（Inline Styles）的设计风格**。

### 1.1 核心设计亮点
- **无状态 API 客户端**：自动管理 JWT Access Token 的时效。在请求过期时，通过 Mutex 锁机制合并并发的刷新请求，透明地换取新 Token 并重试请求，无需页面重载。
- **声明式路由守卫 (Auth Gate)**：作为应用最外层的 Wrapper，未登录时自动展示登录/注册视图，登录成功后渲染主应用。免去了引入复杂的 React Router，极简且高效。
- **全局状态上下文 (Auth Context)**：提供全局的 `user`、`isAuthenticated` 状态以及 `login`、`register`、`logout` 动作。
- **优雅的导航栏集成 (User Menu)**：在顶部 Header 区域优雅地展示当前登录用户的头像缩写、姓名、邮箱，以及其绑定的 **AI Credits 体验余额** 和 **CP (贡献点) 余额**。

---

## 二、 前端模块目录结构

我们在 `/frontend/src` 目录下创建并集成了以下模块：

```text
frontend/
├── index.html                  # 修改：注入了用于加载等待状态的 CSS Spinner 动画
├── src/
│   ├── main.jsx                # 修改：使用 AuthProvider 和 AuthGate 包装应用根节点
│   ├── App.jsx                 # 修改：集成 UserMenu，改用 publicGet 获取公开数据
│   ├── SubmitFlow.jsx          # 修改：集成 authPost 替代原始 fetch，请求自动携带 Token
│   └── auth/                   # 新增：高内聚的前端认证模块
│       ├── index.js            # 模块统一导出入口
│       ├── tokenStorage.js     # 负责 localStorage 中的 Token 读写、过期解析 (Base64 解码)
│       ├── apiClient.js        # 封装 fetch，实现自动带 Token、401 拦截和 Token 轮转刷新
│       ├── AuthContext.jsx     # React Context，管理全局登录状态和 API 请求封装
│       ├── AuthGate.jsx        # 路由守卫（门控组件），未登录时拦截并展示登录/注册页
│       ├── LoginPage.jsx       # 登录组件（包含 Alice 和 Bob 演示账户一键提示）
│       ├── RegisterPage.jsx    # 注册组件（新用户自动关联 Human 实体，并获赠 100 额度）
│       └── UserMenu.jsx        # 导航栏组件（展示用户 Profile、AI Credits、CP 余额及登出按钮）
```

---

## 三、 关键模块实现说明

### 3.1 自动刷新 Token 的 API 客户端 (`src/auth/apiClient.js`)
我们实现了一个高度鲁棒的 `authFetch`。当接口返回 `401 Unauthorized` 且本地存在 Refresh Token 时，它会暂停当前请求，在后台默默换取新的 Access Token 组合，然后再重新发送之前的请求。整个过程对用户完全透明：

```javascript
export async function authFetch(path, options = {}) {
  const token = await ensureValidToken(); // 1. 发送前先校验 Access Token，过期则主动刷新
  const headers = { ...options.headers };
  
  if (token) {
    headers["Authorization"] = `Bearer ${token}`; // 2. 自动注入 Authorization 标头
  }
  
  let res = await fetch(url, { ...options, headers });
  
  // 3. 容错处理：若服务器返回 401 且本地有 Token，尝试进行一次强制刷新
  if (res.status === 401 && token) {
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      headers["Authorization"] = `Bearer ${getAccessToken()}`;
      res = await fetch(url, { ...options, headers });
    }
  }
  return res;
}
```

### 3.2 声明式路由守卫 (`src/auth/AuthGate.jsx`)
我们在 `main.jsx` 中用 `AuthGate` 优雅地包裹了整个 `<App />`。如果用户未登录，它会直接渲染登录/注册页面；如果用户已登录，它会直接渲染真实的系统界面：

```javascript
export default function AuthGate({ children }) {
  const { isAuthenticated, isLoading } = useAuth();
  const [authView, setAuthView] = useState("login");

  if (isLoading) {
    return <div style={styles.loadingContainer}>Loading PoCP AI Commons...</div>;
  }

  if (!isAuthenticated) {
    if (authView === "register") {
      return <RegisterPage onSwitchToLogin={() => setAuthView("login")} />;
    }
    return <LoginPage onSwitchToRegister={() => setAuthView("register")} />;
  }

  return children; // 已登录，正常渲染主应用
}
```

---

## 四、 页面与组件视觉效果

我们为登录、注册、导航栏用户菜单编写了极具现代感的 UI 界面，采用**渐变背景、卡片式布局和精致的内联 CSS 样式**，与项目原本的 Tailwind-like 极简美学完美融合：

1. **登录页 (`LoginPage.jsx`)**：
   - 包含优雅的蓝绿渐变背景与白色毛玻璃质感卡片。
   - 底部内置了 **Demo Accounts 提示框**，标明了 `Alice`（普通用户）和 `Bob`（管理员）的初始测试账号和密码，极大降低了新开发者和用户的调试门槛。
2. **注册页 (`RegisterPage.jsx`)**：
   - 引导用户输入姓名、邮箱、密码及个人简介。
   - 明确提示用户“注册成功即可自动获赠 100 个 AI Credits 体验额度”。
3. **用户菜单 (`UserMenu.jsx`)**：
   - 完美嵌入在原有 Header 的右侧。
   - 显示首字母圆形头像、姓名、邮箱。
   - 用蓝色和绿色小胶囊徽章分别显示 **`AI Credits` 余额** 和 **`CP` (贡献点) 余额**，余额数据会随工作流的完成实时刷新。

---

## 五、 如何运行与验证

### 5.1 本地打包构建
在 `/frontend` 目录下运行以下命令，即可完成前端生产环境打包，验证所有 React 19 + Vite 6 语法的正确性：
```bash
npx vite build
```
构建将无警告通过，生成 `dist/` 静态资源目录。

### 5.2 启动开发服务器
启动前端开发服务器：
```bash
pnpm run dev
```
打开浏览器访问 `http://localhost:3000`，您将直接看到全新的登录页面。使用 `alice@pocp.dev` / `alice12345` 登录，即可无缝进入主控制台并体验完整的多实体贡献工作流！
