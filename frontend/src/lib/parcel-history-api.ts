import { getApiBaseUrl } from "@/lib/api";

export async function parcelHistoryRequest<T>(token: string, path: string): Promise<T> {
  const response = await fetch(`${getApiBaseUrl()}/ruolo/particelle/storia${path}`, {
    headers: { Authorization: `Bearer ${token}` }, cache: "no-store",
  });
  if (!response.ok) {
    if (response.status === 404) throw new Error("La storia richiesta non è disponibile. Il servizio potrebbe non essere ancora aggiornato: riprova o torna alla ricerca.");
    if (response.status === 401) throw new Error("Sessione scaduta. Accedi di nuovo a GAIA.");
    if (response.status === 403) throw new Error("Non hai i permessi per consultare questa storia.");
    throw new Error("Impossibile caricare la storia della particella. Riprova tra poco.");
  }
  return response.json() as Promise<T>;
}
