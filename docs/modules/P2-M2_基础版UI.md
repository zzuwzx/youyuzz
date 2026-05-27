# P2-M2: 基础版 UI 页面

> pc-client/frontend/src/ | ✅ 已完成 | 2026-05-27

## 目标
极简纯净的 GUI，仅保留核心功能入口，无灰色不可用按钮。

## 页面清单
| 页面 | 路由 | 内容 | 状态 |
|---|---|---|---|
| 主页面 | / | 搜索框 + 结果列表 + 安装按钮 + 状态栏 | ✅ |
| 设置页 | /settings | 网盘/通知/通用 3 个分组 | ✅ |
| VIP 升级页 | /vip | 基础版 vs VIP 对比 + 激活码输入 | ✅ |

## 组件清单
| 组件 | 说明 | 状态 |
|---|---|---|
| SearchBox | 搜索输入框（48px, 500ms 防抖） | ✅ |
| GameList | 搜索结果列表（标题/版本/大小） | ✅ |
| InstallButton | 安装按钮（#E94560 霓虹红粉，200x44px） | ✅ |
| ProgressBar | 进度条（6px，速度/ETA 显示） | ✅ |
| StatusBar | 顶部状态栏（Switch状态 + 版本 + VIP状态） | ✅ |
| DeviceStatus | 设备状态卡片 | ✅ |
| Modal | 弹窗组件 | ✅ |
| Loading | 加载状态 | ✅ |
| Error | 错误状态 + 重试 | ✅ |
| Empty | 空状态 | ✅ |
| LocalInstall | 本地离线安装弹窗 | ✅ |
| Settings | 设置面板 | ✅ |
| InstallProgress | 安装进度详情 | ✅ |

## 文件清单
| 文件 | 说明 |
|---|---|
| src/components/SearchBox.tsx | 搜索框（500ms 防抖，useDebounce） |
| src/components/GameList.tsx | 游戏列表（骨架屏 + 空状态） |
| src/components/InstallButton.tsx | 安装按钮（霓虹红粉 #E94560） |
| src/components/ProgressBar.tsx | 进度条（背景 #2A2A4A，填充 #E94560） |
| src/components/StatusBar.tsx | 顶部状态栏（Switch/VIP/版本） |
| src/components/index.ts | 组件统一导出 |
| src/pages/MainPage.tsx | 主页面布局 |
| src/pages/SettingsPage.tsx | 设置页面（3 组设置） |
| src/pages/VIPPage.tsx | VIP 升级页面（对比卡片 + 激活码） |
| src/hooks/useDebounce.ts | 500ms 防抖 Hook |
| src/types/api.ts | 类型定义（GameItem/InstallProgress 等） |

## 构建验证
- `npm run build` ✅ 通过
- 输出: 196KB JS + 17KB CSS
- 路由 `/` `/settings` `/vip` 正常
- lucide-react 图标库已集成

## 待办清单
- [x] 主页面布局（搜索 + 列表 + 操作栏）
- [x] SearchBox 组件（48px, 500ms 防抖）
- [x] GameList 组件（封面 + 标题 + 版本 + 大小）
- [x] InstallButton + 进度条（#E94560 霓虹红粉）
- [x] StatusBar 组件（Switch状态 + 版本 + VIP状态）
- [x] 设置页面（网盘/通知/通用 3 个分组）
- [x] VIP 升级页面（对比卡片 + 激活码输入）
- [x] 组件导出索引更新
- [x] 文档更新

## 下一步
- P2-M3: 接入后端 API（localhost:18888）
- P2-M4: Electron 主进程 + Python 子进程管理
