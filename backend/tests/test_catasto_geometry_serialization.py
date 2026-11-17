"""Geometry serialization and the WKT separator's observable edge cases."""

from itertools import product

import pytest
from geoalchemy2.shape import from_shape
from shapely.geometry import Point, Polygon

from app.modules.catasto.services import geometry_serialization as service


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("", []),
        ("   ", []),
        (",", [""]),
        (",,", ["", ""]),
        (" a , , b , ", ["a", "", "b"]),
        ("(1 2,3 4),(5 6,7 8)", ["(1 2,3 4)", "(5 6,7 8)"]),
        ("((a,b),(c,d)), (e,f)", ["((a,b),(c,d))", "(e,f)"]),
        ("(a,b", ["(a,b"]),
        (")a,b", [")a,b"]),
        (")(,a", [")(", "a"]),
        ("a,(b),c", ["a", "(b)", "c"]),
        ("à, (è,ò) , ù", ["à", "(è,ò)", "ù"]),
    ],
)
def test_top_level_separators_preserve_empty_parts_and_unbalanced_input(value, expected):
    assert service._split_top_level(value) == expected


def test_separator_exhaustive_short_strings_against_prefix_depths():
    # Independent reference: classify each comma using the entire prefix.
    # It also defines behavior for negative depths and unmatched parentheses.
    for size in range(7):
        for chars in product("(), x", repeat=size):
            value = "".join(chars)
            boundaries = [
                index
                for index, char in enumerate(value)
                if char == "," and value[:index].count("(") == value[:index].count(")")
            ]
            expected = []
            start = 0
            for end in boundaries:
                expected.append(value[start:end].strip())
                start = end + 1
            if value[start:].strip():
                expected.append(value[start:].strip())
            assert service._split_top_level(value) == expected, repr(value)


@pytest.mark.parametrize("value", [None, object(), "", "  ", "POINT (1 2)", "SRID=4326"])
def test_unsupported_geometry_has_no_json_type_or_centroid(value):
    assert service.geometry_to_geojson_dict(value) is None
    assert service.geometry_type_label(value) is None
    assert service.centroid_geojson_dict(value) is None


def test_polygon_rings_srid_case_and_fallback_centroid():
    value = " srid=4326; polygon ((0 0, 4 0, 4 4, 0 0), (1 1, 2 1, 1 1)) "
    expected = {
        "type": "Polygon",
        "coordinates": [
            [[0.0, 0.0], [4.0, 0.0], [4.0, 4.0], [0.0, 0.0]],
            [[1.0, 1.0], [2.0, 1.0], [1.0, 1.0]],
        ],
    }
    assert service.geometry_to_geojson_dict(value) == expected
    assert service.geometry_type_label(value) == "Polygon"
    # Existing string fallback averages every vertex, including repeated ones.
    assert service.centroid_geojson_dict(value) == {
        "type": "Point",
        "coordinates": [12 / 7, 7 / 7],
    }


def test_multipolygon_keeps_polygon_and_ring_order():
    value = "MULTIPOLYGON (((0 0,2 0,0 0)),((8 8,9 8,8 8),(8 9,9 9,8 9)))"
    expected = {
        "type": "MultiPolygon",
        "coordinates": [
            [[[0.0, 0.0], [2.0, 0.0], [0.0, 0.0]]],
            [
                [[8.0, 8.0], [9.0, 8.0], [8.0, 8.0]],
                [[8.0, 9.0], [9.0, 9.0], [8.0, 9.0]],
            ],
        ],
    }
    assert service.geometry_to_geojson_dict(value) == expected
    assert service.geometry_type_label(value) == "MultiPolygon"
    assert service.centroid_geojson_dict(value) == {
        "type": "Point",
        "coordinates": [52 / 9, 51 / 9],
    }


@pytest.mark.parametrize("value", ["POLYGON EMPTY", "MULTIPOLYGON EMPTY", "POLYGON (())"])
def test_empty_polygons_preserve_the_type_and_have_no_centroid(value):
    assert service.geometry_type_label(value) in {"Polygon", "MultiPolygon"}
    assert service.centroid_geojson_dict(value) is None


@pytest.mark.parametrize("value", ["POLYGON ((bad 1,2 3))", "MULTIPOLYGON (((0 bad)))"])
def test_invalid_numbers_still_raise(value):
    for operation in (
        service.geometry_to_geojson_dict,
        service.geometry_type_label,
        service.centroid_geojson_dict,
    ):
        with pytest.raises(ValueError):
            operation(value)


def test_wkb_uses_real_shape_serialization_and_geometric_centroid():
    for shape in (Point(2, 3), Polygon([(0, 0), (4, 0), (4, 4), (0, 0)])):
        geometry = from_shape(shape, srid=4326)
        assert service.geometry_to_geojson_dict(geometry) == dict(shape.__geo_interface__)
        assert service.geometry_type_label(geometry) == shape.geom_type
        assert service.centroid_geojson_dict(geometry) == dict(shape.centroid.__geo_interface__)


def test_unwrapped_coordinate_parsers_and_underspecified_points():
    assert service._parse_polygon_coords("0 0,1 1") == [[[0.0, 0.0]], [[1.0, 1.0]]]
    assert service._parse_multipolygon_coords("0 0,1 1") == [
        [[[0.0, 0.0]]],
        [[[1.0, 1.0]]],
    ]
    assert service._parse_ring_coords("0 0 9, 1, 2 3") == [[0.0, 0.0], [2.0, 3.0]]
    assert service._flatten_coordinates("1 2") == []
    assert service._flatten_coordinates([1]) == []
    assert service._flatten_coordinates([]) == []
    assert service._flatten_coordinates([[[1, 2, 3]], "ignore", [4.5, 6]]) == [
        [1.0, 2.0],
        [4.5, 6.0],
    ]
