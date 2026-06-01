from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.application_user import ApplicationUser


def get_catasto_dashboard_summary_read_model(db: Session, current_user: ApplicationUser) -> dict[str, object]:
    from app.modules.catasto.routes.dashboard import get_dashboard_summary

    response = get_dashboard_summary(anno=None, db=db, _=current_user)
    return response.model_dump(mode="json")


def get_catasto_particella_read_model(db: Session, current_user: ApplicationUser, particella_id) -> dict[str, object]:
    from app.modules.catasto.routes.particelle import get_particella

    response = get_particella(particella_id=particella_id, db=db, _=current_user)
    return {
        "id": str(response.id),
        "nome_comune": response.nome_comune,
        "codice_catastale": response.codice_catastale,
        "foglio": response.foglio,
        "particella": response.particella,
        "subalterno": response.subalterno,
        "num_distretto": response.num_distretto,
        "ha_anagrafica": response.ha_anagrafica,
        "fuori_distretto": response.fuori_distretto,
        "has_geometry": bool(getattr(response, "geojson", None) or getattr(response, "geometry", None)),
    }
