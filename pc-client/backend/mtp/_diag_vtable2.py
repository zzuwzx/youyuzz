import ctypes, os, time
from ctypes import wintypes, POINTER, c_void_p, byref, windll, cast
import uuid

class GUID(ctypes.Structure):
    _fields_ = [("Data1", wintypes.DWORD), ("Data2", wintypes.WORD),
                ("Data3", wintypes.WORD), ("Data4", wintypes.BYTE*8)]

def make_guid(s):
    u = uuid.UUID(s)
    return GUID(u.time_low, u.time_mid, u.time_hi_version,
                (wintypes.BYTE*8)(u.clock_seq_hi_variant, u.clock_seq_low, *u.node.to_bytes(6,"big")))

CLSID_FO = make_guid("{3AD05575-8857-4850-9277-11B85BDB8E09}")
IID_IFO = make_guid("{947AAB5F-0A5C-4C13-B4D6-4BF7836FC9F8}")
IID_IShellItem = make_guid("{43826D1E-E718-42EE-BC55-A1E261C37BFE}")

ole32 = windll.ole32
shell32 = windll.shell32
user32 = windll.user32

# Message pump helpers
MSG = wintypes.MSG

ole32.CoInitializeEx.argtypes = [c_void_p, wintypes.DWORD]
ole32.CoInitializeEx.restype = ctypes.c_long
ole32.CoInitializeEx(None, 2)  # COINIT_APARTMENTTHREADED

# Create IFileOperation
ppv = c_void_p(0)
hr = ole32.CoCreateInstance(ctypes.byref(CLSID_FO), None, 0x17,
                            ctypes.byref(IID_IFO), ctypes.byref(ppv))
print("CoCreateInstance: 0x{:08X}".format(hr & 0xFFFFFFFF))

if hr < 0:
    ole32.CoUninitialize()
    exit()

# SetOperationFlags
flags = 0x0004 | 0x0010 | 0x0200 | 0x0400 | 0x00000001  # FOFX_NOSIZELIMIT
SetFlagsType = ctypes.WINFUNCTYPE(ctypes.c_long, c_void_p, wintypes.DWORD)
vtbl = cast(ppv, POINTER(c_void_p))[0]
set_flags_addr = cast(vtbl + 5*8, POINTER(c_void_p))[0]
set_flags = SetFlagsType(set_flags_addr)
hr = set_flags(ppv, flags)
print("SetOperationFlags: 0x{:08X}".format(hr & 0xFFFFFFFF))

# CopyItems - try with local temp files
import tempfile
src = os.path.join(tempfile.gettempdir(), "_ifop_src.txt")
dst_dir = os.path.join(tempfile.gettempdir(), "_ifop_dst")
os.makedirs(dst_dir, exist_ok=True)
with open(src, "w") as f:
    f.write("test")

shell32.SHCreateItemFromParsingName.argtypes = [ctypes.c_wchar_p, c_void_p, c_void_p, POINTER(c_void_p)]
shell32.SHCreateItemFromParsingName.restype = ctypes.c_long

psi_src = c_void_p(0)
psi_dst = c_void_p(0)
hr_s = shell32.SHCreateItemFromParsingName(src, None,
    ctypes.cast(ctypes.byref(IID_IShellItem), c_void_p), byref(psi_src))
hr_d = shell32.SHCreateItemFromParsingName(dst_dir, None,
    ctypes.cast(ctypes.byref(IID_IShellItem), c_void_p), byref(psi_dst))
print("IShellItem src: 0x{:08X} dst: 0x{:08X}".format(hr_s & 0xFFFFFFFF, hr_d & 0xFFFFFFFF))

if psi_src and psi_dst:
    CopyItemsType = ctypes.WINFUNCTYPE(ctypes.c_long, c_void_p, c_void_p, c_void_p)
    copy_items_addr = cast(vtbl + 11*8, POINTER(c_void_p))[0]
    copy_items = CopyItemsType(copy_items_addr)
    hr = copy_items(ppv, psi_src, psi_dst)
    print("CopyItems: 0x{:08X}".format(hr & 0xFFFFFFFF))

# Now try PerformOperations with WINFUNCTYPE + try pumping messages
PerformOpsType = ctypes.WINFUNCTYPE(ctypes.c_long, c_void_p)
perf_addr = cast(vtbl + 16*8, POINTER(c_void_p))[0]
perf_fn = PerformOpsType(perf_addr)
print("Calling PerformOperations (WINFUNCTYPE)...")
try:
    # Use a VEH-like approach: try with SEH
    hr = perf_fn(ppv)
    print("PerformOperations: 0x{:08X}".format(hr & 0xFFFFFFFF))
except OSError as e:
    print("PerformOperations OSError: {}".format(e))
except Exception as e:
    print("PerformOperations Exception: {}".format(e))

# Cleanup temp
try:
    os.unlink(src)
    import shutil
    shutil.rmtree(dst_dir, ignore_errors=True)
except:
    pass

ole32.CoUninitialize()
