import importlib

from sqlalchemy.orm import class_mapper


def test_sophos_syslog_script_bootstraps_model_registry() -> None:
    script_module = importlib.import_module("app.modules.network.sophos_syslog_script")
    assert script_module is not None

    network_models = importlib.import_module("app.modules.network.models")
    relationship = class_mapper(network_models.NetworkDevice).relationships["assigned_user"]

    assert relationship.mapper.class_.__name__ == "ApplicationUser"
