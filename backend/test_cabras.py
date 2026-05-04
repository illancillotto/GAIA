import asyncio
import sys
sys.path.insert(0, '/app')

async def main():
    from app.core.database import SessionLocal
    from app.services.elaborazioni_capacitas import pick_credential, _decrypt
    from app.modules.elaborazioni.capacitas.session import CapacitasSessionManager
    from app.modules.elaborazioni.capacitas.apps.involture.client import InVoltureClient
    from app.services.elaborazioni_capacitas_terreni import sync_terreni_batch
    from app.modules.elaborazioni.capacitas.models import (
        CapacitasTerreniBatchRequest, CapacitasTerreniBatchItem
    )
    from app.models.catasto_phase1 import CatConsorzioUnit, CatCapacitasTerrenoRow
    from app.models.capacitas import CapacitasCredential
    from sqlalchemy import select

    db = SessionLocal()
    
    credential = db.get(CapacitasCredential, 1)
    password = _decrypt(credential.password_encrypted)
    print(f'Credenziale: {credential.username}')

    print(f'Login Capacitas come {credential.username}...')
    async with CapacitasSessionManager(credential.username, password) as manager:
        await manager.activate_app('involture')
        client = InVoltureClient(manager)

        print('Ricerca frazioni per Cabras...')
        frazioni = await client.search_frazioni('Cabras')
        print(f'Frazioni trovate: {len(frazioni)}')
        for f in frazioni:
            print(f'  id={f.id!r} display={f.display!r}')

        if not frazioni:
            print('Nessuna frazione trovata, uscita.')
            return

        print('\n--- RICERCA Cabras foglio 24 particella 3 (sub vuoto) ---')
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
            fetch_certificati=False,
            fetch_details=False,
        )

        result = await sync_terreni_batch(db, client, request)
        item = result.items[0] if result.items else None
        print(f'Risultato: ok={item.ok if item else None}  total_rows={result.total_rows}')
        if item and not item.ok:
            print(f'  ERRORE: {item.error}')

        print('\n--- RIGHE RECUPERATE DA CAPACITAS ---')
        rows = db.execute(
            select(CatCapacitasTerrenoRow)
            .where(CatCapacitasTerrenoRow.foglio == '24', CatCapacitasTerrenoRow.particella == '3')
            .order_by(CatCapacitasTerrenoRow.id.desc())
            .limit(30)
        ).scalars().all()
        print(f'Rows in DB (foglio=24 particella=3): {len(rows)}')
        for r in rows:
            print(f'  sub={r.sub!r:10} visual_state={r.row_visual_state!r:20} cco={r.cco!r} anno={r.anno!r}')

        print('\n--- UNITA CONSORZIALI ---')
        units = db.execute(
            select(CatConsorzioUnit)
            .where(CatConsorzioUnit.foglio == '24', CatConsorzioUnit.particella == '3')
        ).scalars().all()
        print(f'CatConsorzioUnit (foglio=24 particella=3): {len(units)}')
        for u in units:
            print(f'  id={u.id} subalterno={u.subalterno!r} particella_id={u.particella_id} is_active={u.is_active}')

    db.close()

asyncio.run(main())
