"use client";

import { useEffect, useState } from "react";

import { ProtectedPage } from "@/components/app/protected-page";
import { getSyncCapabilities } from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import type { SyncCapabilities } from "@/types/api";

export default function SyncPage() {
  const [capabilities, setCapabilities] = useState<SyncCapabilities | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadCapabilities() {
      const token = getStoredAccessToken();
      if (!token) return;

      try {
        setCapabilities(await getSyncCapabilities(token));
        setError(null);
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : "Errore caricamento sync");
      }
    }

    void loadCapabilities();
  }, []);

  return (
    <ProtectedPage
      title="Sync NAS"
      description="Stato reale del connector NAS configurato nel backend e preview della capability di sync."
    >
      {error ? <p className="status-note error-text">{error}</p> : null}
      {capabilities ? (
        <table className="data-table">
          <tbody>
            <tr>
              <th>Host</th>
              <td>{capabilities.host}</td>
            </tr>
            <tr>
              <th>Porta</th>
              <td>{capabilities.port}</td>
            </tr>
            <tr>
              <th>Username</th>
              <td>{capabilities.username}</td>
            </tr>
            <tr>
              <th>SSH configurato</th>
              <td>{capabilities.ssh_configured ? "Si" : "No"}</td>
            </tr>
            <tr>
              <th>Live sync</th>
              <td>{capabilities.supports_live_sync ? "Attivo" : "Non ancora implementato"}</td>
            </tr>
          </tbody>
        </table>
      ) : (
        <p className="status-note">Nessuna capability disponibile.</p>
      )}
    </ProtectedPage>
  );
}
