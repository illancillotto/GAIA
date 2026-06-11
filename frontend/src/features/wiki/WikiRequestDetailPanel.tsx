"use client";

import { EmptyState } from "@/components/ui/empty-state";
import { SearchIcon } from "@/components/ui/icons";
import { WikiRequestArtifactsPanel } from "./WikiRequestArtifactsPanel";
import { WikiRequestDeliveryPanel } from "./WikiRequestDeliveryPanel";
import type {
  WikiRequest,
  WikiRequestArtifact,
  WikiRequestAssignee,
  WikiRequestDuplicateCandidate,
  WikiRequestEvent,
  WikiRequestFamily,
} from "@/types/api";

type DeliveryStatusValue = "discovery" | "planned" | "in_progress" | "released" | "wont_do";

type WikiRequestDetailPanelProps = {
  selectedRequest: WikiRequest | null;
  artifacts: WikiRequestArtifact[];
  artifactsLoading: boolean;
  screenshotPreviewUrl: string | null;
  downloadingArtifactId: string | null;
  onDownloadArtifact: (artifact: WikiRequestArtifact) => Promise<void>;
  draftExternalTicketKey: string;
  draftExternalTicketUrl: string;
  draftDeliveryStatus: DeliveryStatusValue;
  draftDeliveryNotes: string;
  deliveryStatusOptions: Array<{ value: DeliveryStatusValue; label: string }>;
  onExternalTicketKeyChange: (value: string) => void;
  onExternalTicketUrlChange: (value: string) => void;
  onDeliveryStatusChange: (value: DeliveryStatusValue) => void;
  onDeliveryNotesChange: (value: string) => void;
  family: WikiRequestFamily | null;
  linkedDuplicates: WikiRequestDuplicateCandidate[];
  linkedDuplicatesLoading: boolean;
  duplicates: WikiRequestDuplicateCandidate[];
  duplicatesLoading: boolean;
  unlinkingDuplicateId: string | null;
  promotingCanonicalId: string | null;
  markingDuplicateId: string | null;
  onUnlinkDuplicate: (requestId: string) => Promise<void>;
  onMakeCanonical: (requestId: string) => Promise<void>;
  onMarkDuplicate: (requestId: string) => Promise<void>;
  draftStatus: WikiRequest["status"];
  onDraftStatusChange: (value: WikiRequest["status"]) => void;
  statusOptions: Array<{ value: string; label: string }>;
  draftPriority: WikiRequest["priority"];
  onDraftPriorityChange: (value: WikiRequest["priority"]) => void;
  priorityOptions: Array<{ value: string; label: string }>;
  draftSeverity: WikiRequest["severity"];
  onDraftSeverityChange: (value: WikiRequest["severity"]) => void;
  severityOptions: Array<{ value: string; label: string }>;
  draftAssignedTo: string;
  onDraftAssignedToChange: (value: string) => void;
  assignees: WikiRequestAssignee[];
  draftResolutionMessage: string;
  onDraftResolutionMessageChange: (value: string) => void;
  draftNotes: string;
  onDraftNotesChange: (value: string) => void;
  timelineLoading: boolean;
  timeline: WikiRequestEvent[];
  error: string | null;
  successMessage: string | null;
  saving: boolean;
  onSave: () => void;
  formatDateTime: (value: string) => string;
  statusBadgeClasses: (status: WikiRequest["status"]) => string;
  statusLabel: (status: WikiRequest["status"]) => string;
  requestTypeLabel: (requestType: WikiRequest["request_type"]) => string;
  priorityBadgeClasses: (priority: WikiRequest["priority"]) => string;
  priorityLabel: (priority: WikiRequest["priority"]) => string;
  severityBadgeClasses: (severity: WikiRequest["severity"]) => string;
  severityLabel: (severity: WikiRequest["severity"]) => string;
};

export function WikiRequestDetailPanel({
  selectedRequest,
  artifacts,
  artifactsLoading,
  screenshotPreviewUrl,
  downloadingArtifactId,
  onDownloadArtifact,
  draftExternalTicketKey,
  draftExternalTicketUrl,
  draftDeliveryStatus,
  draftDeliveryNotes,
  deliveryStatusOptions,
  onExternalTicketKeyChange,
  onExternalTicketUrlChange,
  onDeliveryStatusChange,
  onDeliveryNotesChange,
  family,
  linkedDuplicates,
  linkedDuplicatesLoading,
  duplicates,
  duplicatesLoading,
  unlinkingDuplicateId,
  promotingCanonicalId,
  markingDuplicateId,
  onUnlinkDuplicate,
  onMakeCanonical,
  onMarkDuplicate,
  draftStatus,
  onDraftStatusChange,
  statusOptions,
  draftPriority,
  onDraftPriorityChange,
  priorityOptions,
  draftSeverity,
  onDraftSeverityChange,
  severityOptions,
  draftAssignedTo,
  onDraftAssignedToChange,
  assignees,
  draftResolutionMessage,
  onDraftResolutionMessageChange,
  draftNotes,
  onDraftNotesChange,
  timelineLoading,
  timeline,
  error,
  successMessage,
  saving,
  onSave,
  formatDateTime,
  statusBadgeClasses,
  statusLabel,
  requestTypeLabel,
  priorityBadgeClasses,
  priorityLabel,
  severityBadgeClasses,
  severityLabel,
}: WikiRequestDetailPanelProps) {
  return (
    <article className="rounded-[32px] border border-[#d9dfd4] bg-white p-5 shadow-sm xl:sticky xl:top-6 xl:self-start">
      {selectedRequest ? (
        <div className="space-y-5">
          <div className="space-y-4 border-b border-gray-100 pb-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="space-y-3">
                <div className="flex flex-wrap items-center gap-2">
                  <span className={`rounded-full border px-2 py-0.5 text-xs font-medium ${statusBadgeClasses(selectedRequest.status)}`}>
                    {statusLabel(selectedRequest.status)}
                  </span>
                  <span className="rounded-full border border-gray-200 bg-gray-50 px-2 py-0.5 text-xs text-gray-600">
                    {requestTypeLabel(selectedRequest.request_type)}
                  </span>
                  <span className={`rounded-full border px-2 py-0.5 text-xs font-medium ${priorityBadgeClasses(selectedRequest.priority)}`}>
                    Priorita {priorityLabel(selectedRequest.priority)}
                  </span>
                  <span className={`rounded-full border px-2 py-0.5 text-xs font-medium ${severityBadgeClasses(selectedRequest.severity)}`}>
                    Severita {severityLabel(selectedRequest.severity)}
                  </span>
                </div>
                <div>
                  <h3 className="text-xl font-semibold text-gray-900">Dettaglio richiesta</h3>
                  <p className="mt-1 text-sm leading-6 text-gray-600">
                    Vista completa del caso, del contesto allegato e delle decisioni operative da prendere.
                  </p>
                </div>
              </div>
              <a href={`/wiki/requests/${selectedRequest.id}`} className="text-xs font-medium text-[#1D4E35] underline underline-offset-2">
                Apri pagina richiesta
              </a>
            </div>
            <p className="text-xs text-gray-500">
              Creata da {selectedRequest.created_by ?? "n/d"} il {formatDateTime(selectedRequest.created_at)}.
            </p>
          </div>

          <div className="grid gap-3 md:grid-cols-3">
            <div className="rounded-[24px] border border-[#e5ebe5] bg-[#fafbf9] px-4 py-3">
              <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#87948c]">Owner</p>
              <p className="mt-2 text-sm font-semibold text-[#223d30]">{selectedRequest.assigned_to_name || "Non assegnata"}</p>
              <p className="mt-1 text-xs text-[#66766e]">{selectedRequest.assigned_to || "Serve presa in carico"}</p>
            </div>
            <div className="rounded-[24px] border border-[#e5ebe5] bg-[#fafbf9] px-4 py-3">
              <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#87948c]">Delivery</p>
              <p className="mt-2 text-sm font-semibold text-[#223d30]">{selectedRequest.delivery_status || "Da collegare"}</p>
              <p className="mt-1 text-xs text-[#66766e]">{selectedRequest.external_ticket_key || "Nessun ticket esterno"}</p>
            </div>
            <div className="rounded-[24px] border border-[#e5ebe5] bg-[#fafbf9] px-4 py-3">
              <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#87948c]">Ultimo update</p>
              <p className="mt-2 text-sm font-semibold text-[#223d30]">{formatDateTime(selectedRequest.updated_at)}</p>
              <p className="mt-1 text-xs text-[#66766e]">{selectedRequest.page_path || "Percorso non indicato"}</p>
            </div>
          </div>

          <div className="space-y-2">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Domanda utente</p>
            <div className="rounded-2xl border border-gray-200 bg-[#fafaf7] px-4 py-3 text-sm leading-relaxed text-gray-800">
              {selectedRequest.user_question}
            </div>
          </div>

          <div className="space-y-2">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Risposta agente</p>
            <div className="rounded-2xl border border-gray-200 bg-[#fafaf7] px-4 py-3 text-sm leading-relaxed text-gray-700">
              {selectedRequest.agent_response || "Nessuna risposta registrata."}
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            <div className="rounded-2xl border border-gray-200 bg-[#fafaf7] px-4 py-3 text-sm text-gray-700">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Modulo</p>
              <p className="mt-2">{selectedRequest.module_key || "n/d"}</p>
            </div>
            <div className="rounded-2xl border border-gray-200 bg-[#fafaf7] px-4 py-3 text-sm text-gray-700">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Canale</p>
              <p className="mt-2">{selectedRequest.source_channel || "n/d"}</p>
            </div>
            <div className="rounded-2xl border border-gray-200 bg-[#fafaf7] px-4 py-3 text-sm text-gray-700">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Impatto</p>
              <p className="mt-2">{selectedRequest.impact_scope || "n/d"}</p>
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div className="rounded-2xl border border-gray-200 bg-[#fafaf7] px-4 py-3 text-sm text-gray-700">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Pagina</p>
              <p className="mt-2 break-all">{selectedRequest.page_path || "n/d"}</p>
            </div>
            <div className="rounded-2xl border border-gray-200 bg-[#fafaf7] px-4 py-3 text-sm text-gray-700">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Conversation ID</p>
              <p className="mt-2 break-all">{selectedRequest.conversation_id || "n/d"}</p>
            </div>
          </div>

          <WikiRequestDeliveryPanel
            externalTicketKey={selectedRequest.external_ticket_key}
            externalTicketUrl={selectedRequest.external_ticket_url}
            deliveryStatus={selectedRequest.delivery_status}
            draftExternalTicketKey={draftExternalTicketKey}
            draftExternalTicketUrl={draftExternalTicketUrl}
            draftDeliveryStatus={draftDeliveryStatus}
            draftDeliveryNotes={draftDeliveryNotes}
            deliveryStatusOptions={deliveryStatusOptions}
            onExternalTicketKeyChange={onExternalTicketKeyChange}
            onExternalTicketUrlChange={onExternalTicketUrlChange}
            onDeliveryStatusChange={onDeliveryStatusChange}
            onDeliveryNotesChange={onDeliveryNotesChange}
          />

          <WikiRequestArtifactsPanel
            artifacts={artifacts}
            artifactsLoading={artifactsLoading}
            screenshotPreviewUrl={screenshotPreviewUrl}
            downloadingArtifactId={downloadingArtifactId}
            onDownloadArtifact={onDownloadArtifact}
          />

          <div className="space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Deduplica casi simili</p>
              {selectedRequest.canonical_request_id ? (
                <span className="rounded-full border border-gray-200 bg-gray-50 px-2 py-1 text-[11px] text-gray-600">
                  Caso canonico collegato
                </span>
              ) : null}
            </div>
            {selectedRequest.canonical_request_id ? (
              <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
                <p className="font-medium">Questa richiesta e marcata come duplicata.</p>
                <p className="mt-1">
                  Caso canonico:{" "}
                  <a href={`/wiki/requests/${selectedRequest.canonical_request_id}`} className="font-medium underline underline-offset-2">
                    {selectedRequest.canonical_request_question || selectedRequest.canonical_request_id}
                  </a>
                  {selectedRequest.canonical_request_status ? ` · stato ${selectedRequest.canonical_request_status}` : ""}
                </p>
              </div>
            ) : null}
            <div className="rounded-2xl border border-gray-200 bg-[#fafaf7] p-3">
              <div className="mb-3 flex items-center justify-between gap-3">
                <div>
                  <p className="text-sm font-medium text-gray-900">Famiglia caso canonico</p>
                  <p className="text-xs text-gray-500">
                    Vista del gruppo casi gia accorpati sullo stesso filone con impatto e promotore attuale.
                  </p>
                </div>
                {family ? (
                  <div className="flex flex-wrap gap-2 text-[11px] text-gray-600">
                    <span className="rounded-full border border-gray-200 bg-white px-2 py-1">{family.family_size} casi</span>
                    <span className="rounded-full border border-gray-200 bg-white px-2 py-1">{family.affected_users} utenti</span>
                  </div>
                ) : null}
              </div>
              {family ? (
                <div className="mb-3 rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-3 text-sm text-emerald-950">
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">Caso canonico attuale</p>
                  <div className="mt-2 flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <p className="font-medium">{family.canonical_request.user_question}</p>
                      <p className="mt-1 text-xs text-emerald-800">
                        {family.canonical_request.created_by || "n/d"}
                        {family.canonical_request.module_key ? ` · modulo ${family.canonical_request.module_key}` : ""}
                        {family.latest_created_at ? ` · ultimo caso ${formatDateTime(family.latest_created_at)}` : ""}
                      </p>
                    </div>
                    <a
                      href={`/wiki/requests/${family.canonical_request.id}`}
                      className="rounded-full border border-emerald-200 bg-white px-3 py-1.5 text-xs font-medium text-emerald-800"
                    >
                      Apri canonico
                    </a>
                  </div>
                </div>
              ) : null}
              {linkedDuplicatesLoading ? (
                <p className="text-sm text-gray-500">Caricamento duplicati collegati...</p>
              ) : linkedDuplicates.length === 0 ? (
                <p className="text-sm text-gray-500">Nessun duplicato collegato al caso canonico.</p>
              ) : (
                <div className="space-y-3">
                  {linkedDuplicates.map((candidate) => (
                    <div key={candidate.id} className="rounded-xl border border-gray-100 bg-white px-3 py-3">
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div className="space-y-2">
                          <div className="flex flex-wrap items-center gap-2">
                            <span
                              className={`rounded-full border px-2 py-0.5 text-xs font-medium ${statusBadgeClasses(
                                candidate.status as WikiRequest["status"],
                              )}`}
                            >
                              {statusLabel(candidate.status as WikiRequest["status"])}
                            </span>
                            <span className="rounded-full border border-gray-200 bg-gray-50 px-2 py-0.5 text-xs text-gray-600">
                              {requestTypeLabel(candidate.request_type as WikiRequest["request_type"])}
                            </span>
                          </div>
                          <p className="text-sm font-medium text-gray-900">{candidate.user_question}</p>
                          <p className="text-xs text-gray-500">
                            {candidate.created_by || "n/d"}
                            {candidate.assigned_to_name ? ` · assegnata a ${candidate.assigned_to_name}` : ""}
                            {candidate.module_key ? ` · modulo ${candidate.module_key}` : ""}
                            {candidate.page_path ? ` · ${candidate.page_path}` : ""}
                          </p>
                        </div>
                        <div className="flex flex-wrap gap-2">
                          <a href={`/wiki/requests/${candidate.id}`} className="rounded-full border border-gray-200 px-3 py-1.5 text-xs font-medium text-gray-700">
                            Apri caso
                          </a>
                          {candidate.id !== selectedRequest.id ? (
                            <button
                              type="button"
                              onClick={() => void onUnlinkDuplicate(candidate.id)}
                              disabled={unlinkingDuplicateId === candidate.id}
                              className="rounded-full border border-rose-200 bg-rose-50 px-3 py-1.5 text-xs font-medium text-rose-700 transition hover:bg-rose-100 disabled:opacity-50"
                            >
                              {unlinkingDuplicateId === candidate.id ? "Sgancio..." : "Sgancia"}
                            </button>
                          ) : null}
                          <button
                            type="button"
                            onClick={() => void onMakeCanonical(candidate.id)}
                            disabled={promotingCanonicalId === candidate.id}
                            className="rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-xs font-medium text-emerald-800 transition hover:bg-emerald-100 disabled:opacity-50"
                          >
                            {promotingCanonicalId === candidate.id ? "Aggiorno..." : "Rendi canonico"}
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
            <div className="rounded-2xl border border-gray-200 bg-[#fafaf7] p-3">
              {duplicatesLoading ? (
                <p className="text-sm text-gray-500">Sto cercando richieste simili...</p>
              ) : duplicates.length === 0 ? (
                <p className="text-sm text-gray-500">Nessun caso simile abbastanza vicino nel backlog corrente.</p>
              ) : (
                <div className="space-y-3">
                  {duplicates.map((candidate) => (
                    <div key={candidate.id} className="rounded-xl border border-gray-100 bg-white px-3 py-3">
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div className="space-y-2">
                          <div className="flex flex-wrap items-center gap-2">
                            <span
                              className={`rounded-full border px-2 py-0.5 text-xs font-medium ${statusBadgeClasses(
                                candidate.status as WikiRequest["status"],
                              )}`}
                            >
                              {statusLabel(candidate.status as WikiRequest["status"])}
                            </span>
                            <span className="rounded-full border border-gray-200 bg-gray-50 px-2 py-0.5 text-xs text-gray-600">
                              {requestTypeLabel(candidate.request_type as WikiRequest["request_type"])}
                            </span>
                            <span className="text-xs text-gray-400">{Math.round(candidate.similarity_score * 100)}% match</span>
                          </div>
                          <p className="text-sm font-medium text-gray-900">{candidate.user_question}</p>
                          <p className="text-xs text-gray-500">
                            {candidate.match_reason}
                            {candidate.module_key ? ` · modulo ${candidate.module_key}` : ""}
                            {candidate.page_path ? ` · ${candidate.page_path}` : ""}
                          </p>
                          <p className="text-xs text-gray-400">
                            {candidate.created_by || "n/d"}
                            {candidate.assigned_to_name ? ` · assegnata a ${candidate.assigned_to_name}` : ""}
                            {` · ${formatDateTime(candidate.created_at)}`}
                          </p>
                        </div>
                        <div className="flex flex-wrap gap-2">
                          <a href={`/wiki/requests/${candidate.id}`} className="rounded-full border border-gray-200 px-3 py-1.5 text-xs font-medium text-gray-700">
                            Apri caso
                          </a>
                          <button
                            type="button"
                            onClick={() => void onMarkDuplicate(candidate.id)}
                            disabled={markingDuplicateId === candidate.id}
                            className="rounded-full bg-[#1D4E35] px-3 py-1.5 text-xs font-medium text-white transition hover:bg-[#163d29] disabled:opacity-50"
                          >
                            {markingDuplicateId === candidate.id ? "Collegamento..." : "Segna come duplicata"}
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {selectedRequest.desired_outcome || selectedRequest.observed_behavior || selectedRequest.expected_behavior ? (
            <div className="grid gap-4 xl:grid-cols-3">
              <div className="rounded-2xl border border-gray-200 bg-[#fafaf7] px-4 py-3 text-sm text-gray-700">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Comportamento osservato</p>
                <p className="mt-2 whitespace-pre-wrap">{selectedRequest.observed_behavior || "n/d"}</p>
              </div>
              <div className="rounded-2xl border border-gray-200 bg-[#fafaf7] px-4 py-3 text-sm text-gray-700">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Comportamento atteso</p>
                <p className="mt-2 whitespace-pre-wrap">{selectedRequest.expected_behavior || "n/d"}</p>
              </div>
              <div className="rounded-2xl border border-gray-200 bg-[#fafaf7] px-4 py-3 text-sm text-gray-700">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Esito desiderato</p>
                <p className="mt-2 whitespace-pre-wrap">{selectedRequest.desired_outcome || "n/d"}</p>
              </div>
            </div>
          ) : null}

          {selectedRequest.user_feedback_submitted_at || selectedRequest.user_feedback_notes ? (
            <div className="rounded-2xl border border-violet-200 bg-violet-50 px-4 py-4 text-sm text-violet-950">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-violet-700">Feedback utente</p>
              <p className="mt-2 font-medium">
                {selectedRequest.user_feedback_rating === "helpful" ? "Utile / risolto" : "Non risolto / incompleto"}
              </p>
              {selectedRequest.user_feedback_notes ? <p className="mt-2 whitespace-pre-wrap">{selectedRequest.user_feedback_notes}</p> : null}
              <p className="mt-2 text-xs text-violet-700">Inviato {formatDateTime(selectedRequest.user_feedback_submitted_at ?? selectedRequest.updated_at)}</p>
            </div>
          ) : null}

          <div className="grid gap-4 md:grid-cols-2">
            <label className="space-y-2">
              <span className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Stato</span>
              <select
                value={draftStatus}
                onChange={(event) => onDraftStatusChange(event.target.value as WikiRequest["status"])}
                className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm text-gray-700 outline-none transition focus:border-[#1D4E35] focus:ring-2 focus:ring-[#1D4E35]/10"
              >
                {statusOptions.filter((option) => option.value !== "all").map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
            <div className="space-y-2">
              <span className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Ultimo aggiornamento</span>
              <div className="rounded-xl border border-gray-200 bg-[#fafaf7] px-3 py-2 text-sm text-gray-700">
                {formatDateTime(selectedRequest.updated_at)}
              </div>
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-3">
            <label className="space-y-2">
              <span className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Priorita</span>
              <select
                value={draftPriority}
                onChange={(event) => onDraftPriorityChange(event.target.value as WikiRequest["priority"])}
                className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm text-gray-700 outline-none transition focus:border-[#1D4E35] focus:ring-2 focus:ring-[#1D4E35]/10"
              >
                {priorityOptions.filter((option) => option.value !== "all").map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="space-y-2">
              <span className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Severita</span>
              <select
                value={draftSeverity}
                onChange={(event) => onDraftSeverityChange(event.target.value as WikiRequest["severity"])}
                className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm text-gray-700 outline-none transition focus:border-[#1D4E35] focus:ring-2 focus:ring-[#1D4E35]/10"
              >
                {severityOptions.filter((option) => option.value !== "all").map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="space-y-2">
              <span className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Assegnatario</span>
              <select
                value={draftAssignedTo}
                onChange={(event) => onDraftAssignedToChange(event.target.value)}
                className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm text-gray-700 outline-none transition focus:border-[#1D4E35] focus:ring-2 focus:ring-[#1D4E35]/10"
              >
                <option value="">Non assegnata</option>
                {assignees.map((assignee) => (
                  <option key={assignee.username} value={assignee.username}>
                    {(assignee.full_name || assignee.username) + ` · ${assignee.role}`}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <label className="block space-y-2">
            <span className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Messaggio per l&apos;utente</span>
            <textarea
              value={draftResolutionMessage}
              onChange={(event) => onDraftResolutionMessageChange(event.target.value)}
              rows={4}
              placeholder="Sintetizza in modo leggibile cosa e stato verificato, deciso o risolto."
              className="w-full rounded-2xl border border-gray-200 px-3 py-3 text-sm text-gray-700 outline-none transition focus:border-[#1D4E35] focus:ring-2 focus:ring-[#1D4E35]/10"
            />
          </label>

          <label className="block space-y-2">
            <span className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Note admin</span>
            <textarea
              value={draftNotes}
              onChange={(event) => onDraftNotesChange(event.target.value)}
              rows={7}
              placeholder="Aggiungi il motivo della decisione, riferimento ticket o prossimi passi."
              className="w-full rounded-2xl border border-gray-200 px-3 py-3 text-sm text-gray-700 outline-none transition focus:border-[#1D4E35] focus:ring-2 focus:ring-[#1D4E35]/10"
            />
          </label>

          <div className="space-y-2">
            <span className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Timeline caso</span>
            <div className="rounded-2xl border border-gray-200 bg-[#fafaf7] p-3">
              {timelineLoading ? (
                <p className="text-sm text-gray-500">Caricamento timeline...</p>
              ) : timeline.length === 0 ? (
                <p className="text-sm text-gray-500">Nessun evento registrato.</p>
              ) : (
                <div className="space-y-3">
                  {timeline.map((event) => (
                    <div key={event.id} className="rounded-xl border border-gray-100 bg-white px-3 py-3">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <p className="text-sm font-medium text-gray-900">{event.event_type.replaceAll("_", " ")}</p>
                        <span className="text-xs text-gray-400">{formatDateTime(event.created_at)}</span>
                      </div>
                      <p className="mt-1 text-xs text-gray-500">
                        {event.actor_username || "sistema"}
                        {event.from_status || event.to_status ? ` · ${event.from_status || "n/d"} → ${event.to_status || "n/d"}` : ""}
                      </p>
                      {event.payload ? (
                        <div className="mt-2 flex flex-wrap gap-2">
                          {Object.entries(event.payload).map(([key, value]) => (
                            <span key={key} className="rounded-full border border-gray-200 bg-gray-50 px-2 py-1 text-[11px] text-gray-600">
                              {key}: {String(value)}
                            </span>
                          ))}
                        </div>
                      ) : null}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="space-y-1 text-xs">
              {error ? <p className="text-red-600">{error}</p> : null}
              {successMessage ? <p className="text-green-600">{successMessage}</p> : null}
            </div>
            <button
              type="button"
              onClick={onSave}
              disabled={saving}
              className="rounded-full bg-[#1D4E35] px-4 py-2 text-sm font-medium text-white transition hover:bg-[#163d29] disabled:opacity-50"
            >
              {saving ? "Salvataggio..." : "Salva aggiornamento"}
            </button>
          </div>
        </div>
      ) : (
        <EmptyState icon={SearchIcon} title="Seleziona una richiesta" description="Apri un elemento dalla coda per aggiornare stato e note." />
      )}
    </article>
  );
}
