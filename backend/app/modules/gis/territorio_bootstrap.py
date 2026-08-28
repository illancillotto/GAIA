from __future__ import annotations

from typing import Any

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.application_user import ApplicationUserRole
from app.modules.gis.bootstrap import _ensure_role_permission
from app.modules.gis.external_sources import normalize_external_layer_metadata
from app.modules.gis.models import GisLayer
from app.modules.gis.schemas import GisAccessLevel, GisExternalLayerConfig

TERRITORIO_WORKSPACE = "territorio"
TERRITORIO_DOMAIN_MODULE = "gis"
CC_BY_4 = "CC BY 4.0"


def _ras_attribution(title: str) -> str:
    return (
        "Dati: Regione Autonoma della Sardegna - Sardegna Geoportale, "
        f'"{title}", licenza CC BY 4.0 '
        "(https://creativecommons.org/licenses/by/4.0/). Nessuna modifica "
        "ai dati; resa cartografica tramite GAIA."
    )


ADE_ATTRIBUTION = (
    "Dati: Agenzia delle Entrate - Cartografia Catastale, licenza CC BY 4.0 "
    "(https://creativecommons.org/licenses/by/4.0/). Titolarita dei dati: "
    "Agenzia delle Entrate. Nessuna modifica ai dati; resa cartografica "
    "tramite GAIA."
)


def _definition(
    name: str,
    remote_layer: str,
    title: str,
    description: str,
    theme: str,
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    configured = {
        "source_key": "ras_sitr_vector",
        "official_source": "ras_sitr",
        "queryable": "wfs_queryable",
        "default_opacity": 0.65,
        "cache_ttl_seconds": 3600,
        "attribution": _ras_attribution(title),
        **(options or {}),
    }
    return {
        "name": name,
        "remote_layer": remote_layer,
        "title": title,
        "description": description,
        "theme": theme,
        "source_key": configured["source_key"],
        "official_source": configured["official_source"],
        "queryable": configured["queryable"],
        "default_opacity": configured["default_opacity"],
        "cache_ttl_seconds": configured["cache_ttl_seconds"],
        "license": CC_BY_4,
        "attribution": configured["attribution"],
    }


TERRITORIO_GIS_LAYER_DEFINITIONS: tuple[dict[str, Any], ...] = (
    _definition(
        "ras_aree_bonifica",
        "dbu:areebonifica",
        "PPR06 - Aree della bonifica",
        "La particella ricade in area di bonifica?",
        "bonifica",
    ),
    _definition(
        "ras_comprensori_irrigui",
        "dbu:agr_consorzi_irrigui_bonif_comprensori",
        "AGR - Consorzi di Bonifica - delimitazioni comprensori irrigui",
        "Confronto informativo tra il comprensorio regionale e quello consortile.",
        "bonifica",
    ),
    _definition(
        "ras_distretti_irrigui",
        "dbu:agr_consorzi_irrigui_bonif_distretti",
        "AGR - Consorzi di Bonifica - delimitazioni distretti irrigui",
        "Sovrapposizione informativa: la fonte autorevole per il distretto resta GAIA.",
        "bonifica",
    ),
    _definition(
        "ras_uso_suolo_2008",
        "dbu:usosuolo2008_areali",
        "Carta dell'Uso del Suolo 2008 - poligoni",
        "Uso del suolo censito dalla fonte regionale.",
        "colture",
    ),
    _definition(
        "ras_colture_2008",
        "dbu:usosuolocolture2008",
        "Carta delle colture dell'Uso del Suolo",
        "Confronto con la coltura dichiarata in DUI.",
        "colture",
    ),
    _definition(
        "ras_vincolo_idrogeologico",
        "dbu:vincolo_idrogeologico_sardegna_rdl_3267_1923",
        "Vincolo Idrogeologico ai sensi del RDL 3267/1923",
        "Contesto per gli interventi sulla rete.",
        "vincoli",
    ),
    _definition(
        "ras_beni_paesaggistici",
        "dbu:benipaesaggisticiexart136_142",
        "PPR06 - Beni paesaggistici storico culturali puntuali ex artt. 136 e 142 D.Lgs. 42/04",
        "Beni tutelati potenzialmente interferenti.",
        "vincoli",
    ),
    _definition(
        "ras_fascia_150m_fiumi",
        "dbu:art142_fascia_150m_fiumi_indic",
        "Art. 142 - Fascia di 150 m dai fiumi (dati indicativi)",
        "Dato dichiarato indicativo dalla sorgente; e una segnalazione, non un accertamento.",
        "vincoli",
    ),
    _definition(
        "ras_siti_interesse_comunitario",
        "dbu:sitiinteressecomunitario",
        "PPR06 - Siti di interesse comunitario",
        "Interferenza potenziale con Rete Natura 2000.",
        "vincoli",
    ),
    _definition(
        "ras_reticolo_idrografico",
        "dbu:dbgt_10k_22_v05_04_reticolo_idrografico",
        "DBGT10K_22_v05 - 04 Reticolo Idrografico",
        "Confronto del reticolo idrografico con la rete consortile.",
        "idrografia",
    ),
    _definition(
        "ras_reticolo_naturale",
        "dbu:dbgt_10k_22_v05_04_reticolo_idrografico_naturale",
        "DBGT10K_22_v05 - 04 Reticolo Idrografico Naturale",
        "Distinzione tra reticolo naturale e artificiale.",
        "idrografia",
    ),
    _definition(
        "ras_laghi_invasi_stagni",
        "dbu:laghiinvasistagni",
        "PPR06 - Laghi naturali, invasi artificiali, stagni e lagune",
        "Corpi idrici di riferimento.",
        "idrografia",
    ),
    _definition(
        "ras_limiti_comunali",
        "dbu:limiti_amministr_com_ctr",
        "Limiti amministrativi comunali CTR",
        "Attribuzione comunale della particella.",
        "amministrativo",
    ),
    _definition(
        "ras_aree_incendiate_2024",
        "dbu:areeincendiateperim2024",
        "CFVA - Perimetri dei soprassuoli percorsi dal fuoco - 2024",
        "Contesto per esenzioni, danni e contenzioso sul ruolo.",
        "eventi",
    ),
    _definition(
        "ade_particelle_wms",
        "CP.CadastralParcel",
        "Particelle catastali ufficiali",
        "Confronto tra geometria GAIA e cartografia catastale ufficiale.",
        "catasto_ufficiale",
        {
            "source_key": "ade_catasto_wms",
            "official_source": "agenzia_entrate",
            "queryable": "wms_infoable",
            "attribution": ADE_ATTRIBUTION,
        },
    ),
    _definition(
        "ade_zone_censuarie_wms",
        "CP.CadastralZoning",
        "Zone censuarie catastali",
        "Inquadramento censuario ufficiale.",
        "catasto_ufficiale",
        {
            "source_key": "ade_catasto_wms",
            "official_source": "agenzia_entrate",
            "queryable": "wms_infoable",
            "attribution": ADE_ATTRIBUTION,
        },
    ),
    _definition(
        "ade_fabbricati_wms",
        "fabbricati",
        "Fabbricati catastali",
        "Presenza di fabbricati nella cartografia catastale ufficiale.",
        "catasto_ufficiale",
        {
            "source_key": "ade_catasto_wms",
            "official_source": "agenzia_entrate",
            "queryable": "wms_infoable",
            "attribution": ADE_ATTRIBUTION,
        },
    ),
    _definition(
        "ras_ortofoto_1977",
        "raster:ortofoto_1977_1978",
        "Ortofoto 1977-1978",
        "Basemap storica per la ricostruzione degli usi consolidati.",
        "ortofoto",
        {
            "source_key": "ras_sitr_raster",
            "queryable": "wms_visual_only",
            "default_opacity": 1.0,
            "cache_ttl_seconds": 86400,
        },
    ),
    _definition(
        "ras_dtm_1m",
        "raster:DTM_1M_MOSAICO_ALTIMETRIA",
        "DTM 1 m - altimetria",
        "Quote da rilievo LiDAR per il dimensionamento dei tratti.",
        "morfologia",
        {
            "source_key": "ras_sitr_raster",
            "queryable": "wms_visual_only",
            "cache_ttl_seconds": 86400,
        },
    ),
    _definition(
        "ras_dtm_1m_hillshade",
        "raster:DTM_1M_MOSAICO_OMBRE",
        "DTM 1 m - ombreggiatura",
        "Lettura morfologica del terreno.",
        "morfologia",
        {
            "source_key": "ras_sitr_raster",
            "queryable": "wms_visual_only",
            "cache_ttl_seconds": 86400,
        },
    ),
    _definition(
        "ras_dtm_10m",
        "raster:DTM_10M_ALTIMETRIA_REV01",
        "DTM 10 m - altimetria",
        "Copertura altimetrica estesa dove manca il rilievo a 1 m.",
        "morfologia",
        {
            "source_key": "ras_sitr_raster",
            "queryable": "wms_visual_only",
            "cache_ttl_seconds": 86400,
        },
    ),
)


def _external_metadata(definition: dict[str, Any], render_order: int) -> dict[str, Any]:
    external = {
        "source_key": definition["source_key"],
        "service": "wms",
        "version": "1.3.0",
        "remote_layer": definition["remote_layer"],
        "format": "image/png",
        "transparent": True,
        "srid": 3857,
        "queryable": definition["queryable"],
        "info_format": "application/json"
        if definition["queryable"] == "wms_infoable"
        else None,
        "cache_ttl_seconds": definition["cache_ttl_seconds"],
        "license": definition.get("license"),
        "attribution": definition.get("attribution"),
    }
    try:
        GisExternalLayerConfig.model_validate(external)
    except ValidationError as exc:
        raise ValueError(
            f"Invalid territorio layer definition: {definition.get('name', '<unknown>')}"
        ) from exc
    return (
        normalize_external_layer_metadata(
            "wms_external",
            {
                "catalog_seed": "territorio_external_m22",
                "theme": definition["theme"],
                "default_opacity": definition["default_opacity"],
                "render_order": render_order,
                "external": external,
                "export": {"shapefile": False},
                "qgis": {"mode": "not_published", "editable": False},
            },
        )
        or {}
    )


def _apply_definition(
    layer: GisLayer, definition: dict[str, Any], render_order: int
) -> None:
    layer.workspace = TERRITORIO_WORKSPACE
    layer.name = str(definition["name"])
    layer.title = str(definition["title"])
    layer.description = str(definition["description"])
    layer.domain_module = TERRITORIO_DOMAIN_MODULE
    layer.source_type = "wms_external"
    layer.official_source = str(definition["official_source"])
    layer.postgis_schema = None
    layer.postgis_table = None
    layer.geometry_column = None
    layer.geometry_type = None
    layer.srid = 3857
    layer.feature_id_column = None
    layer.martin_layer_id = None
    layer.ogc_service_url = None
    layer.qgis_project_path = None
    layer.nas_export_root = None
    layer.metadata_json = _external_metadata(definition, render_order)
    layer.is_active = True


def ensure_territorio_gis_catalog(
    db: Session,
    definitions: tuple[dict[str, Any], ...] = TERRITORIO_GIS_LAYER_DEFINITIONS,
) -> int:
    created = 0
    for render_order, definition in enumerate(definitions):
        layer = db.scalar(
            select(GisLayer).where(
                GisLayer.workspace == TERRITORIO_WORKSPACE,
                GisLayer.name == definition["name"],
            )
        )
        if layer is None:
            layer = GisLayer(
                workspace=TERRITORIO_WORKSPACE,
                name=str(definition["name"]),
                title=str(definition["title"]),
            )
            db.add(layer)
            db.flush()
            created += 1
        _apply_definition(layer, definition, render_order)
        _ensure_role_permission(
            db, layer, ApplicationUserRole.VIEWER, GisAccessLevel.viewer
        )
    db.commit()
    return created
