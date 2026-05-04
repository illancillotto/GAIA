"""
Sync e verifica di una particella del consorzio Capacitas.

Uso:
    docker exec -w /app gaia-backend python test_fix_verification.py <comune> <foglio> <particella>

Esempi:
    docker exec -w /app gaia-backend python test_fix_verification.py Cabras 24 3
    docker exec -w /app gaia-backend python test_fix_verification.py Cabras 24 37
    docker exec -w /app gaia-backend python test_fix_verification.py Cabras 1 4
    docker exec -w /app gaia-backend python test_fix_verification.py Uras 1 680
"""
import asyncio
import sys
sys.path.insert(0, '/app')


def _sep(title: str = "") -> None:
    print(f"\n{'=' * 60}")
    if title:
        print(title)
        print('=' * 60)


async def main(comune_input: str, foglio: str, particella: str) -> None:
    from app.core.database import SessionLocal
    from app.services.elaborazioni_capacitas import _decrypt
    from app.modules.elaborazioni.capacitas.session import CapacitasSessionManager
    from app.modules.elaborazioni.capacitas.apps.involture.client import InVoltureClient
    from app.services.elaborazioni_capacitas_terreni import sync_terreni_batch
    from app.modules.elaborazioni.capacitas.models import (
        CapacitasTerreniBatchRequest, CapacitasTerreniBatchItem,
    )
    from app.models.catasto_phase1 import (
        CatParticella, CatConsorzioUnit, CatConsorzioOccupancy,
        CatCapacitasTerrenoRow, CatCapacitasCertificato, CatCapacitasIntestatario,
        CatUtenzaIrrigua, CatUtenzaIntestatario, CatComune,
    )
    from app.models.capacitas import CapacitasCredential
    from sqlalchemy import func, or_, select

    db = SessionLocal()
    credential = db.get(CapacitasCredential, 1)
    password = _decrypt(credential.password_encrypted)

    # Risolve CatComune dal nome (case-insensitive)
    comune = db.scalar(
        select(CatComune).where(func.lower(CatComune.nome_comune) == comune_input.lower())
    )
    if comune is None:
        # Prova ricerca parziale
        comuni_candidati = db.execute(
            select(CatComune).where(CatComune.nome_comune.ilike(f"%{comune_input}%"))
        ).scalars().all()
        if not comuni_candidati:
            print(f"ERRORE: comune '{comune_input}' non trovato in DB.")
            db.close()
            return
        if len(comuni_candidati) > 1:
            print(f"Comuni trovati per '{comune_input}':")
            for c in comuni_candidati:
                print(f"  {c.nome_comune}")
            print("Specifica meglio il nome.")
            db.close()
            return
        comune = comuni_candidati[0]

    label = f"{comune.nome_comune} {foglio}/{particella}"
    print(f"\nComune: {comune.nome_comune} (id={comune.id}, cap_code={comune.cod_comune_capacitas}, belfiore={comune.codice_catastale})")

    # ------------------------------------------------------------------
    _sep(f"STATO DB PRE-SYNC — {label}")
    # ------------------------------------------------------------------

    parts = db.execute(
        select(CatParticella).where(
            CatParticella.comune_id == comune.id,
            CatParticella.foglio == foglio,
            CatParticella.particella == particella,
        )
    ).scalars().all()
    print(f"\nParticelle AE ({len(parts)}):")
    for p in parts:
        print(f"  sub={p.subalterno!r:6} is_current={p.is_current} sup={p.superficie_mq} mq")

    utenze = db.execute(
        select(CatUtenzaIrrigua).where(
            CatUtenzaIrrigua.comune_id == comune.id,
            CatUtenzaIrrigua.foglio == foglio,
            CatUtenzaIrrigua.particella == particella,
        )
    ).scalars().all()
    print(f"\nUtenze irrigue ({len(utenze)}):")
    for u in utenze:
        ni = db.scalar(select(func.count(CatUtenzaIntestatario.id)).where(CatUtenzaIntestatario.utenza_id == u.id))
        print(f"  cco={u.cco!r:20} sub={u.subalterno!r:6} anno={u.anno_campagna} intestatari={ni}")

    # CatConsorzioUnit: filtra per comune_id o source_comune_id (la particella potrebbe
    # esistere solo nel consorzio e non nell'AE, quindi serve source_comune_id come fallback)
    units_pre = db.execute(
        select(CatConsorzioUnit).where(
            or_(
                CatConsorzioUnit.comune_id == comune.id,
                CatConsorzioUnit.source_comune_id == comune.id,
                CatConsorzioUnit.cod_comune_capacitas == comune.cod_comune_capacitas,
            ),
            CatConsorzioUnit.foglio == foglio,
            CatConsorzioUnit.particella == particella,
        )
    ).scalars().all()
    print(f"\nUnità consorziali ({len(units_pre)}):")
    for u in units_pre:
        occs = db.execute(
            select(CatConsorzioOccupancy)
            .where(CatConsorzioOccupancy.unit_id == u.id)
            .order_by(CatConsorzioOccupancy.id.desc())
            .limit(5)
        ).scalars().all()
        for occ in occs:
            utenza_ok = "OK  " if occ.utenza_id else "NONE"
            print(f"  sub={u.subalterno!r:6} utenza_id={utenza_ok} is_current={str(occ.is_current):5} cco={occ.cco!r}")

    # CatCapacitasTerrenoRow: filtra per belfiore o cod_comune_capacitas
    rows_pre = db.execute(
        select(CatCapacitasTerrenoRow).where(
            or_(
                CatCapacitasTerrenoRow.belfiore == comune.codice_catastale,
                CatCapacitasTerrenoRow.com == str(comune.cod_comune_capacitas),
            ),
            CatCapacitasTerrenoRow.foglio == foglio,
            CatCapacitasTerrenoRow.particella == particella,
        )
        .order_by(CatCapacitasTerrenoRow.id.desc())
        .limit(10)
    ).scalars().all()
    print(f"\nRighe Capacitas in DB ({len(rows_pre)}):")
    for r in rows_pre:
        print(f"  sub={r.sub!r:8} cco={r.cco!r:20} anno={r.anno} state={r.row_visual_state}")

    # ------------------------------------------------------------------
    _sep(f"SYNC Capacitas — {label}")
    # ------------------------------------------------------------------

    async with CapacitasSessionManager(credential.username, password) as manager:
        await manager.activate_app('involture')
        client = InVoltureClient(manager)

        frazioni = await client.search_frazioni(comune.nome_comune)
        print(f"Frazioni '{comune.nome_comune}': {len(frazioni)}")
        for f in frazioni:
            print(f"  id={f.id!r} label={f.display!r}")

        # Scansione diagnostica: mostra quante righe restituisce ogni frazione
        if len(frazioni) > 1:
            from app.modules.elaborazioni.capacitas.models import CapacitasTerreniSearchRequest
            print(f"\nScansione frazioni per {foglio}/{particella}:")
            for fraz in frazioni:
                try:
                    search_req = CapacitasTerreniSearchRequest(
                        frazione_id=fraz.id,
                        sezione='',
                        foglio=foglio,
                        particella=particella,
                        sub='',
                    )
                    result = await client.search_terreni(search_req)
                    rows = result.rows if result else []
                    if rows:
                        stati = [r.row_visual_state for r in rows]
                        ccos = list({r.cco for r in rows if r.cco})
                        print(f"  {fraz.id!r:5} {fraz.display!r:40} -> {len(rows)} righe | stati={stati} | CCO={ccos}")
                    else:
                        print(f"  {fraz.id!r:5} {fraz.display!r:40} -> 0 righe")
                except Exception as exc:
                    print(f"  {fraz.id!r:5} {fraz.display!r:40} -> ERRORE: {exc}")

        request = CapacitasTerreniBatchRequest(
            items=[CapacitasTerreniBatchItem(
                label=label,
                comune=comune.nome_comune,
                sezione='',
                foglio=foglio,
                particella=particella,
                sub='',
            )],
            continue_on_error=True,
            credential_id=1,
            fetch_certificati=True,
            fetch_details=False,
        )
        result = await sync_terreni_batch(db, client, request)
        item = result.items[0] if result.items else None
        print(f"\nRisultato sync:")
        print(f"  ok={item.ok if item else None}")
        print(f"  righe Capacitas: {result.total_rows}")
        print(f"  certificati:     {result.imported_certificati}")
        print(f"  unità:           {result.linked_units}")
        print(f"  occupancies:     {result.linked_occupancies}")
        if item and not item.ok:
            print(f"  ERRORE: {item.error}")

    # ------------------------------------------------------------------
    _sep(f"STATO DB POST-SYNC — {label}")
    # ------------------------------------------------------------------

    rows_post = db.execute(
        select(CatCapacitasTerrenoRow).where(
            or_(
                CatCapacitasTerrenoRow.belfiore == comune.codice_catastale,
                CatCapacitasTerrenoRow.com == str(comune.cod_comune_capacitas),
            ),
            CatCapacitasTerrenoRow.foglio == foglio,
            CatCapacitasTerrenoRow.particella == particella,
        )
        .order_by(CatCapacitasTerrenoRow.id.desc())
        .limit(20)
    ).scalars().all()
    print(f"\nRighe Capacitas ({len(rows_post)}):")
    for r in rows_post:
        print(f"  sub={r.sub!r:8} cco={r.cco!r:20} anno={r.anno} state={r.row_visual_state}")

    units_post = db.execute(
        select(CatConsorzioUnit).where(
            or_(
                CatConsorzioUnit.comune_id == comune.id,
                CatConsorzioUnit.source_comune_id == comune.id,
                CatConsorzioUnit.cod_comune_capacitas == comune.cod_comune_capacitas,
            ),
            CatConsorzioUnit.foglio == foglio,
            CatConsorzioUnit.particella == particella,
        )
    ).scalars().all()
    print(f"\nUnità consorziali ({len(units_post)}):")
    for unit in units_post:
        occs = db.execute(
            select(CatConsorzioOccupancy)
            .where(CatConsorzioOccupancy.unit_id == unit.id)
            .order_by(CatConsorzioOccupancy.id.desc())
            .limit(5)
        ).scalars().all()
        for occ in occs:
            utenza_ok = "OK  " if occ.utenza_id else "NONE"
            print(f"  sub={unit.subalterno!r:6} utenza_id={utenza_ok} is_current={str(occ.is_current):5} cco={occ.cco!r}")

    all_ccos = list({r.cco for r in rows_post if r.cco})
    print(f"\nCertificati per CCO ({len(all_ccos)} distinti):")
    for cco in sorted(all_ccos):
        cert = db.scalar(
            select(CatCapacitasCertificato)
            .where(CatCapacitasCertificato.cco == cco)
            .order_by(CatCapacitasCertificato.collected_at.desc())
        )
        if cert is None:
            print(f"  CCO={cco:20} — nessun certificato")
            continue
        ints = db.execute(
            select(CatCapacitasIntestatario).where(CatCapacitasIntestatario.certificato_id == cert.id)
        ).scalars().all()
        print(f"  CCO={cco:20} intestatari={len(ints)}")
        for i in ints:
            print(f"    -> {i.denominazione!r:40} CF={i.codice_fiscale!r}")

    print(f"\nUtenze irrigue post-sync ({len(utenze)}):")
    for u in utenze:
        db.refresh(u)
        intestatari = db.execute(
            select(CatUtenzaIntestatario).where(CatUtenzaIntestatario.utenza_id == u.id)
        ).scalars().all()
        print(f"  cco={u.cco!r:20} sub={u.subalterno!r:6} intestatari={len(intestatari)}")
        for i in intestatari:
            print(f"    -> {i.denominazione!r:40} CF={i.codice_fiscale!r}")

    db.close()
    _sep(f"COMPLETATO — {label}")


if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) != 3:
        print("Uso: python test_fix_verification.py <comune> <foglio> <particella>")
        print("Es:  python test_fix_verification.py Cabras 24 3")
        sys.exit(1)
    asyncio.run(main(comune_input=args[0], foglio=args[1], particella=args[2]))
