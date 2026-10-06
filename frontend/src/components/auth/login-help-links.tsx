"use client";

import { useEffect, useState } from "react";

import { GAIA_CA_DOWNLOAD_BASE, GAIA_CA_SHA256 } from "@/lib/gaia-ca";

const downloads = [
  ["Windows Intel/AMD (.exe)", "CBO-CA-GAIA-Windows-amd64.exe"],
  ["Windows ARM64 (.exe)", "CBO-CA-GAIA-Windows-arm64.exe"],
  ["Pacchetto Linux e macOS", "GAIA-CA-client.tar.gz"],
  ["Guida di installazione", "GUIDA-CLIENT.txt"],
];

export function LoginHelpLinks() {
  const [available, setAvailable] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    fetch("/gaia-ca/manifest.json", { signal: controller.signal, cache: "no-store" })
      .then((response) => response.ok ? response.json() : null)
      .then((manifest) => setAvailable(manifest?.sha256 === GAIA_CA_SHA256))
      .catch(() => setAvailable(false));
    return () => controller.abort();
  }, []);

  return (
    <div className="space-y-3">
      <div className="flex justify-end">
        <a className="text-base font-semibold uppercase tracking-[0.11em] text-primary transition hover:opacity-80 sm:text-xs sm:tracking-[0.16em]" href="/auth/password-dimenticata">
          Password dimenticata?
        </a>
      </div>
      {available ? (
        <section aria-label="Certificato HTTPS GAIA" className="rounded-lg border border-outline-variant/30 p-3 text-sm">
          <p className="font-semibold text-primary">Certificato HTTPS GAIA</p>
          <p className="mt-1 text-on-surface-variant">Confronta l’impronta con il CED prima di installare. Gli EXE non sono firmati Authenticode.</p>
          <div className="mt-2 flex flex-wrap gap-x-4 gap-y-2">
            {downloads.map(([label, filename]) => (
              <a key={filename} href={`${GAIA_CA_DOWNLOAD_BASE}/${filename}`} className="text-primary underline" download>{label}</a>
            ))}
          </div>
          <p className="mt-2 break-all font-mono text-xs">SHA-256: {GAIA_CA_SHA256}</p>
        </section>
      ) : null}
    </div>
  );
}
