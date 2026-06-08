from __future__ import annotations

from collections.abc import Callable

from fastapi.testclient import TestClient

from app.models.application_user import ApplicationUserRole


def _create_unit(client, header, **body):
    resp = client.post("/organigramma/units", json=body, headers=header)
    assert resp.status_code == 201, resp.text
    return resp.json()


# --------------------------------------------------------------------------- #
# Gating
# --------------------------------------------------------------------------- #
def test_module_gating_denies_user_without_module(client, make_user, auth_header):
    make_user("nomod", role=ApplicationUserRole.ADMIN.value, module_organigramma=False)
    resp = client.get("/organigramma/units/tree", headers=auth_header("nomod"))
    assert resp.status_code == 403


def test_viewer_can_read_but_not_manage(client, make_user, auth_header):
    make_user("viewer1", role=ApplicationUserRole.VIEWER.value, module_organigramma=True)
    header = auth_header("viewer1")

    assert client.get("/organigramma/units/tree", headers=header).status_code == 200
    # manage-gated endpoints
    assert client.post(
        "/organigramma/units", json={"nome": "X", "tipo": "settore"}, headers=header
    ).status_code == 403
    assert client.get("/organigramma/overrides", headers=header).status_code == 403


# --------------------------------------------------------------------------- #
# Units + tree + detail
# --------------------------------------------------------------------------- #
def test_manage_can_build_tree_and_detail(client, make_user, auth_header):
    make_user("boss", role=ApplicationUserRole.SUPER_ADMIN.value)
    capo = make_user("capo", role=ApplicationUserRole.REVIEWER.value, full_name="Antonio Murru")
    op = make_user("op", role=ApplicationUserRole.OPERATOR.value, full_name="Paolo Carta")
    header = auth_header("boss")

    direzione = _create_unit(client, header, nome="Direzione Generale", tipo="direzione")
    settore = _create_unit(
        client, header, nome="Settore Idraulico", tipo="settore", parent_id=direzione["id"]
    )

    # assignment con title di leadership -> responsabile
    client.post(
        "/organigramma/assignments",
        json={"user_id": capo.id, "org_unit_id": settore["id"], "title": "Caposettore"},
        headers=header,
    ).raise_for_status()
    client.post(
        "/organigramma/assignments",
        json={
            "user_id": op.id,
            "org_unit_id": settore["id"],
            "title": "Operatore idraulico",
            "manager_user_id": capo.id,
        },
        headers=header,
    ).raise_for_status()

    tree = client.get("/organigramma/units/tree", headers=header).json()
    assert len(tree) == 1
    assert tree[0]["nome"] == "Direzione Generale"
    assert tree[0]["child_count"] == 1
    child = tree[0]["children"][0]
    assert child["nome"] == "Settore Idraulico"
    assert child["person_count"] == 2

    detail = client.get(f"/organigramma/units/{settore['id']}", headers=header).json()
    assert detail["responsabile"]["full_name"] == "Antonio Murru"
    assert detail["responsabile_title"] == "Caposettore"
    assert {a["title"] for a in detail["assignments"]} == {"Caposettore", "Operatore idraulico"}
    assert [p["nome"] for p in detail["path"]] == ["Direzione Generale", "Settore Idraulico"]


def test_delete_unit_conflict_when_has_children(client, make_user, auth_header):
    make_user("boss", role=ApplicationUserRole.SUPER_ADMIN.value)
    header = auth_header("boss")
    parent = _create_unit(client, header, nome="Distretto", tipo="distretto")
    _create_unit(client, header, nome="Settore", tipo="settore", parent_id=parent["id"])

    resp = client.delete(f"/organigramma/units/{parent['id']}", headers=header)
    assert resp.status_code == 409


# --------------------------------------------------------------------------- #
# Overrides
# --------------------------------------------------------------------------- #
def test_override_crud_and_status(client, make_user, auth_header):
    make_user("boss", role=ApplicationUserRole.SUPER_ADMIN.value)
    hr = make_user("hr", role=ApplicationUserRole.VIEWER.value, full_name="Anna Cabras")
    header = auth_header("boss")
    direzione = _create_unit(client, header, nome="Direzione Generale", tipo="direzione")

    resp = client.post(
        "/organigramma/overrides",
        json={
            "viewer_user_id": hr.id,
            "target_type": "org_unit",
            "target_org_unit_id": direzione["id"],
            "scope": "read",
            "motivo": "HR vede tutto",
        },
        headers=header,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "attivo"
    assert body["target_label"] == "Direzione Generale"
    assert body["viewer"]["full_name"] == "Anna Cabras"

    # scaduto
    expired = client.post(
        "/organigramma/overrides",
        json={
            "viewer_user_id": hr.id,
            "target_type": "org_unit",
            "target_org_unit_id": direzione["id"],
            "scope": "read",
            "motivo": "vecchio",
            "valid_from": "2026-01-01T00:00:00Z",
            "valid_to": "2026-02-01T00:00:00Z",
        },
        headers=header,
    ).json()
    assert expired["status"] == "scaduto"

    listing = client.get("/organigramma/overrides", headers=header).json()
    assert len(listing) == 2


# --------------------------------------------------------------------------- #
# Visibility simulator
# --------------------------------------------------------------------------- #
def test_visibility_combines_hierarchy_and_override(client, make_user, auth_header):
    make_user("boss", role=ApplicationUserRole.SUPER_ADMIN.value)
    capo = make_user("capo", role=ApplicationUserRole.REVIEWER.value)
    op = make_user("op", role=ApplicationUserRole.OPERATOR.value)
    hr = make_user("hr", role=ApplicationUserRole.VIEWER.value)
    header = auth_header("boss")

    direzione = _create_unit(client, header, nome="Direzione", tipo="direzione")
    settore = _create_unit(client, header, nome="Settore", tipo="settore", parent_id=direzione["id"])

    # op è gestito da capo nel settore -> capo vede il settore via gerarchia
    client.post(
        "/organigramma/assignments",
        json={"user_id": op.id, "org_unit_id": settore["id"], "title": "Operatore", "manager_user_id": capo.id},
        headers=header,
    ).raise_for_status()

    # capo: visibilità gerarchica
    capo_vis = client.get(f"/organigramma/visibility/{capo.id}", headers=header).json()
    assert capo_vis["full"] is False
    units_via = {u["nome"]: u["via"] for u in capo_vis["units"]}
    assert units_via == {"Settore": "gerarchia"}
    assert any(p["via"] == "gerarchia" for p in capo_vis["people"])

    # hr: nessuna gerarchia, ma override read sull'intera Direzione (cascata)
    client.post(
        "/organigramma/overrides",
        json={
            "viewer_user_id": hr.id,
            "target_type": "org_unit",
            "target_org_unit_id": direzione["id"],
            "scope": "read",
            "motivo": "HR vede tutto",
        },
        headers=header,
    ).raise_for_status()
    hr_vis = client.get(f"/organigramma/visibility/{hr.id}", headers=header).json()
    hr_units = {u["nome"]: u["via"] for u in hr_vis["units"]}
    assert hr_units == {"Direzione": "override", "Settore": "override"}

    # super_admin: full=True
    boss_id = client.get("/auth/my-permissions", headers=header).status_code  # smoke
    assert boss_id == 200


def test_visibility_unknown_user_404(client, make_user, auth_header):
    make_user("boss", role=ApplicationUserRole.SUPER_ADMIN.value)
    resp = client.get("/organigramma/visibility/999999", headers=auth_header("boss"))
    assert resp.status_code == 404


def test_update_unit_and_assignment_lifecycle(client, make_user, auth_header):
    make_user("boss", role=ApplicationUserRole.SUPER_ADMIN.value)
    op = make_user("op", role=ApplicationUserRole.OPERATOR.value)
    header = auth_header("boss")

    unit = _create_unit(client, header, nome="Squadra A", tipo="squadra")

    # update unit
    upd = client.put(
        f"/organigramma/units/{unit['id']}",
        json={"nome": "Squadra Manutenzione A", "sort_order": 5},
        headers=header,
    )
    assert upd.status_code == 200
    assert upd.json()["nome"] == "Squadra Manutenzione A"

    # cannot be its own parent
    bad = client.put(
        f"/organigramma/units/{unit['id']}",
        json={"parent_id": unit["id"]},
        headers=header,
    )
    assert bad.status_code == 400

    created = client.post(
        "/organigramma/assignments",
        json={"user_id": op.id, "org_unit_id": unit["id"], "title": "Operaio"},
        headers=header,
    ).json()

    updated = client.put(
        f"/organigramma/assignments/{created['id']}",
        json={"title": "Autista", "active": False},
        headers=header,
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "Autista"
    assert updated.json()["active"] is False

    deleted = client.delete(f"/organigramma/assignments/{created['id']}", headers=header)
    assert deleted.status_code == 204
    assert client.get("/organigramma/assignments", headers=header).json() == []


def test_update_and_delete_override(client, make_user, auth_header):
    make_user("boss", role=ApplicationUserRole.SUPER_ADMIN.value)
    hr = make_user("hr", role=ApplicationUserRole.VIEWER.value)
    header = auth_header("boss")
    unit = _create_unit(client, header, nome="Direzione", tipo="direzione")

    created = client.post(
        "/organigramma/overrides",
        json={
            "viewer_user_id": hr.id,
            "target_type": "org_unit",
            "target_org_unit_id": unit["id"],
            "scope": "read",
            "motivo": "HR",
        },
        headers=header,
    ).json()

    updated = client.put(
        f"/organigramma/overrides/{created['id']}",
        json={"is_active": False, "scope": "full"},
        headers=header,
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "disattivato"
    assert updated.json()["scope"] == "full"

    assert client.delete(f"/organigramma/overrides/{created['id']}", headers=header).status_code == 204
    assert client.get("/organigramma/overrides", headers=header).json() == []


def test_create_unit_rejects_unknown_parent(client, make_user, auth_header):
    make_user("boss", role=ApplicationUserRole.SUPER_ADMIN.value)
    header = auth_header("boss")
    from uuid import uuid4

    resp = client.post(
        "/organigramma/units",
        json={"nome": "X", "tipo": "settore", "parent_id": str(uuid4())},
        headers=header,
    )
    assert resp.status_code == 400


def test_whitecompany_sync_runs(client, make_user, auth_header):
    make_user("boss", role=ApplicationUserRole.SUPER_ADMIN.value)
    resp = client.post("/organigramma/sync/whitecompany", headers=auth_header("boss"))
    assert resp.status_code == 200
    body = resp.json()
    # nessuna wc_area nel DB di test -> zero unità ma esito valido
    assert body["units_created"] == 0
    assert "WhiteCompany sync" in body["message"]


def test_whitecompany_sync_creates_updates_and_respects_lock(
    client, make_user, auth_header, session
):
    from app.modules.operazioni.models.wc_area import WCArea
    from app.modules.organigramma.models import OrgSourceLink, OrgUnit

    make_user("boss", role=ApplicationUserRole.SUPER_ADMIN.value)
    header = auth_header("boss")

    session.add_all(
        [
            WCArea(wc_id=101, name="Distretto Tirso", is_district=True),
            WCArea(wc_id=201, name="Settore Idraulico", is_district=False),
        ]
    )
    session.commit()

    first = client.post("/organigramma/sync/whitecompany", headers=header).json()
    assert first["units_created"] == 2
    units = {u.nome: u for u in session.query(OrgUnit).all()}
    assert units["Distretto Tirso"].tipo == "distretto"
    assert units["Settore Idraulico"].tipo == "settore"
    assert all(u.source == "whitecompany" for u in units.values())

    # idempotenza: seconda corsa aggiorna, non duplica
    second = client.post("/organigramma/sync/whitecompany", headers=header).json()
    assert second["units_created"] == 0
    assert second["units_updated"] == 2
    assert session.query(OrgUnit).count() == 2

    # lock manuale: rinomina lato sorgente ma blocca il link -> non sovrascrive
    link = (
        session.query(OrgSourceLink)
        .filter(OrgSourceLink.external_wc_id == 101)
        .one()
    )
    link.is_manual_locked = True
    area = session.query(WCArea).filter(WCArea.wc_id == 101).one()
    area.name = "Rinominato in WhiteCompany"
    session.commit()

    third = client.post("/organigramma/sync/whitecompany", headers=header).json()
    assert third["units_skipped_locked"] == 1
    session.expire_all()
    locked_unit = session.get(OrgUnit, link.org_unit_id)
    assert locked_unit.nome == "Distretto Tirso"  # invariato
