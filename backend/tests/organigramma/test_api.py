from __future__ import annotations

from collections.abc import Callable

from fastapi.testclient import TestClient

from app.models.application_user import ApplicationUserRole


def _create_unit(client, header, structure_kind: str = "organigramma", **body):
    resp = client.post(f"/organigramma/units?structure_kind={structure_kind}", json=body, headers=header)
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


def test_inaz_admin_can_read_but_only_super_admin_can_manage(client, make_user, auth_header):
    make_user("inazadmin", role=ApplicationUserRole.ADMIN.value, module_organigramma=False, module_inaz=True)
    header = auth_header("inazadmin")

    assert client.get("/organigramma/units/tree", headers=header).status_code == 200
    assert client.post(
        "/organigramma/units", json={"nome": "X", "tipo": "settore"}, headers=header
    ).status_code == 403
    assert client.post("/organigramma/sync/whitecompany", headers=header).status_code == 403


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


def test_structure_kind_keeps_territorial_assignments_separate(client, make_user, auth_header):
    make_user("boss", role=ApplicationUserRole.SUPER_ADMIN.value)
    operatore = make_user("territoriale", role=ApplicationUserRole.OPERATOR.value, full_name="Operatore Territoriale")
    header = auth_header("boss")

    org_unit = _create_unit(client, header, nome="Direzione Operativa", tipo="direzione")
    territorial_unit = _create_unit(
        client,
        header,
        structure_kind="territoriale",
        nome="Distretto Nord",
        tipo="distretto",
    )

    org_assignment = client.post(
        "/organigramma/assignments?structure_kind=organigramma",
        json={"user_id": operatore.id, "org_unit_id": org_unit["id"], "title": "Operatore"},
        headers=header,
    )
    assert org_assignment.status_code == 201, org_assignment.text

    territorial_assignment = client.post(
        "/organigramma/assignments?structure_kind=territoriale",
        json={"user_id": operatore.id, "org_unit_id": territorial_unit["id"], "title": "Presidio territoriale"},
        headers=header,
    )
    assert territorial_assignment.status_code == 201, territorial_assignment.text

    org_tree = client.get("/organigramma/units/tree?structure_kind=organigramma", headers=header)
    territorial_tree = client.get("/organigramma/units/tree?structure_kind=territoriale", headers=header)
    assert org_tree.status_code == 200, org_tree.text
    assert territorial_tree.status_code == 200, territorial_tree.text
    assert [node["nome"] for node in org_tree.json()] == ["Direzione Operativa"]
    assert [node["nome"] for node in territorial_tree.json()] == ["Distretto Nord"]

    org_assignments = client.get(
        f"/organigramma/assignments?structure_kind=organigramma&user_id={operatore.id}",
        headers=header,
    )
    territorial_assignments = client.get(
        f"/organigramma/assignments?structure_kind=territoriale&user_id={operatore.id}",
        headers=header,
    )
    assert [item["title"] for item in org_assignments.json()] == ["Operatore"]
    assert [item["title"] for item in territorial_assignments.json()] == ["Presidio territoriale"]


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
        json={"nome": "Squadra Manutenzione A", "sort_order": 5, "canvas_x": 420, "canvas_y": 260},
        headers=header,
    )
    assert upd.status_code == 200
    assert upd.json()["nome"] == "Squadra Manutenzione A"
    assert upd.json()["canvas_x"] == 420
    assert upd.json()["canvas_y"] == 260

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


# --------------------------------------------------------------------------- #
# Drafts + revisions
# --------------------------------------------------------------------------- #
def test_drafts_bootstrap_current_revision_and_clone_tree(client, make_user, auth_header):
    make_user("boss", role=ApplicationUserRole.SUPER_ADMIN.value)
    operator = make_user("opdraft", role=ApplicationUserRole.OPERATOR.value, full_name="Bozza Operatore")
    header = auth_header("boss")

    direzione = _create_unit(client, header, nome="Direzione Draft", tipo="direzione")
    settore = _create_unit(client, header, nome="Settore Draft", tipo="settore", parent_id=direzione["id"])
    assign_resp = client.post(
        "/organigramma/assignments",
        json={"user_id": operator.id, "org_unit_id": settore["id"], "title": "Operatore"},
        headers=header,
    )
    assert assign_resp.status_code == 201, assign_resp.text

    current_revision = client.get("/organigramma/drafts/revisions/current", headers=header)
    assert current_revision.status_code == 200, current_revision.text
    assert current_revision.json()["status"] == "published"

    created = client.post(
        "/organigramma/drafts",
        json={"name": "Bozza giugno", "notes": "Test foundation"},
        headers=header,
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["status"] == "draft"
    assert body["unit_count"] == 2
    assert body["assignment_count"] == 1
    assert body["event_count"] == 1

    tree = client.get(f"/organigramma/drafts/{body['id']}/tree", headers=header)
    assert tree.status_code == 200, tree.text
    tree_body = tree.json()
    assert len(tree_body) == 1
    assert tree_body[0]["nome"] == "Direzione Draft"
    assert tree_body[0]["children"][0]["nome"] == "Settore Draft"

    assignments = client.get(f"/organigramma/drafts/{body['id']}/assignments", headers=header)
    assert assignments.status_code == 200, assignments.text
    assert assignments.json()[0]["person"]["full_name"] == "Bozza Operatore"

    events = client.get(f"/organigramma/drafts/{body['id']}/events", headers=header)
    assert events.status_code == 200, events.text
    assert events.json()[0]["action"] == "draft_created"


def test_drafts_publish_and_discard_lifecycle(client, make_user, auth_header):
    make_user("boss", role=ApplicationUserRole.SUPER_ADMIN.value)
    header = auth_header("boss")

    _create_unit(client, header, nome="Direzione Lifecycle", tipo="direzione")

    first = client.post(
        "/organigramma/drafts",
        json={"name": "Bozza publish"},
        headers=header,
    )
    assert first.status_code == 201, first.text
    first_body = first.json()

    publish = client.post(f"/organigramma/drafts/{first_body['id']}/publish", headers=header)
    assert publish.status_code == 200, publish.text
    published_body = publish.json()
    assert published_body["status"] == "published"
    assert published_body["published_at"] is not None
    assert published_body["event_count"] == 2

    revisions = client.get("/organigramma/drafts/revisions", headers=header)
    assert revisions.status_code == 200, revisions.text
    published_revisions = [revision for revision in revisions.json() if revision["status"] == "published"]
    assert len(published_revisions) == 1
    assert published_revisions[0]["id"] == published_body["working_revision_id"]

    second = client.post(
        "/organigramma/drafts",
        json={"name": "Bozza discard"},
        headers=header,
    )
    assert second.status_code == 201, second.text
    second_body = second.json()

    discard = client.post(f"/organigramma/drafts/{second_body['id']}/discard", headers=header)
    assert discard.status_code == 200, discard.text
    discarded_body = discard.json()
    assert discarded_body["status"] == "discarded"
    assert discarded_body["event_count"] == 2

    no_active = client.get("/organigramma/drafts/my-active", headers=header)
    assert no_active.status_code == 200, no_active.text
    assert no_active.json() is None


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


def test_export_snapshot_returns_units_assignments_and_overrides(client, make_user, auth_header):
    make_user("boss", role=ApplicationUserRole.SUPER_ADMIN.value)
    capo = make_user("exportcapo", role=ApplicationUserRole.REVIEWER.value, full_name="Capo Export")
    viewer = make_user("exportviewer", role=ApplicationUserRole.VIEWER.value, full_name="Viewer Export")
    header = auth_header("boss")

    direzione = _create_unit(client, header, nome="Direzione Export", tipo="direzione")
    settore = _create_unit(client, header, nome="Settore Export", tipo="settore", parent_id=direzione["id"])

    created_assignment = client.post(
        "/organigramma/assignments",
        json={"user_id": capo.id, "org_unit_id": settore["id"], "title": "Caposettore"},
        headers=header,
    )
    assert created_assignment.status_code == 201, created_assignment.text

    created_override = client.post(
        "/organigramma/overrides",
        json={
            "viewer_user_id": viewer.id,
            "target_type": "org_unit",
            "target_org_unit_id": direzione["id"],
            "scope": "read",
            "motivo": "Export test",
        },
        headers=header,
    )
    assert created_override.status_code == 201, created_override.text

    exported = client.get("/organigramma/io/export", headers=header)
    assert exported.status_code == 200, exported.text
    body = exported.json()
    assert body["schema_version"] == 1
    assert body["exported_by_username"] == "boss"
    assert {unit["nome"] for unit in body["units"]} == {"Direzione Export", "Settore Export"}
    assert body["assignments"][0]["title"] == "Caposettore"
    assert body["overrides"][0]["motivo"] == "Export test"


def test_import_snapshot_replace_recreates_organigramma(client, make_user, auth_header):
    make_user("boss", role=ApplicationUserRole.SUPER_ADMIN.value)
    manager = make_user("importmanager", role=ApplicationUserRole.REVIEWER.value, full_name="Manager Import")
    viewer = make_user("importviewer", role=ApplicationUserRole.VIEWER.value, full_name="Viewer Import")
    header = auth_header("boss")

    snapshot = {
        "schema_version": 1,
        "units": [
            {
                "id": "11111111-1111-1111-1111-111111111111",
                "nome": "Direzione Import",
                "tipo": "direzione",
                "parent_id": None,
                "is_active": True,
                "sort_order": 0,
                "canvas_x": 10,
                "canvas_y": 20,
                "source": "manuale",
                "wc_area_id": None,
                "legacy_team_id": None,
            },
            {
                "id": "22222222-2222-2222-2222-222222222222",
                "nome": "Settore Import",
                "tipo": "settore",
                "parent_id": "11111111-1111-1111-1111-111111111111",
                "is_active": True,
                "sort_order": 1,
                "canvas_x": 30,
                "canvas_y": 40,
                "source": "manuale",
                "wc_area_id": None,
                "legacy_team_id": None,
            },
        ],
        "assignments": [
            {
                "id": "33333333-3333-3333-3333-333333333333",
                "user_id": manager.id,
                "org_unit_id": "22222222-2222-2222-2222-222222222222",
                "manager_user_id": None,
                "title": "Caposettore",
                "is_primary": True,
                "active": True,
                "valid_from": None,
                "valid_to": None,
                "source": "manuale",
                "wc_operator_id": None,
            }
        ],
        "overrides": [
            {
                "id": "44444444-4444-4444-4444-444444444444",
                "viewer_user_id": viewer.id,
                "target_type": "org_unit",
                "target_user_id": None,
                "target_org_unit_id": "11111111-1111-1111-1111-111111111111",
                "scope": "read",
                "motivo": "Import snapshot",
                "valid_from": None,
                "valid_to": None,
                "is_active": True,
            }
        ],
    }

    imported = client.post("/organigramma/io/import?mode=replace", json=snapshot, headers=header)
    assert imported.status_code == 200, imported.text
    body = imported.json()
    assert body["mode"] == "replace"
    assert body["units_created"] == 2
    assert body["assignments_created"] == 1
    assert body["overrides_created"] == 1

    tree = client.get("/organigramma/units/tree", headers=header)
    assert tree.status_code == 200, tree.text
    tree_body = tree.json()
    assert len(tree_body) == 1
    assert tree_body[0]["nome"] == "Direzione Import"
    assert tree_body[0]["children"][0]["nome"] == "Settore Import"

    assignments = client.get("/organigramma/assignments", headers=header)
    assert assignments.status_code == 200, assignments.text
    assert assignments.json()[0]["title"] == "Caposettore"

    overrides = client.get("/organigramma/overrides", headers=header)
    assert overrides.status_code == 200, overrides.text
    assert overrides.json()[0]["motivo"] == "Import snapshot"


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


def test_whitecompany_sync_maps_user_chart_to_area_tree_by_root_area_id(
    client, make_user, auth_header, session
):
    from app.modules.accessi.wc_org_charts import WCOrgChart, WCOrgChartEntry
    from app.modules.operazioni.models.wc_area import WCArea
    from app.modules.operazioni.models.wc_operator import WCOperator
    from app.modules.organigramma.models import OrgAssignment, OrgUnit

    make_user("boss", role=ApplicationUserRole.SUPER_ADMIN.value)
    dirigente = make_user("dir", role=ApplicationUserRole.REVIEWER.value, full_name="Dirigente")
    caposettore = make_user("sett", role=ApplicationUserRole.REVIEWER.value, full_name="Capo settore")
    caposezione = make_user("sez", role=ApplicationUserRole.REVIEWER.value, full_name="Capo sezione")
    header = auth_header("boss")

    root_area = WCArea(wc_id=1, name="Area agraria", is_district=False)
    settore_area = WCArea(wc_id=2, name="Settore Manutenzione", is_district=False)
    sezione_area = WCArea(wc_id=6, name="Sezione reti sud", is_district=False)
    session.add_all([root_area, settore_area, sezione_area])
    session.flush()

    dirigente_wc = WCOperator(wc_id=455, gaia_user_id=dirigente.id)
    caposettore_wc = WCOperator(wc_id=13010, gaia_user_id=caposettore.id)
    caposezione_wc = WCOperator(wc_id=548, gaia_user_id=caposezione.id)
    session.add_all([dirigente_wc, caposettore_wc, caposezione_wc])
    session.flush()

    area_chart = WCOrgChart(wc_id=9, chart_type="area", name="Area Agraria")
    user_chart = WCOrgChart(wc_id=1, chart_type="user", name="Area agraria")
    session.add_all([area_chart, user_chart])
    session.flush()

    session.add_all(
        [
            WCOrgChartEntry(
                org_chart_id=area_chart.id,
                wc_id=1,
                label="Area agraria",
                wc_area_id=root_area.id,
                source_field="datasource_node|chart=area|depth=0",
                sort_order=0,
            ),
            WCOrgChartEntry(
                org_chart_id=area_chart.id,
                wc_id=2,
                label="Settore Manutenzione",
                wc_area_id=settore_area.id,
                source_field="datasource_node|chart=area|depth=1|parent=1",
                sort_order=1,
            ),
            WCOrgChartEntry(
                org_chart_id=area_chart.id,
                wc_id=6,
                label="Sezione reti sud",
                wc_area_id=sezione_area.id,
                source_field="datasource_node|chart=area|depth=2|parent=2",
                sort_order=2,
            ),
            WCOrgChartEntry(
                org_chart_id=user_chart.id,
                wc_id=455,
                label="Dirigente",
                role="Dirigente",
                wc_operator_id=dirigente_wc.id,
                source_field="datasource_node|chart=user|depth=0",
                sort_order=0,
            ),
            WCOrgChartEntry(
                org_chart_id=user_chart.id,
                wc_id=13010,
                label="Capo settore",
                role="Capo settore",
                wc_operator_id=caposettore_wc.id,
                source_field="datasource_node|chart=user|depth=1|parent=455",
                sort_order=1,
            ),
            WCOrgChartEntry(
                org_chart_id=user_chart.id,
                wc_id=548,
                label="Capo sezione",
                role="Capo sezione",
                wc_operator_id=caposezione_wc.id,
                source_field="datasource_node|chart=user|depth=2|parent=13010",
                sort_order=2,
            ),
        ]
    )
    session.commit()

    body = client.post("/organigramma/sync/whitecompany", headers=header).json()
    assert body["units_created"] == 3
    assert body["assignments_created"] == 3

    session.expire_all()
    units = {u.nome: u for u in session.query(OrgUnit).all()}
    assert units["Settore Manutenzione"].parent_id == units["Area agraria"].id

    assignments = {
        row.user_id: row
        for row in session.query(OrgAssignment).all()
    }
    assert assignments[dirigente.id].org_unit_id == units["Area agraria"].id
    assert assignments[caposettore.id].org_unit_id == units["Settore Manutenzione"].id
    assert assignments[caposezione.id].org_unit_id in {
        units["Settore Manutenzione"].id,
        units["Sezione reti sud"].id,
    }
