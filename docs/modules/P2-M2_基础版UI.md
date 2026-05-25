# P2-M2: 基础版 UI 页面

> pc-client/frontend/src/ | 待开始

## 目标
极简纯净的 GUI，仅保留核心功能入口，无灰色不可用按钮。

## 页面清单
| 页面 | 路由 | 内容 |
|---|---|---|
| 主页面 | / | 搜索框 + 结果列表 + 安装按钮 + 状态栏 |
| 设置页 | /settings | Cookie/PushDeer Key/网盘账号/通用设置 |
| VIP升级页 | /vip | 基础版 vs VIP 对比 + 激活码输入 |

## 组件
- SearchBox — 搜索输入框（48px, 500ms 防抖）
- GameList — 搜索结果列表
- InstallButton — 安装按钮（#E94560 霓虹红粉）
- StatusBar — 顶部状态栏（Switch状态 + 版本 + VIP状态）
- SettingsPanel — 设置侧滑面板
- VIPUpgrade — VIP 升级页

## 待办
- [ ] 主页面布局（搜索 + 列表 + 操作栏）
- [ ] SearchBox 组件
- [ ] GameList 组件
- [ ] InstallButton + 进度条
- [ ] StatusBar 组件
- [ ] 设置页面（3个分组）
- [ ] VIP 升级页面（对比卡片 + 激活码输入）
