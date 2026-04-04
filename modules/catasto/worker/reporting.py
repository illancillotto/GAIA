from __future__ import annotations

from collections import Counter
import json
from pathlib import Path


def write_batch_report(batch, requests: list[object], target_dir: Path) -> tuple[Path, Path]:
    target_dir.mkdir(parents=True, exist_ok=True)
    status_counter = Counter(getattr(item, "status", "unknown") for item in requests)

    report = {
        "batch_id": str(batch.id),
        "batch_name": batch.name,
        "status": batch.status,
        "total_items": len(requests),
        "completed": status_counter.get("completed", 0),
        "failed": status_counter.get("failed", 0),
        "skipped": status_counter.get("skipped", 0),
        "not_found": status_counter.get("not_found", 0),
        "requests": [
            {
                "request_id": str(item.id),
                "row_index": item.row_index,
                "search_mode": item.search_mode,
                "label": _build_request_label(item),
                "status": item.status,
                "current_operation": item.current_operation,
                "error_message": item.error_message,
                "attempts": item.attempts,
                "artifact_dir": item.artifact_dir,
                "document_id": str(item.document_id) if item.document_id else None,
                "processed_at": item.processed_at.isoformat() if item.processed_at else None,
            }
            for item in requests
        ],
    }

    json_path = target_dir / "report.json"
    md_path = target_dir / "report.md"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        "# Report Visure",
        "",
        f"- Batch: {batch.name or batch.id}",
        f"- Stato: {batch.status}",
        f"- Totale: {len(requests)}",
        f"- Completate: {status_counter.get('completed', 0)}",
        f"- Fallite: {status_counter.get('failed', 0)}",
        f"- Saltate: {status_counter.get('skipped', 0)}",
        f"- Not found: {status_counter.get('not_found', 0)}",
        "",
        "## Richieste",
    ]
    for item in requests:
        lines.append(
            f"- [{item.status}] {_build_request_label(item)}"
            f" | attempts={item.attempts}"
            f" | artifact_dir={item.artifact_dir or '-'}"
            f" | error={item.error_message or '-'}"
        )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path


def _build_request_label(request: object) -> str:
    if getattr(request, "search_mode", "immobile") == "soggetto":
        subject_kind = getattr(request, "subject_kind", None) or "SOGGETTO"
        subject_id = getattr(request, "subject_id", None) or "-"
        request_type = getattr(request, "request_type", None) or "-"
        return f"{subject_kind} {subject_id} ({request_type})"
    comune = getattr(request, "comune", None) or "-"
    foglio = getattr(request, "foglio", None) or "-"
    particella = getattr(request, "particella", None) or "-"
    subalterno = getattr(request, "subalterno", None)
    suffix = f"/{subalterno}" if subalterno else ""
    return f"{comune} Fg.{foglio} Part.{particella}{suffix}"
