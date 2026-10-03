package main

import (
	"crypto/ecdsa"
	"crypto/elliptic"
	"crypto/rand"
	"crypto/x509"
	"crypto/x509/pkix"
	"encoding/pem"
	"errors"
	"math/big"
	"strings"
	"testing"
	"time"
)

var now = time.Date(2026, 9, 25, 12, 0, 0, 0, time.UTC)

func makeCertificate(t *testing.T, mutate func(*x509.Certificate)) []byte {
	t.Helper()
	key, err := ecdsa.GenerateKey(elliptic.P384(), rand.Reader)
	if err != nil {
		t.Fatal(err)
	}
	template := &x509.Certificate{
		SerialNumber:          big.NewInt(1),
		Subject:               pkix.Name{CommonName: expectedName},
		NotBefore:             now.Add(-time.Hour),
		NotAfter:              now.AddDate(10, 0, 0),
		IsCA:                  true,
		BasicConstraintsValid: true,
		KeyUsage:              x509.KeyUsageCertSign | x509.KeyUsageCRLSign,
	}
	if mutate != nil {
		mutate(template)
	}
	der, err := x509.CreateCertificate(rand.Reader, template, template, &key.PublicKey, key)
	if err != nil {
		t.Fatal(err)
	}
	return pem.EncodeToMemory(&pem.Block{Type: "CERTIFICATE", Bytes: der})
}

type fakeSystem struct {
	admin        bool
	relaunchErr  error
	relaunched   [][]string
	answer       bool
	asked        []string
	told         []string
	failures     int
	stored       [][]byte
	hasErr       error
	addErr       error
	removeErr    error
	addIsNoop    bool
	hasCallCount int
}

func (f *fakeSystem) IsAdmin() bool { return f.admin }
func (f *fakeSystem) Relaunch(args []string) error {
	f.relaunched = append(f.relaunched, args)
	return f.relaunchErr
}
func (f *fakeSystem) Ask(text string) bool {
	f.asked = append(f.asked, text)
	return f.answer
}
func (f *fakeSystem) Tell(text string, failure bool) {
	f.told = append(f.told, text)
	if failure {
		f.failures++
	}
}
func (f *fakeSystem) StoreHas(der []byte) (bool, error) {
	f.hasCallCount++
	if f.hasErr != nil {
		return false, f.hasErr
	}
	for _, item := range f.stored {
		if string(item) == string(der) {
			return true, nil
		}
	}
	return false, nil
}
func (f *fakeSystem) StoreAdd(der []byte) error {
	if f.addErr != nil {
		return f.addErr
	}
	if !f.addIsNoop {
		f.stored = append(f.stored, der)
	}
	return nil
}
func (f *fakeSystem) StoreRemove(der []byte) (int, error) {
	if f.removeErr != nil {
		return 0, f.removeErr
	}
	removed := 0
	kept := f.stored[:0]
	for _, item := range f.stored {
		if string(item) == string(der) {
			removed++
		} else {
			kept = append(kept, item)
		}
	}
	f.stored = kept
	return removed, nil
}

func TestParseArgs(t *testing.T) {
	options, err := ParseArgs([]string{"/s", "/SHA256=" + strings.Repeat("ab", 32), "/elevated", "/u"})
	if err != nil || !options.Silent || !options.Uninstall || !options.Elevated || options.Expected == "" {
		t.Fatalf("unexpected: %+v %v", options, err)
	}
	if options, _ := ParseArgs([]string{"/?"}); !options.Help {
		t.Fatal("help not parsed")
	}
	for _, bad := range [][]string{{"/X"}, {"/SHA256=abc"}, {"--silent"}, {"/SHA256=" + strings.Repeat("ab", 32) + " /U"}} {
		if _, err := ParseArgs(bad); err == nil {
			t.Fatalf("%v accepted", bad)
		}
	}
}

func TestLoadCertificateRefusesAnythingButAValidPublicCA(t *testing.T) {
	good := makeCertificate(t, nil)
	if _, certificate, err := LoadCertificate(good, now); err != nil || certificate.Subject.CommonName != expectedName {
		t.Fatalf("good certificate refused: %v", err)
	}
	withKey := append(append([]byte{}, good...), pem.EncodeToMemory(&pem.Block{Type: "EC PRIVATE KEY", Bytes: []byte{1, 2, 3}})...)
	cases := map[string][]byte{
		"private key":   withKey,
		"two":           append(append([]byte{}, good...), good...),
		"garbage":       []byte("not a certificate"),
		"leading text":  append([]byte("junk\n"), good...),
		"malformed PEM": []byte("-----BEGIN CERTIFICATE-----\ninvalid\n"),
		"empty":         nil,
		"trailing text": append(append([]byte{}, good...), []byte("junk")...),
		"corrupt":       pem.EncodeToMemory(&pem.Block{Type: "CERTIFICATE", Bytes: []byte{1, 2, 3}}),
		"not a ca":      makeCertificate(t, func(c *x509.Certificate) { c.IsCA = false }),
		"no cert sign":  makeCertificate(t, func(c *x509.Certificate) { c.KeyUsage = x509.KeyUsageDigitalSignature }),
		"wrong name":    makeCertificate(t, func(c *x509.Certificate) { c.Subject.CommonName = "Other CA" }),
		"expired":       makeCertificate(t, func(c *x509.Certificate) { c.NotAfter = now.Add(-time.Minute); c.NotBefore = now.AddDate(-1, 0, 0) }),
		"not yet valid": makeCertificate(t, func(c *x509.Certificate) { c.NotBefore = now.Add(time.Hour) }),
	}
	for name, data := range cases {
		if _, _, err := LoadCertificate(data, now); err == nil {
			t.Errorf("%s accepted", name)
		}
	}
}

func TestFingerprintFormats(t *testing.T) {
	der, _, _ := LoadCertificate(makeCertificate(t, nil), now)
	fingerprint := Fingerprint(der)
	if len(fingerprint) != 95 || strings.Count(fingerprint, ":") != 31 || fingerprint != strings.ToUpper(fingerprint) {
		t.Fatalf("bad format: %s", fingerprint)
	}
	if NormalizeFingerprint(strings.ToLower(fingerprint)+" ") != NormalizeFingerprint(fingerprint) {
		t.Fatal("normalisation differs")
	}
}

func TestInteractiveInstallAsksForTheFingerprintFirst(t *testing.T) {
	data := makeCertificate(t, nil)
	der, _, _ := LoadCertificate(data, now)

	declined := &fakeSystem{admin: true}
	if code := Run(nil, data, declined, now); code != ExitDeclined || len(declined.stored) != 0 {
		t.Fatalf("declined: code %d stored %d", code, len(declined.stored))
	}
	if !strings.Contains(declined.asked[0], Fingerprint(der)) {
		t.Fatal("the question does not show the fingerprint")
	}

	accepted := &fakeSystem{admin: true, answer: true}
	if code := Run(nil, data, accepted, now); code != ExitOK || len(accepted.stored) != 1 || accepted.failures != 0 {
		t.Fatalf("accepted: code %d stored %d", code, len(accepted.stored))
	}
	if !strings.Contains(accepted.told[len(accepted.told)-1], "riapri Microsoft Edge") {
		t.Fatal("no restart hint")
	}

	again := &fakeSystem{admin: true, answer: true, stored: accepted.stored}
	if code := Run(nil, data, again, now); code != ExitOK || len(again.stored) != 1 || !strings.Contains(again.told[0], "gia' installato") {
		t.Fatalf("second run: %d %v", code, again.told)
	}
}

func TestSilentInstallNeedsNoQuestionAndChecksTheFingerprint(t *testing.T) {
	data := makeCertificate(t, nil)
	der, _, _ := LoadCertificate(data, now)

	system := &fakeSystem{admin: true}
	code := Run([]string{"/S", "/SHA256=" + strings.ToLower(Fingerprint(der))}, data, system, now)
	if code != ExitOK || len(system.stored) != 1 || len(system.asked) != 0 {
		t.Fatalf("silent: %d stored %d asked %d", code, len(system.stored), len(system.asked))
	}

	wrong := &fakeSystem{admin: true}
	code = Run([]string{"/S", "/SHA256=" + strings.Repeat("00", 32)}, data, wrong, now)
	if code != ExitMismatch || len(wrong.stored) != 0 || wrong.hasCallCount != 0 {
		t.Fatalf("mismatch: %d stored %d", code, len(wrong.stored))
	}

	silentNoFingerprint := &fakeSystem{admin: true}
	if code := Run([]string{"/S"}, data, silentNoFingerprint, now); code != ExitUsage || len(silentNoFingerprint.stored) != 0 {
		t.Fatalf("silent without fingerprint: %d", code)
	}
}

func TestWithoutAdministratorRightsItRelaunchesElevatedOnce(t *testing.T) {
	data := makeCertificate(t, nil)

	system := &fakeSystem{}
	if code := Run(nil, data, system, now); code != ExitOK || len(system.stored) != 0 {
		t.Fatalf("relaunch: %d", code)
	}
	if len(system.relaunched) != 1 || strings.Join(system.relaunched[0], " ") != "/ELEVATED" {
		t.Fatalf("relaunch args: %v", system.relaunched)
	}

	refused := &fakeSystem{relaunchErr: errors.New("no")}
	if code := Run(nil, data, refused, now); code != ExitNeedsAdmin || refused.failures != 1 {
		t.Fatalf("refused: %d", code)
	}

	loop := &fakeSystem{}
	if code := Run([]string{"/ELEVATED"}, data, loop, now); code != ExitNeedsAdmin || len(loop.relaunched) != 0 {
		t.Fatalf("loop guard: %d relaunches %d", code, len(loop.relaunched))
	}
}

func TestFailuresAreReportedAndNothingIsClaimed(t *testing.T) {
	data := makeCertificate(t, nil)
	cases := map[string]*fakeSystem{
		"cannot read the store": {admin: true, answer: true, hasErr: errors.New("boom")},
		"cannot add":            {admin: true, answer: true, addErr: errors.New("denied")},
		"not there afterwards":  {admin: true, answer: true, addIsNoop: true},
	}
	for name, system := range cases {
		if code := Run(nil, data, system, now); code != ExitError || system.failures != 1 {
			t.Errorf("%s: code %d failures %d", name, code, system.failures)
		}
	}
	if code := Run(nil, []byte("bad"), &fakeSystem{admin: true}, now); code != ExitError {
		t.Errorf("bad embedded certificate: %d", code)
	}
}

func TestUninstallRemovesOnlyWhatIsThere(t *testing.T) {
	data := makeCertificate(t, nil)
	der, _, _ := LoadCertificate(data, now)

	present := &fakeSystem{admin: true, answer: true, stored: [][]byte{der, []byte("other")}}
	if code := Run([]string{"/U"}, data, present, now); code != ExitOK || len(present.stored) != 1 || len(present.asked) != 1 {
		t.Fatalf("uninstall: %d stored %d", code, len(present.stored))
	}
	absent := &fakeSystem{admin: true, answer: true}
	if code := Run([]string{"/U"}, data, absent, now); code != ExitOK || !strings.Contains(absent.told[0], "non era installato") {
		t.Fatalf("absent: %d", code)
	}
	failing := &fakeSystem{admin: true, answer: true, removeErr: errors.New("denied")}
	if code := Run([]string{"/U"}, data, failing, now); code != ExitError || failing.failures != 1 {
		t.Fatalf("failing: %d", code)
	}
}

func TestUsageAndHelp(t *testing.T) {
	data := makeCertificate(t, nil)
	wrong := &fakeSystem{admin: true}
	if code := Run([]string{"/nope"}, data, wrong, now); code != ExitUsage || wrong.failures != 1 || len(wrong.stored) != 0 {
		t.Fatalf("usage: %d", code)
	}
	help := &fakeSystem{}
	if code := Run([]string{"/?"}, data, help, now); code != ExitOK || len(help.relaunched) != 0 || help.failures != 0 {
		t.Fatalf("help: %d", code)
	}
}

func TestSilentNeedsAdminAndUninstallNeedsConsent(t *testing.T) {
	data := makeCertificate(t, nil)
	der, _, _ := LoadCertificate(data, now)
	system := &fakeSystem{}
	if code := Run([]string{"/S", "/SHA256=" + Fingerprint(der)}, data, system, now); code != ExitNeedsAdmin || len(system.relaunched) != 0 {
		t.Fatalf("silent elevation: %d", code)
	}
	declined := &fakeSystem{admin: true, stored: [][]byte{der}}
	if code := Run([]string{"/U"}, data, declined, now); code != ExitDeclined || len(declined.stored) != 1 {
		t.Fatalf("uninstall declined: %d", code)
	}
}
