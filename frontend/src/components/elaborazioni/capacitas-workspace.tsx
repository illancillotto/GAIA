"use client";

import { useEffect, useMemo, useState } from "react";

import { ProtectedPage } from "@/components/app/protected-page";
import {
  ElaborazioneHero,
  ElaborazioneMiniStat,
  ElaborazioneNoticeCard,
  ElaborazionePanelHeader,
} from "@/components/elaborazioni/module-chrome";
import { ElaborazioneWorkspaceModal } from "@/components/elaborazioni/workspace-modal";
import { EmptyState } from "@/components/ui/empty-state";
import { LockIcon, SearchIcon, UsersIcon } from "@/components/ui/icons";
import { listCapacitasCredentials, searchCapacitasInvolture } from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import type { CapacitasAnagrafica, CapacitasCredential, CapacitasSearchResult } from "@/types/api";

const SEARCH_TYPE_OPTIONS = [
  { value: 0, label: "Denominazione esatta" },
  { value: 1, label: "Denominazione inizia per" },
  { value: 2, label: "Codice fiscale" },
  { value: 3, label: "CCO / FRA / CCS" },
  { value: 4, label: "Denominazione contiene" },
  { value: 5, label: "Utenza" },
  { value: 6, label: "Indirizzo" },
  { value: 7, label: "Data di nascita" },
  { value: 9, label: "Contiene storico" },
  { value: 10, label: "Avviso" },
  { value: 11, label: "Titolo" },
  { value: 12, label: "Partita IVA" },
  { value: 13, label: "Codice soggetto" },
];

function renderIdentity(row: CapacitasAnagrafica): string {
  return row.Denominazione ?? row.CodiceFiscale ?? row.PartitaIva ?? row.CCO ?? "Record";
}

export function ElaborazioniCapacitasWorkspace({ embedded = false }: { embedded?: boolean }) {
  const [settingsModalOpen, setSettingsModalOpen] = useState(false);
  const [credentials, setCredentials] = useState<CapacitasCredential[]>([]);
  const [results, setResults] = useState<CapacitasSearchResult | null>(null);
  const [loadingCredentials, setLoadingCredentials] = useState(false);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [formState, setFormState] = useState({
    q: "",
    tipo_ricerca: 1,
    solo_con_beni: false,
    credential_id: "",
  });

  useEffect(() => {
    void loadCredentials();
  }, []);

  async function loadCredentials(): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) return;

    setLoadingCredentials(true);
    try {
      const nextCredentials = await listCapacitasCredentials(token);
      setCredentials(nextCredentials);
      setError(null);
      setFormState((current) => ({
        ...current,
        credential_id: current.credential_id
          ? current.credential_id
          : nextCredentials.length === 1
            ? String(nextCredentials[0].id)
            : "",
      }));
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Errore caricamento credenziali Capacitas");
    } finally {
      setLoadingCredentials(false);
    }
  }

  async function handleSearch(): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) return;

    setSearching(true);
    try {
      const payload = {
        q: formState.q.trim(),
        tipo_ricerca: formState.tipo_ricerca,
        solo_con_beni: formState.solo_con_beni,
        credential_id: formState.credential_id ? Number.parseInt(formState.credential_id, 10) : undefined,
      };
      const response = await searchCapacitasInvolture(token, payload);
      setResults(response);
      setError(null);
    } catch (searchError) {
      setError(searchError instanceof Error ? searchError.message : "Errore ricerca inVOLTURE");
      setResults(null);
    } finally {
      setSearching(false);
    }
  }

  const activeCredential = useMemo(
    () => credentials.find((credential) => String(credential.id) === formState.credential_id) ?? null,
    [credentials, formState.credential_id],
  );
  const activeCredentialsCount = credentials.filter((credential) => credential.active).length;

  const content = (
    <>
      <div className="space-y-6">
        <ElaborazioneHero
          badge={
            <>
              <UsersIcon className="h-3.5 w-3.5" />
              Capacitas inVOLTURE
            </>
          }
          title="Ricerca anagrafica sul portale inVOLTURE usando il pool account del modulo Elaborazioni."
          description="La schermata mette in evidenza il pool disponibile, la credenziale effettiva selezionata e il risultato della ricerca in un layout coerente con il resto del modulo."
          actions={
            error ? (
              <ElaborazioneNoticeCard title="Errore ricerca" description={error} tone="danger" />
            ) : (
              <>
                <ElaborazioneNoticeCard
                  title="Credenziali dedicate"
                  description="Se non selezioni un account manualmente, il backend sceglie una credenziale attiva nella finestra oraria corretta."
                />
                <button className="btn-secondary" onClick={() => setSettingsModalOpen(true)} type="button">
                  Apri Credenziali
                </button>
              </>
            )
          }
        >
          <div className="grid gap-3 sm:grid-cols-3">
            <ElaborazioneMiniStat eyebrow="Pool" value={`${activeCredentialsCount}/${credentials.length}`} description="Account attivi sul totale configurato." />
            <ElaborazioneMiniStat eyebrow="Ricerca corrente" value={results?.total ?? 0} description="Record restituiti dall'ultima ricerca." tone={results && results.total > 0 ? "success" : "default"} />
            <ElaborazioneMiniStat eyebrow="Account forzato" value={activeCredential ? activeCredential.label : "Auto"} description="Se impostato, il backend non esegue auto-selezione." />
          </div>
        </ElaborazioneHero>

        <article className="overflow-hidden rounded-[28px] border border-[#d9dfd6] bg-white shadow-panel">
          <ElaborazionePanelHeader
            badge={
              <>
                <LockIcon className="h-3.5 w-3.5" />
                Ricerca anagrafica
              </>
            }
            title="Parametri della query inVOLTURE"
            description="Usa Codice fiscale per ricerche puntuali oppure modalità lessicali sulla denominazione."
          />
          <div className="p-6">
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              <label className="space-y-2 xl:col-span-2">
                <span className="label-caption">Valore ricerca</span>
                <input
                  className="form-control"
                  placeholder="Codice fiscale, denominazione, CCO~FRA~CCS..."
                  value={formState.q}
                  onChange={(event) => setFormState((current) => ({ ...current, q: event.target.value }))}
                />
              </label>
              <label className="space-y-2">
                <span className="label-caption">Tipo ricerca</span>
                <select
                  className="form-control"
                  value={formState.tipo_ricerca}
                  onChange={(event) =>
                    setFormState((current) => ({
                      ...current,
                      tipo_ricerca: Number.parseInt(event.target.value, 10),
                    }))
                  }
                >
                  {SEARCH_TYPE_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="space-y-2">
                <span className="label-caption">Credenziale</span>
                <select
                  className="form-control"
                  value={formState.credential_id}
                  onChange={(event) => setFormState((current) => ({ ...current, credential_id: event.target.value }))}
                >
                  <option value="">Auto-selezione backend</option>
                  {credentials.map((credential) => (
                    <option key={credential.id} value={credential.id}>
                      {credential.label} · {credential.username}
                    </option>
                  ))}
                </select>
              </label>
            </div>

            <div className="mt-4 flex flex-wrap items-center gap-3">
              <label className="flex items-center gap-3 rounded-lg border border-gray-100 bg-gray-50 px-4 py-3">
                <input
                  checked={formState.solo_con_beni}
                  className="h-4 w-4 accent-[#1D4E35]"
                  type="checkbox"
                  onChange={(event) => setFormState((current) => ({ ...current, solo_con_beni: event.target.checked }))}
                />
                <span className="text-sm text-gray-700">Solo soggetti con beni</span>
              </label>
              <button
                className="btn-primary"
                disabled={searching || !formState.q.trim() || loadingCredentials}
                onClick={() => void handleSearch()}
                type="button"
              >
                {searching ? "Ricerca in corso..." : "Avvia ricerca"}
              </button>
              {activeCredential ? (
                <span className="text-xs text-gray-500">
                  Credenziale forzata: {activeCredential.label} · fascia {activeCredential.allowed_hours_start}:00-
                  {activeCredential.allowed_hours_end}:00
                </span>
              ) : (
                <span className="text-xs text-gray-500">
                  Se non forzi un account, il backend seleziona automaticamente una credenziale attiva nella fascia oraria corrente.
                </span>
              )}
            </div>
          </div>
        </article>

        <article className="overflow-hidden rounded-[28px] border border-[#d9dfd6] bg-white p-0 shadow-panel">
          <ElaborazionePanelHeader
            badge={
              <>
                <SearchIcon className="h-3.5 w-3.5" />
                Risultati ricerca
              </>
            }
            title={results == null ? "Nessuna ricerca eseguita" : `${results.total} record restituiti dal portale`}
            description="I risultati sono riportati così come esposti da inVOLTURE, senza reinterpretazione lato frontend."
          />
          {results == null ? (
            <div className="p-5">
              <EmptyState
                icon={SearchIcon}
                title="Avvia una ricerca Capacitas"
                description="Inserisci un criterio e lancia una ricerca per vedere gli anagrafici restituiti da inVOLTURE."
              />
            </div>
          ) : results.rows.length === 0 ? (
            <div className="p-5">
              <EmptyState
                icon={SearchIcon}
                title="Nessun risultato"
                description="Il portale non ha restituito anagrafiche compatibili con i parametri selezionati."
              />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Nominativo</th>
                    <th>Codice fiscale</th>
                    <th>Partita IVA</th>
                    <th>Comune</th>
                    <th>CCO</th>
                    <th>Patrimonio</th>
                    <th>Meta</th>
                  </tr>
                </thead>
                <tbody>
                  {results.rows.map((row, index) => (
                    <tr key={`${row.CCO ?? row.IDXANA ?? row.id ?? index}`}>
                      <td className="font-medium text-gray-900">{renderIdentity(row)}</td>
                      <td>{row.CodiceFiscale ?? "—"}</td>
                      <td>{row.PartitaIva ?? "—"}</td>
                      <td>{row.Comune ?? "—"}</td>
                      <td>{row.CCO ?? "—"}</td>
                      <td>{row.Patrimonio ?? "—"}</td>
                      <td className="text-xs text-gray-500">
                        {row.Stato ?? "—"} · {row.IDXANA ?? row.id ?? "n/d"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </article>
      </div>
      <ElaborazioneWorkspaceModal
        description="Configurazione credenziali aperta in modale per mantenere il contesto della ricerca Capacitas."
        href="/elaborazioni/settings"
        onClose={() => setSettingsModalOpen(false)}
        open={settingsModalOpen}
        title="Credenziali"
      />
    </>
  );

  if (embedded) {
    return content;
  }

  return (
    <ProtectedPage
      title="Capacitas inVOLTURE"
      description="Ricerca anagrafica operativa sul portale inVOLTURE usando il pool credenziali Capacitas."
      breadcrumb="Elaborazioni / Capacitas"
      requiredModule="catasto"
    >
      {content}
    </ProtectedPage>
  );
}
