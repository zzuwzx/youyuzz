import sys, os, time, threading
import pythoncom, win32com.client, win32gui, win32con

pythoncom.CoInitialize()
shell = win32com.client.Dispatch("Shell.Application")
mc = shell.NameSpace(17)

dest_folder = None
for item in mc.Items():
    if "Switch" in item.Name:
        print(f"Found: {item.Name}")
        for sub in item.GetFolder.Items():
            if "SD Card install" in sub.Name:
                dest_folder = sub.GetFolder
                print(f"Target: {sub.Name}")
                break
        break

if dest_folder is None:
    print("Switch/DBI not found!")
    pythoncom.CoUninitialize()
    sys.exit(1)

# Create test file
test_file = os.path.join(os.environ['TEMP'], '_gui_mtp_test.txt')
with open(test_file, 'w') as f:
    f.write('GUI message pump test')

src_dir = os.path.dirname(test_file)
src_name = os.path.basename(test_file)
local_folder = shell.NameSpace(src_dir)
local_item = local_folder.ParseName(src_name)

if local_item is None:
    print("Could not parse source file")
    pythoncom.CoUninitialize()
    sys.exit(1)

before = [it.Name for it in dest_folder.Items()]
print(f"Before: {before}")

print("Calling CopyHere(1556)...")
dest_folder.CopyHere(local_item, 1556)
print("CopyHere returned. Starting message pump...")

# Run a message pump for up to 60 seconds
# This is what Tkinter mainloop does internally
start = time.time()
while time.time() - start < 30:
    pythoncom.PumpWaitingMessages()
    # Also pump Windows messages via PeekMessage
    msg = None
    try:
        import ctypes
        user32 = ctypes.windll.user32
        msg = (ctypes.c_ulong * 7)()
        while user32.PeekMessageW(msg, None, 0, 0, 1):  # PM_REMOVE
            user32.TranslateMessage(msg)
            user32.DispatchMessageW(msg)
    except:
        pass
    time.sleep(0.01)

after = [it.Name for it in dest_folder.Items()]
print(f"After ({len(after)}): {after}")
new_files = [f for f in after if f not in before]
if new_files:
    print(f"*** SUCCESS! New files: {new_files} ***")
else:
    print("FAILED - no new files")

os.unlink(test_file)
pythoncom.CoUninitialize()
