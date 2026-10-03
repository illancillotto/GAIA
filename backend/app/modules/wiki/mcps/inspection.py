"""Authenticated dataset inspection, outside the model-visible MCP catalog."""

from starlette.responses import JSONResponse
from starlette.routing import Route

from .data.service import serialize_record

ENTITY_SCOPES = {
    "subjects": {"utenze.read"},
    "districts": {"catasto.read"},
    "parcels": {"catasto.read"},
    "irrigation_accounts": {"catasto.read"},
    "subject_accounts": {"utenze.read", "catasto.read"},
    "account_parcels": {"catasto.read"},
    "irrigation_applications": {"catasto.read"},
    "role_notices": {"ruolo.read"},
    "role_lines": {"ruolo.read"},
    "payments": {"ruolo.read"},
}


def pagination(request):
    limit = int(request.query_params.get("limit", "25"))
    offset = int(request.query_params.get("offset", "0"))
    before = int(request.query_params.get("before", "0"))
    if not 1 <= limit <= 100 or not 0 <= offset <= 100000 or before < 0:
        raise ValueError("Invalid pagination")
    return limit, offset, before


def inspection_routes(service, context_factory):
    async def inspect(request):
        context = context_factory()
        kind = request.path_params["kind"]
        try:
            limit, offset, before = pagination(request)
        except ValueError:
            return JSONResponse({"error": "INVALID_ARGUMENT"}, status_code=400)
        if kind == "catalog":
            return JSONResponse(
                {
                    "source": "gaia_synthetic_db",
                    "dataset_version": service.manifest["dataset_version"],
                    "entities": [
                        {"name": name, "count": service.manifest["row_counts"][name]}
                        for name, scopes in ENTITY_SCOPES.items()
                        if scopes <= context.scopes
                    ],
                    "audit_enabled": service.audit is not None,
                }
            )
        if kind == "calls":
            if service.audit is None:
                return JSONResponse({"error": "AUDIT_NOT_CONFIGURED"}, status_code=503)
            return JSONResponse(
                service.audit.history(
                    context, service.manifest["dataset_version"], before=before, limit=limit
                )
            )
        if kind not in ENTITY_SCOPES:
            return JSONResponse({"error": "NOT_FOUND"}, status_code=404)
        if not ENTITY_SCOPES[kind] <= context.scopes:
            return JSONResponse({"error": "PERMISSION_DENIED"}, status_code=403)
        rows = service.connection.execute(
            f"SELECT * FROM {kind} ORDER BY id LIMIT ? OFFSET ?", (limit, offset)
        ).fetchall()
        count = service.manifest["row_counts"][kind]
        return JSONResponse(
            {
                "source": "gaia_synthetic_db",
                "entity": kind,
                "dataset_version": service.manifest["dataset_version"],
                "results": [serialize_record(row) for row in rows],
                "total": count,
                "next_offset": offset + limit if offset + limit < count else None,
            }
        )

    return [Route("/inspect/{kind}", inspect, methods=["GET"])]
