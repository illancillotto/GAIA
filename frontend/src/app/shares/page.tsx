"use client";

import { useEffect, useState } from "react";

import { ProtectedPage } from "@/components/app/protected-page";
import { getShares } from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import type { Share } from "@/types/api";

export default function SharesPage() {
  const [shares, setShares] = useState<Share[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadShares() {
      const token = getStoredAccessToken();
      if (!token) return;

      try {
        setShares(await getShares(token));
        setError(null);
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : "Errore caricamento share");
      }
    }

    void loadShares();
  }, []);

  return (
    <ProtectedPage
      title="Share NAS"
      description="Vista reale delle cartelle condivise attualmente esposte dal backend."
    >
      {error ? <p className="status-note error-text">{error}</p> : null}
      <table className="data-table">
        <thead>
          <tr>
            <th>Nome</th>
            <th>Path</th>
            <th>Settore</th>
            <th>Descrizione</th>
          </tr>
        </thead>
        <tbody>
          {shares.map((share) => (
            <tr key={share.id}>
              <td>{share.name}</td>
              <td className="mono">{share.path}</td>
              <td>{share.sector ?? "-"}</td>
              <td>{share.description ?? "-"}</td>
            </tr>
          ))}
          {shares.length === 0 ? (
            <tr>
              <td colSpan={4}>Nessuna share disponibile nel backend.</td>
            </tr>
          ) : null}
        </tbody>
      </table>
    </ProtectedPage>
  );
}
