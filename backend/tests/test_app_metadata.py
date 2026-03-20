from app.main import app


def test_app_metadata_matches_project_settings() -> None:
    assert app.title == "NAS Access Audit Platform"
    assert app.version == "0.1.0"
    assert app.docs_url == "/docs"
    assert app.redoc_url == "/redoc"


def test_registered_routes_include_health_and_docs() -> None:
    paths = {route.path for route in app.routes}

    assert "/health" in paths
    assert "/docs" in paths
    assert "/openapi.json" in paths
