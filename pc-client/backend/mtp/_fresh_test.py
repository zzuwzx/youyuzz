import os, time
import pythoncom, win32com.client

pythoncom.CoInitialize()

try:
    shell = win32com.client.Dispatch("Shell.Application")
    mc = shell.NameSpace(17)
    
    for item in mc.Items():
        if "Switch" in item.Name:
            for sub in item.GetFolder.Items():
                if "SD Card install" in sub.Name:
                    print(f"Target: {sub.Name}")
                    
                    # Use a substantial test file (>1MB)
                    test_file = os.path.join(os.environ['TEMP'], '_big_mtp_test.dat')
                    size_bytes = 5 * 1024 * 1024  # 5 MB
                    with open(test_file, 'wb') as f:
                        f.write(os.urandom(size_bytes))
                    size_mb = size_bytes / (1024*1024)
                    
                    print(f"Test file: {test_file} ({size_mb:.1f} MB)")
                    
                    src_dir = os.path.dirname(test_file)
                    src_name = os.path.basename(test_file)
                    local_folder = shell.NameSpace(src_dir)
                    local_item = local_folder.ParseName(src_name)
                    
                    if local_item is None:
                        print("ParseName FAILED")
                        break
                    
                    # Record time before
                    t0 = time.time()
                    
                    # CopyHere(20) - same as working code
                    dest = sub.GetFolder
                    dest.CopyHere(local_item, 20)
                    print(f"CopyHere(20) called. t={time.time()-t0:.1f}s")
                    
                    # Wait with PumpWaitingMessages
                    estimated = max(10, int(size_mb / 25.0)) + 5
                    print(f"Waiting {estimated}s...")
                    for _ in range(int(estimated * 10)):
                        pythoncom.PumpWaitingMessages()
                        time.sleep(0.1)
                    for _ in range(15):
                        pythoncom.PumpWaitingMessages()
                        time.sleep(0.1)
                    
                    elapsed = time.time() - t0
                    print(f"Wait complete. t={elapsed:.1f}s")
                    
                    # Re-navigate to get FRESH folder reference (avoid cache)
                    mc2 = shell.NameSpace(17)
                    for item2 in mc2.Items():
                        if "Switch" in item2.Name:
                            for sub2 in item2.GetFolder.Items():
                                if "SD Card install" in sub2.Name:
                                    fresh_dest = sub2.GetFolder
                                    after = [it.Name for it in fresh_dest.Items()]
                                    print(f"\nAfter (fresh ref, {len(after)}): {after}")
                                    
                                    # Also check "1: SD Card" to see if DBI moved it
                                    for sub3 in item2.GetFolder.Items():
                                        if "SD Card" in sub3.Name and "install" not in sub3.Name:
                                            sd_items = [it.Name for it in sub3.GetFolder.Items()[:10]]
                                            print(f"SD Card root (first 10): {sd_items}")
                                    break
                            break
                    
                    os.unlink(test_file)
                    break
            break
    else:
        print("Switch not found!")

finally:
    pythoncom.CoUninitialize()
