import sys, os, time, ctypes
import pythoncom, win32com.client

pythoncom.CoInitialize()
shell = win32com.client.Dispatch("Shell.Application")
mc = shell.NameSpace(17)

for item in mc.Items():
    if "Switch" in item.Name:
        print(f"Device: {item.Name}")
        for sub in item.GetFolder.Items():
            print(f"  Partition: {sub.Name}")
            if "SD Card install" in sub.Name:
                dest = sub.GetFolder
                print(f"  Target: {sub.Name}")
                
                before = [it.Name for it in dest.Items()]
                print(f"  Before: {before}")
                
                # Try an actual .nsz game file
                game_dir = r"Z:\switch\游戏\合成大西瓜\dlc-14"
                if os.path.isdir(game_dir):
                    nsz_files = [f for f in os.listdir(game_dir) if f.endswith('.nsz')]
                    if nsz_files:
                        test_file = os.path.join(game_dir, nsz_files[0])
                        size_mb = os.path.getsize(test_file) / (1024*1024)
                        print(f"  Source: {nsz_files[0]} ({size_mb:.1f} MB)")
                        
                        src = shell.NameSpace(game_dir)
                        item = src.ParseName(nsz_files[0])
                        
                        # Use flags that ALLOW progress UI to appear
                        # 4=SILENT | 16=NOCONFIRMATION | 256=SIMPLEPROGRESS
                        # Actually try WITHOUT silent first to see UI
                        flags = 16 | 512 | 1024  # NOCONFIRMATION | NOCONFIRMMKDIR | NOERRORUI
                        print(f"  CopyHere(flags={flags})...")
                        dest.CopyHere(item, flags)
                        print(f"  CopyHere returned. Waiting 60s...")
                        
                        # Long wait with message pump
                        for _ in range(6000):
                            pythoncom.PumpWaitingMessages()
                            time.sleep(0.01)
                        
                        after = [it.Name for it in dest.Items()]
                        print(f"  After: {after}")
                        new = [f for f in after if f not in before]
                        if new:
                            print(f"  *** SUCCESS: {new} ***")
                        else:
                            print(f"  FAILED - no new files after 60s")
                    else:
                        print("  No .nsz files found")
                else:
                    print(f"  Game dir not found: {game_dir}")
                break
        break
else:
    print("Switch not found!")

pythoncom.CoUninitialize()
