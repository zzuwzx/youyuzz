import ctypes, os, time
from ctypes import wintypes, POINTER, c_void_p, byref, windll, cast
import pythoncom, win32com.client

# SHFILEOPSTRUCT for SHFileOperation
class SHFILEOPSTRUCTW(ctypes.Structure):
    _fields_ = [
        ("hwnd", wintypes.HWND),
        ("wFunc", wintypes.UINT),
        ("pFrom", ctypes.c_wchar_p),
        ("pTo", ctypes.c_wchar_p),
        ("fFlags", wintypes.WORD),
        ("fAnyOperationsAborted", wintypes.BOOL),
        ("hNameMappings", c_void_p),
        ("lpszProgressTitle", ctypes.c_wchar_p),
    ]

FO_COPY = 0x0002
FOF_SILENT = 0x0004
FOF_NOCONFIRMATION = 0x0010
FOF_NOCONFIRMMKDIR = 0x0200
FOF_NOERRORUI = 0x0400
FOF_WANTNUKEWARNING = 0x4000  # Win2k+ only, for safety

shell32 = windll.shell32
shell32.SHFileOperationW.argtypes = [POINTER(SHFILEOPSTRUCTW)]
shell32.SHFileOperationW.restype = ctypes.c_int

# First, test SHFileOperation with LOCAL files to verify it works
print("=== Test 1: SHFileOperation local ===")
test_src = os.path.join(os.environ['TEMP'], "_shfo_src.txt")
test_dst_dir = os.path.join(os.environ['TEMP'], "_shfo_dst")
os.makedirs(test_dst_dir, exist_ok=True)
with open(test_src, "w") as f:
    f.write("SHFileOperation test")

# SHFileOperation needs double-null-terminated strings
from_buf = test_src + "\0\0"
to_buf = test_dst_dir + "\0\0"

fop = SHFILEOPSTRUCTW()
fop.wFunc = FO_COPY
fop.pFrom = from_buf
fop.pTo = to_buf
fop.fFlags = FOF_SILENT | FOF_NOCONFIRMATION | FOF_NOCONFIRMMKDIR | FOF_NOERRORUI

result = shell32.SHFileOperationW(byref(fop))
print(f"SHFileOperation local: result={result}")
result_file = os.path.join(test_dst_dir, "_shfo_src.txt")
if os.path.isfile(result_file):
    print(f"  *** LOCAL COPY SUCCESS! ***")
else:
    print(f"  Failed")

os.unlink(test_src)
import shutil
shutil.rmtree(test_dst_dir, ignore_errors=True)

# Test 2: SHFileOperation with MTP destination
print("\n=== Test 2: SHFileOperation to MTP ===")
pythoncom.CoInitialize()
try:
    shell = win32com.client.Dispatch("Shell.Application")
    mc = shell.NameSpace(17)
    
    dest_path = None
    for item in mc.Items():
        if "Switch" in item.Name:
            for sub in item.GetFolder.Items():
                if "SD Card install" in sub.Name:
                    dest_path = sub.Path
                    print(f"MTP dest path: {dest_path}")
                    break
            break
    
    if dest_path is None:
        print("MTP destination not found!")
    else:
        test_src2 = os.path.join(os.environ['TEMP'], "_shfo_mtp_test.txt")
        with open(test_src2, "w") as f:
            f.write("MTP SHFileOperation test")
        
        print(f"Source: {test_src2}")
        print(f"Dest: {dest_path}")
        
        from_buf2 = test_src2 + "\0\0"
        to_buf2 = dest_path + "\0\0"
        
        fop2 = SHFILEOPSTRUCTW()
        fop2.wFunc = FO_COPY
        fop2.pFrom = from_buf2
        fop2.pTo = to_buf2
        fop2.fFlags = FOF_SILENT | FOF_NOCONFIRMATION | FOF_NOCONFIRMMKDIR | FOF_NOERRORUI
        
        print("Calling SHFileOperationW...")
        result2 = shell32.SHFileOperationW(byref(fop2))
        print(f"SHFileOperation MTP: result={result2}")
        print(f"AnyOperationsAborted: {fop2.fAnyOperationsAborted}")
        
        # Check if file appeared
        time.sleep(2)
        dest_folder = None
        for item in mc.Items():
            if "Switch" in item.Name:
                for sub in item.GetFolder.Items():
                    if "SD Card install" in sub.Name:
                        dest_folder = sub.GetFolder
                        break
                break
        
        if dest_folder:
            after = [it.Name for it in dest_folder.Items()]
            found = [f for f in after if "_shfo_mtp_test" in f]
            if found:
                print(f"*** MTP COPY SUCCESS! Found: {found} ***")
            else:
                print(f"MTP copy failed. Contents: {after[:5]}")
        
        os.unlink(test_src2)
finally:
    pythoncom.CoUninitialize()
