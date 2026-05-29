# P3-M3: 网页端管理后台

> cloud/admin/ | ✅ 已完成（2026-05-28）

## 目录
```
cloud/admin/
  index.html          主页面
  css/style.css       深色主题样式
  js/api.js           API 封装
  js/auth.js          登录状态管理
  js/router.js        hash 路由
  js/pages/login.js   登录页
  js/pages/codes.js   兑换码管理
  js/pages/users.js   用户列表
  js/pages/stats.js   统计概览
```

## 技术栈
- 纯 HTML + Vanilla JS + CSS，零构建依赖
- 深色主题：#1A1A2E / #16213E / #E94560

## 页面
| 页面 | 路由 | 功能 |
|------|------|------|
| 登录 | #/login | 输入 Admin Token |
| 兑换码 | #/codes | 批量生成、复制、导出 CSV |
| 用户 | #/users | 查看列表、禁用/启用 |
| 统计 | #/stats | 总授权/活跃/已用码/未用码 |

## 部署
- **Worker URL**：`https://youyuzz-auth.zxxxwang-82a.workers.dev`（已在 api.js 中配置）
- **Pages 地址**：https://youyuzz-admin.pages.dev
- **部署时间**：2026-05-28

## 本地测试
浏览器直接打开 `cloud/admin/index.html`
