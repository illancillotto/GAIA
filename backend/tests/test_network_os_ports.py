"""OS classification preserves port precedence and eager iterable consumption."""

from itertools import combinations

import pytest

from app.modules.network import services

PORTS = (3389, 445, 22, 80, 443, 9999)
SUBSETS = [list(case) for size in range(len(PORTS) + 1) for case in combinations(PORTS, size)]


def expected_os(ports):
    if 3389 in ports:
        return "Windows"
    if 445 in ports:
        if 22 in ports:
            return "Linux/Unix server"
        return "Windows or SMB appliance"
    if 22 in ports:
        return "Linux/Unix"
    if 80 in ports or 443 in ports:
        return "Embedded/Web appliance"
    return None


@pytest.mark.parametrize("ports", SUBSETS)
def test_every_combination_and_iterable_shape(ports):
    expected = expected_os(ports)
    for data in [ports, tuple(ports), set(ports), iter(ports), iter(reversed(ports))]:
        assert services._guess_operating_system(data) == expected
    assert services._guess_operating_system([*ports, *reversed(ports)]) == expected


@pytest.mark.parametrize("ports", [[], [3389], [445], [445, 22], [22], [80, 443]])
def test_input_is_fully_consumed_even_when_first_port_decides_result(ports):
    seen = []

    def source():
        for port in ports:
            seen.append(port)
            yield port
        seen.append("end")

    assert services._guess_operating_system(source()) == expected_os(ports)
    assert seen == [*ports, "end"]


@pytest.mark.parametrize("first", [3389, 445, 22, 80, 9999])
def test_iteration_failure_propagates_before_any_classification(first):
    def source():
        yield first
        raise RuntimeError("port source")

    with pytest.raises(RuntimeError, match="port source"):
        services._guess_operating_system(source())


def test_unhashable_port_still_fails_during_materialization():
    with pytest.raises(TypeError, match="unhashable"):
        services._guess_operating_system([3389, []])


@pytest.mark.parametrize("ports", [["445", "22"], [None, True], [445.0, 22.0], [False, 80.0]])
def test_other_hashable_values_keep_builtin_set_membership(ports):
    assert services._guess_operating_system(ports) == expected_os(ports)
