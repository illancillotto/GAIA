from __future__ import annotations

import base64
import hashlib
import json
import logging
import ssl
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import certifi
import httpx

from app.core.config import settings
from app.modules.utenze.anpr.auth import PdndAuthManager

logger = logging.getLogger(__name__)

UTC = timezone.utc
ANPR_TIMEOUT_SECONDS = 30.0
_RESPONSE_MAP_VALIDATED = False


@dataclass(slots=True)
class C030Result:
    success: bool
    anpr_id: str | None
    id_operazione_anpr: str | None
    esito: str
    error_detail: str | None
    id_operazione_client: str


@dataclass(slots=True)
class C004Result:
    success: bool
    esito: str
    data_decesso: date | None
    id_operazione_anpr: str | None
    error_detail: str | None
    id_operazione_client: str
    raw_response: dict | None


class AnprClient:
    def __init__(self, auth_manager: PdndAuthManager | None = None, base_url: str | None = None) -> None:
        self.auth_manager = auth_manager or PdndAuthManager()
        self.base_url = (base_url or settings.anpr_base_url).rstrip("/")

    @staticmethod
    def _build_operation_id() -> str:
        # Keep the identifier compact and numeric to satisfy ANPR length constraints.
        return str(int(time.time() * 1000))

    @staticmethod
    def _resolve_verify() -> bool | ssl.SSLContext:
        if not settings.anpr_ssl_verify:
            return False
        bundle_path = (settings.anpr_ca_bundle_path or "").strip()
        if bundle_path:
            if not Path(bundle_path).exists():
                logger.warning("ANPR_CA_BUNDLE_PATH does not exist: %s", bundle_path)
                return True
            context = ssl.create_default_context(cafile=certifi.where())
            context.load_verify_locations(cafile=bundle_path)
            return context
        return True

    async def c030_get_anpr_id(self, codice_fiscale: str, subject_id_short: str) -> C030Result:
        id_operazione_client = self._build_operation_id()
        purpose_id = (settings.purpose_id_c030 or "").strip() or None
        request_payload = {
            "idOperazioneClient": id_operazione_client,
            "criteriRicerca": {
                "codiceFiscale": codice_fiscale,
            },
            "datiRichiesta": {
                "dataRiferimentoRichiesta": date.today().isoformat(),
                "motivoRichiesta": f"GAIA-CHECK-{subject_id_short}",
                "casoUso": "C030",
            },
        }

        try:
            response = await self._post_json(
                "/C030-servizioAccertamentoIdUnicoNazionale/v1/anpr-service-e002",
                request_payload,
                motivo_richiesta=f"GAIA-CHECK-{subject_id_short}",
                purpose_id=purpose_id,
            )
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return C030Result(
                    success=False,
                    anpr_id=None,
                    id_operazione_anpr=self._extract_id_operazione_anpr(exc.response),
                    esito="not_found",
                    error_detail=self._extract_problem_detail(exc.response),
                    id_operazione_client=id_operazione_client,
                )
            logger.exception("ANPR C030 HTTP error for subject=%s", subject_id_short)
            return C030Result(
                success=False,
                anpr_id=None,
                id_operazione_anpr=self._extract_id_operazione_anpr(exc.response),
                esito="error",
                error_detail=self._extract_problem_detail(exc.response),
                id_operazione_client=id_operazione_client,
            )
        except httpx.RequestError as exc:
            logger.exception("ANPR C030 request error for subject=%s", subject_id_short)
            return C030Result(
                success=False,
                anpr_id=None,
                id_operazione_anpr=None,
                esito="error",
                error_detail=str(exc),
                id_operazione_client=id_operazione_client,
            )

        payload = self._safe_json(response)
        anomalies = self._extract_anomalies(payload)
        if self._has_not_found_anomaly(anomalies):
            return C030Result(
                success=False,
                anpr_id=None,
                id_operazione_anpr=payload.get("idOperazioneANPR"),
                esito="not_found",
                error_detail=self._anomalies_to_text(anomalies),
                id_operazione_client=id_operazione_client,
            )
        if self._has_cancelled_anomaly(anomalies):
            return C030Result(
                success=False,
                anpr_id=None,
                id_operazione_anpr=payload.get("idOperazioneANPR"),
                esito="cancelled",
                error_detail=self._anomalies_to_text(anomalies),
                id_operazione_client=id_operazione_client,
            )

        anpr_id = (
            payload.get("listaSoggetti", {})
            .get("datiSoggetto", [{}])[0]
            .get("identificativi", {})
            .get("idANPR")
        )
        if anpr_id:
            return C030Result(
                success=True,
                anpr_id=str(anpr_id),
                id_operazione_anpr=payload.get("idOperazioneANPR"),
                esito="anpr_id_found",
                error_detail=None,
                id_operazione_client=id_operazione_client,
            )

        return C030Result(
            success=False,
            anpr_id=None,
            id_operazione_anpr=payload.get("idOperazioneANPR"),
            esito="error",
            error_detail="ANPR C030 response did not contain idANPR",
            id_operazione_client=id_operazione_client,
        )

    async def c004_check_death(self, anpr_id: str, subject_id_short: str) -> C004Result:
        id_operazione_client = self._build_operation_id()
        purpose_id = (settings.purpose_id_c004 or "").strip() or None
        request_payload = {
            "idOperazioneClient": id_operazione_client,
            "criteriRicerca": {
                "idANPR": anpr_id,
            },
            "verifica": {
                "datiDecesso": {
                    "dataEvento": (date.today() - timedelta(days=1)).isoformat(),
                }
            },
            "datiRichiesta": {
                "dataRiferimentoRichiesta": date.today().isoformat(),
                "motivoRichiesta": f"GAIA-CHECK-{subject_id_short}",
                "casoUso": "C004",
            },
        }

        try:
            response = await self._post_json(
                "/C004-servizioVerificaDichDecesso/v1/anpr-service-e002",
                request_payload,
                motivo_richiesta=f"GAIA-CHECK-{subject_id_short}",
                purpose_id=purpose_id,
            )
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return C004Result(
                    success=False,
                    esito="not_found",
                    data_decesso=None,
                    id_operazione_anpr=self._extract_id_operazione_anpr(exc.response),
                    error_detail=self._extract_problem_detail(exc.response),
                    id_operazione_client=id_operazione_client,
                    raw_response=self._safe_json(exc.response),
                )
            logger.exception("ANPR C004 HTTP error for subject=%s", subject_id_short)
            return C004Result(
                success=False,
                esito="error",
                data_decesso=None,
                id_operazione_anpr=self._extract_id_operazione_anpr(exc.response),
                error_detail=self._extract_problem_detail(exc.response),
                id_operazione_client=id_operazione_client,
                raw_response=self._safe_json(exc.response),
            )
        except httpx.RequestError as exc:
            logger.exception("ANPR C004 request error for subject=%s", subject_id_short)
            return C004Result(
                success=False,
                esito="error",
                data_decesso=None,
                id_operazione_anpr=None,
                error_detail=str(exc),
                id_operazione_client=id_operazione_client,
                raw_response=None,
            )

        payload = self._safe_json(response)
        if not _RESPONSE_MAP_VALIDATED:
            logger.warning("ANPR C004 raw response mapping not validated yet: %s", payload)

        anomalies = self._extract_anomalies(payload)
        info_items = self._extract_info_soggetto_ente(payload)
        data_decesso = self._extract_death_date(anomalies, info_items)

        if self._has_deceased_anomaly(anomalies) or self._has_deceased_info(info_items):
            return C004Result(
                success=True,
                esito="deceased",
                data_decesso=data_decesso,
                id_operazione_anpr=payload.get("idOperazioneANPR"),
                error_detail=None,
                id_operazione_client=id_operazione_client,
                raw_response=payload,
            )

        return C004Result(
            success=True,
            esito="alive",
            data_decesso=data_decesso,
            id_operazione_anpr=payload.get("idOperazioneANPR"),
            error_detail=None,
            id_operazione_client=id_operazione_client,
            raw_response=payload,
        )

    async def _post_json(self, path: str, payload: dict, *, motivo_richiesta: str, purpose_id: str | None) -> httpx.Response:
        endpoint_url = f"{self.base_url}{path}"
        payload_bytes = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        headers = await self._build_headers(
            payload_bytes,
            endpoint_url=endpoint_url,
            motivo_richiesta=motivo_richiesta,
            purpose_id=purpose_id,
        )
        async with httpx.AsyncClient(timeout=ANPR_TIMEOUT_SECONDS, verify=self._resolve_verify()) as client:
            response = await client.post(
                endpoint_url,
                content=payload_bytes,
                headers=headers,
            )
            response.raise_for_status()
            return response

    async def _build_headers(
        self,
        payload_bytes: bytes,
        *,
        endpoint_url: str,
        motivo_richiesta: str,
        purpose_id: str | None,
    ) -> dict[str, str]:
        tracking_evidence = self.auth_manager.build_agid_jwt_tracking_evidence(
            endpoint_url=endpoint_url,
            purpose_id=purpose_id,
        )
        tracking_digest = hashlib.sha256(tracking_evidence.encode("utf-8")).hexdigest()
        voucher = await self.auth_manager.get_voucher(purpose_id=purpose_id, tracking_digest=tracking_digest)
        digest_value = base64.b64encode(hashlib.sha256(payload_bytes).digest()).decode("ascii")
        digest_header = f"SHA-256={digest_value}"
        return {
            "Authorization": f"Bearer {voucher}",
            "Accept": "application/json",
            "Digest": digest_header,
            "Agid-JWT-Signature": self.auth_manager.build_agid_jwt_signature(
                payload_bytes,
                endpoint_url=endpoint_url,
                digest_header=digest_header,
            ),
            "Agid-JWT-TrackingEvidence": tracking_evidence,
            "Content-Type": "application/json",
        }

    @staticmethod
    def _safe_json(response: httpx.Response) -> dict | None:
        try:
            payload = response.json()
        except ValueError:
            return None
        return payload if isinstance(payload, dict) else None

    @staticmethod
    def _extract_id_operazione_anpr(response: httpx.Response) -> str | None:
        payload = AnprClient._safe_json(response)
        if not payload:
            return None
        value = payload.get("idOperazioneANPR")
        return str(value) if value else None

    @staticmethod
    def _extract_problem_detail(response: httpx.Response) -> str:
        payload = AnprClient._safe_json(response)
        if payload:
            errors = payload.get("listaErrori") or payload.get("listaAnomalie") or []
            if isinstance(errors, list) and errors:
                return AnprClient._anomalies_to_text(errors)
        return response.text or f"HTTP {response.status_code}"

    @staticmethod
    def _extract_anomalies(payload: dict | None) -> list[dict]:
        anomalies = (payload or {}).get("listaAnomalie") or []
        return [item for item in anomalies if isinstance(item, dict)]

    @staticmethod
    def _extract_info_soggetto_ente(payload: dict | None) -> list[dict]:
        rows = ((payload or {}).get("listaSoggetti") or {}).get("datiSoggetto") or []
        if not rows or not isinstance(rows, list):
            return []
        info_items = rows[0].get("infoSoggettoEnte") or []
        return [item for item in info_items if isinstance(item, dict)]

    @staticmethod
    def _anomalies_to_text(anomalies: list[dict]) -> str:
        parts: list[str] = []
        for item in anomalies:
            text = " | ".join(
                str(value).strip()
                for value in (
                    item.get("codiceErroreAnomalia"),
                    item.get("tipoErroreAnomalia"),
                    item.get("testoErroreAnomalia"),
                    item.get("valoreErroreAnomalia"),
                )
                if value
            )
            if text:
                parts.append(text)
        return "; ".join(parts) or "ANPR anomaly"

    @classmethod
    def _has_not_found_anomaly(cls, anomalies: list[dict]) -> bool:
        return any(cls._contains_any(item, ["non trovato", "not found", "assen", "inesistent"]) for item in anomalies)

    @classmethod
    def _has_cancelled_anomaly(cls, anomalies: list[dict]) -> bool:
        return any(
            cls._contains_any(item, ["cancell"]) and not cls._contains_any(item, ["decesso", "decedut", "morto"])
            for item in anomalies
        )

    @classmethod
    def _has_deceased_anomaly(cls, anomalies: list[dict]) -> bool:
        return any(cls._contains_any(item, ["decesso", "decedut", "morto"]) for item in anomalies)

    @classmethod
    def _has_deceased_info(cls, info_items: list[dict]) -> bool:
        for item in info_items:
            chiave = str(item.get("chiave") or "").strip().lower()
            valore = str(item.get("valore") or "").strip().upper()
            valore_testo = str(item.get("valoreTesto") or "").strip().lower()
            dettaglio = str(item.get("dettaglio") or "").strip().lower()
            if "decesso" in chiave or "deced" in chiave or "morto" in chiave:
                if valore in {"A", "S"} or "si" in valore_testo or "deced" in dettaglio:
                    return True
            if valore in {"A", "S"} and cls._contains_any(item, ["decesso", "decedut", "morto"]):
                return True
        return False

    @classmethod
    def _contains_any(cls, item: dict, needles: list[str]) -> bool:
        haystack = " ".join(str(value).lower() for value in item.values() if value is not None)
        return any(needle in haystack for needle in needles)

    @staticmethod
    def _extract_death_date(anomalies: list[dict], info_items: list[dict]) -> date | None:
        for item in info_items:
            parsed = AnprClient._parse_iso_date(item.get("valoreData"))
            if parsed:
                return parsed
        for item in anomalies:
            parsed = AnprClient._parse_iso_date(item.get("valoreErroreAnomalia"))
            if parsed:
                return parsed
        return None

    @staticmethod
    def _parse_iso_date(value: object) -> date | None:
        if not value or not isinstance(value, str):
            return None
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            return None
