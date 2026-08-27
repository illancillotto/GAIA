"use client";

import { useEffect, useState } from "react";
import type { MutableRefObject } from "react";

import { getElaborazioneCredentials } from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import type { ElaborazioneCredential } from "@/types/api";

type BatchCredentialSelectorProps = {
  disabled?: boolean;
  selectionRef: MutableRefObject<string[]>;
};

export function BatchCredentialSelector({ disabled = false, selectionRef }: BatchCredentialSelectorProps) {
  const [credentials, setCredentials] = useState<ElaborazioneCredential[]>([]);
  const [selectedIds, setSelectedIds] = useState<string[]>(selectionRef.current);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const token = getStoredAccessToken();
    if (!token) return;

    void getElaborazioneCredentials(token)
      .then((status) => {
        if (!cancelled) {
          setCredentials(status.credentials.filter((credential) => credential.active));
          setError(null);
        }
      })
      .catch((loadError: unknown) => {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : "Errore caricamento credenziali SISTER");
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  function toggleCredential(credentialId: string, checked: boolean): void {
    const nextIds = checked ? [...selectedIds, credentialId] : selectedIds.filter((item) => item !== credentialId);
    selectionRef.current = nextIds;
    setSelectedIds(nextIds);
  }

  return (
    <fieldset className="mt-5 rounded-2xl border border-[#d9dfd6] bg-[#f7f9f5] p-4" disabled={disabled}>
      <legend className="px-1 text-sm font-semibold text-gray-900">Credenziali SISTER del batch</legend>
      <p className="mt-1 text-xs leading-5 text-gray-600">
        Se non selezioni nulla il worker usa il pool automatico. Le fasce orarie configurate restano sempre rispettate.
      </p>
      {error ? <p className="mt-3 text-sm text-red-700">{error}</p> : null}
      {!error && credentials.length === 0 ? (
        <p className="mt-3 text-sm text-gray-500">Nessuna credenziale SISTER attiva disponibile.</p>
      ) : (
        <div className="mt-3 grid gap-2 md:grid-cols-2 xl:grid-cols-3">
          {credentials.map((credential) => (
            <label className="flex cursor-pointer items-start gap-3 rounded-xl border border-gray-200 bg-white px-3 py-3" key={credential.id}>
              <input
                checked={selectedIds.includes(credential.id)}
                className="mt-1 h-4 w-4 accent-[#1D4E35]"
                onChange={(event) => toggleCredential(credential.id, event.target.checked)}
                type="checkbox"
              />
              <span>
                <span className="block text-sm font-semibold text-gray-900">{credential.label}</span>
                <span className="block text-xs text-gray-500">
                  {credential.sister_username} · {credential.schedule_enabled ? "Fasce orarie attive" : "Sempre disponibile"}
                </span>
              </span>
            </label>
          ))}
        </div>
      )}
    </fieldset>
  );
}
