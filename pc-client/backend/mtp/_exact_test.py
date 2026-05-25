# Direct test using youyuzaizai's exact approach but automated
import os, time
import pythoncom, win32com.client

pythoncom.CoInitialize()

try:
    shell = win32com.client.Dispatch("Shell.Application")
    mc = shell.NameSpace(17)
    
    for item in mc.Items():
        if "Switch" in item.Name:
            print(f"Device: {repr(item.Name)}")
            switch_folder = item.GetFolder
            for sub in switch_folder.Items():
                print(f"  Sub: {repr(sub.Name)} (type={type(sub.Name)})")
                if "install" in sub.Name:
                    dest = sub.GetFolder
                    print(f"  -> Target: {repr(sub.Name)}")
                    
                    # List ALL files recursively in the Switch MTP
                    print("  Listing Switch contents...")
                    for s2 in switch_folder.Items():
                        print(f"    Top: {repr(s2.Name)}")
                        try:
                            f2 = s2.GetFolder
                            for s3 in f2.Items():
                                print(f"      {repr(s3.Name)}")
                        except:
                            pass
                    
                    # Now try CopyHere with a real game file
                    game_dir = r"Z:\switch\游戏\合成大西瓜\dlc-14"
                    if os.path.isdir(game_dir):
                        nsz = [f for f in os.listdir(game_dir) if f.endswith('.nsz')]
                        if nsz:
                            file_path = os.path.join(game_dir, nsz[0])
                            size_mb = os.path.getsize(file_path) / (1024*1024)
                            print(f"\n  Game file: {nsz[0]} ({size_mb:.1f} MB)")
                            
                            src_folder = shell.NameSpace(game_dir)
                            src_item = src_folder.ParseName(nsz[0])
                            print(f"  src_item: {src_item}")
                            
                            if src_item:
                                print("  CopyHere(20)...")
                                dest.CopyHere(src_item, 20)
                                print("  CopyHere returned")
                                
                                estimated = max(10, int(size_mb / 25.0)) + 5
                                print(f"  Waiting {estimated}s...")
                                for _ in range(int(estimated * 10)):
                                    pythoncom.PumpWaitingMessages()
                                    time.sleep(0.1)
                                for _ in range(15):
                                    pythoncom.PumpWaitingMessages()
                                    time.sleep(0.1)
                                print("  Wait done")
                                
                                # Re-check
                                mc2 = shell.NameSpace(17)
                                for item2 in mc2.Items():
                                    if "Switch" in item2.Name:
                                        for sub2 in item2.GetFolder.Items():
                                            if "install" in sub2.Name:
                                                after = [it.Name for it in sub2.GetFolder.Items()]
                                                print(f"  After: {after}")
                    break
            break
    else:
        print("Switch not found")

finally:
    pythoncom.CoUninitialize()
