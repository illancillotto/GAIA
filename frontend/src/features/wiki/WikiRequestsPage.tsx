"use client";

import { useDeferredValue, useEffect, useMemo, useState } from "react";

import { EmptyState } from "@/components/ui/empty-state";
import { MetricCard } from "@/components/ui/metric-card";
import { SearchIcon } from "@/components/ui/icons";
import {
  downloadWikiRequestArtifact,
  getWikiRequestAssignees,
  getWikiRequestArtifacts,
  getWikiRequestDuplicates,
  getWikiRequestEvents,
  getWikiRequestFamily,
  getWikiRequestLinkedDuplicates,
  getWikiRequests,
  makeWikiRequestCanonical,
  markWikiRequestDuplicate,
  unlinkWikiRequestDuplicate,
  updateWikiRequest,
} from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import type { WikiRequest, WikiRequestArtifact, WikiRequestAssignee, WikiRequestDuplicateCandidate, WikiRequestEvent, WikiRequestFamily } from "@/types/api";

type RequestStatusFilter = "all" | "new" | "triaged" | "investigating" | "waiting_user" | "planned" | "resolved" | "duplicate" | "rejected";
type RequestCategoryFilter = "all" | "feature_request" | "bug_report" | "question" | "support_request";
type RequestPriorityFilter = "all" | "low" | "medium" | "high" | "urgent";
type RequestTypeFilter = "all" | "help_request" | "bug_report" | "feature_request" | "access_issue" | "data_issue" | "other_request";
type RequestSeverityFilter = "all" | "low" | "medium" | "high" | "critical";

const statusOptions: Array<{ value: RequestStatusFilter; label: string }> = [
  { value: "all", label: "Tutti gli stati" },
  { value: "new", label: "Nuova" },
  { value: "triaged", label: "Triaged" },
  { value: "investigating", label: "Investigating" },
  { value: "waiting_user", label: "Waiting user" },
  { value: "planned", label: "Planned" },
  { value: "resolved", label: "Resolved" },
  { value: "duplicate", label: "Duplicate" },
  { value: "rejected", label: "Rejected" },
];

const categoryOptions: Array<{ value: RequestCategoryFilter; label: string }> = [
  { value: "all", label: "Tutte le categorie" },
  { value: "feature_request", label: "Feature request" },
  { value: "bug_report", label: "Bug report" },
  { value: "question", label: "Question" },
  { value: "support_request", label: "Support request" },
];

const requestTypeOptions: Array<{ value: RequestTypeFilter; label: string }> = [
  { value: "all", label: "Tutti i tipi" },
  { value: "help_request", label: "Supporto operativo" },
  { value: "bug_report", label: "Problema / anomalia" },
  { value: "feature_request", label: "Nuova funzionalità" },
  { value: "access_issue", label: "Problema di accesso" },
  { value: "data_issue", label: "Problema dati" },
  { value: "other_request", label: "Altro" },
];

const priorityOptions: Array<{ value: RequestPriorityFilter; label: string }> = [
  { value: "all", label: "Tutte le priorità" },
  { value: "low", label: "Bassa" },
  { value: "medium", label: "Media" },
  { value: "high", label: "Alta" },
  { value: "urgent", label: "Urgente" },
];

const severityOptions: Array<{ value: RequestSeverityFilter; label: string }> = [
  { value: "all", label: "Tutte le severità" },
  { value: "low", label: "Bassa" },
  { value: "medium", label: "Media" },
  { value: "high", label: "Alta" },
  { value: "critical", label: "Critica" },
];

function statusBadgeClasses(status: WikiRequest["status"]): string {
  switch (status) {
    case "resolved":
      return "border-green-200 bg-green-50 text-green-700";
    case "planned":
      return "border-blue-200 bg-blue-50 text-blue-700";
    case "triaged":
      return "border-amber-200 bg-amber-50 text-amber-700";
    case "investigating":
      return "border-orange-200 bg-orange-50 text-orange-700";
    case "waiting_user":
      return "border-violet-200 bg-violet-50 text-violet-700";
    case "duplicate":
      return "border-gray-200 bg-gray-50 text-gray-700";
    case "rejected":
      return "border-rose-200 bg-rose-50 text-rose-700";
    default:
      return "border-emerald-200 bg-emerald-50 text-emerald-700";
  }
}

function statusLabel(status: WikiRequest["status"]): string {
  if (status === "new") return "Nuova";
  if (status === "triaged") return "Triaged";
  if (status === "investigating") return "Investigating";
  if (status === "waiting_user") return "Waiting user";
  if (status === "planned") return "Planned";
  if (status === "resolved") return "Resolved";
  if (status === "duplicate") return "Duplicate";
  if (status === "rejected") return "Rejected";
  return status;
}

function categoryLabel(category: WikiRequest["category"]): string {
  if (category === "feature_request") return "Feature request";
  if (category === "bug_report") return "Bug report";
  if (category === "question") return "Question";
  if (category === "support_request") return "Support request";
  return category;
}

function requestTypeLabel(requestType: WikiRequest["request_type"]): string {
  if (requestType === "help_request") return "Supporto operativo";
  if (requestType === "bug_report") return "Problema / anomalia";
  if (requestType === "feature_request") return "Nuova funzionalità";
  if (requestType === "access_issue") return "Problema di accesso";
  if (requestType === "data_issue") return "Problema dati";
  if (requestType === "other_request") return "Altro";
  return requestType;
}

function priorityBadgeClasses(priority: WikiRequest["priority"]): string {
  switch (priority) {
    case "urgent":
      return "border-red-200 bg-red-50 text-red-700";
    case "high":
      return "border-amber-200 bg-amber-50 text-amber-700";
    case "low":
      return "border-gray-200 bg-gray-50 text-gray-600";
    default:
      return "border-blue-200 bg-blue-50 text-blue-700";
  }
}

function priorityLabel(priority: WikiRequest["priority"]): string {
  if (priority === "low") return "Bassa";
  if (priority === "medium") return "Media";
  if (priority === "high") return "Alta";
  if (priority === "urgent") return "Urgente";
  return priority;
}

function severityBadgeClasses(severity: WikiRequest["severity"]): string {
  switch (severity) {
    case "critical":
      return "border-red-200 bg-red-50 text-red-700";
    case "high":
      return "border-amber-200 bg-amber-50 text-amber-700";
    case "low":
      return "border-gray-200 bg-gray-50 text-gray-600";
    default:
      return "border-blue-200 bg-blue-50 text-blue-700";
  }
}

function severityLabel(severity: WikiRequest["severity"]): string {
  if (severity === "low") return "Bassa";
  if (severity === "medium") return "Media";
  if (severity === "high") return "Alta";
  if (severity === "critical") return "Critica";
  return severity;
}

function formatDateTime(value: string): string {
  try {
    return new Intl.DateTimeFormat("it-IT", {
      dateStyle: "short",
      timeStyle: "short",
    }).format(new Date(value));
  } catch {
    return value;
  }
}

function formatSnapshotValue(value: unknown): string {
  if (value == null) return "n/d";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  if (Array.isArray(value)) return value.map((item) => formatSnapshotValue(item)).join(", ");
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}

function humanizeSnapshotKey(value: string): string {
  return value
    .replaceAll("_", " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

export function WikiRequestsPage({ supportOnly = false, initialRequestId = null }: { supportOnly?: boolean; initialRequestId?: string | null }) {
  const [items, setItems] = useState<WikiRequest[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<RequestStatusFilter>("all");
  const [categoryFilter, setCategoryFilter] = useState<RequestCategoryFilter>("all");
  const [requestTypeFilter, setRequestTypeFilter] = useState<RequestTypeFilter>("all");
  const [priorityFilter, setPriorityFilter] = useState<RequestPriorityFilter>("all");
  const [severityFilter, setSeverityFilter] = useState<RequestSeverityFilter>("all");
  const [query, setQuery] = useState("");
  const [draftStatus, setDraftStatus] = useState<WikiRequest["status"]>("new");
  const [draftPriority, setDraftPriority] = useState<WikiRequest["priority"]>("medium");
  const [draftSeverity, setDraftSeverity] = useState<WikiRequest["severity"]>("medium");
  const [draftAssignedTo, setDraftAssignedTo] = useState("");
  const [draftResolutionMessage, setDraftResolutionMessage] = useState("");
  const [draftNotes, setDraftNotes] = useState("");
  const [assignees, setAssignees] = useState<WikiRequestAssignee[]>([]);
  const [timeline, setTimeline] = useState<WikiRequestEvent[]>([]);
  const [artifacts, setArtifacts] = useState<WikiRequestArtifact[]>([]);
  const [duplicates, setDuplicates] = useState<WikiRequestDuplicateCandidate[]>([]);
  const [family, setFamily] = useState<WikiRequestFamily | null>(null);
  const [linkedDuplicates, setLinkedDuplicates] = useState<WikiRequestDuplicateCandidate[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [timelineLoading, setTimelineLoading] = useState(false);
  const [artifactsLoading, setArtifactsLoading] = useState(false);
  const [duplicatesLoading, setDuplicatesLoading] = useState(false);
  const [linkedDuplicatesLoading, setLinkedDuplicatesLoading] = useState(false);
  const [markingDuplicateId, setMarkingDuplicateId] = useState<string | null>(null);
  const [promotingCanonicalId, setPromotingCanonicalId] = useState<string | null>(null);
  const [unlinkingDuplicateId, setUnlinkingDuplicateId] = useState<string | null>(null);
  const [downloadingArtifactId, setDownloadingArtifactId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [screenshotPreviewUrl, setScreenshotPreviewUrl] = useState<string | null>(null);

  const deferredQuery = useDeferredValue(query.trim().toLowerCase());

  useEffect(() => {
    async function loadRequests() {
      const token = getStoredAccessToken();
      if (!token) {
        setError("Sessione non disponibile.");
        setItems([]);
        setLoading(false);
        return;
      }

      setLoading(true);
      try {
        const [requestsResponse, assigneesResponse] = await Promise.all([
          getWikiRequests(token),
          getWikiRequestAssignees(token),
        ]);
        setItems(requestsResponse);
        setAssignees(assigneesResponse);
        setSelectedId((current) => current ?? initialRequestId ?? requestsResponse[0]?.id ?? null);
        setError(null);
      } catch (loadError) {
        setItems([]);
        setAssignees([]);
        setSelectedId(null);
        setError(loadError instanceof Error ? loadError.message : "Errore caricamento richieste Wiki");
      } finally {
        setLoading(false);
      }
    }

    void loadRequests();
  }, [initialRequestId]);

  const filteredItems = useMemo(() => {
    return items.filter((item) => {
      if (supportOnly && !["help_request", "bug_report", "access_issue", "data_issue", "other_request"].includes(item.request_type)) {
        return false;
      }
      if (statusFilter !== "all" && item.status !== statusFilter) {
        return false;
      }
      if (categoryFilter !== "all" && item.category !== categoryFilter) {
        return false;
      }
      if (requestTypeFilter !== "all" && item.request_type !== requestTypeFilter) {
        return false;
      }
      if (priorityFilter !== "all" && item.priority !== priorityFilter) {
        return false;
      }
      if (severityFilter !== "all" && item.severity !== severityFilter) {
        return false;
      }
      if (!deferredQuery) {
        return true;
      }
      const haystack = [
        item.user_question,
        item.agent_response ?? "",
        item.created_by ?? "",
        item.admin_notes ?? "",
        item.assigned_to ?? "",
        item.assigned_to_name ?? "",
        item.module_key ?? "",
        item.request_type,
        item.page_path ?? "",
        item.severity,
        item.source_channel,
        item.category,
        item.status,
        item.priority,
      ]
        .join(" ")
        .toLowerCase();
      return haystack.includes(deferredQuery);
    });
  }, [items, supportOnly, statusFilter, categoryFilter, requestTypeFilter, priorityFilter, severityFilter, deferredQuery]);

  const selectedRequest = useMemo(
    () => filteredItems.find((item) => item.id === selectedId) ?? items.find((item) => item.id === selectedId) ?? null,
    [filteredItems, items, selectedId],
  );
  const uiSnapshotArtifact = useMemo(
    () => artifacts.find((item) => item.artifact_type === "ui_snapshot") ?? null,
    [artifacts],
  );
  const screenshotArtifact = useMemo(
    () => artifacts.find((item) => item.artifact_type === "screenshot") ?? null,
    [artifacts],
  );
  const screenshotMetaArtifact = useMemo(
    () => artifacts.find((item) => item.artifact_type === "screenshot_meta") ?? null,
    [artifacts],
  );
  const moduleSnapshot = useMemo(() => {
    const payload = uiSnapshotArtifact?.payload;
    if (!payload || typeof payload !== "object" || !("module_snapshot" in payload)) {
      return null;
    }
    const value = payload.module_snapshot;
    return value && typeof value === "object" ? (value as Record<string, unknown>) : null;
  }, [uiSnapshotArtifact]);
  const moduleSnapshotEntity = useMemo(() => {
    const entity = moduleSnapshot?.entity;
    return entity && typeof entity === "object" ? (entity as Record<string, unknown>) : null;
  }, [moduleSnapshot]);
  const moduleSnapshotFilters = useMemo(() => {
    const filters = moduleSnapshot?.filters;
    return filters && typeof filters === "object" ? (filters as Record<string, unknown>) : null;
  }, [moduleSnapshot]);
  const moduleSnapshotActiveTabs = useMemo(() => {
    const tabs = moduleSnapshot?.active_tabs;
    return Array.isArray(tabs) ? tabs : [];
  }, [moduleSnapshot]);

  useEffect(() => {
    if (!selectedRequest) {
      if (filteredItems[0]) {
        setSelectedId(filteredItems[0].id);
      }
      return;
    }
    setDraftStatus(selectedRequest.status);
    setDraftPriority(selectedRequest.priority);
    setDraftSeverity(selectedRequest.severity);
    setDraftAssignedTo(selectedRequest.assigned_to ?? "");
    setDraftResolutionMessage(selectedRequest.resolution_message ?? "");
    setDraftNotes(selectedRequest.admin_notes ?? "");
    setSuccessMessage(null);
  }, [selectedRequest, filteredItems]);

  const scopedItems = useMemo(
    () => (supportOnly ? items.filter((item) => ["help_request", "bug_report", "access_issue", "data_issue", "other_request"].includes(item.request_type)) : items),
    [items, supportOnly],
  );

  const summary = useMemo(() => {
    return {
      total: scopedItems.length,
      newCount: scopedItems.filter((item) => item.status === "new").length,
      triaged: scopedItems.filter((item) => item.status === "triaged").length,
      planned: scopedItems.filter((item) => item.status === "planned").length,
      urgent: scopedItems.filter((item) => item.priority === "urgent").length,
      resolved: scopedItems.filter((item) => item.status === "resolved").length,
    };
  }, [scopedItems]);

  useEffect(() => {
    return () => {
      if (screenshotPreviewUrl) {
        URL.revokeObjectURL(screenshotPreviewUrl);
      }
    };
  }, [screenshotPreviewUrl]);

  useEffect(() => {
    async function loadTimeline() {
      if (!selectedRequest) {
        setTimeline([]);
        return;
      }
      const token = getStoredAccessToken();
      if (!token) {
        setTimeline([]);
        return;
      }
      setTimelineLoading(true);
      try {
        const items = await getWikiRequestEvents(token, selectedRequest.id);
        setTimeline(items);
      } catch {
        setTimeline([]);
      } finally {
        setTimelineLoading(false);
      }
    }
    void loadTimeline();
  }, [selectedRequest]);

  useEffect(() => {
    async function loadArtifacts() {
      if (!selectedRequest) {
        setArtifacts([]);
        setScreenshotPreviewUrl((current) => {
          if (current) URL.revokeObjectURL(current);
          return null;
        });
        return;
      }
      const token = getStoredAccessToken();
      if (!token) {
        setArtifacts([]);
        return;
      }
      setArtifactsLoading(true);
      try {
        const items = await getWikiRequestArtifacts(token, selectedRequest.id);
        setArtifacts(items);
        const screenshotArtifact = items.find((item) => item.artifact_type === "screenshot");
        if (screenshotArtifact) {
          const blob = await downloadWikiRequestArtifact(token, selectedRequest.id, screenshotArtifact.id);
          const previewUrl = URL.createObjectURL(blob);
          setScreenshotPreviewUrl((current) => {
            if (current) URL.revokeObjectURL(current);
            return previewUrl;
          });
        } else {
          setScreenshotPreviewUrl((current) => {
            if (current) URL.revokeObjectURL(current);
            return null;
          });
        }
      } catch {
        setArtifacts([]);
        setScreenshotPreviewUrl((current) => {
          if (current) URL.revokeObjectURL(current);
          return null;
        });
      } finally {
        setArtifactsLoading(false);
      }
    }
    void loadArtifacts();
  }, [selectedRequest]);

  useEffect(() => {
    async function loadDuplicates() {
      if (!selectedRequest) {
        setDuplicates([]);
        return;
      }
      const token = getStoredAccessToken();
      if (!token) {
        setDuplicates([]);
        return;
      }
      setDuplicatesLoading(true);
      try {
        const items = await getWikiRequestDuplicates(token, selectedRequest.id);
        setDuplicates(items);
      } catch {
        setDuplicates([]);
      } finally {
        setDuplicatesLoading(false);
      }
    }
    void loadDuplicates();
  }, [selectedRequest]);

  useEffect(() => {
    async function loadLinkedDuplicates() {
      if (!selectedRequest) {
        setFamily(null);
        setLinkedDuplicates([]);
        return;
      }
      const token = getStoredAccessToken();
      if (!token) {
        setLinkedDuplicates([]);
        return;
      }
      setLinkedDuplicatesLoading(true);
      try {
        const [familyResponse, items] = await Promise.all([
          getWikiRequestFamily(token, selectedRequest.id),
          getWikiRequestLinkedDuplicates(token, selectedRequest.id),
        ]);
        setFamily(familyResponse);
        setLinkedDuplicates(items);
      } catch {
        setFamily(null);
        setLinkedDuplicates([]);
      } finally {
        setLinkedDuplicatesLoading(false);
      }
    }
    void loadLinkedDuplicates();
  }, [selectedRequest]);

  async function handleSave() {
    if (!selectedRequest) {
      return;
    }
    const token = getStoredAccessToken();
    if (!token) {
      setError("Sessione non disponibile.");
      return;
    }

    setSaving(true);
    setSuccessMessage(null);
    try {
      const updated = await updateWikiRequest(token, selectedRequest.id, {
        status: draftStatus,
        priority: draftPriority as "low" | "medium" | "high" | "urgent",
        severity: draftSeverity as "low" | "medium" | "high" | "critical",
        assigned_to: draftAssignedTo || null,
        resolution_message: draftResolutionMessage || null,
        admin_notes: draftNotes || null,
      });
      setItems((current) => current.map((item) => (item.id === updated.id ? updated : item)));
      setSuccessMessage("Richiesta aggiornata.");
      setError(null);
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Errore aggiornamento richiesta Wiki");
    } finally {
      setSaving(false);
    }
  }

  async function handleMarkDuplicate(candidateId: string) {
    if (!selectedRequest) {
      return;
    }
    const token = getStoredAccessToken();
    if (!token) {
      setError("Sessione non disponibile.");
      return;
    }

    setMarkingDuplicateId(candidateId);
    setSuccessMessage(null);
    try {
      const updated = await markWikiRequestDuplicate(token, selectedRequest.id, {
        canonical_request_id: candidateId,
        admin_notes: draftNotes || null,
      });
      setItems((current) => current.map((item) => (item.id === updated.id ? updated : item)));
      setDraftStatus(updated.status);
      setSuccessMessage("Richiesta collegata al caso canonico.");
      const [eventsResponse, duplicatesResponse, linkedResponse] = await Promise.all([
        getWikiRequestEvents(token, updated.id),
        getWikiRequestDuplicates(token, updated.id),
        getWikiRequestLinkedDuplicates(token, updated.id),
      ]);
      const familyResponse = await getWikiRequestFamily(token, updated.id);
      setTimeline(eventsResponse);
      setDuplicates(duplicatesResponse);
      setLinkedDuplicates(linkedResponse);
      setFamily(familyResponse);
      setError(null);
    } catch (markError) {
      setError(markError instanceof Error ? markError.message : "Errore collegamento duplicato");
    } finally {
      setMarkingDuplicateId(null);
    }
  }

  async function handleUnlinkDuplicate(requestId: string) {
    const token = getStoredAccessToken();
    if (!token) {
      setError("Sessione non disponibile.");
      return;
    }

    setUnlinkingDuplicateId(requestId);
    setSuccessMessage(null);
    try {
      const updated = await unlinkWikiRequestDuplicate(token, requestId);
      setItems((current) => current.map((item) => (item.id === updated.id ? updated : item)));
      if (selectedRequest?.id === updated.id) {
        setDraftStatus(updated.status);
      }
      const [eventsResponse, duplicatesResponse, linkedResponse] = await Promise.all([
        selectedRequest ? getWikiRequestEvents(token, selectedRequest.id) : Promise.resolve([]),
        selectedRequest ? getWikiRequestDuplicates(token, selectedRequest.id) : Promise.resolve([]),
        selectedRequest ? getWikiRequestLinkedDuplicates(token, selectedRequest.id) : Promise.resolve([]),
      ]);
      const familyResponse = selectedRequest ? await getWikiRequestFamily(token, selectedRequest.id) : null;
      setTimeline(eventsResponse);
      setDuplicates(duplicatesResponse);
      setLinkedDuplicates(linkedResponse);
      setFamily(familyResponse);
      setSuccessMessage("Duplicato sganciato dal caso canonico.");
      setError(null);
    } catch (unlinkError) {
      setError(unlinkError instanceof Error ? unlinkError.message : "Errore nello sgancio del duplicato");
    } finally {
      setUnlinkingDuplicateId(null);
    }
  }

  async function handleMakeCanonical(requestId: string) {
    const token = getStoredAccessToken();
    if (!token) {
      setError("Sessione non disponibile.");
      return;
    }

    setPromotingCanonicalId(requestId);
    setSuccessMessage(null);
    try {
      const familyResponse = await makeWikiRequestCanonical(token, requestId, {
        admin_notes: draftNotes || null,
      });
      setFamily(familyResponse);
      setLinkedDuplicates(familyResponse.linked_duplicates);
      setItems((current) =>
        current.map((item) => {
          if (item.id === familyResponse.canonical_request.id) {
            return familyResponse.canonical_request;
          }
          if (item.id === requestId) {
            return familyResponse.canonical_request;
          }
          if (item.id === selectedRequest?.id && item.id !== familyResponse.canonical_request.id) {
            return {
              ...item,
              status: "duplicate",
              canonical_request_id: familyResponse.canonical_request.id,
              canonical_request_question: familyResponse.canonical_request.user_question,
              canonical_request_status: familyResponse.canonical_request.status,
            };
          }
          return item;
        }),
      );
      setSelectedId(familyResponse.canonical_request.id);
      const [eventsResponse, duplicatesResponse] = await Promise.all([
        getWikiRequestEvents(token, familyResponse.canonical_request.id),
        getWikiRequestDuplicates(token, familyResponse.canonical_request.id),
      ]);
      setTimeline(eventsResponse);
      setDuplicates(duplicatesResponse);
      setSuccessMessage("Caso canonico aggiornato.");
      setError(null);
    } catch (promoteError) {
      setError(promoteError instanceof Error ? promoteError.message : "Errore nel cambio del caso canonico");
    } finally {
      setPromotingCanonicalId(null);
    }
  }

  async function handleDownloadArtifact(artifact: WikiRequestArtifact) {
    if (!selectedRequest) {
      return;
    }
    const token = getStoredAccessToken();
    if (!token) {
      setError("Sessione non disponibile.");
      return;
    }

    setDownloadingArtifactId(artifact.id);
    setError(null);
    setSuccessMessage(null);
    try {
      if (artifact.artifact_type === "ui_snapshot" || artifact.artifact_type === "screenshot_meta") {
        const payload = artifact.payload ?? {};
        const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json;charset=utf-8" });
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = `${artifact.artifact_type}-${selectedRequest.id}.json`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
      } else {
        const blob = await downloadWikiRequestArtifact(token, selectedRequest.id, artifact.id);
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = artifact.filename || `${artifact.artifact_type}-${selectedRequest.id}`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
      }
      setSuccessMessage("Artifact scaricato.");
    } catch (downloadError) {
      setError(downloadError instanceof Error ? downloadError.message : "Errore download artifact");
    } finally {
      setDownloadingArtifactId(null);
    }
  }

  if (error && !loading && items.length === 0) {
    return <EmptyState icon={SearchIcon} title="Richieste Wiki non disponibili" description={error} />;
  }

  return (
    <div className="space-y-6">
      <section className="grid gap-4 md:grid-cols-3 xl:grid-cols-5">
        <MetricCard label="Totale richieste" value={summary.total.toString()} sub="storico registrato" />
        <MetricCard label="Nuove" value={summary.newCount.toString()} sub="da prendere in carico" />
        <MetricCard label="Triaged" value={summary.triaged.toString()} sub="qualificate" />
        <MetricCard label="Urgenti" value={summary.urgent.toString()} sub="da trattare subito" />
        <MetricCard label="Planned" value={summary.planned.toString()} sub="in roadmap" />
        <MetricCard label="Resolved" value={summary.resolved.toString()} sub="chiuse" />
      </section>

      <section className="rounded-3xl border border-[#d9dfd4] bg-white p-5 shadow-sm">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Governance richieste</p>
            <h2 className="mt-1 text-xl font-semibold text-gray-900">{supportOnly ? "Inbox supporto Wiki" : "Richieste registrate dal Wiki"}</h2>
            <p className="mt-1 text-sm text-gray-500">
              {supportOnly
                ? "Coda operativa su supporto, anomalie, accesso e problemi dati generati dal Wiki."
                : "Le richieste vengono generate dai fallback `found=false` del widget e della pagina Wiki."}
            </p>
          </div>
          <div className="grid gap-3 md:grid-cols-6">
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Cerca per testo, autore o note"
              className="rounded-xl border border-gray-200 px-3 py-2 text-sm text-gray-700 outline-none transition focus:border-[#1D4E35] focus:ring-2 focus:ring-[#1D4E35]/10"
            />
            <select
              value={statusFilter}
              onChange={(event) => setStatusFilter(event.target.value as RequestStatusFilter)}
              className="rounded-xl border border-gray-200 px-3 py-2 text-sm text-gray-700 outline-none transition focus:border-[#1D4E35] focus:ring-2 focus:ring-[#1D4E35]/10"
            >
              {statusOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
            <select
              value={categoryFilter}
              onChange={(event) => setCategoryFilter(event.target.value as RequestCategoryFilter)}
              className="rounded-xl border border-gray-200 px-3 py-2 text-sm text-gray-700 outline-none transition focus:border-[#1D4E35] focus:ring-2 focus:ring-[#1D4E35]/10"
            >
              {categoryOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
            <select
              value={priorityFilter}
              onChange={(event) => setPriorityFilter(event.target.value as RequestPriorityFilter)}
              className="rounded-xl border border-gray-200 px-3 py-2 text-sm text-gray-700 outline-none transition focus:border-[#1D4E35] focus:ring-2 focus:ring-[#1D4E35]/10"
            >
              {priorityOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
            <select
              value={requestTypeFilter}
              onChange={(event) => setRequestTypeFilter(event.target.value as RequestTypeFilter)}
              className="rounded-xl border border-gray-200 px-3 py-2 text-sm text-gray-700 outline-none transition focus:border-[#1D4E35] focus:ring-2 focus:ring-[#1D4E35]/10"
            >
              {requestTypeOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
            <select
              value={severityFilter}
              onChange={(event) => setSeverityFilter(event.target.value as RequestSeverityFilter)}
              className="rounded-xl border border-gray-200 px-3 py-2 text-sm text-gray-700 outline-none transition focus:border-[#1D4E35] focus:ring-2 focus:ring-[#1D4E35]/10"
            >
              {severityOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-[minmax(0,1.1fr)_minmax(24rem,0.9fr)]">
        <article className="rounded-3xl border border-[#d9dfd4] bg-white p-4 shadow-sm">
          <div className="flex items-center justify-between gap-3 border-b border-gray-100 pb-3">
            <div>
              <p className="text-sm font-semibold text-gray-900">Coda richieste</p>
              <p className="text-xs text-gray-500">{filteredItems.length} elementi nel filtro corrente.</p>
            </div>
          </div>
          <div className="mt-4 space-y-3">
            {loading ? (
              <p className="text-sm text-gray-500">Caricamento richieste...</p>
            ) : filteredItems.length === 0 ? (
              <EmptyState icon={SearchIcon} title="Nessuna richiesta trovata" description="Prova a modificare i filtri o la ricerca." />
            ) : (
              filteredItems.map((item) => {
                const isSelected = item.id === selectedId;
                return (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => setSelectedId(item.id)}
                    className={`w-full rounded-2xl border px-4 py-3 text-left transition ${
                      isSelected
                        ? "border-[#1D4E35] bg-[#eef6ef] shadow-sm"
                        : "border-gray-200 bg-white hover:border-[#bfd0c3] hover:bg-[#f8fbf8]"
                    }`}
                  >
                    <div className="flex flex-wrap items-center gap-2">
                    <span className={`rounded-full border px-2 py-0.5 text-xs font-medium ${statusBadgeClasses(item.status)}`}>
                      {statusLabel(item.status)}
                      </span>
                      <span className="rounded-full border border-gray-200 bg-gray-50 px-2 py-0.5 text-xs text-gray-600">
                        {requestTypeLabel(item.request_type)}
                      </span>
                      <span className={`rounded-full border px-2 py-0.5 text-xs font-medium ${priorityBadgeClasses(item.priority)}`}>
                        {priorityLabel(item.priority)}
                      </span>
                      <span className={`rounded-full border px-2 py-0.5 text-xs font-medium ${severityBadgeClasses(item.severity)}`}>
                        {severityLabel(item.severity)}
                      </span>
                      <span className="text-xs text-gray-400">{formatDateTime(item.created_at)}</span>
                    </div>
                    <p className="mt-2 line-clamp-2 text-sm font-medium text-gray-900">{item.user_question}</p>
                    <p className="mt-2 text-xs text-gray-500">
                      Creata da <span className="font-medium text-gray-700">{item.created_by ?? "n/d"}</span>
                      {item.assigned_to_name ? (
                        <>
                          {" · "}Assegnata a <span className="font-medium text-gray-700">{item.assigned_to_name}</span>
                        </>
                      ) : null}
                    </p>
                  </button>
                );
              })
            )}
          </div>
        </article>

        <article className="rounded-3xl border border-[#d9dfd4] bg-white p-5 shadow-sm">
          {selectedRequest ? (
            <div className="space-y-5">
              <div className="space-y-2 border-b border-gray-100 pb-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className={`rounded-full border px-2 py-0.5 text-xs font-medium ${statusBadgeClasses(selectedRequest.status)}`}>
                      {statusLabel(selectedRequest.status)}
                    </span>
                    <span className="rounded-full border border-gray-200 bg-gray-50 px-2 py-0.5 text-xs text-gray-600">
                      {requestTypeLabel(selectedRequest.request_type)}
                    </span>
                    <span className={`rounded-full border px-2 py-0.5 text-xs font-medium ${priorityBadgeClasses(selectedRequest.priority)}`}>
                      Priorità {priorityLabel(selectedRequest.priority)}
                    </span>
                    <span className={`rounded-full border px-2 py-0.5 text-xs font-medium ${severityBadgeClasses(selectedRequest.severity)}`}>
                      Severità {severityLabel(selectedRequest.severity)}
                    </span>
                  </div>
                  <a
                    href={`/wiki/requests/${selectedRequest.id}`}
                    className="text-xs font-medium text-[#1D4E35] underline underline-offset-2"
                  >
                    Apri pagina richiesta
                  </a>
                </div>
                <h3 className="text-lg font-semibold text-gray-900">Dettaglio richiesta</h3>
                <p className="text-xs text-gray-500">
                  Creata da {selectedRequest.created_by ?? "n/d"} il {formatDateTime(selectedRequest.created_at)}.
                </p>
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

              <div className="space-y-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Snapshot del caso</p>
                  <span className="rounded-full border border-gray-200 bg-gray-50 px-2 py-1 text-[11px] text-gray-600">
                    {artifacts.length} artifact
                  </span>
                </div>
                <div className="grid gap-4 xl:grid-cols-[minmax(0,1.05fr)_minmax(20rem,0.95fr)]">
                  <div className="rounded-2xl border border-gray-200 bg-[#fafaf7] p-3">
                    {artifactsLoading ? (
                      <p className="text-sm text-gray-500">Caricamento screenshot e snapshot...</p>
                    ) : screenshotPreviewUrl ? (
                      <div className="space-y-3">
                        <div className="flex items-center justify-between gap-3">
                          <div>
                            <p className="text-sm font-medium text-gray-900">Schermata catturata</p>
                            <p className="text-xs text-gray-500">Freeze frame della pagina nel momento in cui l’operatore ha aperto il caso.</p>
                          </div>
                          <div className="flex flex-wrap gap-2">
                            <a
                              href={screenshotPreviewUrl}
                              target="_blank"
                              rel="noreferrer"
                              className="rounded-full border border-gray-200 bg-white px-3 py-1.5 text-xs font-medium text-gray-700"
                            >
                              Apri immagine
                            </a>
                            {screenshotArtifact ? (
                              <button
                                type="button"
                                onClick={() => void handleDownloadArtifact(screenshotArtifact)}
                                disabled={downloadingArtifactId === screenshotArtifact.id}
                                className="rounded-full border border-gray-200 bg-white px-3 py-1.5 text-xs font-medium text-gray-700 disabled:opacity-50"
                              >
                                {downloadingArtifactId === screenshotArtifact.id ? "Download..." : "Scarica screenshot"}
                              </button>
                            ) : null}
                          </div>
                        </div>
                        <a href={screenshotPreviewUrl} target="_blank" rel="noreferrer">
                          <img
                            src={screenshotPreviewUrl}
                            alt="Screenshot del caso al momento della richiesta"
                            className="max-h-[26rem] w-full rounded-xl border border-gray-200 object-contain"
                          />
                        </a>
                      </div>
                    ) : (
                      <p className="text-sm text-gray-500">Nessuno screenshot salvato per questa richiesta.</p>
                    )}
                  </div>
                  <div className="space-y-4">
                    {moduleSnapshot ? (
                      <div className="space-y-4">
                        <div className="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-950">
                          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">Contesto modulo</p>
                          <div className="mt-3 grid gap-3 md:grid-cols-2">
                            <div>
                              <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-emerald-700/80">Modulo</p>
                              <p className="mt-1 text-sm">{formatSnapshotValue(moduleSnapshot.module)}</p>
                            </div>
                            <div>
                              <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-emerald-700/80">Route</p>
                              <p className="mt-1 text-sm">{formatSnapshotValue(moduleSnapshot.route_type)}</p>
                            </div>
                            <div>
                              <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-emerald-700/80">Entity ID</p>
                              <p className="mt-1 text-sm break-words">{formatSnapshotValue(moduleSnapshot.entity_id)}</p>
                            </div>
                            <div>
                              <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-emerald-700/80">Route Key</p>
                              <p className="mt-1 text-sm break-words">{formatSnapshotValue(moduleSnapshot.route_key)}</p>
                            </div>
                          </div>
                          {moduleSnapshotActiveTabs.length > 0 ? (
                            <div className="mt-3">
                              <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-emerald-700/80">Tab attivi</p>
                              <div className="mt-2 flex flex-wrap gap-2">
                                {moduleSnapshotActiveTabs.map((item) => (
                                  <span key={String(item)} className="rounded-full border border-emerald-200 bg-white px-2 py-1 text-[11px] font-medium text-emerald-900">
                                    {formatSnapshotValue(item)}
                                  </span>
                                ))}
                              </div>
                            </div>
                          ) : null}
                        </div>

                        {moduleSnapshotEntity ? (
                          <div className="rounded-2xl border border-gray-200 bg-[#fafaf7] px-4 py-3 text-sm text-gray-700">
                            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Stato operativo catturato</p>
                            <div className="mt-3 grid gap-3 md:grid-cols-2">
                              {Object.entries(moduleSnapshotEntity).map(([key, value]) => (
                                <div key={key}>
                                  <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-gray-400">{humanizeSnapshotKey(key)}</p>
                                  <p className="mt-1 break-words text-sm text-gray-800">{formatSnapshotValue(value)}</p>
                                </div>
                              ))}
                            </div>
                          </div>
                        ) : null}

                        {moduleSnapshotFilters && Object.keys(moduleSnapshotFilters).length > 0 ? (
                          <div className="rounded-2xl border border-sky-200 bg-sky-50 px-4 py-3 text-sm text-sky-950">
                            <div className="flex flex-wrap items-center justify-between gap-3">
                              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-sky-700">Filtri e parametri attivi</p>
                              {uiSnapshotArtifact ? (
                                <button
                                  type="button"
                                  onClick={() => void handleDownloadArtifact(uiSnapshotArtifact)}
                                  disabled={downloadingArtifactId === uiSnapshotArtifact.id}
                                  className="rounded-full border border-sky-200 bg-white px-3 py-1.5 text-xs font-medium text-sky-900 disabled:opacity-50"
                                >
                                  {downloadingArtifactId === uiSnapshotArtifact.id ? "Download..." : "Scarica snapshot JSON"}
                                </button>
                              ) : null}
                            </div>
                            <div className="mt-3 flex flex-wrap gap-2">
                              {Object.entries(moduleSnapshotFilters).map(([key, value]) => (
                                <span key={key} className="rounded-full border border-sky-200 bg-white px-2.5 py-1 text-[11px] font-medium text-sky-900">
                                  {humanizeSnapshotKey(key)}: {formatSnapshotValue(value)}
                                </span>
                              ))}
                            </div>
                          </div>
                        ) : null}
                      </div>
                    ) : null}

                    <details className="rounded-2xl border border-gray-200 bg-[#fafaf7] px-4 py-3 text-sm text-gray-700">
                      <summary className="cursor-pointer list-none text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">
                        Dettagli tecnici snapshot
                      </summary>
                      <div className="mt-3 space-y-4">
                        <div>
                          <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-gray-400">Metadata screenshot</p>
                          <pre className="mt-2 overflow-x-auto whitespace-pre-wrap text-xs text-gray-600">
                            {JSON.stringify(screenshotMetaArtifact?.payload ?? {}, null, 2)}
                          </pre>
                        </div>
                        <div>
                          <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-gray-400">Snapshot UI completo</p>
                          <pre className="mt-2 max-h-[20rem] overflow-auto whitespace-pre-wrap text-xs text-gray-600">
                            {JSON.stringify(uiSnapshotArtifact?.payload ?? {}, null, 2)}
                          </pre>
                        </div>
                      </div>
                    </details>
                  </div>
                </div>
              </div>

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
                    <p className="font-medium">Questa richiesta è marcata come duplicata.</p>
                    <p className="mt-1">
                      Caso canonico:{" "}
                      <a
                        href={`/wiki/requests/${selectedRequest.canonical_request_id}`}
                        className="font-medium underline underline-offset-2"
                      >
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
                        Vista del gruppo casi già accorpati sullo stesso filone con impatto e promotore attuale.
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
                                  className={`rounded-full border px-2 py-0.5 text-xs font-medium ${statusBadgeClasses(candidate.status as WikiRequest["status"])}`}
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
                              <a
                                href={`/wiki/requests/${candidate.id}`}
                                className="rounded-full border border-gray-200 px-3 py-1.5 text-xs font-medium text-gray-700"
                              >
                                Apri caso
                              </a>
                              {candidate.id !== selectedRequest.id ? (
                                <button
                                  type="button"
                                  onClick={() => void handleUnlinkDuplicate(candidate.id)}
                                  disabled={unlinkingDuplicateId === candidate.id}
                                  className="rounded-full border border-rose-200 bg-rose-50 px-3 py-1.5 text-xs font-medium text-rose-700 transition hover:bg-rose-100 disabled:opacity-50"
                                >
                                  {unlinkingDuplicateId === candidate.id ? "Sgancio..." : "Sgancia"}
                                </button>
                              ) : null}
                              <button
                                type="button"
                                onClick={() => void handleMakeCanonical(candidate.id)}
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
                                <span className={`rounded-full border px-2 py-0.5 text-xs font-medium ${statusBadgeClasses(candidate.status as WikiRequest["status"])}`}>
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
                              <a
                                href={`/wiki/requests/${candidate.id}`}
                                className="rounded-full border border-gray-200 px-3 py-1.5 text-xs font-medium text-gray-700"
                              >
                                Apri caso
                              </a>
                              <button
                                type="button"
                                onClick={() => void handleMarkDuplicate(candidate.id)}
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
                    onChange={(event) => setDraftStatus(event.target.value as WikiRequest["status"])}
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
                  <span className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Priorità</span>
                  <select
                    value={draftPriority}
                    onChange={(event) => setDraftPriority(event.target.value as WikiRequest["priority"])}
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
                  <span className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Severità</span>
                  <select
                    value={draftSeverity}
                    onChange={(event) => setDraftSeverity(event.target.value as WikiRequest["severity"])}
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
                    onChange={(event) => setDraftAssignedTo(event.target.value)}
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
                  onChange={(event) => setDraftResolutionMessage(event.target.value)}
                  rows={4}
                  placeholder="Sintetizza in modo leggibile cosa è stato verificato, deciso o risolto."
                  className="w-full rounded-2xl border border-gray-200 px-3 py-3 text-sm text-gray-700 outline-none transition focus:border-[#1D4E35] focus:ring-2 focus:ring-[#1D4E35]/10"
                />
              </label>

              <label className="block space-y-2">
                <span className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Note admin</span>
                <textarea
                  value={draftNotes}
                  onChange={(event) => setDraftNotes(event.target.value)}
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
                  onClick={handleSave}
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
      </section>
    </div>
  );
}
