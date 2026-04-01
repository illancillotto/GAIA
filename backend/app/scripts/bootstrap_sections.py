from app.core.database import SessionLocal
from app.models.section_permission import Section
from app.repositories.section_permission import create_section
from app.schemas.permissions import SectionCreate

DEFAULT_SECTIONS = [
    ("accessi.dashboard", "Dashboard NAS Control", "accessi", "viewer"),
    ("accessi.users", "Utenti NAS", "accessi", "viewer"),
    ("accessi.groups", "Gruppi NAS", "accessi", "viewer"),
    ("accessi.shares", "Cartelle condivise", "accessi", "viewer"),
    ("accessi.permissions", "Permessi effettivi", "accessi", "viewer"),
    ("accessi.reviews", "Review NAS", "accessi", "reviewer"),
    ("accessi.export", "Export", "accessi", "reviewer"),
    ("accessi.sync", "Sincronizzazione NAS", "accessi", "admin"),
    ("accessi.snapshots", "Snapshot", "accessi", "admin"),
    ("rete.dashboard", "Dashboard Rete", "rete", "viewer"),
    ("rete.devices", "Dispositivi", "rete", "viewer"),
    ("rete.map", "Mappa di rete", "rete", "viewer"),
    ("rete.alerts", "Alert", "rete", "viewer"),
    ("rete.scan", "Scansione manuale", "rete", "admin"),
    ("rete.export", "Export rete", "rete", "reviewer"),
    ("inventario.dashboard", "Dashboard Inventario", "inventario", "viewer"),
    ("inventario.devices", "Dispositivi IT", "inventario", "viewer"),
    ("inventario.warranties", "Garanzie", "inventario", "viewer"),
    ("inventario.assignments", "Assegnazioni", "inventario", "viewer"),
    ("inventario.import", "Import CSV", "inventario", "admin"),
    ("inventario.export", "Export inventario", "inventario", "reviewer"),
    ("inventario.locations", "Sedi", "inventario", "admin"),
    ("catasto.dashboard", "Dashboard Catasto", "catasto", "viewer"),
    ("catasto.single", "Visura singola", "catasto", "viewer"),
    ("catasto.batch", "Batch Catasto", "catasto", "viewer"),
    ("catasto.documents", "Archivio documenti Catasto", "catasto", "viewer"),
    ("catasto.credentials", "Credenziali SISTER", "catasto", "admin"),
    ("utenze.dashboard", "Dashboard Utenze", "utenze", "viewer"),
    ("utenze.subjects", "Soggetti Utenze", "utenze", "viewer"),
    ("utenze.import", "Import archivio Utenze", "utenze", "admin"),
    ("utenze.documents", "Documenti Utenze", "utenze", "viewer"),
    ("utenze.export", "Export Utenze", "utenze", "reviewer"),
]


def main() -> None:
    db = SessionLocal()
    created = 0
    try:
        for idx, (key, label, module, min_role) in enumerate(DEFAULT_SECTIONS):
            existing = db.query(Section).filter(Section.key == key).one_or_none()
            if existing is not None:
                continue
            create_section(
                db,
                SectionCreate(module=module, key=key, label=label, min_role=min_role, sort_order=idx),
                updated_by_id=None,
            )
            created += 1
    finally:
        db.close()
    print(f"sections_bootstrap_created={created}")


if __name__ == "__main__":
    main()
