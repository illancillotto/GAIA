from __future__ import annotations

from app.api.routes import admin_users, audit, auth, catasto, network, permissions, section_permissions, sync
from app.jobs import sync as sync_jobs
from app.modules.accessi import repositories as accessi_repositories
from app.modules.accessi import schemas as accessi_schemas
from app.modules.accessi import services as accessi_services
from app.modules.accessi.routes import admin_users as accessi_admin_users
from app.modules.accessi.routes import audit as accessi_audit
from app.modules.accessi.routes import auth as accessi_auth
from app.modules.accessi.routes import permissions as accessi_permissions
from app.modules.accessi.routes import section_permissions as accessi_section_permissions
from app.modules.accessi.routes import sync as accessi_sync
from app.modules.catasto import routes as catasto_routes
from app.modules.network import router as network_router
from app.modules.network import scheduler as network_scheduler_module
from app.modules.network import schemas as network_module_schemas
from app.modules.network import services as network_module_services
from app.repositories import application_user, audit as audit_repo, permissions as permissions_repo, section_permission
from app.schemas import audit as audit_schemas, auth as auth_schemas, org_structure, permissions as permissions_schemas, sync as sync_schemas, users
from app.services import audit as audit_service, auth as auth_service, nas_connector, nas_parsers, permission_resolver, permissions as permissions_service, sync as sync_service, sync_runs
from app.services import network_scan, network_scheduler


def test_api_route_reexports_point_to_module_routers_and_helpers() -> None:
    assert admin_users.router is accessi_admin_users.router
    assert audit.router is accessi_audit.router
    assert auth.router is accessi_auth.router
    assert permissions.router is accessi_permissions.router
    assert section_permissions.admin_permissions_router is accessi_section_permissions.admin_permissions_router
    assert section_permissions.auth_permissions_router is accessi_section_permissions.auth_permissions_router
    assert section_permissions.sections_router is accessi_section_permissions.sections_router
    assert sync.router is accessi_sync.router
    assert sync.run_live_sync_job is sync_jobs.run_live_sync_job
    assert catasto.router is catasto_routes.router
    assert callable(catasto.get_websocket_token)
    assert network.router is network_router.router
    assert network.run_network_scan is network_module_services.run_network_scan


def test_accessi_and_network_compat_reexports_expose_expected_symbols() -> None:
    assert accessi_repositories.get_application_user_by_id is application_user.get_application_user_by_id
    assert accessi_repositories.get_dashboard_summary is audit_repo.get_dashboard_summary
    assert accessi_repositories.list_effective_permissions is permissions_repo.list_effective_permissions
    assert accessi_repositories.UserSectionPermission is section_permission.UserSectionPermission

    assert accessi_schemas.CurrentUserResponse is auth_schemas.CurrentUserResponse
    assert accessi_schemas.LoginRequest is auth_schemas.LoginRequest
    assert accessi_schemas.OrgStructureWorkspaceResponse is org_structure.OrgStructureWorkspaceResponse
    assert accessi_schemas.EffectivePermissionResponse is permissions_schemas.EffectivePermissionResponse
    assert accessi_schemas.SyncJobResponse is sync_schemas.SyncJobResponse
    assert accessi_schemas.ApplicationUserCreate is users.ApplicationUserCreate

    assert accessi_services.get_dashboard_summary is audit_service.get_dashboard_summary
    assert accessi_services.authenticate_user is auth_service.authenticate_user
    assert accessi_services.NasSSHClient is nas_connector.NasSSHClient
    assert accessi_services.parse_acl_output is nas_parsers.parse_acl_output
    assert accessi_services.resolve_user_permissions is permission_resolver.resolve_user_permissions
    assert accessi_services.list_effective_permissions is permissions_service.list_effective_permissions
    assert accessi_services.build_sync_preview is sync_service.build_sync_preview
    assert accessi_services.create_sync_run is sync_runs.create_sync_run

    assert network_scan.run_network_scan is network_module_services.run_network_scan
    assert network_scan.DiscoveredHost is network_module_services.DiscoveredHost
    assert network_scan.NetworkScanResult is network_module_services.NetworkScanResult
    assert network_scheduler.execute_scheduled_scan is network_scheduler_module.execute_scheduled_scan
    assert network_scheduler.run_scheduler is network_scheduler_module.run_scheduler
    assert network_scan.__all__
    assert network_scheduler.__all__ == ["execute_scheduled_scan", "run_scheduler"]


def test_network_schema_reexports_match_module_definitions() -> None:
    assert network_scan.__all__[0] == "DiscoveredHost"
    assert network_scan.__all__[-1] == "upsert_device_position"
    assert network_scheduler_module.run_scheduler is network_scheduler.run_scheduler

    assert network_module_schemas.DevicePositionResponse is not None
    assert network_module_schemas.NetworkScanTriggerResponse is not None
    assert network_module_schemas.NetworkDashboardSummary is not None

    from app.schemas import network as network_compat_schemas

    assert network_compat_schemas.DevicePositionResponse is network_module_schemas.DevicePositionResponse
    assert network_compat_schemas.NetworkScanTriggerResponse is network_module_schemas.NetworkScanTriggerResponse
    assert network_compat_schemas.NetworkDashboardSummary is network_module_schemas.NetworkDashboardSummary
