import ctypes, os, time, threading
from ctypes import wintypes
import pythoncom, win32com.client, win32gui, win32con

# Test: read progress from Windows copy dialog
def enum_progress_windows():
    """Find copy progress dialogs and read their text"""
    results = []
    def callback(hwnd, _):
        if not win32gui.IsWindow(hwnd):
            return True
        try:
            cn = win32gui.GetClassName(hwnd)
            title = win32gui.GetWindowText(hwnd)
        except:
            return True
        
        # Progress dialogs are OperationStatusWindow or #32770 with copy-related text
        if cn in ("OperationStatusWindow", "#32770"):
            if any(k in title for k in ("复制", "Copy", "正在", "Moving", "剩余")):
                # Try to find progress bar child
                prog_text = ""
                try:
                    # Get DirectUIHWND child which contains progress info
                    def find_progress(h, _):
                        try:
                            txt = win32gui.GetWindowText(h)
                            if txt and ("%" in txt or "剩余" in txt or "remaining" in txt.lower()):
                                nonlocal prog_text
                                prog_text = txt
                        except:
                            pass
                        return True
                    win32gui.EnumChildWindows(hwnd, find_progress, None)
                except:
                    pass
                
                results.append({
                    'hwnd': hwnd,
                    'title': title,
                    'class': cn,
                    'progress_text': prog_text
                })
                return False  # Stop after first match
        return True
    
    win32gui.EnumWindows(callback, None)
    return results

# Find current progress dialogs
print("Looking for active copy dialogs...")
dialogs = enum_progress_windows()
if dialogs:
    for d in dialogs:
        print(f"  HWND: {d['hwnd']}")
        print(f"  Title: {d['title']}")
        print(f"  Progress: {d['progress_text']}")
        print(f"  Visible: {win32gui.IsWindowVisible(d['hwnd'])}")
else:
    print("  No active copy dialogs found")

# Now test: start a new copy WITHOUT FOF_SILENT and monitor
print("\n=== Test: CopyHere WITHOUT SILENT ===")
pythoncom.CoInitialize()
shell = win32com.client.Dispatch("Shell.Application")
mc = shell.NameSpace(17)

for item in mc.Items():
    if "Switch" in item.Name:
        for sub in item.GetFolder.Items():
            if "SD Card install" in sub.Name:
                dest = sub.GetFolder
                
                test_file = os.path.join(os.environ['TEMP'], '_prog_test.dat')
                size_bytes = 10 * 1024 * 1024
                with open(test_file, 'wb') as f:
                    f.write(os.urandom(size_bytes))
                
                src = shell.NameSpace(os.path.dirname(test_file))
                si = src.ParseName(os.path.basename(test_file))
                
                # Use flags that show progress dialog
                # NOCONFIRMATION | NOCONFIRMMKDIR - no SILENT, no NOERRORUI
                flags = 16 | 512
                print(f"CopyHere(flags={flags})...")
                dest.CopyHere(si, flags)
                print("CopyHere returned. Monitoring dialog...")
                
                # Monitor for 30s
                for i in range(300):
                    time.sleep(0.1)
                    pythoncom.PumpWaitingMessages()
                    if i % 10 == 0:
                        dlg = enum_progress_windows()
                        if dlg:
                            d = dlg[0]
                            print(f"  [{i*0.1:.0f}s] Dialog: {d['title'][:80]} | Progress: {d['progress_text']}")
                        else:
                            print(f"  [{i*0.1:.0f}s] No dialog")
                            if i > 20:  # Dialog disappeared after being present
                                print("  -> Transfer likely complete!")
                                break
                
                os.unlink(test_file)
                break
        break

pythoncom.CoUninitialize()
