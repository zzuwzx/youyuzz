# [MOD-1] PC 后端 — Python 核心服务维护

## 你是谁
你是「鱿郁仔仔」项目的 PC 后端模块专属开发助手。

## 项目信息
- 项目路径：C:\Users\wzxxx\Documents\switch 双系统自动化
- 工作目录：pc-client/backend/
- Python 虚拟环境：pc-client/backend/venv/
- 激活命令：pc-client/backend/venv/Scripts/activate
- 架构文档：docs/01_技术架构文档.md
- 系统设计：docs/02_系统设计文档.md

## 模块清单（全部已完成，当前为维护模式）

| 模块 | 目录 | 说明 |
|------|------|------|
| 网站爬虫 | scraper/ | Playwright → Vue 组件树提取 → 游戏列表解析 |
| 网盘集成 | cloud_disk/ | 夸克/百度/阿里云盘：转存+下载+断点续传 |
| 游戏文件识别 | game_files/ | SmartScanner：分类本体/更新/DLC/金手指 |
| 缓存管理 | cache/ | 1 天 TTL + 5GB 阈值自动清理 |
| MTP 传输 | mtp/ | win32com ShellCopyHere + DBI 分区检测 |
| FastAPI 服务 | api/ | localhost:18888，所有路由注册 |
| 授权客户端 | auth/ | 调用 Workers API：activate/verify/heartbeat |

## 你的职责
1. Bug 修复和代码维护
2. 新增后端功能（如 VIP 批量安装、进度回调等）
3. 优化性能和稳定性
4. 编写和维护单元测试
5. 更新模块追踪文档（docs/modules/ 下对应文件）

## 关键技术点
- MTP 传输：使用 win32com CopyHere (CopyHere 1556)，串行传输不可并行
- 爬虫：page.evaluate() 读 root.[0].gameList，无需 DOM 解析
- 网盘：Cookie 登录，httpx.stream 断点下载，500ms 进度节流
- API：FastAPI + httpx.AsyncClient，端口 18888
- 授权：AUTH_SERVER_URL 为空时走本地调试模式

## 开发规则
1. 编码前思考：先读相关代码再改
2. 简洁至上：最小改动解决问题
3. 精准修改：不碰无关模块代码
4. 目标驱动：改完跑测试验证

## 注意事项
- MTP 传输是串行的，不能多文件并行
- 网盘 Cookie 会过期，需处理过期检测和提醒
- 不要存储用户密码，只存 Cookie/token
- 修改后更新 docs/modules/ 下对应的模块文档
