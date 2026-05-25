import sys, os, time
import pythoncom, win32com.client

print("=== Starting GUI Message Pump Test ===", flush=True)

pythoncom.CoInitialize()
print("CoInitialize OK", flush=True)

try:
    shell = win32com.client.Dispatch("Shell.Application")
    print("Shell.Application OK", flush=True)
    
    mc = shell.NameSpace(17)
    print("NameSpace(17) OK", flush=True)
    
    found = False
    for item in mc.Items():
        print(f"  Device: {item.Name}", flush=True)
        if "Switch" in item.Name:
            found = True
            print(f"  -> Found Switch!", flush=True)
            switch_folder = item.GetFolder
            print(f"  -> Got Switch folder", flush=True)
            for sub in switch_folder.Items():
                print(f"    Partition: {sub.Name}", flush=True)
                if "SD Card install" in sub.Name:
                    dest = sub.GetFolder
                    print(f"    -> Target: {sub.Name}", flush=True)
                    
                    before = [it.Name for it in dest.Items()]
                    print(f"    Before: {before}", flush=True)
                    
                    test_file = os.path.join(os.environ['TEMP'], '_gui_test2.txt')
                    with open(test_file, 'w') as f:
                        f.write('test2')
                    
                    src = shell.NameSpace(os.path.dirname(test_file))
                    item = src.ParseName(os.path.basename(test_file))
                    print(f"    Source item: {item}", flush=True)
                    
                    print(f"    CopyHere(1556)...", flush=True)
                    dest.CopyHere(item, 1556)
                    print(f"    CopyHere returned", flush=True)
                    
                    print(f"    Pumping messages for 10s...", flush=True)
                    for _ in range(1000):
                        pythoncom.PumpWaitingMessages()
                        time.sleep(0.01)
                    
                    after = [it.Name for it in dest.Items()]
                    print(f"    After: {after}", flush=True)
                    new = [f for f in after if f not in before]
                    if new:
                        print(f"    *** SUCCESS: {new} ***", flush=True)
                    else:
                        print(f"    FAILED", flush=True)
                    
                    os.unlink(test_file)
                    break
            break
    
    if not found:
        print("Switch not found", flush=True)
        
except Exception as e:
    print(f"ERROR: {e}", flush=True)
    import traceback
    traceback.print_exc()
finally:
    pythoncom.CoUninitialize()
    print("Done", flush=True)
