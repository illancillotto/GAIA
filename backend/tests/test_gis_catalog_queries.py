from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.modules.gis import catalog_queries


def test_feature_geometry_sql_uses_null_when_column_is_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(catalog_queries, "_layer_columns", lambda *_args: ["id"])

    result = catalog_queries._feature_geometry_sql(
        Mock(),
        SimpleNamespace(geometry_column="geometry"),
    )

    assert result == "NULL"
