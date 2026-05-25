import os, time
import pythoncom, win32com.client

pythoncom.CoInitialize()
shell = win32com.client.Dispatch("Shell.Application")
mc = shell.NameSpace(17)

game_dir = r"Z:\switch\游戏\合成大西瓜\dlc-14"
nsz_files = [f for f in os.listdir(game_dir) if f.endswith('.nsz')]
if not nsz_files:
    print("No .nsz files found!")
    pythoncom.CoUninitialize()
    exit()

# Pick largest file
largest = max(nsz_files, key=lambda f: os.path.getsize(os.path.join(game_dir, f)))
file_path = os.path.join(game_dir, largest)
size_mb = os.path.getsize(file_path) / (1024 * 1024)

print(f"File: {largest}")
print(f"Size: {size_mb:.1f} MB ({os.path.getsize(file_path)} bytes)")

for item in mc.Items():
    if "Switch" in item.Name:
        for sub in item.GetFolder.Items():
            if "SD Card install" in sub.Name:
                dest = sub.GetFolder
                
                src_folder = shell.NameSpace(game_dir)
                src_item = src_folder.ParseName(largest)
                
                if src_item:
                    t0 = time.time()
                    print(f"\nCopyHere(20) at {time.strftime('%H:%M:%S')}...")
                    dest.CopyHere(src_item, 20)
                    
                    estimated = max(10, int(size_mb / 25.0)) + 5
                    print(f"Estimated: {estimated}s")
                    
                    for i in range(int(estimated * 10)):
                        pythoncom.PumpWaitingMessages()
                        time.sleep(0.1)
                        if i % 50 == 0:
                            e = time.time() - t0
                            pct = min(100, int(e / estimated * 100))
                            print(f"  [{pct}%] {e:.0f}s / ~{estimated}s")
                    
                    for _ in range(15):
                        pythoncom.PumpWaitingMessages()
                        time.sleep(0.1)
                    
                    e = time.time() - t0
                    print(f"\nDone: {e:.0f}s")
                    print(f"\n>>> SWITCH CHECK <<<")
                    print(f"On your Switch DBI screen, did you see activity?")
                    print(f"Did '{largest[:50]}...' install?")
                break
        break

pythoncom.CoUninitialize()
