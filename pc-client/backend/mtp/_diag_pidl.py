# Try SHGetIDListFromObject approach - get PIDL from FolderItem
import sys; sys.path.insert(0, r"pc-client\backend")
import ctypes, pythoncom, win32com.client
from ctypes import wintypes, POINTER, c_void_p, byref, windll, cast
import uuid

pythoncom.CoInitialize()
shell_app = win32com.client.Dispatch("Shell.Application")
my_computer = shell_app.NameSpace(17)

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

# SHGetIDListFromObject
shell32.SHGetIDListFromObject.argtypes = [c_void_p, POINTER(c_void_p)]
shell32.SHGetIDListFromObject.restype = ctypes.c_long

# SHCreateItemFromIDList
shell32.SHCreateItemFromIDList.argtypes = [c_void_p, POINTER(GUID), POINTER(c_void_p)]
shell32.SHCreateItemFromIDList.restype = ctypes.c_long

for item in my_computer.Items():
    if "Switch" in item.Name:
        switch_folder = item.GetFolder
        for sub in switch_folder.Items():
            if "SD Card install" in sub.Name:
                print(f"Found: {sub.Name}")
                
                # Approach 1: SHGetIDListFromObject on FolderItem
                try:
                    # Get the raw IUnknown from FolderItem
                    unk = sub._oleobj_
                    pidl = c_void_p(0)
                    hr = shell32.SHGetIDListFromObject(unk, byref(pidl))
                    print(f"  SHGetIDListFromObject(FolderItem): hr=0x{hr&0xFFFFFFFF:08X}, pidl=0x{pidl.value:016X if pidl else 0:016X}")
                    if hr >= 0 and pidl:
                        ppv = c_void_p(0)
                        hr2 = shell32.SHCreateItemFromIDList(pidl, byref(IID_IShellItem), byref(ppv))
                        print(f"  SHCreateItemFromIDList: hr=0x{hr2&0xFFFFFFFF:08X}, ppv=0x{ppv.value:016X if ppv else 0:016X}")
                        ole32.CoTaskMemFree(pidl)
                except Exception as e:
                    print(f"  Error: {e}")
                
                # Approach 2: SHGetIDListFromObject on Folder (from GetFolder)
                try:
                    folder = sub.GetFolder
                    unk2 = folder._oleobj_
                    pidl2 = c_void_p(0)
                    hr3 = shell32.SHGetIDListFromObject(unk2, byref(pidl2))
                    print(f"  SHGetIDListFromObject(Folder): hr=0x{hr3&0xFFFFFFFF:08X}, pidl=0x{pidl2.value:016X if pidl2 else 0:016X}")
                    if hr3 >= 0 and pidl2:
                        ppv2 = c_void_p(0)
                        hr4 = shell32.SHCreateItemFromIDList(pidl2, byref(IID_IShellItem), byref(ppv2))
                        print(f"  SHCreateItemFromIDList: hr=0x{hr4&0xFFFFFFFF:08X}, ppv=0x{ppv2.value:016X if ppv2 else 0:016X}")
                        ole32.CoTaskMemFree(pidl2)
                except Exception as e:
                    print(f"  Error: {e}")
                
                break
        break

pythoncom.CoUninitialize()
