"use client";

import type { ApplicationUser, PresenzeCollaborator } from "@/types/api";
import type { CollaboratorRow } from "./page";

type CollaboratorMappingPanelProps = {
  rows: CollaboratorRow[];
  totalRows: number;
  selectedMappings: Record<string, string>;
  collaboratorMap: Map<string, PresenzeCollaborator>;
  sortedUsersByCollaborator: Map<string, ApplicationUser[]>;
  onApplySuggestedMappings: () => Promise<void>;
  onMappingChange: (rowId: string, value: string) => void;
  onSaveMapping: (rowId: string) => Promise<void>;
  onShowMore: () => void;
};

function confidenceLabel(confidence: CollaboratorRow["suggestionConfidence"]): string {
  if (confidence === "high") return "confidenza alta";
  if (confidence === "medium") return "confidenza media";
  return "confidenza bassa";
}

export function CollaboratorMappingPanel({
  rows,
  totalRows,
  selectedMappings,
  collaboratorMap,
  sortedUsersByCollaborator,
  onApplySuggestedMappings,
  onMappingChange,
  onSaveMapping,
  onShowMore,
}: CollaboratorMappingPanelProps) {
  const hiddenRows = totalRows - rows.length;

  return (
    <article className="panel-card">
      <div className="mb-4">
        <p className="section-title">Aggiorna mapping GAIA</p>
        <p className="section-copy">Seleziona un utente GAIA per i collaboratori che richiedono collegamento. Il sistema precompila un suggerimento basato su nome completo, username ed email.</p>
      </div>
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <button className="btn-secondary" type="button" onClick={() => void onApplySuggestedMappings()}>
          Applica suggeriti
        </button>
        <p className="text-sm text-gray-500">
          Vengono applicati solo i collaboratori non ancora mappati con un suggerimento disponibile.
        </p>
      </div>
      <div className="space-y-3">
        {rows.map((row) => (
          <div key={row.id} className="grid gap-3 rounded-2xl border border-gray-100 bg-gray-50 px-4 py-3 lg:grid-cols-[1fr_320px_120px] lg:items-center">
            <div>
              <p className="font-medium text-gray-900">{row.name}</p>
              <p className="text-xs text-gray-500">Matricola {row.employeeCode} · {row.contractSummary}</p>
              {row.suggestionConfidence !== "none" ? (
                <p className="mt-1 text-xs text-emerald-700">
                  Suggerito: {row.suggestedUserLabel} ({confidenceLabel(row.suggestionConfidence)})
                </p>
              ) : null}
            </div>
            <select
              className="form-control"
              value={selectedMappings[row.id] ?? String(collaboratorMap.get(row.id)?.application_user_id ?? "")}
              onChange={(event) => onMappingChange(row.id, event.target.value)}
            >
              <option value="">Nessun mapping</option>
              {(sortedUsersByCollaborator.get(row.id) ?? []).map((user) => (
                <option key={user.id} value={user.id}>
                  {user.username} · {user.email}
                </option>
              ))}
            </select>
            <button className="btn-primary" type="button" onClick={() => void onSaveMapping(row.id)}>
              Salva
            </button>
          </div>
        ))}
        {hiddenRows > 0 ? (
          <button className="btn-secondary" type="button" onClick={onShowMore}>
            Mostra altri mapping ({hiddenRows})
          </button>
        ) : null}
      </div>
    </article>
  );
}
