#!/usr/bin/env python3
"""Generate Vitest happy-path coverage tests for the frontend API facade."""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API_TS = ROOT / "frontend/src/lib/api/index.ts"
OUT_DIR = ROOT / "frontend/tests/unit"


def api_source() -> str:
    """Read the public API modules in facade order."""
    facade = API_TS.read_text()
    module_paths = re.findall(r'export \* from "(\./[^"]+)";', facade)
    if not module_paths:
        return facade
    return "\n".join(
        (API_TS.parent / f"{module_path}.ts").read_text() for module_path in module_paths
    )


SKIP = {
    "isAuthError",
    "getApiBaseUrl",
    "request",
    "requestBlob",
    "requestFormDataWithUploadProgress",
    "createQueryString",
    "getWebSocketBaseUrl",
    "login",
    "getAuthProviders",
    "getCurrentUser",
    "sendPresenceHeartbeat",
    "getPresenceSummary",
    "classifyUtenzeDocumentContent",
}

PRESENZE_PREFIXES = (
    "getGatePresenze",
    "listGatePresenze",
    "createGatePresenze",
    "updateGatePresenze",
    "getMePresenze",
    "listMePresenze",
    "listPresenze",
    "getPresenze",
    "createPresenze",
    "updatePresenze",
    "deletePresenze",
    "mapPresenze",
    "previewPresenze",
    "importPresenze",
    "exportPresenze",
    "downloadPresenze",
    "retryPresenze",
    "cancelPresenze",
    "refreshPresenze",
    "reviewPresenze",
    "testPresenze",
    "applyPresenze",
    "bootstrapPresenze",
)

ME_COVERED = {
    "getMeStatus",
    "getMeSummary",
    "getMeOperazioniSummary",
    "listMeOperazioniActivities",
    "listMeOperazioniReports",
    "listMeOperazioniCases",
    "listMeVehicleSessions",
    "listMeAssignedDevices",
    "listMeVehicleAssignments",
    "getMePresenzeStatus",
    "getMePresenzeSummary",
    "listMePresenzeDailyRecords",
    "getMePresenzeDailyRecord",
}


def extract_functions(source: str) -> list[tuple[str, str, str, str]]:
    lines = source.splitlines()
    functions: list[tuple[str, str, str, str]] = []
    i = 0
    while i < len(lines):
        match = re.match(r"export async function (\w+)(?:<[^>]+>)?\(", lines[i])
        if not match:
            i += 1
            continue
        name = match.group(1)
        start = i
        signature_lines = [lines[i]]
        i += 1
        while i < len(lines):
            signature_lines.append(lines[i])
            combined = "\n".join(signature_lines)
            if re.search(r"\)\s*(?::[^{]+)?\s*\{", combined):
                break
            i += 1
        signature = "\n".join(signature_lines)
        parsed = re.match(
            rf"export async function {re.escape(name)}(?:<[^>]+>)?\((.*)\)(?:: ([^{{]+))?\s*\{{",
            signature,
            re.DOTALL,
        )
        if not parsed:
            i += 1
            continue
        params = " ".join(parsed.group(1).split())
        return_type = (parsed.group(2) or "").strip()
        brace = signature.count("{") - signature.count("}")
        while i < len(lines) and brace > 0:
            i += 1
            brace += lines[i].count("{") - lines[i].count("}")
        body = "\n".join(lines[start:i])
        functions.append((name, params, body, return_type))
    return functions


def domain_for(name: str) -> str:
    if any(name.startswith(prefix) for prefix in PRESENZE_PREFIXES):
        return "presenze"
    if name.startswith(
        (
            "getOrg",
            "createOrg",
            "updateOrg",
            "deleteOrg",
            "syncOrg",
            "exportOrganigramma",
            "importOrganigramma",
            "bootstrapOrg",
            "upsertOrg",
        )
    ):
        return "organigramma"
    if name.startswith(
        (
            "getOperazioni",
            "listOperazioni",
            "createOperazioni",
            "updateOperazioni",
            "deleteOperazioni",
            "getOperator",
            "listOperator",
            "createOperator",
            "updateOperator",
            "deleteOperator",
            "getVehicle",
            "listVehicle",
            "createVehicle",
            "updateVehicle",
            "deleteVehicle",
            "getFuel",
            "listFuel",
            "createFuel",
            "updateFuel",
            "deleteFuel",
            "getReport",
            "listReport",
            "createReport",
            "updateReport",
            "deleteReport",
            "getCase",
            "listCase",
            "createCase",
            "updateCase",
            "deleteCase",
            "getActivity",
            "listActivity",
            "createActivity",
            "updateActivity",
            "deleteActivity",
            "getSegnalazione",
            "listSegnalazione",
            "createSegnalazione",
            "updateSegnalazione",
            "deleteSegnalazione",
            "getPratica",
            "listPratica",
            "createPratica",
            "updatePratica",
            "deletePratica",
            "getMiniapp",
            "listMiniapp",
            "getAttivita",
            "listAttivita",
            "inviteOperator",
            "getMobileSync",
        )
    ):
        return "operazioni"
    if name.startswith(
        (
            "getRiordino",
            "listRiordino",
            "createRiordino",
            "updateRiordino",
            "deleteRiordino",
            "getBlock",
            "listBlock",
            "createBlock",
            "updateBlock",
            "deleteBlock",
            "completeRiordino",
            "reviewRiordino",
            "ensureRiordino",
            "getPractice",
            "listPractice",
            "createPractice",
            "updatePractice",
            "deletePractice",
            "archivePractice",
            "getAppeal",
            "listAppeal",
            "createAppeal",
            "updateAppeal",
            "resolveAppeal",
            "getIssue",
            "listIssue",
            "createIssue",
            "closeIssue",
            "uploadDocument",
            "downloadDocument",
            "getWorkflow",
            "advanceWorkflow",
            "skipWorkflow",
            "reopenWorkflow",
            "getNotification",
            "listNotification",
            "markNotification",
            "getGisLayer",
            "listGisLayer",
            "createGisLayer",
            "updateGisLayer",
            "deleteGisLayer",
            "getLink",
            "listLink",
            "createLink",
            "deleteLink",
            "getConfig",
            "updateConfig",
            "exportRiordino",
            "importRiordino",
        )
    ):
        return "riordino"
    if name.startswith(
        (
            "getSync",
            "listSync",
            "createSync",
            "updateSync",
            "deleteSync",
            "runSync",
            "previewSync",
            "applySync",
            "cancelSync",
            "retrySync",
        )
    ):
        return "sync"
    if name.startswith(
        (
            "getInventory",
            "listInventory",
            "createInventory",
            "updateInventory",
            "deleteInventory",
            "getGisCatalog",
            "listGisCatalog",
            "getGis",
            "listGis",
        )
    ):
        return "inventory"
    if name.startswith(
        (
            "getAnagrafica",
            "listAnagrafica",
            "createAnagrafica",
            "updateAnagrafica",
            "deleteAnagrafica",
            "importAnagrafica",
            "resetAnagrafica",
            "searchAnagrafica",
            "getUtenze",
            "listUtenze",
            "importUtenze",
            "startUtenze",
            "getXlsx",
            "listXlsx",
            "updateUtenze",
            "deleteUtenze",
            "createUtenze",
            "syncUtenze",
            "getAnpr",
            "listAnpr",
            "updateAnpr",
            "triggerAnpr",
            "previewAnpr",
            "runAnpr",
        )
    ):
        return "utenze"
    if name.startswith(
        (
            "getNetwork",
            "listNetwork",
            "createNetwork",
            "updateNetwork",
            "deleteNetwork",
            "triggerNetwork",
            "bulkUpdateNetwork",
            "getSophos",
            "updateSophos",
            "getFloorPlan",
            "createFloorPlan",
            "updateFloorPlan",
            "deleteFloorPlan",
            "getVpn",
            "listVpn",
            "getArp",
            "getFirewall",
            "listFirewall",
            "updateNetwork",
            "getDevice",
            "updateDevice",
            "listDevice",
            "assignNetwork",
            "getNetworkScan",
            "listNetworkScan",
            "getNetworkTracked",
            "createNetworkTracked",
            "updateNetworkTracked",
            "deleteNetworkTracked",
            "getNetworkIp",
            "getNetworkDetection",
            "createNetworkDetection",
            "updateNetworkDetection",
            "deleteNetworkDetection",
        )
    ):
        return "network"
    if name.startswith(
        (
            "getWiki",
            "listWiki",
            "createWiki",
            "updateWiki",
            "deleteWiki",
            "assignWiki",
            "submitWiki",
            "searchWiki",
            "sendWiki",
            "rateWiki",
            "duplicateWiki",
            "makeCanonical",
            "getSupport",
            "listSupport",
            "createSupport",
            "updateSupport",
            "deleteSupport",
            "getConversation",
            "listConversation",
            "updateConversation",
            "createConversation",
            "getTelemetry",
            "listTelemetry",
            "getAudit",
            "listAudit",
            "addWiki",
            "removeWiki",
            "getCluster",
            "getInsight",
            "getAnalytics",
            "getFeedback",
            "postFeedback",
            "getFamily",
            "listFamilies",
        )
    ):
        return "wiki"
    if name.startswith(
        (
            "getElaborazione",
            "listElaborazione",
            "createElaborazione",
            "updateElaborazione",
            "deleteElaborazione",
            "testElaborazione",
            "triggerElaborazione",
            "cancelElaborazione",
            "retryElaborazione",
            "downloadElaborazione",
            "uploadElaborazione",
            "startElaborazione",
            "getCapacitas",
            "listCapacitas",
            "createCapacitas",
            "updateCapacitas",
            "deleteCapacitas",
            "testCapacitas",
            "searchCapacitas",
            "resolveCapacitas",
            "refetchCapacitas",
            "harvestCapacitas",
            "syncCapacitas",
            "getBonifica",
            "listBonifica",
            "createBonifica",
            "updateBonifica",
            "deleteBonifica",
            "testBonifica",
            "runBonifica",
            "approveBonifica",
            "getPostaOnline",
            "listPostaOnline",
            "createPostaOnline",
            "updatePostaOnline",
            "deletePostaOnline",
            "testPostaOnline",
            "getGateMobile",
            "triggerGateMobile",
            "getRuoloAuto",
            "updateRuoloAuto",
            "getIncass",
            "listIncass",
            "createIncass",
            "updateIncass",
            "deleteIncass",
            "getVisure",
            "listVisure",
            "createVisure",
            "updateVisure",
            "deleteVisure",
            "getAutodoc",
            "listAutodoc",
            "createAutodoc",
            "updateAutodoc",
            "deleteAutodoc",
            "getAdeAlignment",
            "listAdeAlignment",
            "createAdeAlignment",
            "updateAdeAlignment",
            "deleteAdeAlignment",
            "getAnprSync",
            "updateAnprSync",
            "previewAnpr",
            "runAnpr",
            "getAutosync",
            "updateAutosync",
            "getBatch",
            "listBatch",
            "createBatch",
            "updateBatch",
            "deleteBatch",
            "getCredential",
            "listCredential",
            "createCredential",
            "updateCredential",
            "deleteCredential",
            "testCredential",
            "getRichiesta",
            "listRichiesta",
            "createRichiesta",
            "updateRichiesta",
            "deleteRichiesta",
            "getRuntimeMetrics",
            "getAutoJob",
            "updateAutoJob",
            "controlAutoJob",
            "getBonificaUser",
            "listBonificaUser",
            "approveBonificaUser",
            "bulkApproveBonificaUser",
        )
    ):
        return "elaborazioni"
    if name.startswith(
        (
            "getCatasto",
            "listCatasto",
            "createCatasto",
            "updateCatasto",
            "deleteCatasto",
            "importCatasto",
            "exportCatasto",
            "searchCatasto",
            "getCat",
            "listCat",
            "createCat",
            "updateCat",
            "deleteCat",
            "getDistretto",
            "listDistretto",
            "createDistretto",
            "updateDistretto",
            "deleteDistretto",
            "getParticella",
            "listParticella",
            "getDomanda",
            "listDomanda",
            "getDeliveryPoint",
            "listDeliveryPoint",
            "createDeliveryPoint",
            "updateDeliveryPoint",
            "deleteDeliveryPoint",
            "getMeterReading",
            "listMeterReading",
            "getGis",
            "listGis",
            "syncCatasto",
            "getAde",
            "listAde",
            "triggerAde",
            "getIrrigation",
            "listIrrigation",
            "previewIrrigation",
            "getAnomalie",
            "listAnomalie",
            "getWhiteCompany",
            "listWhiteCompany",
            "uploadCatasto",
            "downloadCatasto",
            "getArchive",
            "listArchive",
        )
    ):
        return "catasto"
    if name.startswith(
        (
            "getOperazioni",
            "listOperazioni",
            "createOperazioni",
            "updateOperazioni",
            "deleteOperazioni",
            "getOperator",
            "listOperator",
            "createOperator",
            "updateOperator",
            "deleteOperator",
            "getVehicle",
            "listVehicle",
            "createVehicle",
            "updateVehicle",
            "deleteVehicle",
            "getFuel",
            "listFuel",
            "createFuel",
            "updateFuel",
            "deleteFuel",
            "getReport",
            "listReport",
            "createReport",
            "updateReport",
            "deleteReport",
            "getCase",
            "listCase",
            "createCase",
            "updateCase",
            "deleteCase",
            "getActivity",
            "listActivity",
            "createActivity",
            "updateActivity",
            "deleteActivity",
            "getSegnalazione",
            "listSegnalazione",
            "createSegnalazione",
            "updateSegnalazione",
            "deleteSegnalazione",
            "getPratica",
            "listPratica",
            "createPratica",
            "updatePratica",
            "deletePratica",
            "getMiniapp",
            "listMiniapp",
            "getAttivita",
            "listAttivita",
            "inviteOperator",
            "getMobileSync",
        )
    ):
        return "operazioni"
    if name.startswith(
        (
            "getRiordino",
            "listRiordino",
            "createRiordino",
            "updateRiordino",
            "deleteRiordino",
            "getBlock",
            "listBlock",
            "createBlock",
            "updateBlock",
            "deleteBlock",
            "completeRiordino",
            "reviewRiordino",
            "ensureRiordino",
            "getPractice",
            "listPractice",
            "createPractice",
            "updatePractice",
            "deletePractice",
            "archivePractice",
            "getAppeal",
            "listAppeal",
            "createAppeal",
            "updateAppeal",
            "resolveAppeal",
            "getIssue",
            "listIssue",
            "createIssue",
            "closeIssue",
            "uploadDocument",
            "downloadDocument",
            "getWorkflow",
            "advanceWorkflow",
            "skipWorkflow",
            "reopenWorkflow",
            "getNotification",
            "listNotification",
            "markNotification",
            "getGisLayer",
            "listGisLayer",
            "createGisLayer",
            "updateGisLayer",
            "deleteGisLayer",
            "getLink",
            "listLink",
            "createLink",
            "deleteLink",
            "getConfig",
            "updateConfig",
            "exportRiordino",
            "importRiordino",
        )
    ):
        return "riordino"
    if name.startswith(
        (
            "getShare",
            "getNas",
            "listNas",
            "createNas",
            "updateNas",
            "deleteNas",
            "getReview",
            "listReview",
            "createReview",
            "updateReview",
            "deleteReview",
            "getSync",
            "listSync",
            "createSync",
            "updateSync",
            "deleteSync",
            "runSync",
            "previewSync",
            "applySync",
            "getEffective",
            "listEffective",
            "getPermission",
            "listPermission",
            "updatePermission",
            "deletePermission",
            "getDashboard",
            "getMyPermissions",
            "listApplication",
            "listAllApplication",
            "getApplication",
            "updateApplication",
            "deleteApplication",
            "inviteApplication",
            "createApplication",
            "listSection",
            "getInventory",
            "listInventory",
            "createInventory",
            "updateInventory",
            "deleteInventory",
            "getGisCatalog",
            "listGisCatalog",
        )
    ):
        return "platform"
    if name.startswith("getMe") or name.startswith("listMe"):
        return "me"
    return "misc"


PAGINATED_ALL = {
    "listAllApplicationUsers",
    "listAllPresenzeCollaborators",
    "listPresenzeApplicationUsers",
}


def uses_blob(body: str) -> bool:
    return "requestBlob(" in body


def uses_form_upload(body: str) -> bool:
    return "requestFormDataWithUploadProgress" in body


def is_void_return(return_type: str) -> bool:
    return "void" in return_type


def split_params(params: str) -> list[str]:
    parts: list[str] = []
    current: list[str] = []
    depth = 0
    for char in params:
        if char in "{(<[":
            depth += 1
        elif char in "})>]":
            depth -= 1
        if char == "," and depth == 0:
            part = "".join(current).strip()
            if part:
                parts.append(part)
            current = []
        else:
            current.append(char)
    tail = "".join(current).strip()
    if tail:
        parts.append(tail)
    return parts


def fetch_stub_count(body: str) -> int:
    count = len(re.findall(r"\bawait request\b", body))
    count += len(re.findall(r"\bawait get\w+\(", body))
    count += len(re.findall(r"\breturn get\w+\(", body))
    return max(1, count)


def build_call(name: str, params: str, body: str) -> str:
    raw_params = split_params(params)
    args: list[str] = []
    for part in raw_params:
        pname = part.split(":")[0].strip().replace("...", "")
        if pname in {"token"}:
            args.append("TOKEN")
        elif "=>" in part:
            args.append("() => undefined")
        elif pname in {"onProgress"}:
            args.append("() => undefined")
        elif pname.endswith("Id") or pname in {
            "batchId",
            "jobId",
            "recordId",
            "teamId",
            "userId",
            "sectionId",
            "deviceId",
            "firewallId",
            "subjectId",
            "avvisoId",
            "credentialId",
            "adjustmentId",
            "templateId",
            "ruleId",
            "assignmentId",
            "conversationId",
            "requestId",
            "artifactId",
            "unitId",
            "assignment_id",
            "holidayId",
            "alertId",
        }:
            if ": number" in part:
                args.append("1")
            else:
                args.append('"id-1"')
        elif pname.endswith("_id") or pname in {"id"}:
            args.append('"id-1"')
        elif pname in {
            "path",
            "filename",
            "code",
            "state",
            "username",
            "password",
            "identifier",
            "periodStart",
            "periodEnd",
            "period_start",
            "period_end",
            "workDate",
            "isoDate",
            "year",
            "month",
            "status",
            "structureKind",
            "module",
            "query",
            "q",
            "kind",
            "mode",
            "intent",
            "toolName",
            "moduleKey",
        }:
            if "?" in part or "OrgStructureKind" in part:
                args.append('"organigramma"')
            elif pname in {"periodStart", "period_start"}:
                args.append('"2026-08-01"')
            elif pname in {"periodEnd", "period_end"}:
                args.append('"2026-08-31"')
            elif pname in {"year"}:
                args.append("2026")
            elif pname in {"month"}:
                args.append("8")
            elif pname in {"username", "identifier"}:
                args.append('"user"')
            elif pname in {"password"}:
                args.append('"secret"')
            elif pname in {
                "status",
                "mode",
                "intent",
                "toolName",
                "moduleKey",
                "kind",
                "q",
                "query",
            }:
                args.append('"x"')
            elif pname in {"structureKind"}:
                args.append('"organigramma"')
            elif pname in {"module"}:
                args.append('"wiki"')
            else:
                args.append('"value"')
        elif (
            pname
            in {
                "payload",
                "input",
                "body",
                "data",
                "request",
                "params",
                "options",
                "init",
                "update",
                "create",
                "values",
                "filters",
                "formData",
            }
            or "Input" in part
            or "Request" in part
            or "Update" in part
            or "Create" in part
        ):
            if pname == "formData":
                args.append("new FormData()")
            elif pname == "options":
                if "bustCache" in body:
                    args.append("{ bustCache: true }")
                elif "timeoutMs" in part:
                    args.append("{ timeoutMs: 1000 }")
                else:
                    args.append("{}")
            elif pname == "params":
                args.append(
                    "{ page: 1, pageSize: 20, periodStart: '2026-08-01', periodEnd: '2026-08-31', "
                    "parentId: 'id-1', structureKind: 'organigramma', toolName: 'x', moduleKey: 'wiki', "
                    "module: 'wiki', success: true, limit: 10, skip: 0, activeOnly: true, "
                    "windowMinutes: 15, status: 'active', conversationId: 'c1', username: 'u', "
                    "intent: 'x', mode: 'x', q: 'x', bustCache: true }"
                )
            else:
                args.append("{}")
        elif pname in {"file", "files"}:
            args.append("new File(['x'], 'file.csv')")
        elif "[]" in part or "Array" in part:
            args.append("[]")
        elif pname in {
            "text",
            "content",
            "notes",
            "reason",
            "message",
            "label",
            "name",
            "email",
            "subject",
            "detail",
            "description",
        }:
            args.append('"text"')
        elif pname in {
            "enabled",
            "active",
            "force",
            "unlinked",
            "bustCache",
            "activeOnly",
            "isActive",
        }:
            args.append("true")
        elif pname in {"page", "skip", "limit", "pageSize", "page_size"}:
            args.append("1")
        elif pname in {"anno", "count", "amount", "size"}:
            args.append("1")
        elif (
            "boolean" in part.lower()
            or pname.startswith("is")
            or pname.startswith("has")
            or pname.endswith("Only")
        ):
            args.append("false")
        elif "number" in part.lower():
            args.append("1")
        elif "string" in part.lower():
            args.append('"value"')
        elif "Date" in part:
            args.append('"2026-08-01"')
        elif "Record" in part or "object" in part.lower():
            args.append("{}")
        else:
            args.append("{}")
    return f"{name}({', '.join(args)})"


def response_helper(name: str, body: str, return_type: str) -> str:
    if name in PAGINATED_ALL:
        return "jsonResponse({ items: [], total: 0 })"
    if uses_blob(body):
        return "blobResponse()"
    if is_void_return(return_type):
        return "emptyOkResponse()"
    if "[]" in return_type:
        return "jsonResponse([])"
    return "jsonResponse({ ok: true })"


def assertion_for(name: str, params: str, body: str, return_type: str) -> str:
    call = build_call(name, params, body)
    if uses_form_upload(body):
        return f"""const pending = {call};
    const xhr = MockXHR.instances.at(-1)!;
    xhr.loadHandler?.();
    await expect(pending).resolves.toBeDefined();"""
    if is_void_return(return_type):
        return f"await expect({call}).resolves.toBeUndefined();"
    if name in PAGINATED_ALL:
        return f"await expect({call}).resolves.toEqual([]);"
    return f"await expect({call}).resolves.toBeDefined();"


def render_file(domain: str, names: list[str], func_map: dict[str, tuple[str, str, str]]) -> str:
    imports = ",\n  ".join(sorted(names))
    needs_xhr = any(uses_form_upload(func_map[name][1]) for name in names)
    tests = []
    for name in sorted(names):
        params, body, return_type = func_map[name]
        helper = response_helper(name, body, return_type)
        assertion = assertion_for(name, params, body, return_type)
        if uses_form_upload(body):
            tests.append(
                f"""  test("{name}", async () => {{
    {assertion}
  }});"""
            )
        else:
            helper = response_helper(name, body, return_type)
            assertion = assertion_for(name, params, body, return_type)
            stub_count = fetch_stub_count(body)
            stubs = ", ".join([helper] * stub_count)
            tests.append(
                f"""  test("{name}", async () => {{
    stubFetch({stubs});
    {assertion}
  }});"""
            )
    xhr_helpers = ""
    if needs_xhr:
        xhr_helpers = """
class MockXHR {
  static instances: MockXHR[] = [];
  upload = { addEventListener: vi.fn() };
  status = 200;
  statusText = "OK";
  response: unknown = { ok: true };
  open = vi.fn();
  setRequestHeader = vi.fn();
  send = vi.fn();
  addEventListener = vi.fn((event: string, handler: () => void) => {
    if (event === "load") {
      this.loadHandler = handler;
    }
    if (event === "error") {
      this.errorHandler = handler;
    }
  });
  loadHandler: (() => void) | null = null;
  errorHandler: (() => void) | null = null;

  constructor() {
    MockXHR.instances.push(this);
  }
}

"""
    xhr_before_each = ""
    if needs_xhr:
        xhr_before_each = """
  beforeEach(() => {
    MockXHR.instances = [];
    vi.stubGlobal("XMLHttpRequest", MockXHR as unknown as typeof XMLHttpRequest);
  });
"""
    return f"""import {{ afterEach, describe, expect, test, vi{", beforeEach" if needs_xhr else ""} }} from "vitest";

import {{
  {imports},
}} from "@/lib/api";

const TOKEN = "test-token";
{xhr_helpers}
function jsonResponse(payload: unknown, status = 200): Response {{
  return new Response(JSON.stringify(payload), {{
    status,
    headers: {{ "content-type": "application/json" }},
  }});
}}

function blobResponse(content = "blob-data"): Response {{
  return new Response(new Blob([content]), {{ status: 200 }});
}}

function emptyOkResponse(status = 204): Response {{
  return new Response(null, {{ status }});
}}

function stubFetch(...responses: Response[]) {{
  const fetchMock = vi.fn();
  for (const response of responses) {{
    fetchMock.mockResolvedValueOnce(response);
  }}
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}}

describe("api {domain} clients", () => {{
{xhr_before_each}
  afterEach(() => {{
    vi.unstubAllGlobals();
  }});

{chr(10).join(tests)}
}});
"""


def main() -> None:
    source = api_source()
    functions = extract_functions(source)
    buckets: dict[str, list[str]] = defaultdict(list)
    func_map: dict[str, tuple[str, str, str]] = {}

    for name, params, body, return_type in functions:
        if name in SKIP or name in ME_COVERED:
            continue
        if any(name.startswith(prefix) for prefix in PRESENZE_PREFIXES):
            continue
        domain = domain_for(name)
        if domain == "presenze":
            continue
        buckets[domain].append(name)
        func_map[name] = (params, body, return_type)

    for domain, names in sorted(buckets.items()):
        if not names:
            continue
        content = render_file(domain, names, func_map)
        out = OUT_DIR / f"api-{domain}.test.ts"
        out.write_text(content)
        print(f"wrote {out.name}: {len(names)} tests")


if __name__ == "__main__":
    main()
