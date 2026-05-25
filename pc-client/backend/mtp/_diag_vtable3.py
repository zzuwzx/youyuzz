import ctypes, os, shutil, tempfile
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
IID_IShellItemArray = make_guid("{B63EA76D-1F85-456F-A19C-48159EFA858B}")

ole32 = windll.ole32
shell32 = windll.shell32

ole32.CoInitializeEx.argtypes = [c_void_p, wintypes.DWORD]
ole32.CoInitializeEx.restype = ctypes.c_long
ole32.CoInitializeEx(None, 2)

# Create IFileOperation
ppv = c_void_p(0)
hr = ole32.CoCreateInstance(ctypes.byref(CLSID_FO), None, 0x17,
                            ctypes.byref(IID_IFO), ctypes.byref(ppv))
print("CoCreateInstance IFileOperation: 0x{:08X}".format(hr & 0xFFFFFFFF))
vtbl = cast(ppv, POINTER(c_void_p))[0]

# SetOperationFlags (without FOFX_NOSIZELIMIT which caused E_INVALIDARG)
flags = 0x0004 | 0x0010 | 0x0200 | 0x0400  # SILENT|NOCONFIRMATION|NOCONFIRMMKDIR|NOERRORUI
SetFlagsType = ctypes.WINFUNCTYPE(ctypes.c_long, c_void_p, wintypes.DWORD)
set_flags_addr = cast(vtbl + 5*8, POINTER(c_void_p))[0]
set_flags = SetFlagsType(set_flags_addr)
hr = set_flags(ppv, flags)
print("SetOperationFlags: 0x{:08X}".format(hr & 0xFFFFFFFF))

# Create source IShellItem from a temp file
src = os.path.join(tempfile.gettempdir(), "_ifop_src.txt")
dst_dir = os.path.join(tempfile.gettempdir(), "_ifop_dst3")
os.makedirs(dst_dir, exist_ok=True)
with open(src, "w") as f:
    f.write("test via IShellItemArray")

shell32.SHCreateItemFromParsingName.argtypes = [ctypes.c_wchar_p, c_void_p, c_void_p, POINTER(c_void_p)]
shell32.SHCreateItemFromParsingName.restype = ctypes.c_long

psi_src = c_void_p(0)
psi_dst = c_void_p(0)
hr_s = shell32.SHCreateItemFromParsingName(src, None,
    ctypes.cast(ctypes.byref(IID_IShellItem), c_void_p), byref(psi_src))
hr_d = shell32.SHCreateItemFromParsingName(dst_dir, None,
    ctypes.cast(ctypes.byref(IID_IShellItem), c_void_p), byref(psi_dst))
print("SHCreateItemFromParsingName src: 0x{:08X}  dst: 0x{:08X}".format(hr_s & 0xFFFFFFFF, hr_d & 0xFFFFFFFF))

# Wrap source in IShellItemArray
shell32.SHCreateShellItemArrayFromShellItem.argtypes = [c_void_p, c_void_p, POINTER(c_void_p)]
shell32.SHCreateShellItemArrayFromShellItem.restype = ctypes.c_long

psia = c_void_p(0)
hr_sia = shell32.SHCreateShellItemArrayFromShellItem(psi_src,
    ctypes.cast(ctypes.byref(IID_IShellItemArray), c_void_p), byref(psia))
print("SHCreateShellItemArrayFromShellItem: 0x{:08X} psia=0x{:016X}".format(hr_sia & 0xFFFFFFFF, psia.value or 0))

# CopyItems with proper IShellItemArray
CopyItemsType = ctypes.WINFUNCTYPE(ctypes.c_long, c_void_p, c_void_p, c_void_p)
copy_items_addr = cast(vtbl + 11*8, POINTER(c_void_p))[0]
copy_items = CopyItemsType(copy_items_addr)
hr = copy_items(ppv, psia, psi_dst)
print("CopyItems: 0x{:08X}".format(hr & 0xFFFFFFFF))

# PerformOperations
PerformOpsType = ctypes.WINFUNCTYPE(ctypes.c_long, c_void_p)
perf_addr = cast(vtbl + 16*8, POINTER(c_void_p))[0]
perf_fn = PerformOpsType(perf_addr)
print("Calling PerformOperations...")
try:
    hr = perf_fn(ppv)
    print("PerformOperations: 0x{:08X}".format(hr & 0xFFFFFFFF))

    # Check result
    result_file = os.path.join(dst_dir, "_ifop_src.txt")
    if os.path.isfile(result_file):
        with open(result_file) as f:
            content = f.read()
        print("*** SUCCESS! File copied. Content: {} ***".format(content))
    else:
        print("File NOT found at destination")
        for f in os.listdir(dst_dir):
            print("  dst has: {}".format(f))
except OSError as e:
    print("PerformOperations CRASHED: {}".format(e))

# Cleanup
try: os.unlink(src)
except: pass
try: shutil.rmtree(dst_dir, ignore_errors=True)
except: pass

ole32.CoUninitialize()
