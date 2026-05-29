# P3-M2: Cloudflare Workers API

> cloud/worker/ | ✅ 已完成（2026-05-28）

## 目标
实现授权验证 + 版本查询 API。

## Worker 部署信息
- **Worker 地址**：https://youyuzz-auth.zxxxwang-82a.workers.dev
- **凭证文档**：cloud/worker/DEPLOY_INFO.md
- **D1 数据库**：youyuzz（dbc5a8ff-7c30-41d4-bc90-8afdfa55a1dd）
- **部署时间**：2026-05-28

## API 端点

### 授权
| 方法 | 路径 | 说明 |
|---|---|---|
| POST | /api/auth/activate | 激活兑换码，返回 license_key |
| POST | /api/auth/verify | 验证授权是否有效 |
| POST | /api/auth/heartbeat | 心跳上报（超30天未上报→吊销） |
| GET | /api/auth/status | 查询授权状态、到期时间 |

### 版本
| 方法 | 路径 | 说明 |
|---|---|---|
| GET | /api/version/latest | 最新版本号和下载地址 |

### 管理（需 Admin Token）
| 方法 | 路径 | 说明 |
|---|---|---|
| POST | /api/admin/codes/generate | 批量生成兑换码 |
| GET | /api/admin/users | 用户列表 |
| PUT | /api/admin/users/{id} | 修改用户状态 |
| GET | /api/admin/stats | 统计概览 |

## 测试结果（2026-05-28）

| # | 端点 | 结果 | 响应摘要 |
|---|---|---|---|
| 1 | GET /api/health | ✅ | {"status":"ok"} |
| 2 | GET /api/version/latest | ✅ | {"version":"1.0.0","download_url":"..."} |
| 3 | POST /api/admin/codes/generate | ✅ | 生成 2 个兑换码（T2M6-TDUY-XGTT, FA3L-HN5G-Q6P4） |
| 4 | GET /api/admin/users | ✅ | 激活前返回空数组 |
| 5 | GET /api/admin/stats | ✅ | codes_unused:2, active_licenses:0 |
| 6 | POST /api/auth/activate | ✅ | 返回 license_key: 03187466-9529-... |
| 7 | POST /api/auth/verify | ✅ | {"valid":true,"expires_at":"2026-06-27"} |
| 8 | POST /api/auth/heartbeat | ✅ | {"ok":true} |
| 9 | GET /api/auth/status | ✅ | 设备信息 + 到期时间 + 最后心跳时间 |

### 错误处理验证

| 测试场景 | 预期 | 结果 |
|---|---|---|
| 缺少参数（activate/verify/heartbeat） | 400 Bad Request | ✅ |
| 错误 license_key | {"valid":false} | ✅ |
| 无 Admin Token 访问 admin 接口 | 401 Unauthorized | ✅ |

### CORS 验证

| 测试场景 | 结果 |
|---|---|
| OPTIONS 预检请求 | ✅ 204，返回 Access-Control-Allow-Origin: * |
| GET + Origin 头 | ✅ 返回 Access-Control-Allow-Origin: * |

### 激活后数据一致性

| 检查项 | 结果 |
|---|---|
| codes_used: 1 | ✅ |
| codes_unused: 1 | ✅ |
| active_licenses: 1 | ✅ |
| users 列表包含激活记录 | ✅ |

## 待办
- [x] Worker 路由架构（Hono 框架）
- [x] POST /api/auth/activate
- [x] POST /api/auth/verify
- [x] POST /api/auth/heartbeat
- [x] GET /api/auth/status
- [x] GET /api/version/latest
- [x] Admin 中间件（Token 校验）
- [x] POST /api/admin/codes/generate
- [x] GET /api/admin/users
- [x] PUT /api/admin/users/{id}
- [x] GET /api/admin/stats
- [x] CORS 配置
- [x] 错误处理
- [x] 部署到 Cloudflare
- [x] 全部端点测试验证
- [ ] 单元测试（Miniflare + Vitest）— 待补充