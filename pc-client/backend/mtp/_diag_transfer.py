import sys; sys.path.insert(0, r"pc-client\backend")
import pythoncom, win32com.client, os

pythoncom.CoInitialize()
shell_app = win32com.client.Dispatch("Shell.Application")
my_computer = shell_app.NameSpace(17)

for item in my_computer.Items():
    if "Switch" in item.Name:
        switch_folder = item.GetFolder
        for sub in switch_folder.Items():
            name = sub.Name
            if "SD Card install" in name:
                print(f"=== {name} ===")
                print(f"  sub.GetFolder: {sub.GetFolder}")
                folder = sub.GetFolder
                # List current contents
                try:
                    items = list(folder.Items())
                    print(f"  items in folder: {len(items)}")
                    for it in items[:20]:
                        print(f"    - {it.Name} ({it.Size // 1024 if hasattr(it, 'Size') and it.Size else '?'} KB)")
                    if len(items) > 20:
                        print(f"    ... and {len(items)-20} more")
                except Exception as e:
                    print(f"  list error: {e}")
                
                # Now try to copy a test file manually
                print()
                print("=== Manual CopyHere test ===")
                test_src = r"Z:\switch\游戏\合成大西瓜\dlc-14\[010080001592700E][v0].nsz"
                if os.path.isfile(test_src):
                    src_dir = os.path.dirname(test_src)
                    src_name = os.path.basename(test_src)
                    print(f"  source: {test_src}")
                    print(f"  exists: {os.path.isfile(test_src)}")
                    print(f"  size: {os.path.getsize(test_src)} bytes")
                    
                    local_folder = shell_app.NameSpace(src_dir)
                    print(f"  local_folder: {local_folder}")
                    if local_folder:
                        local_item = local_folder.ParseName(src_name)
                        print(f"  local_item: {local_item}")
                        if local_item:
                            print("  calling CopyHere(1556)...")
                            folder.CopyHere(local_item, 1556)
                            print("  CopyHere returned")
                            # Check if file appeared
                            import time
                            time.sleep(2)
                            items2 = list(folder.Items())
                            print(f"  items after copy: {len(items2)}")
                            found = False
                            for it in items2:
                                if src_name in it.Name:
                                    print(f"    FOUND: {it.Name}")
                                    found = True
                            if not found:
                                print(f"    NOT FOUND - file did not appear!")
                                print(f"    New items:")
                                for it in items2:
                                    if it.Name not in [x.Name for x in items]:
                                        print(f"      - {it.Name}")
                else:
                    print(f"  test file not found: {test_src}")
                break
        break

pythoncom.CoUninitialize()
