"""
IFileOperation 后端 — 纯 ctypes vtable 实现

通过手写 COM vtable 调用 Windows IFileOperation 接口，获得:
  - 原生 Advise(IFileOperationProgressSink) 进度回调
  - 基于 Shell MTP 栈的可靠传输
  - 零外部依赖（仅 ctypes + shell32/ole32 DLL）

技术细节:
  - CLSID_FileOperation:  {3AD05575-8857-4850-9277-11B85BDB8E09}
  - IID_IFileOperation:   {947AAB5F-0A5C-4C13-B4D6-4BF7836FC9F8}
  - IID_ProgressSink:     {04B0F1A3-9492-4F82-8690-6E72EAA8A7E2}
  - IID_IShellItem:       {43826D1E-E718-42EE-BC55-A1E261C37BFE}

VTable 布局 (IUnknown + IFileOperation = 18 方法):
  [0]  QueryInterface
  [1]  AddRef
  [2]  Release
  [3]  Advise
  [4]  Unadvise
  [5]  SetOperationFlags
  [6]  SetProgressMessage
  [7]  SetProgressDialog
  [8]  SetProperties
  [9]  SetOwnerWindow
  [10] ApplyPropertiesToItems
  [11] CopyItems
  [12] MoveItems
  [13] NewItem
  [14] DeleteItems
  [15] RenameItems
  [16] PerformOperations
  [17] GetAnyOperationsAborted

参考:
  - SquidInstallerGUI.py 验证了 Shell MTP 栈可靠性
  - docs/01_技术架构文档.md ADR-002
"""
import ctypes
from ctypes import wintypes, POINTER, c_void_p, byref, windll, cast, sizeof
import logging
import os
import threading
import time
import uuid
from typing import Optional

from .base import (
    MTPTransfer, PartitionType, PartitionInfo, CopyResult,
    TransferProgress, ProgressCallback,
)
from .dbi_discovery import DBIDiscoveryError, find_switch_device, discover_partitions as _discover_partitions

logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════
# COM 基础类型
# ══════════════════════════════════════════════════════════

HRESULT = ctypes.c_long
ULONG = wintypes.ULONG
DWORD = wintypes.DWORD
BOOL = wintypes.BOOL
HWND = wintypes.HWND
LPCWSTR = ctypes.c_wchar_p

# COM GUID: 16 字节 (little-endian)
# 结构: Data1(u32) + Data2(u16) + Data3(u16) + Data4(u8×8)
class GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", wintypes.DWORD),
        ("Data2", wintypes.WORD),
        ("Data3", wintypes.WORD),
        ("Data4", wintypes.BYTE * 8),
    ]

REFIID = POINTER(GUID)
REFCLSID = POINTER(GUID)

# Win32 COM API 函数签名
ole32 = windll.ole32
shell32 = windll.shell32

# CoCreateInstance
# HRESULT CoCreateInstance(REFCLSID rclsid, LPUNKNOWN pUnkOuter,
#                          DWORD dwClsContext, REFIID riid, LPVOID *ppv)
ole32.CoCreateInstance.argtypes = [
    REFCLSID, c_void_p, DWORD, REFIID, POINTER(c_void_p),
]
ole32.CoCreateInstance.restype = HRESULT

# SHCreateItemFromParsingName
# HRESULT SHCreateItemFromParsingName(PCWSTR pszPath, IBindCtx *pbc,
#                                     REFIID riid, void **ppv)
shell32.SHCreateItemFromParsingName.argtypes = [
    LPCWSTR, c_void_p, REFIID, POINTER(c_void_p),
]
shell32.SHCreateItemFromParsingName.restype = HRESULT
# SHGetIDListFromObject — 从 Shell 对象获取 PIDL
# HRESULT SHGetIDListFromObject(IUnknown *punk, PIDLIST_ABSOLUTE *ppidl)
shell32.SHGetIDListFromObject.argtypes = [c_void_p, POINTER(c_void_p)]
shell32.SHGetIDListFromObject.restype = HRESULT

# SHCreateItemFromIDList — 从 PIDL 创建 IShellItem
# HRESULT SHCreateItemFromIDList(PCIDLIST_ABSOLUTE pidl, REFIID riid, void **ppv)
shell32.SHCreateItemFromIDList.argtypes = [c_void_p, REFIID, POINTER(c_void_p)]
shell32.SHCreateItemFromIDList.restype = HRESULT

# ILFree — 释放 PIDL
shell32.ILFree.argtypes = [c_void_p]
shell32.ILFree.restype = None


CLSCTX_ALL = 0x17  # CLSCTX_INPROC_SERVER | CLSCTX_INPROC_HANDLER | CLSCTX_LOCAL_SERVER

# 成功/失败 HRESULT 检查
S_OK = 0
E_NOTIMPL = 0x80004001
E_FAIL = 0x80004005
E_NOINTERFACE = 0x80004002


def _make_guid(s: str) -> GUID:
    """将 "{XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX}" 字符串转为 GUID 结构。"""
    u = uuid.UUID(s)
    return GUID(
        Data1=u.time_low,
        Data2=u.time_mid,
        Data3=u.time_hi_version,
        Data4=(wintypes.BYTE * 8)(
            u.clock_seq_hi_variant, u.clock_seq_low,
            *u.node.to_bytes(6, "big"),
        ),
    )


def _check_hr(hr: int, msg: str = "") -> int:
    """检查 HRESULT，失败时记录日志。"""
    if hr < 0:
        logger.error("%s (HRESULT: 0x%08X)", msg, hr & 0xFFFFFFFF)
    return hr


# ── 预定义的 GUID ──────────────────────────────────────

CLSID_FileOperation = _make_guid("{3AD05575-8857-4850-9277-11B85BDB8E09}")
IID_IFileOperation = _make_guid("{947AAB5F-0A5C-4C13-B4D6-4BF7836FC9F8}")
IID_IShellItem = _make_guid("{43826D1E-E718-42EE-BC55-A1E261C37BFE}")
IID_ProgressSink = _make_guid("{04B0F1A3-9492-4F82-8690-6E72EAA8A7E2}")

# Copy 操作 flags
FOF_SILENT = 0x0004
FOF_NOCONFIRMATION = 0x0010
FOF_NOCONFIRMMKDIR = 0x0200
FOF_NOERRORUI = 0x0400
FOFX_NOSIZELIMIT = 0x00000001          # Vista+: 移除 4GB 限制
FOFX_EARLYFAILURE = 0x00100000         # 预检失败

DEFAULT_IFILEOP_FLAGS = (
    FOF_SILENT
    | FOF_NOCONFIRMATION
    | FOF_NOCONFIRMMKDIR
    | FOF_NOERRORUI
    | FOFX_NOSIZELIMIT
)


# ══════════════════════════════════════════════════════════
# IFileOperation VTable (18 个方法)
# ══════════════════════════════════════════════════════════

# 函数签名类型的定义
# 每个方法的第一个参数是 IFileOperation* this 指针

# IUnknown 方法
_fn_QueryInterface = ctypes.WINFUNCTYPE(HRESULT, c_void_p, REFIID, POINTER(c_void_p))
_fn_AddRef = ctypes.WINFUNCTYPE(ULONG, c_void_p)
_fn_Release = ctypes.WINFUNCTYPE(ULONG, c_void_p)

# IFileOperation 方法
_fn_Advise = ctypes.WINFUNCTYPE(HRESULT, c_void_p, c_void_p, POINTER(DWORD))
_fn_Unadvise = ctypes.WINFUNCTYPE(HRESULT, c_void_p, DWORD)
_fn_SetOperationFlags = ctypes.WINFUNCTYPE(HRESULT, c_void_p, DWORD)
_fn_SetProgressMessage = ctypes.WINFUNCTYPE(HRESULT, c_void_p, LPCWSTR)
_fn_SetProgressDialog = ctypes.WINFUNCTYPE(HRESULT, c_void_p, c_void_p)
_fn_SetProperties = ctypes.WINFUNCTYPE(HRESULT, c_void_p, c_void_p)
_fn_SetOwnerWindow = ctypes.WINFUNCTYPE(HRESULT, c_void_p, HWND)
_fn_ApplyPropertiesToItems = ctypes.WINFUNCTYPE(HRESULT, c_void_p, c_void_p)
_fn_CopyItems = ctypes.WINFUNCTYPE(HRESULT, c_void_p, c_void_p, c_void_p)  # IUnknown*, IShellItem*
_fn_MoveItems = ctypes.WINFUNCTYPE(HRESULT, c_void_p, c_void_p, c_void_p)
_fn_NewItem = ctypes.WINFUNCTYPE(HRESULT, c_void_p, c_void_p, DWORD, LPCWSTR, LPCWSTR, c_void_p)
_fn_DeleteItems = ctypes.WINFUNCTYPE(HRESULT, c_void_p, c_void_p)
_fn_RenameItems = ctypes.WINFUNCTYPE(HRESULT, c_void_p, c_void_p, LPCWSTR)
_fn_PerformOperations = ctypes.WINFUNCTYPE(HRESULT, c_void_p)
_fn_GetAnyOperationsAborted = ctypes.WINFUNCTYPE(HRESULT, c_void_p, POINTER(BOOL))

class IFileOperationVtbl(ctypes.Structure):
    _fields_ = [
        # IUnknown
        ("QueryInterface", _fn_QueryInterface),
        ("AddRef", _fn_AddRef),
        ("Release", _fn_Release),
        # IFileOperation
        ("Advise", _fn_Advise),
        ("Unadvise", _fn_Unadvise),
        ("SetOperationFlags", _fn_SetOperationFlags),
        ("SetProgressMessage", _fn_SetProgressMessage),
        ("SetProgressDialog", _fn_SetProgressDialog),
        ("SetProperties", _fn_SetProperties),
        ("SetOwnerWindow", _fn_SetOwnerWindow),
        ("ApplyPropertiesToItems", _fn_ApplyPropertiesToItems),
        ("CopyItems", _fn_CopyItems),
        ("MoveItems", _fn_MoveItems),
        ("NewItem", _fn_NewItem),
        ("DeleteItems", _fn_DeleteItems),
        ("RenameItems", _fn_RenameItems),
        ("PerformOperations", _fn_PerformOperations),
        ("GetAnyOperationsAborted", _fn_GetAnyOperationsAborted),
    ]


# ══════════════════════════════════════════════════════════
# IFileOperationProgressSink VTable + COM 对象
# ══════════════════════════════════════════════════════════

# 进度回调注册表: 通过 COM 对象指针查找 Python callback
_sink_callbacks: dict[int, ProgressCallback] = {}
_sink_lock = threading.Lock()

# ProgressSink 方法签名
_fn_PS_QueryInterface = ctypes.WINFUNCTYPE(HRESULT, c_void_p, REFIID, POINTER(c_void_p))
_fn_PS_AddRef = ctypes.WINFUNCTYPE(ULONG, c_void_p)
_fn_PS_Release = ctypes.WINFUNCTYPE(ULONG, c_void_p)
_fn_PS_StartOperations = ctypes.WINFUNCTYPE(HRESULT, c_void_p)
_fn_PS_FinishOperations = ctypes.WINFUNCTYPE(HRESULT, c_void_p, HRESULT)
_fn_PS_PreRenameItem = ctypes.WINFUNCTYPE(HRESULT, c_void_p, DWORD, c_void_p, LPCWSTR)
_fn_PS_PostRenameItem = ctypes.WINFUNCTYPE(HRESULT, c_void_p, DWORD, c_void_p, LPCWSTR, HRESULT, c_void_p)
_fn_PS_PreMoveItem = ctypes.WINFUNCTYPE(HRESULT, c_void_p, DWORD, c_void_p, c_void_p, LPCWSTR)
_fn_PS_PostMoveItem = ctypes.WINFUNCTYPE(HRESULT, c_void_p, DWORD, c_void_p, c_void_p, LPCWSTR, HRESULT, c_void_p)
_fn_PS_PreCopyItem = ctypes.WINFUNCTYPE(HRESULT, c_void_p, DWORD, c_void_p, c_void_p, LPCWSTR)
_fn_PS_PostCopyItem = ctypes.WINFUNCTYPE(HRESULT, c_void_p, DWORD, c_void_p, c_void_p, LPCWSTR, HRESULT, c_void_p)
_fn_PS_PreDeleteItem = ctypes.WINFUNCTYPE(HRESULT, c_void_p, DWORD, c_void_p)
_fn_PS_PostDeleteItem = ctypes.WINFUNCTYPE(HRESULT, c_void_p, DWORD, c_void_p, HRESULT, c_void_p)
_fn_PS_PreNewItem = ctypes.WINFUNCTYPE(HRESULT, c_void_p, DWORD, c_void_p, LPCWSTR)
_fn_PS_PostNewItem = ctypes.WINFUNCTYPE(HRESULT, c_void_p, DWORD, c_void_p, LPCWSTR, LPCWSTR, DWORD, HRESULT, c_void_p)
_fn_PS_UpdateProgress = ctypes.WINFUNCTYPE(HRESULT, c_void_p, DWORD, DWORD)
_fn_PS_ResetTimer = ctypes.WINFUNCTYPE(HRESULT, c_void_p)
_fn_PS_PauseTimer = ctypes.WINFUNCTYPE(HRESULT, c_void_p)
_fn_PS_ResumeTimer = ctypes.WINFUNCTYPE(HRESULT, c_void_p)

class ProgressSinkVtbl(ctypes.Structure):
    _fields_ = [
        ("QueryInterface", _fn_PS_QueryInterface),
        ("AddRef", _fn_PS_AddRef),
        ("Release", _fn_PS_Release),
        ("StartOperations", _fn_PS_StartOperations),
        ("FinishOperations", _fn_PS_FinishOperations),
        ("PreRenameItem", _fn_PS_PreRenameItem),
        ("PostRenameItem", _fn_PS_PostRenameItem),
        ("PreMoveItem", _fn_PS_PreMoveItem),
        ("PostMoveItem", _fn_PS_PostMoveItem),
        ("PreCopyItem", _fn_PS_PreCopyItem),
        ("PostCopyItem", _fn_PS_PostCopyItem),
        ("PreDeleteItem", _fn_PS_PreDeleteItem),
        ("PostDeleteItem", _fn_PS_PostDeleteItem),
        ("PreNewItem", _fn_PS_PreNewItem),
        ("PostNewItem", _fn_PS_PostNewItem),
        ("UpdateProgress", _fn_PS_UpdateProgress),
        ("ResetTimer", _fn_PS_ResetTimer),
        ("PauseTimer", _fn_PS_PauseTimer),
        ("ResumeTimer", _fn_PS_ResumeTimer),
    ]


class ProgressSinkObject(ctypes.Structure):
    """
    IFileOperationProgressSink COM 对象的内存布局。

    内存结构:
      [0..7]   lpVtbl          → 指向 ProgressSinkVtbl 的指针
      [8..11]  ref_count       → COM 引用计数
      [12..19] py_obj_id       → 用于在 _sink_callbacks 字典中查找 Python callback
    """
    _fields_ = [
        ("lpVtbl", POINTER(ProgressSinkVtbl)),
        ("ref_count", ULONG),
        ("py_obj_id", ctypes.c_size_t),
    ]


# ── ProgressSink 方法实现 ────────────────────────────────

def _sink_get_callback(this_ptr: int) -> Optional[ProgressCallback]:
    """从 COM 对象指针获取关联的 Python 进度回调。"""
    obj = cast(ctypes.c_void_p(this_ptr), POINTER(ProgressSinkObject))
    obj_id = obj.contents.py_obj_id
    with _sink_lock:
        return _sink_callbacks.get(obj_id)


def _sink_register_callback(sink_ptr: int, cb: ProgressCallback):
    """注册进度回调关联。"""
    obj = cast(ctypes.c_void_p(sink_ptr), POINTER(ProgressSinkObject))
    obj_id = obj.contents.py_obj_id
    with _sink_lock:
        _sink_callbacks[obj_id] = cb


def _sink_unregister_callback(sink_ptr: int):
    """注销进度回调关联。"""
    obj = cast(ctypes.c_void_p(sink_ptr), POINTER(ProgressSinkObject))
    obj_id = obj.contents.py_obj_id
    with _sink_lock:
        _sink_callbacks.pop(obj_id, None)


# --- IUnknown 实现 ---

sink_qid = _fn_PS_QueryInterface(lambda this, riid, ppv: _sink_queryinterface(this, riid, ppv))
def _sink_queryinterface(this, riid, ppv):
    """ProgressSink: QueryInterface — 仅支持自身的 IID。"""
    pguid = riid.contents
    our_iid = IID_ProgressSink
    if (pguid.Data1 == our_iid.Data1 and pguid.Data2 == our_iid.Data2
            and pguid.Data3 == our_iid.Data3
            and bytes(pguid.Data4) == bytes(our_iid.Data4)):
        # IID match → 返回自身并 AddRef
        cast(ppv, POINTER(c_void_p))[0] = ctypes.c_void_p(this).value
        _sink_addref(this)
        return S_OK
    cast(ppv, POINTER(c_void_p))[0] = 0
    return E_NOINTERFACE


sink_addref = _fn_PS_AddRef(lambda this: _sink_addref(this))
def _sink_addref(this) -> int:
    obj = cast(ctypes.c_void_p(this), POINTER(ProgressSinkObject))
    obj.contents.ref_count += 1
    return obj.contents.ref_count


sink_release = _fn_PS_Release(lambda this: _sink_release(this))
def _sink_release(this) -> int:
    obj = cast(ctypes.c_void_p(this), POINTER(ProgressSinkObject))
    obj.contents.ref_count -= 1
    if obj.contents.ref_count == 0:
        _sink_unregister_callback(this)
        # 注意: 不释放 Python 分配的 ctypes 内存；由 GC 处理
    return obj.contents.ref_count


# --- IFileOperationProgressSink 方法 ---
# 大多数方法仅返回 S_OK；核心是 UpdateProgress

sink_startops = _fn_PS_StartOperations(lambda this: S_OK)
sink_finishops = _fn_PS_FinishOperations(lambda this, hr: S_OK)
sink_prerename = _fn_PS_PreRenameItem(lambda *a: S_OK)
sink_postrename = _fn_PS_PostRenameItem(lambda *a: S_OK)
sink_premove = _fn_PS_PreMoveItem(lambda *a: S_OK)
sink_postmove = _fn_PS_PostMoveItem(lambda *a: S_OK)
sink_precopy = _fn_PS_PreCopyItem(lambda *a: S_OK)
sink_postcopy = _fn_PS_PostCopyItem(lambda *a: S_OK)
sink_predelete = _fn_PS_PreDeleteItem(lambda *a: S_OK)
sink_postdelete = _fn_PS_PostDeleteItem(lambda *a: S_OK)
sink_prenew = _fn_PS_PreNewItem(lambda *a: S_OK)
sink_postnew = _fn_PS_PostNewItem(lambda *a: S_OK)

sink_update_progress = _fn_PS_UpdateProgress(
    lambda this, total, done: _sink_update_progress(this, total, done)
)
def _sink_update_progress(this, total: int, done: int) -> int:
    """
    核心进度回调。

    Windows 在传输过程中频繁调用此方法:
      - total: 总工作量（字节数相关）
      - done:  已完成工作量
    """
    cb = _sink_get_callback(this)
    if cb:
        ratio = done / total if total > 0 else 0.0
        progress = TransferProgress(
            bytes_total=total,
            bytes_done=done,
            ratio=min(ratio, 1.0),
            elapsed_sec=0.0,   # 由外层 backend 跟踪
        )
        cb(progress)
    return S_OK

sink_reset_timer = _fn_PS_ResetTimer(lambda this: S_OK)
sink_pause_timer = _fn_PS_PauseTimer(lambda this: S_OK)
sink_resume_timer = _fn_PS_ResumeTimer(lambda this: S_OK)


def _create_progress_sink_vtbl() -> ProgressSinkVtbl:
    """构建 ProgressSink vtable 实例。"""
    return ProgressSinkVtbl(
        QueryInterface=sink_qid,
        AddRef=sink_addref,
        Release=sink_release,
        StartOperations=sink_startops,
        FinishOperations=sink_finishops,
        PreRenameItem=sink_prerename,
        PostRenameItem=sink_postrename,
        PreMoveItem=sink_premove,
        PostMoveItem=sink_postmove,
        PreCopyItem=sink_precopy,
        PostCopyItem=sink_postcopy,
        PreDeleteItem=sink_predelete,
        PostDeleteItem=sink_postdelete,
        PreNewItem=sink_prenew,
        PostNewItem=sink_postnew,
        UpdateProgress=sink_update_progress,
        ResetTimer=sink_reset_timer,
        PauseTimer=sink_pause_timer,
        ResumeTimer=sink_resume_timer,
    )


def _create_progress_sink(callback: ProgressCallback) -> tuple[int, ctypes.c_void_p]:
    """
    创建 IFileOperationProgressSink COM 对象。

    Returns:
        (sink_ptr, sink_obj_ptr): COM 对象的内存地址和 ctypes 实例。
        调用方负责在不再需要时释放。
    """
    obj = ProgressSinkObject()
    obj.ref_count = 1
    # 使用 id(callback) 不够唯一——用对象地址
    obj.py_obj_id = id(obj)

    # vtable — 使用类级别共享可减少分配
    _shared_sink_vtbl = _create_progress_sink_vtbl()
    obj.lpVtbl = POINTER(ProgressSinkVtbl)(_shared_sink_vtbl)

    # 注册回调
    _sink_register_callback(ctypes.addressof(obj), callback)

    # 返回对象地址作为 COM 接口指针
    ptr = ctypes.c_void_p(ctypes.addressof(obj))
    return ptr


# ══════════════════════════════════════════════════════════
# IShellItem 辅助: 通过 ParsingName 创建
# ══════════════════════════════════════════════════════════

def _create_shell_item_from_path(file_path: str) -> c_void_p:
    """
    通过 SHCreateItemFromParsingName 创建 IShellItem。

    返回原始 IShellItem 接口指针；调用方需要自行 Release。
    """
    ppv = c_void_p(0)
    hr = shell32.SHCreateItemFromParsingName(
        file_path, None, byref(IID_IShellItem), byref(ppv),
    )
    _check_hr(hr, f"SHCreateItemFromParsingName 失败: {file_path}")
    if hr < 0:
        raise OSError(f"无法创建 IShellItem: {file_path}")
    return ppv



def _create_mtp_shell_item(partition_marker: str) -> c_void_p:
    """
    为 DBI MTP 安装分区创建 IShellItem（PyIUnknown 内存读取 + PIDL 链方案）。

    技术路线:
      1. win32com 导航到 MTP 目标文件夹
      2. 从 PyIUnknown 内存偏移 16 读取原始 COM 指针
      3. SHGetIDListFromObject → PIDL → SHCreateItemFromIDList → IShellItem*

    注意: 此函数临时初始化 COM，调用方应确保在调用前未在
          同一线程持有其他 COM 引用。

    Args:
        partition_marker: "SD Card install" 或 "NAND install"

    Returns:
        原始 IShellItem 接口指针；调用方负责 Release。
    """
    import pythoncom as _pycom
    import win32com.client as _win32
    import struct as _struct

    _pycom.CoInitialize()
    try:
        shell = _win32.Dispatch("Shell.Application")
        mc = shell.NameSpace(17)
        for item in mc.Items():
            if "Switch" in item.Name:
                for sub in item.GetFolder.Items():
                    if partition_marker in sub.Name:
                        unk = sub.GetFolder._oleobj_.QueryInterface(
                            _pycom.IID_IUnknown
                        )
                        buf = (ctypes.c_char * 64).from_address(id(unk))
                        raw_ptr = _struct.unpack_from("<Q", buf.raw, 16)[0]

                        pidl = c_void_p(0)
                        hr = shell32.SHGetIDListFromObject(
                            c_void_p(raw_ptr), byref(pidl)
                        )
                        if hr < 0:
                            raise OSError(
                                f"SHGetIDListFromObject 失败: "
                                f"0x{hr & 0xFFFFFFFF:08X}"
                            )

                        psi = c_void_p(0)
                        hr = shell32.SHCreateItemFromIDList(
                            pidl, byref(IID_IShellItem), byref(psi)
                        )
                        shell32.ILFree(pidl)
                        if hr < 0:
                            raise OSError(
                                f"SHCreateItemFromIDList 失败: "
                                f"0x{hr & 0xFFFFFFFF:08X}"
                            )
                        logger.debug(
                            "MTP IShellItem 创建成功: %s (0x%016X)",
                            partition_marker, psi.value,
                        )
                        return psi
        raise RuntimeError(f"MTP 分区未找到: {partition_marker}")
    finally:
        _pycom.CoUninitialize()

def _release_com(ptr: c_void_p):
    """对 COM 对象调用 Release。"""
    if ptr:
        # 假定对象以标准 IUnknown 布局开头 (vtable[2] = Release)
        vtbl = cast(ptr, POINTER(POINTER(c_void_p)))[0]
        release_fn = cast(vtbl[2], ctypes.CFUNCTYPE(ULONG, c_void_p))
        release_fn(ptr)


# ══════════════════════════════════════════════════════════
# IFileOperation 包装器
# ══════════════════════════════════════════════════════════

def _create_ifile_operation() -> c_void_p:
    """
    通过 CoCreateInstance 创建 IFileOperation COM 实例。

    Returns:
        原始 IFileOperation 接口指针。
    """
    ppv = c_void_p(0)
    hr = ole32.CoCreateInstance(
        byref(CLSID_FileOperation), None, CLSCTX_ALL,
        byref(IID_IFileOperation), byref(ppv),
    )
    _check_hr(hr, "CoCreateInstance(IFileOperation) 失败")
    if hr < 0:
        raise RuntimeError(
            "无法创建 IFileOperation COM 实例。"
            "请确认系统支持 (Windows Vista+)。"
        )
    return ppv


def _get_vtbl_method(ptr: c_void_p, index: int):
    """通过 vtable 获取 COM 对象的指定方法地址。"""
    vtbl_ptr = cast(ptr, POINTER(POINTER(c_void_p)))[0]
    return vtbl_ptr[index]


# ══════════════════════════════════════════════════════════
# IFileOperationBackend
# ══════════════════════════════════════════════════════════

class IFileOperationBackend(MTPTransfer):
    """
    Phase 1 后期后端 — 基于 IFileOperation COM + 原生 Advise 进度回调。

    相比 ShellCopyHereBackend:
      - 真实 Windows MTP 栈进度（非阻尼模拟）
      - 零 pywin32 依赖（仅 ctypes + ole32/shell32 DLL）
      - 支持完整体验的传输速率/ETA 计算
    """

    def __init__(self):
        self._partitions: dict[PartitionType, PartitionInfo] = {}
        self._switch_shell_item: Optional[c_void_p] = None

    # ── 设备发现 ──────────────────────────────────────

    def is_device_connected(self) -> bool:
        try:
            switch_item, _ = find_switch_device()
            return switch_item is not None
        except Exception:
            return False

    def discover_partitions(self) -> dict[PartitionType, PartitionInfo]:
        
        self._partitions = _discover_partitions()
        return self._partitions

    # ── 文件传输 ──────────────────────────────────────

    def copy_file(
        self,
        source: str,
        partition: PartitionType = PartitionType.SD_CARD,
        *,
        on_progress: Optional[ProgressCallback] = None,
    ) -> CopyResult:
        if not os.path.isfile(source):
            logger.error("源文件不存在: %s", source)
            return CopyResult.IO_ERROR

        file_size = os.path.getsize(source)

        # 1. 分区检查
        try:
            if not self._partitions:
                self.discover_partitions()
            pi = self._partitions.get(partition)
            if pi is None:
                return CopyResult.PARTITION_NOT_FOUND
        except DBIDiscoveryError:
            return CopyResult.DEVICE_NOT_FOUND

        # 2. 空间检查
        if file_size > pi.free_bytes > 0:
            return CopyResult.NO_SPACE

        # 3. 尝试 IFileOperation COM 路径（本地文件系统），
        #    失败时回退到 Shell CopyHere（MTP 等 Shell 命名空间）
        try:
            return self._copy_via_ifileoperation(source, file_size, partition, on_progress)
        except (OSError, RuntimeError) as e:
            logger.debug("IFileOperation 不可用，回退到 Shell CopyHere: %s", e)
            return self._copy_via_shell(source, file_size, partition, on_progress)

    def _copy_via_ifileoperation(
        self,
        source: str,
        file_size: int,
        partition: PartitionType,
        on_progress: Optional[ProgressCallback] = None,
    ) -> CopyResult:
        """通过 IFileOperation COM 执行拷贝（仅本地文件系统目标）。"""
        pfo = None
        psi_src = None
        psi_dst = None

        try:
            pfo = _create_ifile_operation()
            psi_src = _create_shell_item_from_path(source)
            psi_dst = _create_shell_item_from_path(self._get_dest_shell_path(partition))

            # SetOperationFlags
            set_flags = cast(
                _get_vtbl_method(pfo, 5),
                POINTER(_fn_SetOperationFlags),
            ).contents
            set_flags(pfo, DEFAULT_IFILEOP_FLAGS)

            # Advise（注册进度回调）
            cookie = DWORD(0)
            if on_progress is not None:
                sink_ptr = _create_progress_sink(on_progress)
                advise_fn = cast(
                    _get_vtbl_method(pfo, 3),
                    POINTER(_fn_Advise),
                ).contents
                advise_fn(pfo, sink_ptr, byref(cookie))

            # CopyItems
            copy_fn = cast(
                _get_vtbl_method(pfo, 11),
                POINTER(_fn_CopyItems),
            ).contents
            hr = copy_fn(pfo, psi_src, psi_dst)
            if _check_hr(hr, "CopyItems 入队失败") < 0:
                return CopyResult.COPY_FAILED

            # PerformOperations —— 阻塞直到完成
            start_time = time.time()
            fn_ptr = _get_vtbl_method(pfo, 16)
            perform_fn = _fn_PerformOperations(fn_ptr)


            hr = perform_fn(pfo)
            elapsed = time.time() - start_time

            if hr < 0:
                logger.error("PerformOperations 失败: 0x%08X", hr & 0xFFFFFFFF)
                return CopyResult.COPY_FAILED

            # 发送最终 100% 进度
            if on_progress:
                final = TransferProgress(
                    bytes_total=file_size,
                    bytes_done=file_size,
                    ratio=1.0,
                    elapsed_sec=elapsed,
                )
                on_progress(final)

            # 检查是否被用户取消
            fn_ptr2 = _get_vtbl_method(pfo, 17)
            abort_fn = _fn_GetAnyOperationsAborted(fn_ptr2)


            aborted = BOOL(0)
            abort_fn(pfo, byref(aborted))
            if aborted.value:
                return CopyResult.CANCELLED

            logger.info("IFileOperation 传输完成: %s (%d MB, %.1fs)",
                        source, file_size // (1024 * 1024), elapsed)
            return CopyResult.OK
        finally:
            if pfo:
                _release_com(pfo)
            if psi_src:
                _release_com(psi_src)
            if psi_dst:
                _release_com(psi_dst)

    def _copy_via_shell(
        self,
        source: str,
        file_size: int,
        partition: PartitionType,
        on_progress: Optional[ProgressCallback] = None,
    ) -> CopyResult:
        """
        通过 Shell.Application CopyHere 执行 MTP 传输。

        当 IFileOperation 无法解析 MTP 目标路径时使用此回退路径。
        使用阻尼进度模拟（与 ShellCopyHereBackend 一致）。
        """
        import math as _math
        import pythoncom as _pythoncom
        import win32com.client as _win32
        import win32gui as _win32gui
        import win32con as _win32con

        _COPY_FLAGS = 1556
        _pythoncom.CoInitialize()
        try:
            shell_app = _win32.Dispatch("Shell.Application")
            my_computer = shell_app.NameSpace(17)

            # 定位目标文件夹
            dest_folder = None
            target_marker = (
                "5: SD Card install" if partition == PartitionType.SD_CARD
                else "6: NAND install"
            )
            for item in my_computer.Items():
                if "Switch" in item.Name:
                    for sub in item.GetFolder.Items():
                        if target_marker in sub.Name:
                            dest_folder = sub.GetFolder
                            break
                    break

            if dest_folder is None:
                return CopyResult.PARTITION_NOT_FOUND

            # 执行 CopyHere
            source_dir = os.path.dirname(source)
            source_name = os.path.basename(source)
            local_folder = shell_app.NameSpace(source_dir)
            local_item = local_folder.ParseName(source_name)
            if local_item is None:
                return CopyResult.IO_ERROR

            dest_folder.CopyHere(local_item, _COPY_FLAGS)

            # 阻尼进度模拟
            if on_progress is not None:
                size_mb = file_size / (1024 * 1024)
                expected_sec = max(1.5, size_mb / 28.0)
                start_time = time.time()
                visual_ratio = 0.0

                while visual_ratio < 0.96:
                    elapsed = time.time() - start_time
                    target = 1.0 - _math.exp(-2.2 * (elapsed / expected_sec))
                    if target > 0.95:
                        target = 0.95 + (1.0 - _math.exp(-0.2 * (elapsed / expected_sec))) * 0.04
                    visual_ratio += (target - visual_ratio) * 0.18
                    visual_ratio = min(0.96, visual_ratio)

                    progress = TransferProgress(
                        bytes_total=file_size,
                        bytes_done=int(file_size * visual_ratio),
                        ratio=visual_ratio,
                        elapsed_sec=elapsed,
                        eta_sec=max(0, expected_sec - elapsed),
                    )
                    on_progress(progress)
                    time.sleep(0.03)

                # 最终对齐
                on_progress(TransferProgress(
                    bytes_total=file_size, bytes_done=file_size,
                    ratio=1.0, elapsed_sec=time.time() - start_time,
                ))

            logger.info("Shell CopyHere 传输完成: %s", source)
            return CopyResult.OK
        except Exception as e:
            logger.exception("Shell CopyHere 传输异常: %s", e)
            return CopyResult.COPY_FAILED
        finally:
            _pythoncom.CoUninitialize()

    # ── 存储查询 ──────────────────────────────────────

    def get_free_space(self, partition: PartitionType) -> int:
        try:
            if not self._partitions:
                self.discover_partitions()
            pi = self._partitions.get(partition)
            return pi.free_bytes if pi else -1
        except Exception:
            return -1

    # ── 内部辅助 ──────────────────────────────────────

    def _get_dest_shell_path(self, partition: PartitionType) -> str:
        """
        获取目标分区的完整 Shell 命名空间路径。

        通过 Shell.Application 导航到 MTP 设备 -> DBI 安装分区，
        读取 FolderItem.Path 属性获取完整的 Shell 解析路径。

        MTP 路径格式类似:
          ::{20D04FE0-...}\\\\?\\usb#vid_XXXX&pid_XXXX#...#{...}\\SID-{...}

        该路径可作为 SHCreateItemFromParsingName 的输入。
        """
        import pythoncom
        import win32com.client

        pythoncom.CoInitialize()
        try:
            shell_app = win32com.client.Dispatch("Shell.Application")
            my_computer = shell_app.NameSpace(17)

            target_marker = (
                "5: SD Card install" if partition == PartitionType.SD_CARD
                else "6: NAND install"
            )

            for item in my_computer.Items():
                if "Switch" in item.Name:
                    switch_folder = item.GetFolder
                    for sub in switch_folder.Items():
                        if target_marker in sub.Name:
                            shell_path = sub.Path
                            if not shell_path:
                                raise DBIDiscoveryError(
                                    f"无法获取 {target_marker} 的 Shell 路径"
                                )
                            logger.debug("MTP 目标路径: %s", shell_path)
                            return shell_path

            raise DBIDiscoveryError(f"未找到分区: {target_marker}")
        finally:
            pythoncom.CoUninitialize()
