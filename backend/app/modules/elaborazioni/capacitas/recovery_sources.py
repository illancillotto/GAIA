from __future__ import annotations

from app.modules.elaborazioni.capacitas.apps.incass.client import InCassClient
from app.modules.elaborazioni.capacitas.apps.involture.client import InVoltureClient
from app.modules.elaborazioni.capacitas.models import CapacitasInCassSearchResult
from app.modules.elaborazioni.capacitas.recovery_identity import normalize_identifier


def assert_source_identity(values, identifiers):
    observed = {normalize_identifier(value) for value in values} - {""}
    if not observed or not observed <= set(identifiers):
        raise ValueError("Identità fiscale della sorgente Capacitas assente o in conflitto")


class CanonicalInCassClient(InCassClient):
    def __init__(self, manager, identifiers):
        super().__init__(manager)
        self.identifiers = identifiers

    async def refresh_session(self):
        await super().refresh_session()
        await self._manager.activate_app("involture")

    async def search_notices(self, identifier):
        rows = {}
        for canonical_identifier in self.identifiers:
            result = await super().search_notices(canonical_identifier)
            if result.total != len(result.rows):
                raise ValueError("Ricerca avvisi Capacitas incompleta: totale e righe discordanti")
            for row in result.rows:
                assert_source_identity((row.codice_fiscale,), self.identifiers)
                if not row.avviso:
                    raise ValueError("Avviso Capacitas privo di riferimento")
                rows[row.avviso] = row
        return CapacitasInCassSearchResult(total=len(rows), rows=list(rows.values()))

    async def search_mailing_subjects(self, identifier):
        rows = {}
        for canonical_identifier in self.identifiers:
            for row in await super().search_mailing_subjects(canonical_identifier):
                assert_source_identity((row.codice_fiscale,), self.identifiers)
                if not row.external_id:
                    raise ValueError("Soggetto mailing Capacitas privo di identificativo")
                rows[row.external_id] = row
        return list(rows.values())


class ValidatedInVoltureClient(InVoltureClient):
    def __init__(self, manager, identifiers, archive):
        super().__init__(manager)
        self.identifiers = identifiers
        self.archive = archive

    async def relogin(self):
        await super().relogin()
        await self._manager.activate_app("incass")

    async def fetch_certificato(self, **context):
        certificate = await super().fetch_certificato(**context)
        self.archive(certificate.model_dump(mode="json"))
        owners = {normalize_identifier(owner.codice_fiscale) for owner in certificate.intestatari}
        if not set(self.identifiers).intersection(owners):
            raise ValueError("Il certificato non contiene l'identità canonica richiesta")
        for parcel in certificate.terreni:
            if not parcel.external_row_id:
                raise ValueError("Terreno nel certificato privo di identificativo sorgente")
            detail = await self.fetch_terreno_detail(external_row_id=parcel.external_row_id)
            if not detail.foglio or not detail.particella:
                raise ValueError("Dettaglio terreno privo di foglio o particella")
            parcel.foglio = detail.foglio
            parcel.particella = detail.particella
            parcel.sub = detail.sub
        self.archive(certificate.model_dump(mode="json"))
        return certificate


async def discover_involture(client, subject):
    rows = {}
    for identifier in subject.identifiers:
        result = await client.search_by_cf(identifier)
        if result.total != len(result.rows):
            raise ValueError("Ricerca anagrafica Capacitas incompleta")
        for row in result.rows:
            assert_source_identity((row.codice_fiscale, row.partita_iva), subject.identifiers)
            key = (row.id_ana, row.cco, row.com, row.pvc, row.fraz, row.sche)
            rows[key] = row.model_copy(
                update={"source_search_codici_fiscali": list(subject.identifiers)}
            )
    return list(rows.values())


def certificate_context(row):
    required = {"cco": row.cco, "com": row.com, "pvc": row.pvc, "fra": row.fraz}
    if any(value is None or not str(value).strip() for value in required.values()):
        raise ValueError("Contesto utenza Capacitas incompleto")
    return {**required, "ccs": row.sche or "00000"}
