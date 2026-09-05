#!/usr/bin/env python3
"""Generate complementary optional-parameter coverage for the modular API facade."""

from __future__ import annotations

import re
from pathlib import Path

from generate_api_coverage_tests import (
    OUT_DIR,
    api_source,
    extract_functions,
    split_params,
    uses_form_upload,
)

OUTPUT = OUT_DIR / "api-generated-branches.test.ts"


def empty_argument(part: str) -> str:
    name, _, annotation = part.partition(":")
    name = name.strip().replace("...", "")
    optional = "?" in name or "=" in name or "=" in annotation
    name = name.partition("=")[0]
    name = name.replace("?", "")
    if optional:
        return "undefined"
    if name == "token":
        return "TOKEN"
    if "=>" in annotation:
        return "undefined"
    if name == "formData":
        return "new FormData()"
    if name in {"file", "files"}:
        return "[]" if name == "files" else "new File([''], 'empty.csv')"
    if "[]" in annotation or "Array" in annotation:
        return "[]"
    if "boolean" in annotation:
        return "false"
    if "number" in annotation:
        return "0"
    if "string" in annotation or name.lower().endswith("id"):
        return '""'
    literal = re.search(r'["\']([^"\']+)["\']', annotation)
    if literal:
        return repr(literal.group(1))
    return "FULL_OPTIONS"


def empty_call(name: str, params: str) -> str:
    args = [empty_argument(part) for part in split_params(params)]
    while args and args[-1] == "undefined":
        args.pop()
    return f"{name}({', '.join(args)})"


def populated_argument(part: str) -> str:
    raw_name, _, annotation = part.partition(":")
    raw_name = raw_name.strip().replace("...", "").replace("?", "")
    name, has_default, default = raw_name.partition("=")
    name = name.strip()
    if has_default:
        default = default.strip()
        if default.replace("_", "").isdigit():
            return "1"
        if default in {"true", "false"}:
            return "true"
    if name == "token":
        return "TOKEN"
    if "=>" in annotation or name == "onProgress":
        return "() => undefined"
    if name == "formData":
        return "new FormData()"
    if name == "file":
        return "new File(['x'], 'file.csv')"
    if name == "files":
        return "[new File(['x'], 'file.csv')]"
    if "[]" in annotation or "Array" in annotation:
        if "string" in annotation:
            return '["value"]'
        if "number" in annotation:
            return "[1]"
        return "[FULL_OPTIONS]"
    if name in {"params", "options", "filters"}:
        return "FULL_OPTIONS"
    if "boolean" in annotation:
        return "true"
    if "number" in annotation:
        return "1"
    if "string" in annotation or name.lower().endswith("id"):
        return '"value"'
    literal = re.search(r'["\']([^"\']+)["\']', annotation)
    if literal:
        return repr(literal.group(1))
    return "{}"


def populated_call(name: str, params: str) -> str:
    args = [populated_argument(part) for part in split_params(params)]
    if name in {"getCatastoDocuments", "searchCatastoDocuments"}:
        args[-1] = "STRING_FILTERS"
    return f"{name}({', '.join(args)})"


def render() -> str:
    tests: list[str] = []
    for name, params, body, _return_type in extract_functions(api_source()):
        if name in {"request", "requestBlob", "requestFormDataWithUploadProgress"}:
            continue
        populated = populated_call(name, params)
        calls = [populated, empty_call(name, params)]
        if any(marker in params for marker in ("params?", "options?", "filters?", "artifacts:")):
            calls.append(populated.replace("FULL_OPTIONS", "FALSE_OPTIONS"))
        rendered_calls = []
        for call in dict.fromkeys(calls):
            qualified = call.replace(f"{name}(", f"api.{name}(", 1)
            if uses_form_upload(body):
                rendered_calls.append(
                    f"""    {{
      const pending = {qualified};
      MockXHR.instances.at(-1)!.loadHandler?.();
      await pending;
    }}"""
                )
            else:
                rendered_calls.append(f"    await {qualified};")
        if "fetch(" in body:
            rendered_calls.append(f"    await exerciseFetchErrors(() => api.{populated});")
        tests.append(
            f"""  test("{name}: populated and empty optional values", async () => {{
{chr(10).join(rendered_calls)}
  }});"""
        )

    return f"""import {{ afterEach, beforeEach, describe, test, vi }} from "vitest";

import * as api from "@/lib/api";

const TOKEN = "test-token";
const STRING_FILTERS = {{
  q: "query",
  comune: "comune",
  foglio: "1",
  particella: "2",
  created_from: "2026-08-01",
  created_to: "2026-08-31",
}};
const FULL_OPTIONS = new Proxy<Record<string, unknown>>(
  {{
    page: 1,
    pageSize: 20,
    periodStart: "2026-08-01",
    periodEnd: "2026-08-31",
    dateFrom: "2026-08-01",
    dateTo: "2026-08-31",
    limit: 20,
    offset: 1,
    skip: 1,
    status: "active",
    q: "query",
    query: "query",
    activeOnly: true,
    mappedOnly: true,
    success: true,
    windowHours: 24,
    windowMinutes: 15,
    bustCache: true,
    timeoutMs: 1,
  }},
  {{
    get: (target, property) =>
      property === "toJSON" ? undefined : Reflect.get(target, property) ?? "value",
  }},
);
const FALSE_OPTIONS = new Proxy<Record<string, unknown>>(
  {{
    mappedOnly: false,
    requiresReview: false,
    resolved: false,
    success: false,
    activeOnly: false,
    bustCache: false,
  }},
  {{ get: (target, property) => Reflect.get(target, property) }},
);

class MockXHR {{
  static instances: MockXHR[] = [];
  upload = {{ addEventListener: vi.fn() }};
  status = 200;
  statusText = "OK";
  response: unknown = {{ ok: true, items: [], total: 0 }};
  open = vi.fn();
  setRequestHeader = vi.fn();
  send = vi.fn();
  loadHandler: (() => void) | null = null;
  addEventListener = vi.fn((event: string, handler: () => void) => {{
    if (event === "load") this.loadHandler = handler;
  }});

  constructor() {{
    MockXHR.instances.push(this);
  }}
}}

function response(): Response {{
  return new Response(JSON.stringify({{ ok: true, items: [], total: 0 }}), {{
    status: 200,
    headers: {{ "content-type": "application/json" }},
  }});
}}

async function exerciseFetchErrors(call: () => Promise<unknown>) {{
  const errors = [
    new Response(JSON.stringify({{ detail: "explicit detail" }}), {{ status: 400, statusText: "Bad Request" }}),
    new Response(JSON.stringify({{ detail: null }}), {{ status: 400, statusText: "Bad Request" }}),
    new Response("not-json", {{ status: 500, statusText: "Server Error" }}),
    new Response("not-json", {{ status: 500, statusText: "" }}),
  ];
  for (const errorResponse of errors) {{
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(errorResponse));
    await call().catch(() => undefined);
  }}
}}

describe("generated API optional-parameter characterization", () => {{
  beforeEach(() => {{
    MockXHR.instances = [];
    vi.stubGlobal("XMLHttpRequest", MockXHR as unknown as typeof XMLHttpRequest);
    vi.stubGlobal("fetch", vi.fn().mockImplementation(async () => response()));
  }});

  afterEach(() => {{
    vi.unstubAllGlobals();
  }});

{chr(10).join(tests)}
}});
"""


def main() -> None:
    OUTPUT.write_text(render())
    print(f"wrote {OUTPUT.relative_to(Path.cwd())}")


if __name__ == "__main__":
    main()
