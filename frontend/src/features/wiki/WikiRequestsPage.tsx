"use client";

import { useDeferredValue, useEffect, useMemo, useState } from "react";

import { EmptyState } from "@/components/ui/empty-state";
import { MetricCard } from "@/components/ui/metric-card";
import { SearchIcon } from "@/components/ui/icons";
import { WikiRequestDetailPanel } from "./WikiRequestDetailPanel";
import { WikiRequestsList } from "./WikiRequestsList";
import { WikiRequestsFilters } from "./WikiRequestsFilters";
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
type DeliveryStatusValue = "discovery" | "planned" | "in_progress" | "released" | "wont_do";
type RequestDeliveryFilter = "all" | DeliveryStatusValue | "missing";
type RequestTicketFilter = "all" | "linked" | "unlinked";

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

const deliveryStatusOptions: Array<{ value: DeliveryStatusValue; label: string }> = [
  { value: "discovery", label: "Discovery" },
  { value: "planned", label: "Planned" },
  { value: "in_progress", label: "In progress" },
  { value: "released", label: "Released" },
  { value: "wont_do", label: "Won't do" },
];

const deliveryFilterOptions: Array<{ value: RequestDeliveryFilter; label: string }> = [
  { value: "all", label: "Tutto il delivery" },
  { value: "missing", label: "Delivery mancante" },
  { value: "discovery", label: "Discovery" },
  { value: "planned", label: "Planned" },
  { value: "in_progress", label: "In progress" },
  { value: "released", label: "Released" },
  { value: "wont_do", label: "Won't do" },
];

const ticketFilterOptions: Array<{ value: RequestTicketFilter; label: string }> = [
  { value: "all", label: "Tutti i ticket" },
  { value: "linked", label: "Con ticket esterno" },
  { value: "unlinked", label: "Senza ticket esterno" },
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

function averageResolutionHours(items: WikiRequest[]): string {
  const resolved = items
    .filter((item) => item.status === "resolved")
    .map((item) => {
      const createdAt = new Date(item.created_at).getTime();
      const updatedAt = new Date(item.updated_at).getTime();
      return Number.isFinite(createdAt) && Number.isFinite(updatedAt) && updatedAt >= createdAt
        ? (updatedAt - createdAt) / (1000 * 60 * 60)
        : null;
    })
    .filter((value): value is number => value != null);

  if (resolved.length === 0) {
    return "n/d";
  }
  const avg = resolved.reduce((sum, value) => sum + value, 0) / resolved.length;
  return `${Math.round(avg)}h`;
}

export function WikiRequestsPage({ supportOnly = false, initialRequestId = null }: { supportOnly?: boolean; initialRequestId?: string | null }) {
  const [items, setItems] = useState<WikiRequest[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<RequestStatusFilter>("all");
  const [categoryFilter, setCategoryFilter] = useState<RequestCategoryFilter>("all");
  const [requestTypeFilter, setRequestTypeFilter] = useState<RequestTypeFilter>("all");
  const [priorityFilter, setPriorityFilter] = useState<RequestPriorityFilter>("all");
  const [severityFilter, setSeverityFilter] = useState<RequestSeverityFilter>("all");
  const [deliveryFilter, setDeliveryFilter] = useState<RequestDeliveryFilter>("all");
  const [ticketFilter, setTicketFilter] = useState<RequestTicketFilter>("all");
  const [query, setQuery] = useState("");
  const [draftStatus, setDraftStatus] = useState<WikiRequest["status"]>("new");
  const [draftPriority, setDraftPriority] = useState<WikiRequest["priority"]>("medium");
  const [draftSeverity, setDraftSeverity] = useState<WikiRequest["severity"]>("medium");
  const [draftAssignedTo, setDraftAssignedTo] = useState("");
  const [draftResolutionMessage, setDraftResolutionMessage] = useState("");
  const [draftNotes, setDraftNotes] = useState("");
  const [draftExternalTicketKey, setDraftExternalTicketKey] = useState("");
  const [draftExternalTicketUrl, setDraftExternalTicketUrl] = useState("");
  const [draftDeliveryStatus, setDraftDeliveryStatus] = useState<DeliveryStatusValue>("discovery");
  const [draftDeliveryNotes, setDraftDeliveryNotes] = useState("");
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
      if (deliveryFilter !== "all") {
        if (deliveryFilter === "missing") {
          if (item.delivery_status) {
            return false;
          }
        } else if (item.delivery_status !== deliveryFilter) {
          return false;
        }
      }
      if (ticketFilter !== "all") {
        const hasExternalTicket = Boolean(item.external_ticket_key || item.external_ticket_url);
        if (ticketFilter === "linked" && !hasExternalTicket) {
          return false;
        }
        if (ticketFilter === "unlinked" && hasExternalTicket) {
          return false;
        }
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
        item.external_ticket_key ?? "",
        item.external_ticket_url ?? "",
        item.delivery_status ?? "",
        item.delivery_notes ?? "",
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
  }, [items, supportOnly, statusFilter, categoryFilter, requestTypeFilter, priorityFilter, severityFilter, deliveryFilter, ticketFilter, deferredQuery]);

  const selectedRequest = useMemo(
    () => filteredItems.find((item) => item.id === selectedId) ?? items.find((item) => item.id === selectedId) ?? null,
    [filteredItems, items, selectedId],
  );

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
    setDraftExternalTicketKey(selectedRequest.external_ticket_key ?? "");
    setDraftExternalTicketUrl(selectedRequest.external_ticket_url ?? "");
    setDraftDeliveryStatus((selectedRequest.delivery_status as DeliveryStatusValue | null) ?? "discovery");
    setDraftDeliveryNotes(selectedRequest.delivery_notes ?? "");
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
      waitingUser: scopedItems.filter((item) => item.status === "waiting_user").length,
      unassigned: scopedItems.filter((item) => !item.assigned_to).length,
      avgResolution: averageResolutionHours(scopedItems),
    };
  }, [scopedItems]);

  const linkedTicketItems = useMemo(
    () => filteredItems.filter((item) => item.external_ticket_key || item.external_ticket_url),
    [filteredItems],
  );

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
        external_ticket_key: draftExternalTicketKey || null,
        external_ticket_url: draftExternalTicketUrl || null,
        delivery_status: draftDeliveryStatus,
        delivery_notes: draftDeliveryNotes || null,
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

  function handleExportLinkedTicketsCsv() {
    if (linkedTicketItems.length === 0) {
      return;
    }
    const escapeCsv = (value: string | null | undefined): string => `"${(value ?? "").replaceAll('"', '""')}"`;
    const rows = [
      ["request_id", "status", "priority", "severity", "delivery_status", "external_ticket_key", "external_ticket_url", "module_key", "page_path", "created_by", "user_question"].join(","),
      ...linkedTicketItems.map((item) =>
        [
          escapeCsv(item.id),
          escapeCsv(item.status),
          escapeCsv(item.priority),
          escapeCsv(item.severity),
          escapeCsv(item.delivery_status),
          escapeCsv(item.external_ticket_key),
          escapeCsv(item.external_ticket_url),
          escapeCsv(item.module_key),
          escapeCsv(item.page_path),
          escapeCsv(item.created_by),
          escapeCsv(item.user_question),
        ].join(","),
      ),
    ];
    const blob = new Blob([rows.join("\n")], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "wiki-linked-tickets.csv";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    setSuccessMessage("Export ticket generato.");
  }

  if (error && !loading && items.length === 0) {
    return <EmptyState icon={SearchIcon} title="Richieste Wiki non disponibili" description={error} />;
  }

  return (
    <div className="space-y-6">
      <section className="overflow-hidden rounded-[32px] border border-[#d9dfd4] bg-[radial-gradient(circle_at_top_left,_rgba(232,241,233,0.92),_rgba(255,255,255,0.98)_60%)] p-5 shadow-sm">
        <div className="flex flex-col gap-5">
          <div className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
            <div className="max-w-3xl">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#7a897f]">
                {supportOnly ? "Console supporto" : "Backlog richieste"}
              </p>
              <h1 className="mt-1 text-3xl font-semibold tracking-tight text-[#1d2f24]">
                {supportOnly ? "Inbox supporto orientata al triage" : "Panoramica richieste generate dal Wiki"}
              </h1>
              <p className="mt-2 text-sm leading-6 text-[#5a6b62]">
                {supportOnly
                  ? "Leggi velocemente il carico, individua i casi urgenti, apri il dettaglio e aggiorna stato, assegnazione e delivery senza cambiare contesto."
                  : "Vista di governo su richieste, duplicati, artifact e collegamenti verso il delivery."}
              </p>
            </div>
            <div className="grid gap-3 sm:grid-cols-3 xl:w-[28rem]">
              <div className="rounded-[24px] border border-white/80 bg-white/80 px-4 py-3 shadow-sm">
                <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#87948c]">Da assegnare</p>
                <p className="mt-2 text-2xl font-semibold text-[#1d2f24]">{summary.unassigned}</p>
                <p className="mt-1 text-xs text-[#64756d]">richieste senza owner</p>
              </div>
              <div className="rounded-[24px] border border-white/80 bg-white/80 px-4 py-3 shadow-sm">
                <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#87948c]">Waiting user</p>
                <p className="mt-2 text-2xl font-semibold text-[#1d2f24]">{summary.waitingUser}</p>
                <p className="mt-1 text-xs text-[#64756d]">in attesa di riscontro</p>
              </div>
              <div className="rounded-[24px] border border-white/80 bg-white/80 px-4 py-3 shadow-sm">
                <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#87948c]">Tempo medio</p>
                <p className="mt-2 text-2xl font-semibold text-[#1d2f24]">{summary.avgResolution}</p>
                <p className="mt-1 text-xs text-[#64756d]">chiusura casi risolti</p>
              </div>
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-3 xl:grid-cols-6">
            <MetricCard label="Totale richieste" value={summary.total.toString()} sub="storico registrato" />
            <MetricCard label="Nuove" value={summary.newCount.toString()} sub="da prendere in carico" />
            <MetricCard label="Triaged" value={summary.triaged.toString()} sub="qualificate" />
            <MetricCard label="Urgenti" value={summary.urgent.toString()} sub="da trattare subito" />
            <MetricCard label="Planned" value={summary.planned.toString()} sub="in roadmap" />
            <MetricCard label="Resolved" value={summary.resolved.toString()} sub="chiuse" />
          </div>
        </div>
      </section>

      <WikiRequestsFilters
        supportOnly={supportOnly}
        query={query}
        statusFilter={statusFilter}
        categoryFilter={categoryFilter}
        priorityFilter={priorityFilter}
        requestTypeFilter={requestTypeFilter}
        severityFilter={severityFilter}
        deliveryFilter={deliveryFilter}
        ticketFilter={ticketFilter}
        statusOptions={statusOptions}
        categoryOptions={categoryOptions}
        priorityOptions={priorityOptions}
        requestTypeOptions={requestTypeOptions}
        severityOptions={severityOptions}
        deliveryOptions={deliveryFilterOptions}
        ticketOptions={ticketFilterOptions}
        onQueryChange={setQuery}
        onStatusChange={(value) => setStatusFilter(value as RequestStatusFilter)}
        onCategoryChange={(value) => setCategoryFilter(value as RequestCategoryFilter)}
        onPriorityChange={(value) => setPriorityFilter(value as RequestPriorityFilter)}
        onRequestTypeChange={(value) => setRequestTypeFilter(value as RequestTypeFilter)}
        onSeverityChange={(value) => setSeverityFilter(value as RequestSeverityFilter)}
        onDeliveryChange={(value) => setDeliveryFilter(value as RequestDeliveryFilter)}
        onTicketChange={(value) => setTicketFilter(value as RequestTicketFilter)}
      />

      <section className="flex flex-wrap items-center justify-between gap-3 rounded-[28px] border border-[#d9dfd4] bg-white px-5 py-4 shadow-sm">
        <div>
          <p className="text-sm font-semibold text-gray-900">Export delivery bridge</p>
          <p className="text-xs text-gray-500">
            {linkedTicketItems.length} richieste con ticket nel filtro corrente.
          </p>
        </div>
        <button
          type="button"
          onClick={handleExportLinkedTicketsCsv}
          disabled={linkedTicketItems.length === 0}
          className="rounded-full border border-[#1D4E35] px-4 py-2 text-sm font-medium text-[#1D4E35] transition hover:bg-[#eef6ef] disabled:cursor-not-allowed disabled:opacity-50"
        >
          Esporta ticket CSV
        </button>
      </section>

      <section className="grid gap-6 xl:grid-cols-[minmax(0,1.05fr)_minmax(25rem,0.95fr)]">
        <WikiRequestsList
          filteredItems={filteredItems}
          loading={loading}
          selectedId={selectedId}
          onSelect={setSelectedId}
          formatDateTime={formatDateTime}
          statusBadgeClasses={statusBadgeClasses}
          statusLabel={statusLabel}
          requestTypeLabel={requestTypeLabel}
          priorityBadgeClasses={priorityBadgeClasses}
          priorityLabel={priorityLabel}
          severityBadgeClasses={severityBadgeClasses}
          severityLabel={severityLabel}
        />

        <WikiRequestDetailPanel
          selectedRequest={selectedRequest}
          artifacts={artifacts}
          artifactsLoading={artifactsLoading}
          screenshotPreviewUrl={screenshotPreviewUrl}
          downloadingArtifactId={downloadingArtifactId}
          onDownloadArtifact={handleDownloadArtifact}
          draftExternalTicketKey={draftExternalTicketKey}
          draftExternalTicketUrl={draftExternalTicketUrl}
          draftDeliveryStatus={draftDeliveryStatus}
          draftDeliveryNotes={draftDeliveryNotes}
          deliveryStatusOptions={deliveryStatusOptions}
          onExternalTicketKeyChange={setDraftExternalTicketKey}
          onExternalTicketUrlChange={setDraftExternalTicketUrl}
          onDeliveryStatusChange={setDraftDeliveryStatus}
          onDeliveryNotesChange={setDraftDeliveryNotes}
          family={family}
          linkedDuplicates={linkedDuplicates}
          linkedDuplicatesLoading={linkedDuplicatesLoading}
          duplicates={duplicates}
          duplicatesLoading={duplicatesLoading}
          unlinkingDuplicateId={unlinkingDuplicateId}
          promotingCanonicalId={promotingCanonicalId}
          markingDuplicateId={markingDuplicateId}
          onUnlinkDuplicate={handleUnlinkDuplicate}
          onMakeCanonical={handleMakeCanonical}
          onMarkDuplicate={handleMarkDuplicate}
          draftStatus={draftStatus}
          onDraftStatusChange={setDraftStatus}
          statusOptions={statusOptions}
          draftPriority={draftPriority}
          onDraftPriorityChange={setDraftPriority}
          priorityOptions={priorityOptions}
          draftSeverity={draftSeverity}
          onDraftSeverityChange={setDraftSeverity}
          severityOptions={severityOptions}
          draftAssignedTo={draftAssignedTo}
          onDraftAssignedToChange={setDraftAssignedTo}
          assignees={assignees}
          draftResolutionMessage={draftResolutionMessage}
          onDraftResolutionMessageChange={setDraftResolutionMessage}
          draftNotes={draftNotes}
          onDraftNotesChange={setDraftNotes}
          timelineLoading={timelineLoading}
          timeline={timeline}
          error={error}
          successMessage={successMessage}
          saving={saving}
          onSave={handleSave}
          formatDateTime={formatDateTime}
          statusBadgeClasses={statusBadgeClasses}
          statusLabel={statusLabel}
          requestTypeLabel={requestTypeLabel}
          priorityBadgeClasses={priorityBadgeClasses}
          priorityLabel={priorityLabel}
          severityBadgeClasses={severityBadgeClasses}
          severityLabel={severityLabel}
        />
      </section>
    </div>
  );
}
