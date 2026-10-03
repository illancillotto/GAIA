package main

import (
	"bytes"
	"crypto/sha256"
	"crypto/x509"
	"encoding/hex"
	"encoding/pem"
	"errors"
	"fmt"
	"strings"
	"time"
)

const (
	title        = "Certificato di sicurezza CBO"
	expectedName = "CBO GAIA Root CA"
)

const (
	ExitOK          = 0
	ExitError       = 1
	ExitUsage       = 2
	ExitMismatch    = 3
	ExitNeedsAdmin  = 4
	ExitDeclined    = 5
	usageText       = "Uso: CBO-CA-GAIA-Windows.exe [/S] [/SHA256=impronta] [/U] [/?]\n\n/S  silenzioso: richiede amministratore e /SHA256\n/SHA256=...  impronta SHA-256 attesa\n/U  rimuove solo la CA GAIA incorporata\n\nCodici: 0 ok, 1 errore, 2 uso errato, 3 impronta diversa, 4 amministratore richiesto, 5 annullato."
	elevatedFlag    = "/ELEVATED"
	fingerprintFlag = "/SHA256="
)

type Options struct {
	Silent    bool
	Uninstall bool
	Help      bool
	Elevated  bool
	Expected  string
}

type System interface {
	IsAdmin() bool
	Relaunch(args []string) error
	Ask(text string) bool
	Tell(text string, failure bool)
	StoreHas(der []byte) (bool, error)
	StoreAdd(der []byte) error
	StoreRemove(der []byte) (int, error)
}

func ParseArgs(args []string) (Options, error) {
	var options Options
	for _, argument := range args {
		upper := strings.ToUpper(argument)
		switch {
		case upper == "/S":
			options.Silent = true
		case upper == "/U":
			options.Uninstall = true
		case upper == "/?" || upper == "/H":
			options.Help = true
		case upper == elevatedFlag:
			options.Elevated = true
		case strings.HasPrefix(upper, fingerprintFlag):
			options.Expected = argument[len(fingerprintFlag):]
			if len(NormalizeFingerprint(options.Expected)) != 64 || strings.Trim(options.Expected, "0123456789abcdefABCDEF:") != "" {
				return options, errors.New("l'impronta dopo /SHA256= deve avere 64 cifre esadecimali")
			}
		default:
			return options, fmt.Errorf("opzione sconosciuta: %s", argument)
		}
	}
	return options, nil
}

func LoadCertificate(data []byte, now time.Time) ([]byte, *x509.Certificate, error) {
	var der []byte
	rest := data
	for {
		rest = bytes.TrimSpace(rest)
		if len(rest) == 0 {
			break
		}
		if !bytes.HasPrefix(rest, []byte("-----BEGIN ")) {
			return nil, nil, errors.New("testo inatteso nel certificato")
		}
		var block *pem.Block
		block, rest = pem.Decode(rest)
		if block == nil {
			break
		}
		if block.Type != "CERTIFICATE" {
			return nil, nil, fmt.Errorf("il file contiene un blocco %q: solo il certificato pubblico e' ammesso", block.Type)
		}
		if der != nil {
			return nil, nil, errors.New("il file contiene piu' di un certificato")
		}
		der = block.Bytes
	}
	if der == nil || len(bytes.TrimSpace(rest)) != 0 {
		return nil, nil, errors.New("certificato non valido")
	}
	certificate, err := x509.ParseCertificate(der)
	if err != nil {
		return nil, nil, fmt.Errorf("certificato non leggibile: %w", err)
	}
	if !certificate.IsCA || !certificate.BasicConstraintsValid || certificate.KeyUsage&x509.KeyUsageCertSign == 0 {
		return nil, nil, errors.New("il certificato non e' una autorita' di certificazione")
	}
	if certificate.Subject.CommonName != expectedName {
		return nil, nil, fmt.Errorf("nome inatteso: %s", certificate.Subject.CommonName)
	}
	if now.After(certificate.NotAfter) || now.Before(certificate.NotBefore) {
		return nil, nil, fmt.Errorf("il certificato non e' valido in questa data (scade il %s)", certificate.NotAfter.Format("02/01/2006"))
	}
	return der, certificate, nil
}

func NormalizeFingerprint(value string) string {
	var digits strings.Builder
	for _, character := range strings.ToUpper(value) {
		if (character >= '0' && character <= '9') || (character >= 'A' && character <= 'F') {
			digits.WriteRune(character)
		}
	}
	return digits.String()
}

func Fingerprint(der []byte) string {
	sum := sha256.Sum256(der)
	encoded := strings.ToUpper(hex.EncodeToString(sum[:]))
	pairs := make([]string, 0, 32)
	for index := 0; index < len(encoded); index += 2 {
		pairs = append(pairs, encoded[index:index+2])
	}
	return strings.Join(pairs, ":")
}

func Run(args []string, embedded []byte, system System, now time.Time) int {
	options, err := ParseArgs(args)
	if err != nil {
		system.Tell(err.Error()+"\n\n"+usageText, true)
		return ExitUsage
	}
	if options.Help {
		system.Tell(usageText, false)
		return ExitOK
	}
	if options.Silent && options.Expected == "" {
		system.Tell("La modalita' silenziosa richiede /SHA256.", true)
		return ExitUsage
	}
	der, certificate, err := LoadCertificate(embedded, now)
	if err != nil {
		system.Tell("Installazione interrotta: "+err.Error(), true)
		return ExitError
	}
	fingerprint := Fingerprint(der)
	if options.Expected != "" && NormalizeFingerprint(options.Expected) != NormalizeFingerprint(fingerprint) {
		system.Tell("L'impronta del certificato contenuto in questo programma non coincide con quella attesa.\n\nNon e' stato installato nulla. Scarica di nuovo il programma o chiama il CED.", true)
		return ExitMismatch
	}
	if !system.IsAdmin() {
		if options.Elevated || options.Silent {
			system.Tell("Servono i diritti di amministratore. Riprova con «Esegui come amministratore».", true)
			return ExitNeedsAdmin
		}
		if err := system.Relaunch(append(append([]string{}, args...), elevatedFlag)); err != nil {
			system.Tell("Senza i diritti di amministratore il certificato non puo' essere installato.", true)
			return ExitNeedsAdmin
		}
		return ExitOK
	}
	if options.Uninstall {
		if !options.Silent && !system.Ask("Rimuovere la CA GAIA incorporata? I servizi che la usano perderanno la fiducia TLS.") {
			return ExitDeclined
		}
		return uninstall(der, system)
	}
	if !options.Silent && options.Expected == "" {
		question := fmt.Sprintf("Sta per essere installato nei certificati attendibili di questo computer:\n\n%s\nValido fino al %s\n\nImpronta SHA-256:\n%s\n\nConfronta l'impronta con quella comunicata dal CED. Corrisponde?",
			certificate.Subject.CommonName, certificate.NotAfter.Format("02/01/2006"), fingerprint)
		if !system.Ask(question) {
			return ExitDeclined
		}
	}
	return install(der, fingerprint, system)
}

func install(der []byte, fingerprint string, system System) int {
	present, err := system.StoreHas(der)
	if err != nil {
		system.Tell("Impossibile leggere i certificati del computer: "+err.Error(), true)
		return ExitError
	}
	if present {
		system.Tell("Il certificato e' gia' installato. Non serve altro.", false)
		return ExitOK
	}
	if err := system.StoreAdd(der); err != nil {
		system.Tell("Installazione non riuscita: "+err.Error(), true)
		return ExitError
	}
	present, err = system.StoreHas(der)
	if err != nil || !present {
		system.Tell("Il certificato non risulta installato dopo l'operazione.", true)
		return ExitError
	}
	system.Tell("Certificato installato.\n\nImpronta SHA-256:\n"+fingerprint+"\n\nChiudi e riapri Microsoft Edge o Google Chrome, poi apri https://gaia.lan.", false)
	return ExitOK
}

func uninstall(der []byte, system System) int {
	removed, err := system.StoreRemove(der)
	if err != nil {
		system.Tell("Rimozione non riuscita: "+err.Error(), true)
		return ExitError
	}
	if removed == 0 {
		system.Tell("Il certificato non era installato.", false)
		return ExitOK
	}
	system.Tell("Certificato rimosso.", false)
	return ExitOK
}
