# Exact replica of youyuzaizai.py's transfer pattern
import os, time, sys
import pythoncom, win32com.client

pythoncom.CoInitialize()

try:
    shell = win32com.client.Dispatch("Shell.Application")
    mc = shell.NameSpace(17)
    
    for item in mc.Items():
        if "Switch" in item.Name:
            print(f"Device: {item.Name}")
            for sub in item.GetFolder.Items():
                if "SD Card install" in sub.Name:
                    dest = sub.GetFolder
                    print(f"Target: {sub.Name}")
                    
                    # List before
                    before = [it.Name for it in dest.Items()]
                    print(f"Before ({len(before)}): {before}")
                    
                    # Use a real game file - try Z: drive first
                    game_dir = r"Z:\switch\游戏\合成大西瓜\dlc-14"
                    test_file = None
                    file_size_mb = 0
                    
                    if os.path.isdir(game_dir):
                        nsz = [f for f in os.listdir(game_dir) if f.endswith('.nsz')]
                        if nsz:
                            test_file = os.path.join(game_dir, nsz[0])
                            file_size_mb = os.path.getsize(test_file) / (1024*1024)
                    
                    if test_file is None:
                        # Fallback: use a local file
                        test_file = os.path.join(os.environ['TEMP'], '_real_mtp_test.nsz')
                        with open(test_file, 'wb') as f:
                            f.write(b'\x00' * 1024 * 100)  # 100KB dummy file
                        file_size_mb = 0.1
                        print(f"Using dummy file: {test_file} ({file_size_mb:.1f} MB)")
                    else:
                        print(f"Using game file: {nsz[0]} ({file_size_mb:.1f} MB)")
                    
                    src_dir = os.path.dirname(test_file)
                    src_name = os.path.basename(test_file)
                    local_folder = shell.NameSpace(src_dir)
                    local_item = local_folder.ParseName(src_name)
                    
                    if local_item is None:
                        print("ParseName FAILED!")
                        break
                    
                    print(f"local_item: {local_item}")
                    
                    # === THE EXACT YOUYUZAIZAI PATTERN ===
                    print(f"\nCopyHere(20)...")
                    dest.CopyHere(local_item, 20)
                    print("CopyHere returned")
                    
                    estimated_seconds = max(10, int(file_size_mb / 25.0)) + 5
                    print(f"Waiting ~{estimated_seconds}s (based on {file_size_mb:.1f}MB / 25 MB/s)...")
                    
                    for _ in range(int(estimated_seconds * 10)):
                        pythoncom.PumpWaitingMessages()
                        time.sleep(0.1)
                    for _ in range(15):
                        pythoncom.PumpWaitingMessages()
                        time.sleep(0.1)
                    
                    # Now check: is the file STILL in the folder?
                    # DBI watch folder removes files after processing them
                    after = [it.Name for it in dest.Items()]
                    print(f"\nAfter ({len(after)}): {after}")
                    
                    new_files = [f for f in after if f not in before]
                    gone_files = [f for f in before if f not in after]
                    
                    if new_files:
                        print(f"New files still present: {new_files}")
                        print("File is in folder but DBI hasn't processed yet")
                    elif gone_files:
                        print(f"Files disappeared: {gone_files}")
                        print("*** DBI processed the file! Transfer was SUCCESSFUL! ***")
                    else:
                        print("No change detected")
                    
                    # Also check if the source file is still accessible
                    if os.path.isfile(test_file):
                        print(f"Source file still exists: {os.path.getsize(test_file)} bytes")
                    
                    break
            break
    else:
        print("Switch not found!")

finally:
    pythoncom.CoUninitialize()
    print("\nDone")
