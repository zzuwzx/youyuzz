import tkinter as tk
import os, time, threading
import pythoncom, win32com.client

result = {"status": "pending", "msg": ""}

def do_copyhere():
    pythoncom.CoInitialize()
    try:
        shell = win32com.client.Dispatch("Shell.Application")
        mc = shell.NameSpace(17)
        
        for item in mc.Items():
            if "Switch" in item.Name:
                for sub in item.GetFolder.Items():
                    if "SD Card install" in sub.Name:
                        dest = sub.GetFolder
                        before = [it.Name for it in dest.Items()]
                        result["msg"] += f"Before: {before}\n"
                        
                        test_file = os.path.join(os.environ['TEMP'], '_tk_mtp_test.txt')
                        with open(test_file, 'w') as f:
                            f.write('Tkinter mainloop CopyHere test')
                        
                        local = shell.NameSpace(os.path.dirname(test_file))
                        item = local.ParseName(os.path.basename(test_file))
                        
                        if item is None:
                            result["msg"] += "ParseName failed!\n"
                            result["status"] = "failed"
                            return
                        
                        result["msg"] += "Calling CopyHere(1556)...\n"
                        dest.CopyHere(item, 1556)
                        result["msg"] += "CopyHere returned. Waiting...\n"
                        
                        # Let the Tkinter mainloop pump messages for us
                        # Schedule a check after some time
                        def check_after():
                            after = [it.Name for it in dest.Items()]
                            new = [f for f in after if f not in before]
                            result["msg"] += f"After: {after}\n"
                            if new:
                                result["msg"] += f"*** SUCCESS: {new} ***\n"
                                result["status"] = "success"
                            else:
                                result["msg"] += "FAILED\n"
                                result["status"] = "failed"
                            os.unlink(test_file)
                            root.destroy()
                        
                        root.after(10000, check_after)
                        return
        result["msg"] += "Switch not found!\n"
        result["status"] = "failed"
        root.destroy()
    finally:
        pythoncom.CoUninitialize()

root = tk.Tk()
root.title("MTP CopyHere Test")
root.geometry("400x200")

label = tk.Label(root, text="Testing MTP CopyHere via Tkinter mainloop...\n\nThis window provides a real message pump.", 
                 wraplength=380, justify="left")
label.pack(pady=20)

# Run CopyHere after a short delay to let Tkinter initialize
root.after(500, do_copyhere)
root.after(12000, lambda: root.destroy())  # Timeout

root.mainloop()
print(result["msg"])
print(f"Status: {result['status']}")
