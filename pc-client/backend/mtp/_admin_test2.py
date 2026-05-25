import ctypes, os, tempfile, shutil, sys
from ctypes import wintypes, POINTER, c_void_p, byref, windll, cast
import uuid

# Redirect all output to a log file
log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_admin_result.txt")
class Tee:
    def __init__(self, *files):
        self.files = files
    def write(self, text):
        for f in self.files:
            f.write(text)
            f.flush()
    def flush(self):
        for f in self.files:
            f.flush()

log = open(log_path, "w", encoding="utf-8")
sys.stdout = Tee(sys.stdout, log)
sys.stderr = Tee(sys.stderr, log)

print("=== Admin IFileOperation Test ===")

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

ppv = c_void_p(0)
hr = ole32.CoCreateInstance(ctypes.byref(CLSID_FO), None, 0x17, ctypes.byref(IID_IFO), ctypes.byref(ppv))
print("CoCreateInstance: 0x{:08X}".format(hr & 0xFFFFFFFF))

if hr < 0:
    ole32.CoUninitialize()
    log.close()
    sys.exit(1)

vtbl = cast(ppv, POINTER(c_void_p))[0]

flags = 0x0004 | 0x0010 | 0x0200 | 0x0400
SetFlagsType = ctypes.WINFUNCTYPE(ctypes.c_long, c_void_p, wintypes.DWORD)
set_flags = SetFlagsType(cast(vtbl + 5*8, POINTER(c_void_p))[0])
hr = set_flags(ppv, flags)
print("SetOperationFlags: 0x{:08X}".format(hr & 0xFFFFFFFF))

src = os.path.join(tempfile.gettempdir(), "_admin_test_src.txt")
dst_dir = os.path.join(tempfile.gettempdir(), "_admin_test_dst")
os.makedirs(dst_dir, exist_ok=True)
with open(src, "w") as f: f.write("admin test")

shell32.SHCreateItemFromParsingName.argtypes = [ctypes.c_wchar_p, c_void_p, c_void_p, POINTER(c_void_p)]
shell32.SHCreateItemFromParsingName.restype = ctypes.c_long

psi_src = c_void_p(0); psi_dst = c_void_p(0)
shell32.SHCreateItemFromParsingName(src, None, ctypes.cast(ctypes.byref(IID_IShellItem), c_void_p), byref(psi_src))
shell32.SHCreateItemFromParsingName(dst_dir, None, ctypes.cast(ctypes.byref(IID_IShellItem), c_void_p), byref(psi_dst))

shell32.SHCreateShellItemArrayFromShellItem.argtypes = [c_void_p, c_void_p, POINTER(c_void_p)]
shell32.SHCreateShellItemArrayFromShellItem.restype = ctypes.c_long
psia = c_void_p(0)
shell32.SHCreateShellItemArrayFromShellItem(psi_src, ctypes.cast(ctypes.byref(IID_IShellItemArray), c_void_p), byref(psia))

CopyItemsType = ctypes.WINFUNCTYPE(ctypes.c_long, c_void_p, c_void_p, c_void_p)
copy_items = CopyItemsType(cast(vtbl + 11*8, POINTER(c_void_p))[0])
hr = copy_items(ppv, psia, psi_dst)
print("CopyItems: 0x{:08X}".format(hr & 0xFFFFFFFF))

print("Calling PerformOperations (as admin)...")
PerformOpsType = ctypes.WINFUNCTYPE(ctypes.c_long, c_void_p)
perf_fn = PerformOpsType(cast(vtbl + 16*8, POINTER(c_void_p))[0])
try:
    hr = perf_fn(ppv)
    print("PerformOperations: 0x{:08X}".format(hr & 0xFFFFFFFF))
    result = os.path.join(dst_dir, "_admin_test_src.txt")
    if os.path.isfile(result):
        print("*** SUCCESS! ***")
    else:
        print("File not created")
except OSError as e:
    print("CRASHED: {}".format(e))

try: os.unlink(src)
except: pass
try: shutil.rmtree(dst_dir, ignore_errors=True)
except: pass
ole32.CoUninitialize()
print("Done")
log.close()
