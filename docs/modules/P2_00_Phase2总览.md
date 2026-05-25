# Phase 2: Electron GUI 总览

> 更新时间：2026-05-25 | Phase 2 进行中

---

## 模块清单

| # | 模块 | 目录 | 状态 | 优先级 |
|---|---|---|---|---|
| P2-M1 | 项目脚手架 | pc-client/frontend/ | ✅ 完成 | P0 |
| P2-M2 | 基础版 UI | pc-client/frontend/src/ | 🔴 待开始 | P0 |
| P2-M3 | 核心交互 | pc-client/frontend/src/ | 🔴 待开始 | P0 |
| P2-M4 | 进程管理 | pc-client/frontend/electron/ | 🟡 待开始 | P1 |
| P2-M5 | 打包发布 | pc-client/frontend/ | 🟡 待开始 | P1 |

## 依赖关系

`
P2-M1 (脚手架)
  └── P2-M2 (UI页面) ──→ P2-M3 (API交互) ──→ P2-M4 (进程管理)
                                                       │
                                                       └── P2-M5 (打包)
`

## 开发顺序

1. P2-M1: ✅ 完成 (Vite build OK, Electron 待后期)
2. P2-M2: 搜索框 → 结果列表 → 安装按钮 → 状态栏 → 设置页 → VIP入口
3. P2-M3: 调后端 API(localhost:18888) + 设备检测弹窗 + 本地离线安装
4. P2-M4: Electron 启动/监控/退出 Python 子进程
5. P2-M5: PyInstaller + electron-builder → Windows 安装包

## 设计规范

见 docs/05_UI设计规范.md：深色主题 #1A1A2E + 霓虹红粉 #E94560
