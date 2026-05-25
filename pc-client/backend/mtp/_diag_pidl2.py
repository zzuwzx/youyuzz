import sys; sys.path.insert(0, r"pc-client\backend")
import ctypes, pythoncom, win32com.client
from ctypes import wintypes, POINTER, c_void_p, byref, windll
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

# Try getting raw COM pointer from PyIDispatch
for item in my_computer.Items():
    if "Switch" in item.Name:
        for sub in item.GetFolder.Items():
            if "SD Card install" in sub.Name:
                obj = sub._oleobj_
                print(f"type: {type(obj)}")
                print(f"int: {int(obj)}")
                
                # Try QueryInterface for IUnknown
                try:
                    IID_IUnknown = "{00000000-0000-0000-C000-000000000046}"
                    unk = obj.QueryInterface(IID_IUnknown)
                    print(f"QI IUnknown: {unk} ({type(unk)})")
                except Exception as e:
                    print(f"QI IUnknown failed: {e}")
                
                # Try using the int as a pointer
                try:
                    ptr = ctypes.c_void_p(int(obj))
                    print(f"ptr from int: {ptr}")
                    
                    # Try SHGetIDListFromObject
                    shell32.SHGetIDListFromObject.argtypes = [c_void_p, POINTER(c_void_p)]
                    shell32.SHGetIDListFromObject.restype = ctypes.c_long
                    pidl = c_void_p(0)
                    hr = shell32.SHGetIDListFromObject(ptr, byref(pidl))
                    print(f"SHGetIDListFromObject: hr=0x{hr&0xFFFFFFFF:08X}, pidl=0x{pidl.value if pidl else 0:016X}")
                except Exception as e:
                    print(f"Error with int ptr: {e}")
                
                # Also try the Folder object
                folder = sub.GetFolder
                fobj = folder._oleobj_
                print(f"\nFolder type: {type(fobj)}")
                try:
                    ptr2 = ctypes.c_void_p(int(fobj))
                    pidl2 = c_void_p(0)
                    hr2 = shell32.SHGetIDListFromObject(ptr2, byref(pidl2))
                    print(f"SHGetIDListFromObject(Folder): hr=0x{hr2&0xFFFFFFFF:08X}, pidl=0x{pidl2.value if pidl2 else 0:016X}")
                    if hr2 >= 0 and pidl2:
                        ppv = c_void_p(0)
                        shell32.SHCreateItemFromIDList.argtypes = [c_void_p, POINTER(GUID), POINTER(c_void_p)]
                        shell32.SHCreateItemFromIDList.restype = ctypes.c_long
                        hr3 = shell32.SHCreateItemFromIDList(pidl2, byref(IID_IShellItem), byref(ppv))
                        print(f"SHCreateItemFromIDList: hr=0x{hr3&0xFFFFFFFF:08X}, ppv=0x{ppv.value if ppv else 0:016X}")
                        ole32.CoTaskMemFree(pidl2)
                except Exception as e:
                    print(f"Error with Folder: {e}")
                
                break
        break
pythoncom.CoUninitialize()
