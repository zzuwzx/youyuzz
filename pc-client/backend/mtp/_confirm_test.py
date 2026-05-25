import os, sys, time
import pythoncom, win32com.client

pythoncom.CoInitialize()
shell = win32com.client.Dispatch("Shell.Application")
mc = shell.NameSpace(17)

# Find Switch and list available game folders
game_lib = r"Z:\switch\游戏"
if os.path.isdir(game_lib):
    folders = [d for d in os.listdir(game_lib) if os.path.isdir(os.path.join(game_lib, d))]
    # Find folders with .nsz files
    candidates = []
    for f in folders[:20]:
        full = os.path.join(game_lib, f)
        try:
            for root, dirs, files in os.walk(full):
                nsz = [x for x in files if x.endswith('.nsz')]
                if nsz:
                    size = os.path.getsize(os.path.join(root, nsz[0]))
                    candidates.append((f, nsz[0], size, root))
                    break
        except:
            pass
    
    if not candidates:
        print("No .nsz game files found!")
        pythoncom.CoUninitialize()
        sys.exit(1)
    
    print("Available games:")
    for i, (name, fname, size, root) in enumerate(candidates[:10]):
        print(f"  [{i}] {name} -> {fname} ({size/(1024*1024):.1f} MB)")
    
    # Pick the largest one
    candidates.sort(key=lambda x: x[2], reverse=True)
    game_name, file_name, file_size, file_dir = candidates[0]
    file_path = os.path.join(file_dir, file_name)
    size_mb = file_size / (1024*1024)
    
    print(f"\n=== Testing with: {file_name} ===")
    print(f"Path: {file_path}")
    print(f"Size: {size_mb:.1f} MB")
    
    # Navigate to Switch install folder
    for item in mc.Items():
        if "Switch" in item.Name:
            for sub in item.GetFolder.Items():
                if "SD Card install" in sub.Name:
                    dest = sub.GetFolder
                    
                    src_folder = shell.NameSpace(file_dir)
                    src_item = src_folder.ParseName(file_name)
                    
                    if src_item:
                        t0 = time.time()
                        print("\nCopyHere(20) ...")
                        dest.CopyHere(src_item, 20)
                        
                        estimated = max(10, int(size_mb / 25.0)) + 5
                        print(f"Estimated wait: {estimated}s (based on 25 MB/s)")
                        
                        for i in range(int(estimated * 10)):
                            pythoncom.PumpWaitingMessages()
                            time.sleep(0.1)
                            if i % 50 == 0:
                                elapsed = time.time() - t0
                                print(f"  ... {elapsed:.0f}s / ~{estimated}s")
                        
                        for _ in range(15):
                            pythoncom.PumpWaitingMessages()
                            time.sleep(0.1)
                        
                        elapsed = time.time() - t0
                        print(f"\nDone. Total time: {elapsed:.0f}s")
                        print(f"\n>>> PLEASE CHECK YOUR SWITCH <<<")
                        print(f"Did '{file_name}' install successfully?")
                        print(f"If DBI showed install progress, the transfer worked!")
                    else:
                        print("ParseName FAILED")
                    break
            break

pythoncom.CoUninitialize()
