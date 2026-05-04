"""
Test manuale di verifica per i due bug fix su Cabras foglio 24 / particella 3.

Uso:
    docker exec -w /app gaia-backend python test_fix_verification.py

Verifica:
  Fix 1 - Anno fallback: utenza_id non deve essere None per sub a (CCO 0A1462373)
  Fix 2 - Refetch cert: dopo refetch, CCO 0A1462373 e 0A1031735 devono avere intestatari
"""
import asyncio
import sys
sys.path.insert(0, '/app')


async def main():
    from app.core.database import SessionLocal
    from app.services.elaborazioni_capacitas import _decrypt
    from app.modules.elaborazioni.capacitas.session import CapacitasSessionManager
    from app.modules.elaborazioni.capacitas.apps.involture.client import InVoltureClient
    from app.services.elaborazioni_capacitas_terreni import (
        sync_terreni_batch,
        refetch_certificati_senza_intestatari,
        _find_utenza_for_terreno_row,
    )
    from app.modules.elaborazioni.capacitas.models import (
        CapacitasTerreniBatchRequest, CapacitasTerreniBatchItem, CapacitasTerrenoRow,
    )
    from app.models.catasto_phase1 import (
        CatConsorzioUnit, CatConsorzioOccupancy, CatCapacitasTerrenoRow,
        CatCapacitasCertificato, CatCapacitasIntestatario, CatUtenzaIrrigua,
        CatUtenzaIntestatario,
    )
    from app.models.capacitas import CapacitasCredential
    from sqlalchemy import select, func

    db = SessionLocal()
    credential = db.get(CapacitasCredential, 1)
    password = _decrypt(credential.password_encrypted)

    print("=" * 60)
    print("STATO ATTUALE DB (prima del test)")
    print("=" * 60)

    # Stato attuale utenze Cabras 24/3
    utenze = db.execute(
        select(CatUtenzaIrrigua)
        .where(CatUtenzaIrrigua.foglio == '24', CatUtenzaIrrigua.particella == '3')
    ).scalars().all()
    print(f"\nUtenze foglio=24 particella=3: {len(utenze)}")
    for u in utenze:
        intestatari_count = db.scalar(
            select(func.count(CatUtenzaIntestatario.id)).where(CatUtenzaIntestatario.utenza_id == u.id)
        )
        print(f"  cco={u.cco!r:20} sub={u.subalterno!r:6} anno={u.anno_campagna} intestatari={intestatari_count}")

    # Stato cert senza intestatari (globale)
    subq = select(CatCapacitasIntestatario.certificato_id).distinct().scalar_subquery()
    empty_count = db.scalar(
        select(func.count(CatCapacitasCertificato.id))
        .where(CatCapacitasCertificato.id.notin_(subq))
    )
    total_certs = db.scalar(select(func.count(CatCapacitasCertificato.id)))
    print(f"\nCertificati totali: {total_certs}")
    print(f"Certificati senza intestatari: {empty_count}")

    # Cert specifici per Cabras sub a e sub b
    target_ccos = ['0A1462373', '0A1031735']
    for cco in target_ccos:
        certs = db.execute(
            select(CatCapacitasCertificato)
            .where(CatCapacitasCertificato.cco == cco)
            .order_by(CatCapacitasCertificato.collected_at.desc())
            .limit(3)
        ).scalars().all()
        print(f"\nCertificati CCO {cco}: {len(certs)} snapshot")
        for c in certs:
            n = db.scalar(
                select(func.count(CatCapacitasIntestatario.id))
                .where(CatCapacitasIntestatario.certificato_id == c.id)
            )
            print(f"  collected_at={c.collected_at.date()} intestatari={n}")

    print("\n" + "=" * 60)
    print("FIX 1: Verifica anno fallback con una nuova sync Cabras 24/3")
    print("=" * 60)

    async with CapacitasSessionManager(credential.username, password) as manager:
        await manager.activate_app('involture')
        client = InVoltureClient(manager)

        frazioni = await client.search_frazioni('Cabras')
        print(f"Frazioni Cabras: {len(frazioni)}")

        request = CapacitasTerreniBatchRequest(
            items=[CapacitasTerreniBatchItem(
                label='Cabras 24/3',
                comune='Cabras',
                sezione='',
                foglio='24',
                particella='3',
                sub='',
            )],
            continue_on_error=True,
            credential_id=1,
            fetch_certificati=True,
            fetch_details=False,
        )

        result = await sync_terreni_batch(db, client, request)
        item = result.items[0] if result.items else None
        print(f"Sync result: ok={item.ok if item else None} rows={result.total_rows} cert={result.imported_certificati}")
        if item and not item.ok:
            print(f"  ERRORE: {item.error}")

    print("\nVerifica occupancies dopo sync:")
    rows = db.execute(
        select(CatCapacitasTerrenoRow)
        .where(CatCapacitasTerrenoRow.foglio == '24', CatCapacitasTerrenoRow.particella == '3')
        .order_by(CatCapacitasTerrenoRow.id.desc())
        .limit(10)
    ).scalars().all()
    for r in rows:
        utenza = db.scalar(select(CatUtenzaIrrigua).where(CatUtenzaIrrigua.id == r.id)) if r else None
        print(f"  sub={r.sub!r:8} cco={r.cco!r:20} anno={r.anno} state={r.row_visual_state}")

    # Verifica occupancies e utenza_id
    units = db.execute(
        select(CatConsorzioUnit)
        .where(CatConsorzioUnit.foglio == '24', CatConsorzioUnit.particella == '3')
    ).scalars().all()
    print(f"\nConsorzioUnit foglio=24 particella=3: {len(units)}")
    for unit in units:
        occs = db.execute(
            select(CatConsorzioOccupancy)
            .where(CatConsorzioOccupancy.unit_id == unit.id)
            .order_by(CatConsorzioOccupancy.id.desc())
            .limit(3)
        ).scalars().all()
        for occ in occs:
            print(f"  sub={unit.subalterno!r:6} utenza_id={'OK' if occ.utenza_id else 'NONE':4} is_current={occ.is_current} cco={occ.cco!r}")

    print("\n" + "=" * 60)
    print("FIX 2: Refetch certificati senza intestatari")
    print("=" * 60)

    async with CapacitasSessionManager(credential.username, password) as manager:
        await manager.activate_app('involture')
        client = InVoltureClient(manager)

        # IMPORTANTE: non chiamare search_terreni prima del refetch
        # per evitare il bug di session state Capacitas
        print("Avvio refetch (max 100 certificati senza intestatari)...")
        count = await refetch_certificati_senza_intestatari(db, client, limit=100, throttle_ms=300)
        print(f"Certificati ri-fetchati: {count}")

    print("\nVerifica post-refetch per Cabras CCO:")
    for cco in target_ccos:
        certs = db.execute(
            select(CatCapacitasCertificato)
            .where(CatCapacitasCertificato.cco == cco)
            .order_by(CatCapacitasCertificato.collected_at.desc())
            .limit(3)
        ).scalars().all()
        for c in certs:
            n = db.scalar(
                select(func.count(CatCapacitasIntestatario.id))
                .where(CatCapacitasIntestatario.certificato_id == c.id)
            )
            print(f"  CCO={cco} collected_at={c.collected_at.date()} intestatari={n}")

    # Verifica utenza intestatari
    print("\nVerifica CatUtenzaIntestatario per foglio=24 particella=3:")
    utenze_after = db.execute(
        select(CatUtenzaIrrigua)
        .where(CatUtenzaIrrigua.foglio == '24', CatUtenzaIrrigua.particella == '3')
    ).scalars().all()
    for u in utenze_after:
        intestatari = db.execute(
            select(CatUtenzaIntestatario).where(CatUtenzaIntestatario.utenza_id == u.id)
        ).scalars().all()
        print(f"  cco={u.cco!r:20} sub={u.subalterno!r:6} intestatari={len(intestatari)}")
        for i in intestatari:
            print(f"    -> {i.denominazione!r} CF={i.codice_fiscale!r}")

    db.close()
    print("\n" + "=" * 60)
    print("TEST COMPLETATO")
    print("=" * 60)


asyncio.run(main())
