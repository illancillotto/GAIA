from __future__ import annotations

import ipaddress
import re

from sqlalchemy.orm import Session

from app.models.application_user import ApplicationUser
from app.modules.wiki.schemas import WikiChatResponse
from app.modules.wiki.services.network_read_models import (
    extract_network_device_identifier,
    get_network_dashboard_summary_read_model,
    get_network_device_read_model,
    get_network_firewall_summary_read_model,
)
from app.modules.wiki.services.policy import WikiToolMeta
from app.modules.wiki.services.response_composer import build_live_data_response
from app.modules.wiki.services.tool_registry_common import WikiToolDefinition, contains_any, score_terms

_IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")


def _match_network_dashboard_summary(question: str) -> int:
    if not contains_any(
        question,
        "rete",
        "network",
        "dashboard rete",
        "riepilogo rete",
        "stato rete",
        "network summary",
        "network dashboard",
        "riassunto rete",
    ):
        return 0
    return 8 + score_terms(
        question,
        "rete",
        "network",
        "dashboard",
        "riepilogo",
        "summary",
        "online",
        "dispositivi",
        "device",
        "firewall",
    )


def _match_network_firewall_summary(question: str) -> int:
    if not contains_any(question, "firewall", "sophos", "syslog", "snmp"):
        return 0
    return 10 + score_terms(
        question,
        "firewall",
        "sophos",
        "syslog",
        "snmp",
        "blocchi",
        "blocked",
        "denied",
        "wan",
    )


def _match_network_device_lookup(question: str) -> int:
    match = _IPV4_RE.search(question)
    if match is not None:
        try:
            ipaddress.ip_address(match.group(0))
        except ValueError:
            return 0
        return 12 + score_terms(question, "device", "dispositivo", "host", "pc", "ip", "rete", "network")

    identifier = extract_network_device_identifier(question)
    if identifier and contains_any(question, "device", "dispositivo", "host", "pc", "computer"):
        return 7 + score_terms(question, "device", "dispositivo", "host", "pc", "computer", "rete", "network")
    return 0


def _network_dashboard_summary(db: Session, current_user: ApplicationUser, question: str) -> WikiChatResponse:
    payload = get_network_dashboard_summary_read_model(db, current_user)
    answer = (
        "Dati live rete: "
        f"{payload['total_devices']} dispositivi totali, {payload['online_devices']} online, "
        f"{payload['offline_devices']} offline, {payload['firewalls_online']} firewall online, "
        f"{payload['open_alerts']} alert aperti e {payload['scans_last_24h']} scansioni nelle ultime 24 ore."
    )
    excerpt = (
        f"Dispositivi totali {payload['total_devices']}, online {payload['online_devices']}, "
        f"firewall online {payload['firewalls_online']}, alert aperti {payload['open_alerts']}."
    )
    return build_live_data_response(
        answer=answer,
        tool_name="get_network_dashboard_summary",
        evidence_label="Dashboard rete",
        source_key="rete.dashboard.summary",
        excerpt=excerpt,
        payload=payload,
    )


def _network_firewall_summary(db: Session, current_user: ApplicationUser, question: str) -> WikiChatResponse:
    payload = get_network_firewall_summary_read_model(db, current_user)
    top_firewalls = payload.get("top_firewalls") or []
    top_names = ", ".join(str(item["name"]) for item in top_firewalls[:3]) if top_firewalls else "n/d"
    answer = (
        "Dati live firewall: "
        f"{payload['firewall_count']} appliance censite, {payload['online_firewalls']} online, "
        f"{payload['events_last_24h']} eventi nelle ultime 24 ore e {payload['blocked_events_last_24h']} blocchi."
    )
    excerpt = (
        f"Firewall {payload['firewall_count']}, online {payload['online_firewalls']}, "
        f"eventi 24h {payload['events_last_24h']}, blocchi 24h {payload['blocked_events_last_24h']}, top {top_names}."
    )
    return build_live_data_response(
        answer=answer,
        tool_name="get_network_firewall_summary",
        evidence_label="Riepilogo firewall rete",
        source_key="rete.firewalls.summary",
        excerpt=excerpt,
        payload=payload,
    )


def _find_network_device(db: Session, current_user: ApplicationUser, question: str) -> WikiChatResponse:
    identifier = extract_network_device_identifier(question)
    if not identifier:
        return build_live_data_response(
            answer="Per cercare un dispositivo di rete devo ricevere almeno un IP esplicito o un nome host/dispositivo riconoscibile.",
            tool_name="find_network_device",
            evidence_label="Lookup dispositivo rete non eseguito",
            source_key="rete.devices.lookup",
            excerpt="Identificatore del dispositivo non individuato nella domanda.",
        )

    payload = get_network_device_read_model(db, current_user, identifier)
    if payload is None:
        return build_live_data_response(
            answer=f"Non ho trovato nessun dispositivo di rete che corrisponda a {identifier}.",
            tool_name="find_network_device",
            evidence_label="Dispositivo rete non trovato",
            source_key=f"rete.devices.{identifier}",
            excerpt=f"Lookup device rete eseguito per: {identifier}.",
        )

    assigned_user = payload.get("assigned_user") or {}
    assigned_label = assigned_user.get("full_name") or assigned_user.get("username") or "n/d"
    answer = (
        "Lookup dispositivo rete: "
        f"{payload['resolved_label']} ({payload['ip_address']}), stato {payload['status']}, "
        f"hostname {payload['hostname'] or 'n/d'}, utente {assigned_label}, "
        f"tipo {payload['device_type'] or 'n/d'}, sistema {payload['operating_system'] or 'n/d'}."
    )
    excerpt = (
        f"Device {payload['resolved_label']} su IP {payload['ip_address']}, "
        f"stato {payload['status']}, utente {assigned_label}."
    )
    return build_live_data_response(
        answer=answer,
        tool_name="find_network_device",
        evidence_label="Dettaglio dispositivo rete",
        source_key=f"rete.devices.{payload['ip_address']}",
        excerpt=excerpt,
        payload=payload,
    )


RETE_TOOLS: tuple[WikiToolDefinition, ...] = (
    WikiToolDefinition(
        meta=WikiToolMeta(name="get_network_firewall_summary", module_key="rete"),
        intents=("live_data",),
        priority=90,
        matcher=_match_network_firewall_summary,
        handler=_network_firewall_summary,
    ),
    WikiToolDefinition(
        meta=WikiToolMeta(name="find_network_device", module_key="rete"),
        intents=("live_data",),
        priority=88,
        matcher=_match_network_device_lookup,
        handler=_find_network_device,
    ),
    WikiToolDefinition(
        meta=WikiToolMeta(name="get_network_dashboard_summary", module_key="rete"),
        intents=("live_data",),
        priority=20,
        matcher=_match_network_dashboard_summary,
        handler=_network_dashboard_summary,
    ),
)
