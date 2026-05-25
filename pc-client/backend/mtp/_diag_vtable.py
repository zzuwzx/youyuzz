import ctypes, os
from ctypes import wintypes, POINTER, c_void_p, byref, windll, cast, sizeof
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

ole32 = windll.ole32
ole32.CoInitializeEx.argtypes = [c_void_p, wintypes.DWORD]
ole32.CoInitializeEx.restype = ctypes.c_long
ole32.CoInitializeEx(None, 2)

ppv = c_void_p(0)
hr = ole32.CoCreateInstance(ctypes.byref(CLSID_FO), None, 0x17,
                            ctypes.byref(IID_IFO), ctypes.byref(ppv))
print("CoCreateInstance: hr=0x{:08X}, ppv=0x{:016X}".format(hr & 0xFFFFFFFF, ppv.value or 0))

if hr >= 0 and ppv:
    vtbl_ptr = cast(ppv, POINTER(c_void_p))[0]
    if vtbl_ptr:
        print("vtable base: 0x{:016X}".format(vtbl_ptr))
    else:
        print("vtable is NULL!")

    if vtbl_ptr:
        print()
        method_names = {
            0: "QueryInterface", 1: "AddRef", 2: "Release",
            3: "Advise", 4: "Unadvise", 5: "SetOperationFlags",
            6: "SetProgressMessage", 7: "SetProgressDialog",
            8: "SetProperties", 9: "SetOwnerWindow",
            10: "ApplyPropertiesToItems", 11: "CopyItems",
            12: "MoveItems", 13: "NewItem", 14: "DeleteItems",
            15: "RenameItems", 16: "PerformOperations",
            17: "GetAnyOperationsAborted",
        }
        for i in range(20):
            addr = cast(vtbl_ptr + i * 8, POINTER(c_void_p))[0]
            offset = addr - vtbl_ptr if addr and vtbl_ptr else 0
            name = method_names.get(i, "???")
            marker = " <-- CRASHES" if i == 16 else ""
            print("[{:2d}] 0x{:016X} +0x{:04X}  {}".format(
                i, addr or 0, offset & 0xFFFF, name + marker))

    # Try calling PerformOperations via raw fn pointer
    vtbl = cast(ppv, POINTER(c_void_p))[0]
    PerformOpsType = ctypes.CFUNCTYPE(ctypes.c_long, c_void_p)
    fn_addr = cast(vtbl + 16 * 8, POINTER(c_void_p))[0]
    print("\nPerformOperations fn ptr at vtable[16]: 0x{:016X}".format(fn_addr or 0))

    if fn_addr and fn_addr != c_void_p(-1).value:
        try:
            fn = PerformOpsType(fn_addr)
            print("CFUNCTYPE created OK")
            # Try calling with no items queued (should return S_OK or error code, not crash)
            print("Calling PerformOperations (no items)...")
            hr2 = fn(ppv)
            print("PerformOperations result: 0x{:08X}".format(hr2 & 0xFFFFFFFF))
        except Exception as e:
            print("PerformOperations FAILED: {}".format(e))
    else:
        print("WARNING: PerformOperations fn ptr is NULL or -1")

ole32.CoUninitialize()
