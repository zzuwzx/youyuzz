# Phase 2: Electron GUI 总览

> 更新时间：2026-05-27 | Phase 2 进行中

---

## 模块清单

| # | 模块 | 目录 | 状态 | 优先级 |
|---|---|---|---|---|
| P2-M1 | 项目脚手架 | pc-client/frontend/ | ✅ 完成 | P0 |
| P2-M2 | 基础版 UI | pc-client/frontend/src/ | ✅ 完成 | P0 |
| P2-M3 | 核心交互 | pc-client/frontend/src/ | ✅ 完成 | P0 |
| P2-M4 | 进程管理 | pc-client/frontend/electron/ | ✅ 完成 | P1 |
| P2-M5 | 打包发布 | pc-client/frontend/ | 🔜 待开始 | P1 |

## 依赖关系

```
P2-M1 (脚手架) ✅
  └── P2-M2 (UI页面) ✅ ──→ P2-M3 (API交互) ✅ ──→ P2-M4 (进程管理) ✅
                                                       │
                                                       └── P2-M5 (打包) 🔜
```

## 开发顺序

1. P2-M1: ✅ 完成 (Vite build OK, 196KB JS + 17KB CSS)
2. P2-M2: ✅ 完成 (StatusBar + SearchBox + GameList + InstallButton + Settings + VIP)
3. P2-M3: ✅ 完成 (API 通信层 + 搜索 + 安装 + 设备检测 + 本地安装 + 设置 + 状态覆盖)
4. P2-M4: Electron 启动/监控/退出 Python 子进程
5. P2-M5: PyInstaller + electron-builder → Windows 安装包

## P2-M3 完成详情

- API 通信层: `src/api/client.ts` (fetch wrapper, 统一错误处理)
- 搜索交互: SearchBox + GameList + useSearch Hook
- 安装交互: InstallProgress + useInstall Hook (轮询进度)
- 设备检测: DeviceStatus + useDevice Hook + Modal 弹窗
- 本地安装: LocalInstall 组件 (文件夹选择)
- 设置持久化: Settings + useSettings Hook
- 状态组件: Loading + Error + Empty
- 构建验证: TypeScript 编译通过, Vite 构建成功

## 设计规范

见 docs/05_UI设计规范.md：深色主题 #1A1A2E + 霓虹红粉 #E94560


