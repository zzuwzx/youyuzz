# M1: MTP 传输模块

> pc-client/backend/mtp/ | 方案确定待开发

## 目标
将游戏文件从 PC 传输到 Switch（DBI MTP），提供真实传输进度。

## 技术方案

### 三层架构
`
MTPTransfer (抽象接口)
├── ShellCopyHereBackend    ← 复用SquidInstallerGUI方案快速上线
└── IFileOperationBackend   ← ctypes vtable真实进度回调
`

### IFileOperation ctypes vtable
- CLSID: {3AD05575-8857-4850-9277-11B85BDB8E09}
- IID_IFileOperation: {947AAB5F-0A5C-4C13-B4D6-4BF7836FC9F8}
- IID_ProgressSink: {04B0F1A3-9492-4F82-8690-6E72EAA8A7E2}

核心方法: Advise/SetOperationFlags/CopyItem/PerformOperations
进度回调: UpdateProgress(iWorkTotal,iWorkSoFar)

## 待办
- [ ] 从SquidInstallerGUI提取ShellCopyHere逻辑
- [ ] 定义MTPTransfer抽象基类
- [ ] 手写IFileOperation ctypes vtable(12方法)
- [ ] 实现ProgressSink回调→Python callback
- [ ] DBI分区检测(第5=TF卡,第6=NAND)
- [ ] 存储空间查询+自动分区切换
- [ ] 单元测试(Mock COM+真实设备E2E)

## 参考
- SquidInstallerGUI.py bg_install_worker
- CopyHere(1556): FOF_SILENT|NOCONFIRMATION|NOCONFIRMMKDIR|NOERRORUI