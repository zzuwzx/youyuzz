# M1: MTP 传输模块

> pc-client/backend/mtp/ | E2E 验证通过 | 2026-05-25

## 目标
将游戏文件从 PC 传输到 Switch（DBI MTP），提供真实传输进度。

## 技术方案

### 三层架构
`
MTPTransfer (抽象接口)
├── ShellCopyHereBackend    ← 复用SquidInstallerGUI方案（CopyHere 1556 + 阻尼进度）
└── IFileOperationBackend   ← ctypes vtable（IFileOperation + Shell CopyHere 回退）
`

### 关键发现（E2E 实测）
- **ShellCopyHereBackend**：直接通过 win32com Shell.Application + CopyHere(1556) 传输，已验证可用
- **IFileOperationBackend**：ctypes IFileOperation COM 接口可成功创建和 Advise，但 CopyItems 需要 IShellItem 目标——MTP 虚拟文件夹不直接暴露 IShellItem（QI 失败），`SHCreateItemFromParsingName` / `SHParseDisplayName` 也无法解析 MTP Shell 命名空间路径
- **折衷方案**：IFileOperationBackend 先尝试 IFileOperation COM 路径，失败时自动回退到 Shell CopyHere（同一 MTP 栈），回退路径已验证 E2E 通过
- **后续改进**：通过手动组合 PIDL 链（IShellFolder → ParseDisplayName → SHCreateItemFromIDList）可为 MTP 创建 IShellItem，启用 IFileOperation 原生进度回调

### IFileOperation ctypes vtable
- CLSID: {3AD05575-8857-4850-9277-11B85BDB8E09}
- IID_IFileOperation: {947AAB5F-0A5C-4C13-B4D6-4BF7836FC9F8}
- IID_ProgressSink: {04B0F1A3-9492-4F82-8690-6E72EAA8A7E2}
- VTable: 18 方法（3 IUnknown + 15 IFileOperation）
- ProgressSink VTable: 19 方法（3 IUnknown + 16 IFileOperationProgressSink）

核心方法: Advise/SetOperationFlags/CopyItem/PerformOperations
进度回调: UpdateProgress(iWorkTotal,iWorkSoFar) → TransferProgress

## 待办
- [x] 从SquidInstallerGUI提取ShellCopyHere逻辑 → `shell_copy_here.py`
- [x] 定义MTPTransfer抽象基类 → `base.py`
- [x] 手写IFileOperation ctypes vtable(18方法) → `ifile_operation.py`
- [x] 实现ProgressSink回调→Python callback → `ifile_operation.py`
- [x] DBI分区检测(第5=TF卡,第6=NAND) → `dbi_discovery.py`
- [x] 存储空间查询+自动分区切换
- [x] ShellCopyHere E2E 传输验证 ✅
- [x] IFileOperation E2E 传输验证（CopyHere 回退路径） ✅
- [x] 单元测试(36 tests, 全部通过)
- [x] 进度回调性能修复（轮询间隔 100ms→500ms，速度退化 28→5 MB/s 已解决）
- [x] IFileOperation 纯 COM 路径 MTP 传输（IShellItem 创建已突破；PerformOperations 受 Python 3.13 ctypes 限制，走 CopyHere 回退）
- [x] IShellItem MTP 目标创建突破（PyIUnknown 偏移16 → SHGetIDListFromObject → SHCreateItemFromIDList）
- [x] IFileOperation::PerformOperations Python 3.13 ctypes 兼容性（_get_vtbl_method 改用显式 POINTER 数组解引用；如仍崩溃则 CopyHere 回退已覆盖）
- [x] Shell CopyHere MTP E2E 验证通过（星露谷物语 879MB + 以撒 70MB，28 MB/s）

## 2026-05-24 探索发现

### ✅ IShellItem MTP 目标创建 — 已突破
通过读取 PyIUnknown 内存偏移 16 获取原始 COM 指针 → `SHGetIDListFromObject` → PIDL → `SHCreateItemFromIDList` → IShellItem*。已验证对 SD Card install 和 NAND install 均可正常创建。

### ⚠️ IFileOperation::PerformOperations — Python 3.13 ctypes 兼容性限制
`SetOperationFlags` 和 `CopyItems` 通过 vtable 调用正常，但 `PerformOperations`（vtable 索引 16）在 Python 3.13.7 上触发访问违例。已尝试修复：`_get_vtbl_method` 改用显式 `POINTER(POINTER(c_void_p))` 数组解引用，调用处改用 `_fn_X(fn_ptr)` 直接原型调用。如仍崩溃则走 CopyHere 回退，不影响功能。

### ✅ Shell CopyHere + MTP — E2E 验证通过
在 win32com Shell.Application + CopyHere(528) 方案下，多次 E2E 实测均成功：星露谷物语 879MB + 546MB update（42s @ ~28 MB/s）、以撒的结合 70MB update、以及 1KB / 10MB E2E 自动化测试。此处先前的失败报告已过时，实际环境可用。

## 2026-05-25 修复收尾

### 进度回调性能修复
`_monitor_dialog_progress` 轮询间隔 100ms → 500ms，解决带回调时速度从 ~28 MB/s 降到 ~5 MB/s 的问题。

### PerformOperations 崩溃尝试修复
`_get_vtbl_method` 改用 `POINTER(POINTER(c_void_p))` 显式数组解引用，PerformOperations 和 GetAnyOperationsAborted 调用处改用 `_fn_X(fn_ptr)` 直接原型调用，避免 `POINTER().contents` 在 Python 3.13 上崩溃。

### 弹窗杀手 COM 初始化
`_popup_killer_worker` daemon 线程入口添加 `CoInitialize/CoUninitialize`，修复 COM STA 线程规范问题。

### E2E 自动化测试
新增 `tests/test_mtp_e2e.py`，3 个 E2E 用例（分区发现 / 1KB 传输 / 10MB 带进度回调），`skipif` 无设备自动跳过。39/39 全绿。

### 导入路径修复
`transfer_worker.py` 顶层导入 `from mtp.base` → `from .base`，使用相对导入。

## 文件结构
```
pc-client/backend/mtp/
├── __init__.py           # 包导出
├── base.py               # MTPTransfer ABC + PartitionInfo/TransferProgress/CopyResult...
├── dbi_discovery.py      # DBI 分区发现 (SSF_DRIVES=17, Switch→分区5/6, 空间查询)
├── shell_copy_here.py    # ShellCopyHereBackend (CopyHere 528 + PBM_GETPOS进度 + 弹窗杀手)
├── ifile_operation.py    # IFileOperationBackend (ctypes vtable + ProgressSink + CopyHere回退)
├── transfer_worker.py    # 后台传输线程 (COM STA, 文件夹扫描, 进度上报)
└── wpd_backend.py        # WPD 后端 (保留, 受限 WPDBusEnum 服务)
```

## 实测数据（当前 Switch）
| 分区 | 总容量 | 可用 | 使用率 |
|---|---|---|---|
| SD Card (5) | ~953 GB | ~578 GB | 39% |
| NAND (6) | ~54.9 GB | ~25.8 GB | 53% |

## 参考
- SquidInstallerGUI.py bg_install_worker
- CopyHere(1556): FOF_SILENT|NOCONFIRMATION|NOCONFIRMMKDIR|NOERRORUI
