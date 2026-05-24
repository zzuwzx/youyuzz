# M6: FastAPI 本地服务

> pc-client/backend/api/ | 待开发

## 目标
本地HTTP API(localhost:18888)，供Electron GUI调用，整合所有后端模块。

## API路由
`
GET  /api/search          游戏搜索
GET  /api/game/detail      游戏详情
POST /api/install          开始安装
GET  /api/install/{id}     安装进度
POST /api/install/local    本地离线安装
GET  /api/device/switch    Switch设备状态
GET  /api/device/tfcard    TF卡状态
GET  /api/settings         读取配置
PUT  /api/settings         更新配置
POST /api/auth/activate    激活码验证
GET  /api/version          版本信息
GET  /api/health           健康检查
`

## 待办
- [ ] FastAPI应用初始化+CORS
- [ ] 注册所有路由
- [ ] 请求/响应Pydantic模型
- [ ] 统一错误处理中间件
- [ ] 日志配置
- [ ] SSE实时进度(可选,先轮询)
- [ ] 单元测试(TestClient)