//go:build windows

package main

import (
	"bytes"
	_ "embed"
	"errors"
	"os"
	"strings"
	"syscall"
	"time"
	"unsafe"
)

//go:embed ca.crt
var embeddedCertificate []byte

const (
	certStoreProvSystem     = 10
	certSystemStoreLocalMac = 0x00020000
	x509ASNEncoding         = 1
	certStoreAddUseExisting = 2
	mbOK                    = 0x00000000
	mbYesNo                 = 0x00000004
	mbIconError             = 0x00000010
	mbIconQuestion          = 0x00000020
	mbIconInformation       = 0x00000040
	idYes                   = 6
)

var (
	user32           = syscall.NewLazyDLL("user32.dll")
	shell32          = syscall.NewLazyDLL("shell32.dll")
	crypt32          = syscall.NewLazyDLL("crypt32.dll")
	messageBoxW      = user32.NewProc("MessageBoxW")
	isUserAnAdmin    = shell32.NewProc("IsUserAnAdmin")
	shellExecuteW    = shell32.NewProc("ShellExecuteW")
	certDeleteCertFn = crypt32.NewProc("CertDeleteCertificateFromStore")
	certDuplicateFn  = crypt32.NewProc("CertDuplicateCertificateContext")
)

type windowsSystem struct{ silent bool }

func (windowsSystem) IsAdmin() bool {
	result, _, _ := isUserAnAdmin.Call()
	return result != 0
}

func (windowsSystem) Relaunch(args []string) error {
	executable, err := os.Executable()
	if err != nil {
		return err
	}
	verb, _ := syscall.UTF16PtrFromString("runas")
	file, _ := syscall.UTF16PtrFromString(executable)
	parameters, _ := syscall.UTF16PtrFromString(strings.Join(args, " "))
	result, _, _ := shellExecuteW.Call(0, uintptr(unsafe.Pointer(verb)), uintptr(unsafe.Pointer(file)),
		uintptr(unsafe.Pointer(parameters)), 0, 1)
	if result <= 32 {
		return errors.New("elevazione rifiutata")
	}
	return nil
}

func message(text string, flags uintptr) uintptr {
	body, _ := syscall.UTF16PtrFromString(text)
	caption, _ := syscall.UTF16PtrFromString(title)
	result, _, _ := messageBoxW.Call(0, uintptr(unsafe.Pointer(body)), uintptr(unsafe.Pointer(caption)), flags)
	return result
}

func (windowsSystem) Ask(text string) bool {
	return message(text, mbYesNo|mbIconQuestion) == idYes
}

func (s windowsSystem) Tell(text string, failure bool) {
	if s.silent {
		return
	}
	if failure {
		message(text, mbOK|mbIconError)
		return
	}
	message(text, mbOK|mbIconInformation)
}

func openRoot() (syscall.Handle, error) {
	name, _ := syscall.UTF16PtrFromString("ROOT")
	return syscall.CertOpenStore(certStoreProvSystem, 0, 0, certSystemStoreLocalMac, uintptr(unsafe.Pointer(name)))
}

func sameCertificate(context *syscall.CertContext, der []byte) bool {
	found := unsafe.Slice(context.EncodedCert, context.Length)
	return bytes.Equal(found, der)
}

func (windowsSystem) StoreHas(der []byte) (bool, error) {
	store, err := openRoot()
	if err != nil {
		return false, err
	}
	defer syscall.CertCloseStore(store, 0)
	var context *syscall.CertContext
	for {
		context, err = syscall.CertEnumCertificatesInStore(store, context)
		if context == nil {
			return false, nil
		}
		if sameCertificate(context, der) {
			syscall.CertFreeCertificateContext(context)
			return true, nil
		}
	}
}

func (windowsSystem) StoreAdd(der []byte) error {
	store, err := openRoot()
	if err != nil {
		return err
	}
	defer syscall.CertCloseStore(store, 0)
	context, err := syscall.CertCreateCertificateContext(x509ASNEncoding, &der[0], uint32(len(der)))
	if err != nil {
		return err
	}
	defer syscall.CertFreeCertificateContext(context)
	return syscall.CertAddCertificateContextToStore(store, context, certStoreAddUseExisting, nil)
}

func (windowsSystem) StoreRemove(der []byte) (int, error) {
	store, err := openRoot()
	if err != nil {
		return 0, err
	}
	defer syscall.CertCloseStore(store, 0)
	removed := 0
	var context *syscall.CertContext
	for {
		context, _ = syscall.CertEnumCertificatesInStore(store, context)
		if context == nil {
			return removed, nil
		}
		if sameCertificate(context, der) {
			duplicate, _, _ := certDuplicateFn.Call(uintptr(unsafe.Pointer(context)))
			result, _, callError := certDeleteCertFn.Call(duplicate)
			if result == 0 {
				return removed, callError
			}
			removed++
		}
	}
}

func main() {
	silent := false
	for _, argument := range os.Args[1:] {
		if strings.EqualFold(argument, "/S") {
			silent = true
		}
	}
	os.Exit(Run(os.Args[1:], embeddedCertificate, windowsSystem{silent: silent}, time.Now()))
}
