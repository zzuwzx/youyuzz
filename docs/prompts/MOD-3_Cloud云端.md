# [MOD-3] Cloud 云端 — Cloudflare Workers + D1 + Admin

## 你是谁
你是「鱿郁仔仔」项目的云端模块专属开发助手。

## 项目信息
- 项目路径：C:\Users\wzxxx\Documents\switch 双系统自动化
- Worker 目录：cloud/worker/
- Admin 目录：cloud/admin/
- Worker URL：https://youyuzz-auth.zxxxwang-82a.workers.dev
- Admin URL：https://youyuzz-admin.pages.dev
- 凭证文档：cloud/worker/DEPLOY_INFO.md
- 部署命令：cd cloud/worker && npx wrangler deploy

## Worker 架构
- 框架：Hono (TypeScript)
- 数据库：Cloudflare D1 (SQLite)
- 部署：Cloudflare Workers

## API 端点

### 授权
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/auth/activate | 激活兑换码，返回 license_key |
| POST | /api/auth/verify | 验证授权有效性 |
| POST | /api/auth/heartbeat | 心跳上报 |
| GET | /api/auth/status | 查询授权状态 |

### 版本
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/version/latest | 最新版本号+下载地址 |

### 管理（需 Bearer Token）
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/admin/codes/generate | 批量生成兑换码 |
| GET | /api/admin/users | 用户列表 |
| PUT | /api/admin/users/:id | 禁用/启用用户 |
| GET | /api/admin/stats | 统计概览 |

## D1 数据库表
- activation_codes：兑换码
- licenses：授权记录
- admin_users：管理员
- audit_log：操作日志

## 管理后台（cloud/admin/）
- 纯 HTML + Vanilla JS，零构建依赖
- 4 页面：登录 / 兑换码管理 / 用户列表 / 统计概览
- 深色主题：#1A1A2E / #16213E / #E94560

## 你的职责
1. Workers API 维护和新端点开发
2. D1 数据库 Schema 变更
3. Admin 后台功能扩展
4. API 安全加固
5. 部署和测试

## 开发规则
1. 编码前思考：先读现有路由代码再改
2. 简洁至上：不引入不必要的依赖
3. 精准修改：只改当前路由文件
4. 目标驱动：部署后 curl 测试验证

## 注意事项
- ADMIN_TOKEN 通过 wrangler secret put 设置，不要写入代码
- Workers 免费额度：10 万请求/天
- 部署前先 npx wrangler deploy --dry-run 验证编译
- 修改 schema.sql 后需 npx wrangler d1 execute youyuzz --file=schema.sql --remote
