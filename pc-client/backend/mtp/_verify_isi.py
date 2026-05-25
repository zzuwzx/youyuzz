import ctypes, os, tempfile
from ctypes import wintypes, POINTER, c_void_p, byref, windll, cast
import uuid

class GUID(ctypes.Structure):
    _fields_ = [("Data1", wintypes.DWORD), ("Data2", wintypes.WORD),
                ("Data3", wintypes.WORD), ("Data4", wintypes.BYTE*8)]
def make_guid(s):
    u = uuid.UUID(s)
    return GUID(u.time_low, u.time_mid, u.time_hi_version,
                (wintypes.BYTE*8)(u.clock_seq_hi_variant, u.clock_seq_low, *u.node.to_bytes(6,"big")))

IID_IShellItem = make_guid("{43826D1E-E718-42EE-BC55-A1E261C37BFE}")

shell32 = windll.shell32
ole32 = windll.ole32

ole32.CoInitializeEx.argtypes = [c_void_p, wintypes.DWORD]
ole32.CoInitializeEx.restype = ctypes.c_long
ole32.CoInitializeEx(None, 2)

# Create test file
src = os.path.join(tempfile.gettempdir(), "_verify_isi_src.txt")
dst_dir = os.path.join(tempfile.gettempdir(), "_verify_isi_dst")
os.makedirs(dst_dir, exist_ok=True)
with open(src, "w") as f:
    f.write("IShellItem verification test")

# Create IShellItems
shell32.SHCreateItemFromParsingName.argtypes = [ctypes.c_wchar_p, c_void_p, c_void_p, POINTER(c_void_p)]
shell32.SHCreateItemFromParsingName.restype = ctypes.c_long

psi_src = c_void_p(0)
psi_dst = c_void_p(0)
shell32.SHCreateItemFromParsingName(src, None, ctypes.cast(ctypes.byref(IID_IShellItem), c_void_p), byref(psi_src))
shell32.SHCreateItemFromParsingName(dst_dir, None, ctypes.cast(ctypes.byref(IID_IShellItem), c_void_p), byref(psi_dst))

print(f"psi_src: 0x{psi_src.value:016X}")
print(f"psi_dst: 0x{psi_dst.value:016X}")

# Verify IShellItem by calling GetDisplayName (vtable[5])
# HRESULT GetDisplayName(SIGDN sigdnName, PWSTR *ppszName)
if psi_src:
    vtbl_src = cast(psi_src, POINTER(c_void_p))[0]
    GetDisplayNameType = ctypes.WINFUNCTYPE(ctypes.c_long, c_void_p, wintypes.DWORD, POINTER(ctypes.c_wchar_p))
    get_dn = GetDisplayNameType(cast(vtbl_src + 5*8, POINTER(c_void_p))[0])
    
    # SIGDN_NORMALDISPLAY = 0
    # SIGDN_FILESYSPATH = 2
    pname = ctypes.c_wchar_p()
    hr = get_dn(psi_src, 0, byref(pname))
    print(f"GetDisplayName(NORMAL) src: 0x{hr&0xFFFFFFFF:08X} -> {pname.value if pname else 'NULL'}")
    
    pname = ctypes.c_wchar_p()
    hr = get_dn(psi_src, 2, byref(pname))
    print(f"GetDisplayName(FILESYSPATH) src: 0x{hr&0xFFFFFFFF:08X} -> {pname.value if pname else 'NULL'}")

if psi_dst:
    vtbl_dst = cast(psi_dst, POINTER(c_void_p))[0]
    GetDisplayNameType = ctypes.WINFUNCTYPE(ctypes.c_long, c_void_p, wintypes.DWORD, POINTER(ctypes.c_wchar_p))
    get_dn = GetDisplayNameType(cast(vtbl_dst + 5*8, POINTER(c_void_p))[0])
    
    pname = ctypes.c_wchar_p()
    hr = get_dn(psi_dst, 0, byref(pname))
    print(f"GetDisplayName(NORMAL) dst: 0x{hr&0xFFFFFFFF:08X} -> {pname.value if pname else 'NULL'}")
    
    pname = ctypes.c_wchar_p()
    hr = get_dn(psi_dst, 2, byref(pname))
    print(f"GetDisplayName(FILESYSPATH) dst: 0x{hr&0xFFFFFFFF:08X} -> {pname.value if pname else 'NULL'}")

# Now try IFileOperation with these IShellItems but using IFileOperationVtbl structure (not raw casts)
print("\n=== IFileOperation via IFileOperationVtbl structure ===")

CLSID_FO = make_guid("{3AD05575-8857-4850-9277-11B85BDB8E09}")
IID_IFO = make_guid("{947AAB5F-0A5C-4C13-B4D6-4BF7836FC9F8}")
IID_ISIA = make_guid("{B63EA76D-1F85-456F-A19C-48159EFA858B}")

ppv = c_void_p(0)
hr = ole32.CoCreateInstance(ctypes.byref(CLSID_FO), None, 0x17, ctypes.byref(IID_IFO), ctypes.byref(ppv))
print(f"CoCreateInstance IFileOperation: 0x{hr&0xFFFFFFFF:08X}")

if hr >= 0:
    # Use structure-based vtable access (not raw cast)
    # Define the full vtable structure
    _fn_QI = ctypes.WINFUNCTYPE(ctypes.c_long, c_void_p, c_void_p, POINTER(c_void_p))
    _fn_AddRef = ctypes.WINFUNCTYPE(wintypes.ULONG, c_void_p)
    _fn_Release = ctypes.WINFUNCTYPE(wintypes.ULONG, c_void_p)
    _fn_Advise = ctypes.WINFUNCTYPE(ctypes.c_long, c_void_p, c_void_p, POINTER(wintypes.DWORD))
    _fn_Unadvise = ctypes.WINFUNCTYPE(ctypes.c_long, c_void_p, wintypes.DWORD)
    _fn_SetOpFlags = ctypes.WINFUNCTYPE(ctypes.c_long, c_void_p, wintypes.DWORD)
    _fn_SetProgMsg = ctypes.WINFUNCTYPE(ctypes.c_long, c_void_p, ctypes.c_wchar_p)
    _fn_SetProgDlg = ctypes.WINFUNCTYPE(ctypes.c_long, c_void_p, c_void_p)
    _fn_SetProps = ctypes.WINFUNCTYPE(ctypes.c_long, c_void_p, c_void_p)
    _fn_SetOwnerWnd = ctypes.WINFUNCTYPE(ctypes.c_long, c_void_p, wintypes.HWND)
    _fn_ApplyProps = ctypes.WINFUNCTYPE(ctypes.c_long, c_void_p, c_void_p)
    _fn_CopyItems = ctypes.WINFUNCTYPE(ctypes.c_long, c_void_p, c_void_p, c_void_p)
    _fn_MoveItems = ctypes.WINFUNCTYPE(ctypes.c_long, c_void_p, c_void_p, c_void_p)
    _fn_NewItem = ctypes.WINFUNCTYPE(ctypes.c_long, c_void_p, c_void_p, wintypes.DWORD, ctypes.c_wchar_p, ctypes.c_wchar_p, c_void_p)
    _fn_DeleteItems = ctypes.WINFUNCTYPE(ctypes.c_long, c_void_p, c_void_p)
    _fn_RenameItems = ctypes.WINFUNCTYPE(ctypes.c_long, c_void_p, c_void_p, ctypes.c_wchar_p)
    _fn_PerformOps = ctypes.WINFUNCTYPE(ctypes.c_long, c_void_p)
    _fn_GetAborted = ctypes.WINFUNCTYPE(ctypes.c_long, c_void_p, POINTER(wintypes.BOOL))
    
    class IFOVtbl(ctypes.Structure):
        _fields_ = [
            ("QueryInterface", _fn_QI), ("AddRef", _fn_AddRef), ("Release", _fn_Release),
            ("Advise", _fn_Advise), ("Unadvise", _fn_Unadvise),
            ("SetOperationFlags", _fn_SetOpFlags),
            ("SetProgressMessage", _fn_SetProgMsg),
            ("SetProgressDialog", _fn_SetProgDlg),
            ("SetProperties", _fn_SetProps),
            ("SetOwnerWindow", _fn_SetOwnerWnd),
            ("ApplyPropertiesToItems", _fn_ApplyProps),
            ("CopyItems", _fn_CopyItems), ("MoveItems", _fn_MoveItems),
            ("NewItem", _fn_NewItem), ("DeleteItems", _fn_DeleteItems),
            ("RenameItems", _fn_RenameItems),
            ("PerformOperations", _fn_PerformOps),
            ("GetAnyOperationsAborted", _fn_GetAborted),
        ]
    
    vtbl_ptr = cast(ppv, POINTER(c_void_p))[0]
    vtbl = cast(vtbl_ptr, POINTER(IFOVtbl)).contents
    
    flags = 0x0004 | 0x0010 | 0x0200 | 0x0400
    hr = vtbl.SetOperationFlags(ppv, flags)
    print(f"SetOperationFlags: 0x{hr&0xFFFFFFFF:08X}")
    
    # Create IShellItemArray
    shell32.SHCreateShellItemArrayFromShellItem.argtypes = [c_void_p, c_void_p, POINTER(c_void_p)]
    shell32.SHCreateShellItemArrayFromShellItem.restype = ctypes.c_long
    psia = c_void_p(0)
    shell32.SHCreateShellItemArrayFromShellItem(psi_src, ctypes.cast(ctypes.byref(IID_ISIA), c_void_p), byref(psia))
    
    hr = vtbl.CopyItems(ppv, psia, psi_dst)
    print(f"CopyItems: 0x{hr&0xFFFFFFFF:08X}")
    
    print("Calling PerformOperations via IFOVtbl...")
    try:
        hr = vtbl.PerformOperations(ppv)
        print(f"PerformOperations: 0x{hr&0xFFFFFFFF:08X}")
        result = os.path.join(dst_dir, "_verify_isi_src.txt")
        if os.path.isfile(result):
            print("*** SUCCESS! ***")
        else:
            print("File not created")
    except OSError as e:
        print(f"CRASHED: {e}")

os.unlink(src)
import shutil
shutil.rmtree(dst_dir, ignore_errors=True)
ole32.CoUninitialize()
