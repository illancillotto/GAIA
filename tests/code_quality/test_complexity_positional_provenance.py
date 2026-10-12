import copy
import subprocess
from collections import defaultdict

import pytest
import test_complexity_contracts as contracts

tool = contracts.tool


def git(root, *arguments):
    return subprocess.run(
        ["git", *arguments], cwd=root, capture_output=True, text=True, check=True
    ).stdout.strip()


def positional_resolution(tool, current, report, baseline):
    base = tool.call_index(baseline)
    fingerprints = defaultdict(list)
    for identity, call in base.items():
        fingerprints[call["fingerprint"]].append((identity, call))
    return tool.resolve_baseline_callable(current, report, base, fingerprints)


@pytest.fixture
def positional_case(tool, tmp_path, monkeypatch):
    monkeypatch.setattr(tool, "ROOT", tmp_path)
    monkeypatch.setattr(tool, "load_exceptions", lambda: [])
    path = "frontend/src/Screen.tsx"
    source = tmp_path / path
    source.parent.mkdir(parents=True)
    original = (
        "export function Screen() {\n"
        "  return (\n"
        "    <section>\n"
        '      <input name="selection"\n'
        "        onChange={() =>\n"
        "          choose(value ? value : null)\n"
        "        }\n"
        '        className="selection-control"\n'
        "      />\n"
        '      <button title="first-close"\n'
        "        onClick={() => close()\n"
        "        }\n"
        "      >Close</button>\n"
        '      <aside title="other-close">\n'
        "        <button onClick={() => close()}>Other close</button>\n"
        "      </aside>\n"
        "    </section>\n"
        "  );\n"
        "}\n"
    )
    source.write_text(original)
    git(tmp_path, "init", "-q")
    git(tmp_path, "add", path)
    git(
        tmp_path,
        "-c",
        "user.name=Fixture",
        "-c",
        "user.email=fixture@example.invalid",
        "commit",
        "-qm",
        "immutable positional fixture",
    )
    baseline = tool.baseline_from_report(tool.scan([path]))
    prefix = "".join(f"const SHIFT_{number} = {number};\n" for number in range(5))
    source.write_text(prefix + original.replace("choose(value ? value : null)", "choose(value)"))
    report = tool.scan([path])
    current = next(call for call in report["callables"] if call["line"] == 10)
    rightful = next(call for call in baseline["callables"] if call["line"] == 5)
    return source, baseline, report, current, rightful


def test_source_contradicted_nearest_owner_is_corrected(tool, positional_case):
    _, baseline, report, current, rightful = positional_case
    guessed, ambiguity, equivalent = positional_resolution(tool, current, report, baseline)
    assert guessed["line"] == 11
    assert guessed["loc"] == 1
    assert ambiguity is None and not equivalent
    assert current["loc"] == rightful["loc"] == 2
    assert current["fingerprint"] != rightful["fingerprint"]
    assert tool.compare(report, baseline) == (0, [])


def snapshot(tool, positional_case):
    source, baseline, report, current, _ = positional_case
    path = current["path"]
    mapping, before, after = tool.validated_source_mapping(
        path, baseline["source_commit"], source, baseline["callables"], report["callables"]
    )
    return mapping, before, after, baseline["callables"], report["callables"]


def context():
    return {"source_paths": None, "added_lines": None, "snapshots": {}, "owners": set()}


@pytest.mark.parametrize(
    ("body", "metrics"),
    [
        ("choose(value && other ? value : null)", {"cognitive", "cyclomatic"}),
        ("(\n          choose(value)\n        )", {"loc"}),
    ],
)
def test_real_below_threshold_regression_uses_rightful_metrics(
    tool, positional_case, body, metrics
):
    source, baseline, _, current, rightful = positional_case
    source.write_text(source.read_text().replace("choose(value)", body))
    report = tool.scan([current["path"]])
    code, findings = tool.compare(report, baseline)
    assert code == 1
    target = [finding for finding in findings if finding["symbol"] == current["name"]]
    assert {finding["metric"] for finding in target} == metrics
    assert all(finding["baseline"] == rightful[finding["metric"]] for finding in target)
    assert all(
        finding["value"] < tool.CALLABLE_THRESHOLDS[finding["metric"]]["warning"]
        for finding in target
    )


@pytest.mark.parametrize("commit", [None, "HEAD", "f" * 40, 17])
def test_missing_or_invalid_historical_commit_cannot_make_bug_pass(tool, positional_case, commit):
    _, baseline, report, _, _ = positional_case
    baseline["source_commit"] = commit
    assert tool.compare(report, baseline)[0] != 0


@pytest.mark.parametrize(
    "damage",
    [
        "missing",
        "syntax",
        "external",
        "current",
        "baseline",
        "unrelated",
        "kind",
        "span",
        "duplicate",
    ],
)
def test_unbound_whole_path_evidence_cannot_correct_owner(tool, positional_case, tmp_path, damage):
    source, baseline, report, current, _ = positional_case
    sources = None
    if damage == "missing":
        source.unlink()
    elif damage == "syntax":
        source.write_text("function malformed(")
    elif damage == "external":
        forged = tmp_path / "forged.tsx"
        forged.write_text("export const value = 1;")
        sources = {current["path"]: forged}
    elif damage == "current":
        current["fingerprint"] = "stale"
    elif damage == "baseline":
        baseline["callables"][1]["cognitive"] += 1
    elif damage == "unrelated":
        report["callables"][0]["loc"] += 1
    elif damage == "kind":
        current["kind"] = "forged"
    elif damage == "span":
        current["end_line"] += 1
    else:
        report["callables"].append(copy.deepcopy(current))
    assert tool.compare(report, baseline, source_paths=sources)[0] != 0


@pytest.mark.parametrize("metric", ["cognitive", "cyclomatic", "loc", "nesting", "params"])
def test_stale_metric_is_not_source_bound_or_waived(tool, positional_case, metric):
    _, baseline, report, current, _ = positional_case
    current[metric] += 1
    assert tool.compare(report, baseline)[0] != 0


@pytest.mark.parametrize("side", ["before", "after"])
def test_positively_contradicted_owner_without_safe_fence_is_ambiguous(tool, positional_case, side):
    source, baseline, _, current, _ = positional_case
    text = source.read_text()
    if side == "before":
        text = text.replace("export function Screen()", "function Screen()")
        text = text.replace("<section>", "<article>").replace("</section>", "</article>")
        text = text.replace('name="selection"', 'name="changed"')
    else:
        text = text.replace('className="selection-control"', 'className="changed"')
    source.write_text(text)
    report = tool.scan([current["path"]])
    code, findings = tool.compare(report, baseline)
    assert code == 2
    assert findings[0]["reason"] == "ambiguous_identity"


def test_owner_reservation_prevents_slot_theft(tool, positional_case):
    source, baseline, _, current, _ = positional_case
    source.write_text(
        source.read_text().replace(
            "    </section>",
            "      <input onChange={() => choose(value ? value : null)} />\n    </section>",
        )
    )
    report = tool.scan([current["path"]])
    assert tool.compare(report, baseline)[0] == 2


def test_correction_cannot_consume_owner_twice(tool, positional_case):
    _, baseline, report, current, rightful = positional_case
    resolution = positional_resolution(tool, current, report, baseline)
    local = context()
    assert tool.resolve_source_position(current, report, baseline, resolution, local) == (
        rightful,
        None,
        False,
    )
    assert (
        tool.resolve_source_position(current, report, baseline, resolution, local)[1]["reason"]
        == "ambiguous_identity"
    )


def test_contextual_proof_binds_changed_end_without_fabricated_mapping(tool, positional_case):
    _, _, _, current, rightful = positional_case
    mapping, before, after, old_calls, new_calls = snapshot(tool, positional_case)
    assert current["end_line"] not in mapping
    assert (
        tool.contextual_source_owner(current, mapping, before, after, old_calls, new_calls)
        == rightful
    )


@pytest.mark.parametrize(
    "damage",
    [
        "old_duplicate",
        "new_duplicate",
        "nested",
        "crossing",
        "wrong_start",
        "owner_start",
        "wrong_end",
        "wrong_consumer",
    ],
)
def test_contextual_slot_rejects_competitors_and_invalid_bounds(tool, positional_case, damage):
    _, _, _, current, rightful = positional_case
    mapping, before, after, old_calls, new_calls = snapshot(tool, positional_case)
    old_calls, new_calls = list(old_calls), list(new_calls)
    if damage == "old_duplicate":
        old_calls.append(copy.deepcopy(rightful))
    elif damage == "new_duplicate":
        new_calls.append(copy.deepcopy(current))
    elif damage == "nested":
        new_calls.append({**current, "line": current["end_line"]})
    elif damage == "crossing":
        new_calls.append({**current, "end_line": current["end_line"] + 10})
    elif damage == "wrong_start":
        mapping[current["line"]] += 1
    elif damage == "owner_start":
        rightful["line"] += 1
    elif damage == "wrong_end":
        rightful["end_line"] += 10
    else:
        new_calls = [copy.deepcopy(call) for call in new_calls]
    assert (
        tool.contextual_source_owner(current, mapping, before, after, old_calls, new_calls) is None
    )


def test_one_line_body_cannot_acquire_new_contextual_proof(tool, positional_case):
    _, _, _, current, _ = positional_case
    mapping, before, after, old_calls, new_calls = snapshot(tool, positional_case)
    single = {**current, "end_line": current["line"]}
    assert (
        tool.contextual_source_owner(single, mapping, before, after, old_calls, new_calls) is None
    )


def test_nonuniform_or_nonunique_exterior_context_is_rejected(tool):
    assert (
        tool.exterior_source_fence({1: 1, 2: 3}, ["before", "header"], ["before", "header"], 2, -1)
        is None
    )
    assert (
        tool.exterior_source_fence({1: 1, 2: 2}, ["same", "same"], ["same", "same"], 2, -1) is None
    )


@pytest.mark.parametrize("side", ["old", "new"])
def test_peer_crossing_context_fence_is_not_filtered(tool, positional_case, side):
    _, _, _, current, rightful = positional_case
    mapping, before, after, old_calls, new_calls = snapshot(tool, positional_case)
    old_calls, new_calls = list(old_calls), list(new_calls)
    selected = rightful if side == "old" else current
    peer = {
        **selected,
        "name": "unrelated",
        "line": selected["end_line"] + 1,
        "end_line": selected["end_line"] + 1,
    }
    (old_calls if side == "old" else new_calls).append(peer)
    assert (
        tool.contextual_source_owner(current, mapping, before, after, old_calls, new_calls) is None
    )


def test_report_order_does_not_change_ownership_and_regressions(tool, positional_case):
    _, baseline, report, _, _ = positional_case
    report["callables"].reverse()
    assert tool.compare(report, baseline) == (0, [])


def test_direct_resolution_candidates_preserve_exact_and_unique_contracts(tool, positional_case):
    _, baseline, report, current, rightful = positional_case
    assert tool.positional_candidates(current, report, baseline, None) == []
    assert tool.positional_candidates(current, report, baseline, current) == []
    exact = copy.deepcopy(current)
    baseline["callables"].append(exact)
    assert tool.positional_candidates(current, report, baseline, rightful) == []


def test_source_peer_check_allows_children_but_rejects_adjacent_crossings(tool):
    owner = {"line": 10, "end_line": 20}
    assert not tool.source_fence_has_peer([{"line": 11, "end_line": 12}], owner, 8, 23)
    assert tool.source_fence_has_peer([{"line": 9, "end_line": 11}], owner, 8, 23)
    assert tool.source_fence_has_peer([{"line": 19, "end_line": 24}], owner, 8, 23)


def commit_source(tool, source, text):
    source.write_text(text)
    path = source.relative_to(tool.ROOT).as_posix()
    git(tool.ROOT, "add", path)
    git(
        tool.ROOT,
        "-c",
        "user.name=Fixture",
        "-c",
        "user.email=fixture@example.invalid",
        "commit",
        "--allow-empty",
        "-qm",
        "source-bound counterfixture",
    )
    return tool.baseline_from_report(tool.scan([path]))


def target_call(report, source, header):
    line = next(
        number for number, text in enumerate(source.read_text().splitlines(), 1) if header in text
    )
    return next(call for call in report["callables"] if call["line"] == line)


@pytest.fixture
def comment_case(tool, positional_case):
    source, _, _, _, _ = positional_case
    original = (
        "export function Screen() {\n"
        "  // SELECTION_BEFORE\n"
        "  values.map(() =>\n"
        "    choose(value ? value : null)\n"
        "  );\n"
        "  // SELECTION_AFTER\n"
        "\n"
        "  // FIRST_CLOSE\n"
        "  values.map(() => close());\n"
        "\n"
        "  // SECOND_CLOSE\n"
        "  values.map(() => close());\n"
        "}\n"
    )
    baseline = commit_source(tool, source, original)
    prefix = "".join(f"const SHIFT_{number} = {number};\n" for number in range(5))
    text = prefix + original.replace("choose(value ? value : null)", "choose(value)")
    source.write_text(text)
    report = tool.scan([source.relative_to(tool.ROOT).as_posix()])
    current = target_call(report, source, "values.map(() =>")
    rightful = next(call for call in baseline["callables"] if call["line"] == 3)
    guessed, ambiguity, _ = positional_resolution(tool, current, report, baseline)
    assert guessed != rightful and ambiguity is None
    return source, baseline, report, current, rightful


@pytest.mark.parametrize("side", ["old", "new", "both"])
def test_real_compatible_ancestor_cannot_be_discarded(tool, positional_case, side):
    source, _, _, _, _ = positional_case
    original = git(tool.ROOT, "show", "HEAD:frontend/src/Screen.tsx") + "\n"

    def wrap(text):
        text = text.replace(
            '      <input name="selection"',
            '      <div onClick={() => (\n      <input name="selection"',
        )
        return text.replace(
            '      <button title="first-close"', '      )} />\n      <button title="first-close"'
        )

    baseline_text = wrap(original) if side in {"old", "both"} else original
    baseline = commit_source(tool, source, baseline_text)
    current_text = wrap(original) if side in {"new", "both"} else original
    prefix = "".join(f"const SHIFT_{number} = {number};\n" for number in range(20))
    source.write_text(
        prefix + current_text.replace("choose(value ? value : null)", "choose(value)")
    )
    report = tool.scan(["frontend/src/Screen.tsx"])
    current = target_call(report, source, "onChange={() =>")
    resolution = positional_resolution(tool, current, report, baseline)
    assert resolution[0] is not None and resolution[1] is None
    snapshot_calls = baseline["callables"] if side == "old" else report["callables"]
    selected = next(
        call
        for call in snapshot_calls
        if call["name"] == current["name"] and call["line"] != 1 and call["loc"] == 2
    )
    assert any(
        call["name"] == selected["name"]
        and call["kind"] == selected["kind"]
        and call["line"] < selected["line"]
        and call["end_line"] > selected["end_line"]
        for call in snapshot_calls
    )
    assert (
        tool.resolve_source_position(current, report, baseline, resolution, context())[1]["reason"]
        == "ambiguous_identity"
    )


def test_route_reuses_one_accepted_snapshot_then_fresh_compare_reads_again(
    tool, comment_case, monkeypatch
):
    source, baseline, report, _, _ = comment_case
    accepted = source.read_bytes()
    refused = accepted.replace(b"SELECTION_BEFORE", b"CHANGED_BEFORE")
    source.write_bytes(refused)
    assert [
        tool.source_callable_signature(call)
        for call in tool.scan(["frontend/src/Screen.tsx"])["callables"]
    ] == [tool.source_callable_signature(call) for call in report["callables"]]
    original_read = type(source).read_bytes
    reads = []

    def read(path):
        if path == source:
            reads.append(path)
            return accepted if len(reads) == 1 else refused
        return original_read(path)

    monkeypatch.setattr(type(source), "read_bytes", read)
    assert tool.compare(report, baseline) == (0, [])
    assert len(reads) == 1
    assert tool.compare(report, baseline)[0] == 2
    assert len(reads) == 2


def test_route_refused_snapshot_remains_sticky_until_fresh_context(tool, comment_case):
    source, baseline, report, current, rightful = comment_case
    accepted = source.read_bytes()
    source.write_bytes(accepted.replace(b"SELECTION_BEFORE", b"CHANGED_BEFORE"))
    resolution = positional_resolution(tool, current, report, baseline)
    local = context()
    assert (
        tool.resolve_source_position(current, report, baseline, resolution, local)[1]["reason"]
        == "ambiguous_identity"
    )
    source.write_bytes(accepted)
    assert (
        tool.resolve_source_position(current, report, baseline, resolution, local)[1]["reason"]
        == "ambiguous_identity"
    )
    assert tool.resolve_source_position(current, report, baseline, resolution, context()) == (
        rightful,
        None,
        False,
    )


@pytest.mark.parametrize("reverse", [False, True])
def test_duplicate_requests_cannot_share_corrected_owner_in_either_order(
    tool, comment_case, reverse
):
    _, baseline, report, current, _ = comment_case
    duplicate = copy.deepcopy(current)
    report["callables"].append(duplicate)
    if reverse:
        report["callables"].reverse()
    assert tool.compare(report, baseline)[0] != 0
    local = context()
    requests = [duplicate, current] if reverse else [current, duplicate]
    for request in requests:
        resolution = positional_resolution(tool, request, report, baseline)
        assert tool.resolve_source_position(request, report, baseline, resolution, local)[
            0
        ] != next(call for call in baseline["callables"] if call["line"] == 3)


def test_equivalent_multiset_consumption_prevents_correction(tool, comment_case):
    source, _, _, _, _ = comment_case
    original = git(tool.ROOT, "show", "HEAD:frontend/src/Screen.tsx") + "\n"
    original = original.replace(
        "}\n", "  values.map(() =>\n    choose(value ? value : null)\n  );\n}\n"
    )
    baseline = commit_source(tool, source, original)
    prefix = "".join(f"const SHIFT_{number} = {number};\n" for number in range(5))
    source.write_text(prefix + original.replace("choose(value ? value : null)", "choose(value)", 1))
    report = tool.scan(["frontend/src/Screen.tsx"])
    current = target_call(report, source, "values.map(() =>")
    resolution = positional_resolution(tool, current, report, baseline)
    assert resolution[0] is not None and resolution[1] is None
    assert (
        tool.resolve_source_position(current, report, baseline, resolution, context())[1]["reason"]
        == "ambiguous_identity"
    )


def test_moved_source_slot_cannot_gain_context_from_neighbor(tool, positional_case):
    source, baseline, _, _, _ = positional_case
    text = source.read_text()
    start = text.index('      <input name="selection"')
    end = text.index('      <button title="first-close"')
    selected = text[start:end]
    text = text[:start] + text[end:]
    text = text.replace("    </section>", selected + "    </section>")
    source.write_text(text)
    report = tool.scan(["frontend/src/Screen.tsx"])
    assert tool.compare(report, baseline)[0] != 0


def test_real_boundary_peer_is_not_an_exterior_fence(tool, positional_case):
    source, _, _, _, _ = positional_case
    original = git(tool.ROOT, "show", "HEAD:frontend/src/Screen.tsx") + "\n"
    original = original.replace(
        '        className="selection-control"',
        '        className="selection-control" onBlur={() => blur()}',
    )
    baseline = commit_source(tool, source, original)
    prefix = "".join(f"const SHIFT_{number} = {number};\n" for number in range(5))
    source.write_text(prefix + original.replace("choose(value ? value : null)", "choose(value)"))
    report = tool.scan(["frontend/src/Screen.tsx"])
    current = target_call(report, source, "onChange={() =>")
    mapping, before, after = tool.validated_source_mapping(
        current["path"],
        baseline["source_commit"],
        source,
        baseline["callables"],
        report["callables"],
    )
    trailing = tool.exterior_source_fence(mapping, before, after, current["end_line"], 1)
    assert any(
        call["line"] == trailing and call["name"] == current["name"] for call in report["callables"]
    )
    assert tool.compare(report, baseline)[0] == 2


def test_duplicate_context_label_does_not_establish_new_owner(tool, comment_case):
    source, baseline, report, current, _ = comment_case
    source.write_text(source.read_text().replace("SELECTION_BEFORE", "FIRST_CLOSE"))
    assert [
        tool.source_callable_signature(call) for call in tool.scan([current["path"]])["callables"]
    ] == [tool.source_callable_signature(call) for call in report["callables"]]
    assert tool.compare(report, baseline)[0] == 2


def test_real_nesting_regression_is_not_transferred_to_larger_neighbor(tool, positional_case):
    source, baseline, _, _, rightful = positional_case
    source.write_text(
        source.read_text().replace(
            "choose(value)", "{ if (value) { if (other) { choose(value); } } }"
        )
    )
    report = tool.scan(["frontend/src/Screen.tsx"])
    current = target_call(report, source, "onChange={() =>")
    code, findings = tool.compare(report, baseline)
    assert code == 1
    nesting = next(
        finding
        for finding in findings
        if finding["symbol"] == current["name"] and finding["metric"] == "nesting"
    )
    assert nesting["baseline"] == rightful["nesting"] == 0
    assert nesting["value"] == 2


def test_real_header_parameter_increase_does_not_gain_source_proof(tool, positional_case):
    source, baseline, _, _, rightful = positional_case
    source.write_text(source.read_text().replace("onChange={() =>", "onChange={(event) =>"))
    report = tool.scan(["frontend/src/Screen.tsx"])
    current = target_call(report, source, "onChange={(event) =>")
    code, findings = tool.compare(report, baseline)
    assert code != 0
    assert any(
        finding.get("metric") == "params"
        and finding["symbol"] == current["name"]
        and finding["baseline"] == rightful["params"] == 0
        for finding in findings
    )


def test_added_high_complexity_callback_still_fails(tool, positional_case):
    source, baseline, _, _, _ = positional_case
    conditions = "\n".join(
        f"          if (value > {number}) choose(value);" for number in range(15)
    )
    added = "      <input onChange={() => {\n" + conditions + "\n      }} />\n"
    source.write_text(source.read_text().replace("    </section>", added + "    </section>"))
    report = tool.scan(["frontend/src/Screen.tsx"])
    current = next(
        call
        for call in report["callables"]
        if call["cognitive"] == 15 and call["name"] == "Program<anonymous>"
    )
    assert any(violation["severity"] == "error" for violation in current["violations"])
    added_lines = {current["path"]: set(range(current["line"], current["end_line"] + 1))}
    code, findings = tool.compare(report, baseline, added_lines=added_lines)
    assert code != 0
    assert any(
        finding.get("metric") == "cognitive" and finding["value"] >= 15 for finding in findings
    )
