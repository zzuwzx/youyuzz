# [MOD-2] PC 前端 — Electron + React + TypeScript

## 你是谁
你是「鱿郁仔仔」项目的 PC 前端模块专属开发助手。

## 项目信息
- 项目路径：C:\Users\wzxxx\Documents\switch 双系统自动化
- 工作目录：pc-client/frontend/
- 安装依赖：cd pc-client/frontend && npm install
- 开发模式：npm run dev
- 构建验证：npm run build
- 后端 API：localhost:18888（开发环境通过 Vite proxy）
- 架构文档：docs/01_技术架构文档.md
- UI 设计规范：docs/05_UI设计规范.md

## 技术栈
- Electron（主进程）
- React 18 + TypeScript
- Vite 5（构建工具）
- Tailwind CSS 3（样式）
- React Router（路由）
- Lucide React（图标）

## 当前页面

| 页面 | 路由 | 组件 |
|------|------|------|
| 主页面 | / | SearchBox + GameList + InstallProgress + StatusBar |
| 设置页 | /settings | Settings |
| VIP 页 | /vip | VIPPage（激活码 + 功能对比） |

## 核心文件
- 主进程：electron/main.ts
- Python 桥接：electron/pythonBridge.ts
- API 客户端：src/api/client.ts
- Hooks：src/hooks/（useSearch, useInstall, useDevice, useSettings, useAuth, useDebounce）
- 类型定义：src/types/

## 你的职责
1. UI 组件开发和维护
2. 交互逻辑优化
3. 新增页面/组件（如 VIP 批量安装 UI、实时进度等）
4. 样式调整和适配
5. Electron 主进程维护

## 设计规范
- 深色主题：背景 #1A1A2E，卡片 #16213E，强调色 #E94560
- 基础版 UI：极简，无灰色禁用按钮（直接隐藏 VIP 功能）
- VIP 入口：金色 Crown 图标，醒目但不突兀
- 图标：使用 lucide-react
- 不使用 emoji 或 em dash

## 开发规则
1. 编码前思考：先读相关组件代码再改
2. 简洁至上：组件职责单一，不搞过度抽象
3. 精准修改：只改当前组件，不碰其他页面
4. 目标驱动：npm run build 通过为验收

## 注意事项
- 修改后务必运行 npm run build 验证编译通过
- Electron 主进程和渲染进程通过 preload.ts 桥接
- API 请求在开发环境走 Vite proxy，生产环境走 Electron PythonBridge
