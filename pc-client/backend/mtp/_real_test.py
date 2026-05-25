import os, time
import pythoncom, win32com.client

pythoncom.CoInitialize()
shell = win32com.client.Dispatch("Shell.Application")
mc = shell.NameSpace(17)

game_dir = r"Z:\switch\游戏\以撒的结合：胎衣"
nsz_files = []
for root, dirs, files in os.walk(game_dir):
    for f in files:
        if f.endswith('.nsz'):
            nsz_files.append((os.path.join(root, f), f, os.path.getsize(os.path.join(root, f))))
    if nsz_files:
        break

if not nsz_files:
    print("No files!")
    pythoncom.CoUninitialize()
    exit()

file_path, file_name, file_size = max(nsz_files, key=lambda x: x[2])
size_mb = file_size / (1024*1024)

print(f"File: {file_name}")
print(f"Size: {size_mb:.1f} MB")
print(f"Path: {file_path}")

for item in mc.Items():
    if "Switch" in item.Name:
        for sub in item.GetFolder.Items():
            if "SD Card install" in sub.Name:
                dest = sub.GetFolder
                
                src_dir = os.path.dirname(file_path)
                src_name = os.path.basename(file_path)
                local = shell.NameSpace(src_dir)
                local_item = local.ParseName(src_name)
                
                if local_item:
                    t0 = time.time()
                    print(f"\nCopyHere(20) at {time.strftime('%H:%M:%S')}")
                    print(f"Transferring {size_mb:.1f} MB to Switch...")
                    dest.CopyHere(local_item, 20)
                    
                    estimated = max(10, int(size_mb / 25.0)) + 5
                    print(f"Estimated: {estimated}s")
                    
                    for i in range(int(estimated * 10)):
                        pythoncom.PumpWaitingMessages()
                        time.sleep(0.1)
                        if i % 30 == 0:
                            e = time.time() - t0
                            pct = min(99, int(e / estimated * 100))
                            rate = (size_mb * (pct/100)) / max(1, e)
                            print(f"  [{pct}%] {e:.0f}s elapsed, ~{rate:.1f} MB/s")
                    
                    for _ in range(15):
                        pythoncom.PumpWaitingMessages()
                        time.sleep(0.1)
                    
                    e = time.time() - t0
                    print(f"\nTotal: {e:.0f}s, avg {size_mb/e:.1f} MB/s")
                    print(f"\n>>> On your Switch DBI screen <<<")
                    print(f"Did you see install progress for '{file_name[:60]}...'?")
                    print(f"If yes -> CopyHere(20) WORKS and all our earlier tests were succeeding!")
                break
        break

pythoncom.CoUninitialize()
