# M6: FastAPI 本地服务

> pc-client/backend/api/ | 开发完成 (2026-05-25)

## 目标
本地HTTP API(localhost:18888)，供Electron GUI调用，整合所有后端模块。

## 文件清单

| 文件 | 用途 |
|---|---|
| `backend/config.py` | 全局配置单例（端口18888、路径、爬虫开关、MTP后端选择），自动创建 `%APPDATA%/youyuzz/` 缓存/数据/日志目录 |
| `backend/main.py` | FastAPI 应用入口：CORS 全放行、统一错误处理中间件、双通道日志（控制台+按天轮转文件）、lifespan 管理 scraper/MTP 生命周期 |
| `backend/api/__init__.py` | 路由聚合器，挂载所有子路由到 `/api` 前缀（5个tag） |
| `backend/api/models.py` | 全部 Pydantic v2 请求/响应模型（15个模型） |
| `backend/api/search.py` | `GET /api/search` + `GET /api/game/detail`，集成 M2 scraper |
| `backend/api/install.py` | `POST /api/install` + `GET /api/install/{task_id}/progress` + `POST /api/install/local` + `POST /api/install/batch` + `GET /api/install/{task_id}/stream` (SSE)，内存任务存储 |
| `backend/api/device.py` | `GET /api/device/switch` + `GET /api/device/tfcard`，集成 M1 MTP 后端 + Windows 盘符检测 |
| `backend/api/settings.py` | `GET/PUT /api/settings`（持久化到 `%APPDATA%/youyuzz/data/settings.json`）+ `POST /api/auth/activate`（Phase 1 本地放行） |
| `backend/api/system.py` | `GET /api/version` + `GET /api/health` |
| `backend/tests/test_api.py` | 单元测试：34 个用例，覆盖全部 13 个端点（含 SSE schema 注册 + 进度数据一致性），0.89s 全通过 |

## API路由（13个端点全部可访问）

| 方法 | 路径 | 说明 | 状态 |
|---|---|---|---|
| GET | `/api/search` | 游戏搜索（集成 M2 scraper） | ✅ |
| GET | `/api/game/detail` | 游戏详情（网盘链接解析） | ✅ |
| POST | `/api/install` | 开始安装（返回 task_id） | ✅ |
| GET | `/api/install/{task_id}/progress` | 安装进度轮询 | ✅ |
| GET | `/api/install/{task_id}/stream` | 安装进度 SSE 实时推送 | ✅ |
| POST | `/api/install/local` | 本地离线安装 | ✅ |
| POST | `/api/install/batch` | 批量安装（VIP） | ✅ |
| GET | `/api/device/switch` | Switch设备状态（集成 M1） | ✅ |
| GET | `/api/device/tfcard` | TF卡状态（Windows盘符） | ✅ |
| GET | `/api/settings` | 读取配置 | ✅ |
| PUT | `/api/settings` | 更新配置 | ✅ |
| POST | `/api/auth/activate` | 激活码验证 | ✅ |
| GET | `/api/version` | 版本信息 | ✅ |
| GET | `/api/health` | 健康检查 | ✅ |

## 待办

- [x] FastAPI应用初始化+CORS
- [x] 注册所有路由
- [x] 请求/响应Pydantic模型
- [x] 统一错误处理中间件
- [x] 日志配置
- [x] 集成 M1-M5 模块（scraper + MTP 已注入，其余待 Phase 2 对接安装管线）
- [x] SSE实时进度（`GET /api/install/{task_id}/stream`，retry/data/done 事件，500ms 增量推送，客户端断开检测）
- [x] 单元测试（`tests/test_api.py`，34 个用例，0.89s 全通过）

## 启动方式

```powershell
cd pc-client/backend
./venv/Scripts/python.exe -m uvicorn main:app --host 127.0.0.1 --port 18888 --reload
```

## 运行测试

```powershell
cd pc-client/backend
./venv/Scripts/pytest.exe tests/test_api.py -v
```

Swagger UI: http://127.0.0.1:18888/docs
