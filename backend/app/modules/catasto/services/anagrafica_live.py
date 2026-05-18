from __future__ import annotations

import logging

from app.schemas.catasto_phase1 import CatAnagraficaMatch

logger = logging.getLogger(__name__)


class CapacitasLiveAuthoritativeSanitizer:
    """Sanitizes authoritative Capacitas-live matches for cadastral bulk export."""

    def sanitize(self, match: CatAnagraficaMatch) -> CatAnagraficaMatch:
        has_context = bool(
            (match.cert_com or "").strip()
            and (match.cert_pvc or "").strip()
            and (match.cert_fra or "").strip()
        )
        if has_context:
            return match

        if match.intestatari:
            logger.warning(
                "Capacitas live sanitize cleared owners without context: particella_id=%s cco=%s comune=%s foglio=%s particella=%s",
                match.particella_id,
                match.utenza_latest.cco if match.utenza_latest is not None else None,
                match.comune,
                match.foglio,
                match.particella,
            )
        match.intestatari = []
        match.stato_ruolo = None
        match.stato_cnc = None
        match.cert_com = None
        match.cert_pvc = None
        match.cert_fra = None
        match.cert_ccs = None
        return match
