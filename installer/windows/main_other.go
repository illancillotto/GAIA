//go:build !windows

package main

import (
	"fmt"
	"os"
)

func main() {
	fmt.Fprintln(os.Stderr, "CBO-Internal-Root-CA-Setup e' un programma per Windows.")
	os.Exit(ExitError)
}
