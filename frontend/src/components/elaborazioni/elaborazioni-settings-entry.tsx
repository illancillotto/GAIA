"use client";

import { ElaborazioniSettingsWorkspace } from "@/components/elaborazioni/settings-workspace";
import { PresenzeCredentialVault } from "@/components/presenze/presenze-credential-vault";

export function ElaborazioniSettingsEntry() {
  return (
    <div className="space-y-6">
      <ElaborazioniSettingsWorkspace />
      <section aria-label="Credenziali Presenze INAZ" id="credenziali-inaz">
        <PresenzeCredentialVault />
      </section>
    </div>
  );
}
