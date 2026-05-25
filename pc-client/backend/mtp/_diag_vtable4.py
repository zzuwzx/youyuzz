import ctypes, os, shutil, tempfile, threading, time
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
user32 = windll.user32

result = {"ok": False, "msg": ""}

def sta_thread():
    ole32.CoInitializeEx.argtypes = [c_void_p, wintypes.DWORD]
    ole32.CoInitializeEx.restype = ctypes.c_long
    ole32.CoInitializeEx(None, 2)
    
    try:
        # Create IFileOperation
        ppv = c_void_p(0)
        hr = ole32.CoCreateInstance(ctypes.byref(CLSID_FO), None, 0x17,
                                    ctypes.byref(IID_IFO), ctypes.byref(ppv))
        if hr < 0:
            result["msg"] = "CoCreateInstance failed: 0x{:08X}".format(hr & 0xFFFFFFFF)
            return
        vtbl = cast(ppv, POINTER(c_void_p))[0]
        
        # SetOperationFlags
        flags = 0x0004 | 0x0010 | 0x0200 | 0x0400
        SetFlagsType = ctypes.WINFUNCTYPE(ctypes.c_long, c_void_p, wintypes.DWORD)
        set_flags = SetFlagsType(cast(vtbl + 5*8, POINTER(c_void_p))[0])
        set_flags(ppv, flags)
        
        # Create source/dest IShellItems
        src = os.path.join(tempfile.gettempdir(), "_ifop_src4.txt")
        dst_dir = os.path.join(tempfile.gettempdir(), "_ifop_dst4")
        os.makedirs(dst_dir, exist_ok=True)
        with open(src, "w") as f:
            f.write("thread test")
        
        shell32.SHCreateItemFromParsingName.argtypes = [ctypes.c_wchar_p, c_void_p, c_void_p, POINTER(c_void_p)]
        shell32.SHCreateItemFromParsingName.restype = ctypes.c_long
        
        psi_src = c_void_p(0)
        psi_dst = c_void_p(0)
        shell32.SHCreateItemFromParsingName(src, None,
            ctypes.cast(ctypes.byref(IID_IShellItem), c_void_p), byref(psi_src))
        shell32.SHCreateItemFromParsingName(dst_dir, None,
            ctypes.cast(ctypes.byref(IID_IShellItem), c_void_p), byref(psi_dst))
        
        # IShellItemArray
        shell32.SHCreateShellItemArrayFromShellItem.argtypes = [c_void_p, c_void_p, POINTER(c_void_p)]
        shell32.SHCreateShellItemArrayFromShellItem.restype = ctypes.c_long
        psia = c_void_p(0)
        shell32.SHCreateShellItemArrayFromShellItem(psi_src,
            ctypes.cast(ctypes.byref(IID_IShellItemArray), c_void_p), byref(psia))
        
        # CopyItems
        CopyItemsType = ctypes.WINFUNCTYPE(ctypes.c_long, c_void_p, c_void_p, c_void_p)
        copy_items = CopyItemsType(cast(vtbl + 11*8, POINTER(c_void_p))[0])
        copy_items(ppv, psia, psi_dst)
        
        # Pump messages for a bit before PerformOperations
        msg = wintypes.MSG()
        for _ in range(10):
            while user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 1):  # PM_REMOVE
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
            time.sleep(0.01)
        
        # PerformOperations
        PerformOpsType = ctypes.WINFUNCTYPE(ctypes.c_long, c_void_p)
        perf_fn = PerformOpsType(cast(vtbl + 16*8, POINTER(c_void_p))[0])
        
        try:
            hr = perf_fn(ppv)
            result["msg"] = "PerformOperations: 0x{:08X}".format(hr & 0xFFFFFFFF)
            
            # Check result file
            result_file = os.path.join(dst_dir, "_ifop_src4.txt")
            if os.path.isfile(result_file):
                result["ok"] = True
                result["msg"] += " - FILE COPIED!"
            else:
                result["msg"] += " - file NOT created"
                for f in os.listdir(dst_dir):
                    result["msg"] += " [dst: {}]".format(f)
        except OSError as e:
            result["msg"] = "PerformOperations CRASHED: {}".format(e)
        
        # Cleanup
        try: os.unlink(src)
        except: pass
        try: shutil.rmtree(dst_dir, ignore_errors=True)
        except: pass
        
        # Pump remaining messages
        for _ in range(20):
            while user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 1):
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
            time.sleep(0.01)
        
    finally:
        ole32.CoUninitialize()

# Run in STA thread
t = threading.Thread(target=sta_thread)
t.start()
t.join(timeout=30)
print("Thread result: {}".format(result))
if t.is_alive():
    print("Thread still alive - PerformOperations might be blocking")
