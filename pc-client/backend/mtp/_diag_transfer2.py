import sys; sys.path.insert(0, r"pc-client\backend")
import pythoncom, win32com.client, os, time

pythoncom.CoInitialize()
shell_app = win32com.client.Dispatch("Shell.Application")
my_computer = shell_app.NameSpace(17)

for item in my_computer.Items():
    if "Switch" in item.Name:
        switch_folder = item.GetFolder
        for sub in switch_folder.Items():
            name = sub.Name
            if "SD Card install" in name:
                folder = sub.GetFolder
                
                # Test 1: simple file from C:\temp
                test_file = r"C:\temp\_test_mtp.nsp"
                print(f"Test 1: copying {test_file}")
                src_dir = os.path.dirname(test_file)
                src_name = os.path.basename(test_file)
                local_folder = shell_app.NameSpace(src_dir)
                local_item = local_folder.ParseName(src_name)
                print(f"  NameSpace: {local_folder}, ParseName: {local_item}")
                
                # Try with just FOF_NOCONFIRMMKDIR (512), no silent
                if local_item:
                    folder.CopyHere(local_item, 512)
                    print("  CopyHere(512) returned")
                
                time.sleep(3)
                items = list(folder.Items())
                print(f"  Items after copy: {len(items)}")
                found = [it.Name for it in items if "_test_mtp" in it.Name]
                if found:
                    print(f"  FOUND: {found}")
                else:
                    print(f"  NOT FOUND!")
                    # List all items
                    for it in items:
                        print(f"    - {it.Name}")
                break
        break

pythoncom.CoUninitialize()
