package main

import (
	"fmt"
	"os"
	"syscall"
	"unsafe"
)

var (
	modole32  = syscall.NewLazyDLL("ole32.dll")
	modshell32 = syscall.NewLazyDLL("shell32.dll")

	procCoInitializeEx            = modole32.NewProc("CoInitializeEx")
	procCoCreateInstance          = modole32.NewProc("CoCreateInstance")
	procCoUninitialize            = modole32.NewProc("CoUninitialize")
	procSHCreateItemFromParsingName = modshell32.NewProc("SHCreateItemFromParsingName")
)

type GUID struct {
	Data1 uint32
	Data2 uint16
	Data3 uint16
	Data4 [8]byte
}

func makeGUID(s string) GUID {
	// Simplified - just use hardcoded known GUIDs
	var g GUID
	fmt.Sscanf(s, "{%08X-%04X-%04X-%02X%02X-%02X%02X%02X%02X%02X%02X}",
		&g.Data1, &g.Data2, &g.Data3,
		&g.Data4[0], &g.Data4[1], &g.Data4[2], &g.Data4[3],
		&g.Data4[4], &g.Data4[5], &g.Data4[6], &g.Data4[7])
	return g
}

var (
	CLSID_FileOperation = makeGUID("{3AD05575-8857-4850-9277-11B85BDB8E09}")
	IID_IFileOperation  = makeGUID("{947AAB5F-0A5C-4C13-B4D6-4BF7836FC9F8}")
	IID_IShellItem      = makeGUID("{43826D1E-E718-42EE-BC55-A1E261C37BFE}")
)

func main() {
	fmt.Println("=== Go IFileOperation Test ===")

	// CoInitializeEx(NULL, COINIT_APARTMENTTHREADED)
	ret, _, _ := procCoInitializeEx.Call(0, 2)
	fmt.Printf("CoInitializeEx: 0x%08X\n", ret)

	var ppv uintptr
	ret, _, _ = procCoCreateInstance.Call(
		uintptr(unsafe.Pointer(&CLSID_FileOperation)),
		0, 0x17,
		uintptr(unsafe.Pointer(&IID_IFileOperation)),
		uintptr(unsafe.Pointer(&ppv)),
	)
	fmt.Printf("CoCreateInstance: 0x%08X, ppv=0x%016X\n", ret, ppv)

	if ret != 0 || ppv == 0 {
		fmt.Println("Failed to create IFileOperation")
		procCoUninitialize.Call()
		os.Exit(1)
	}

	// Read vtable
	vtbl := *(*uintptr)(unsafe.Pointer(ppv))
	fmt.Printf("vtable base: 0x%016X\n", vtbl)

	// vtable[5] = SetOperationFlags
	setFlags := *(*uintptr)(unsafe.Pointer(vtbl + 5*8))
	fmt.Printf("SetOperationFlags fn: 0x%016X\n", setFlags)

	flags := uintptr(0x0004 | 0x0010 | 0x0200 | 0x0400)
	ret, _, _ = syscall.SyscallN(setFlags, ppv, flags)
	fmt.Printf("SetOperationFlags: 0x%08X\n", ret)

	// Create a temp file for testing
	tmpDir := os.TempDir()
	srcPath := tmpDir + "\\_go_ifop_src.txt"
	dstPath := tmpDir + "\\_go_ifop_dst"
	os.WriteFile(srcPath, []byte("Go IFileOperation test"), 0644)
	os.MkdirAll(dstPath, 0755)

	// SHCreateItemFromParsingName for source
	var psiSrc uintptr
	srcPathW, _ := syscall.UTF16PtrFromString(srcPath)
	ret, _, _ = procSHCreateItemFromParsingName.Call(
		uintptr(unsafe.Pointer(srcPathW)),
		0,
		uintptr(unsafe.Pointer(&IID_IShellItem)),
		uintptr(unsafe.Pointer(&psiSrc)),
	)
	fmt.Printf("IShellItem src: 0x%08X, psi=0x%016X\n", ret, psiSrc)

	// SHCreateItemFromParsingName for dest
	var psiDst uintptr
	dstPathW, _ := syscall.UTF16PtrFromString(dstPath)
	ret, _, _ = procSHCreateItemFromParsingName.Call(
		uintptr(unsafe.Pointer(dstPathW)),
		0,
		uintptr(unsafe.Pointer(&IID_IShellItem)),
		uintptr(unsafe.Pointer(&psiDst)),
	)
	fmt.Printf("IShellItem dst: 0x%08X, psi=0x%016X\n", ret, psiDst)

	// For simplicity, try passing psiSrc directly to CopyItems
	// vtable[11] = CopyItems
	copyItems := *(*uintptr)(unsafe.Pointer(vtbl + 11*8))
	fmt.Printf("CopyItems fn: 0x%016X\n", copyItems)
	ret, _, _ = syscall.SyscallN(copyItems, ppv, psiSrc, psiDst)
	fmt.Printf("CopyItems: 0x%08X\n", ret)

	// vtable[16] = PerformOperations
	perfOps := *(*uintptr)(unsafe.Pointer(vtbl + 16*8))
	fmt.Printf("PerformOperations fn: 0x%016X\n", perfOps)
	fmt.Println("Calling PerformOperations...")
	
	// Use recover to catch access violation
	func() {
		defer func() {
			if r := recover(); r != nil {
				fmt.Printf("CRASHED: %v\n", r)
			}
		}()
		ret, _, _ = syscall.SyscallN(perfOps, ppv)
		fmt.Printf("PerformOperations: 0x%08X\n", ret)
	}()

	// Check result
	resultFile := dstPath + "\\_go_ifop_src.txt"
	if _, err := os.Stat(resultFile); err == nil {
		data, _ := os.ReadFile(resultFile)
		fmt.Printf("*** SUCCESS! Content: %s ***\n", string(data))
	} else {
		fmt.Println("File NOT created")
	}

	os.Remove(srcPath)
	os.RemoveAll(dstPath)
	procCoUninitialize.Call()
	fmt.Println("Done")
}
