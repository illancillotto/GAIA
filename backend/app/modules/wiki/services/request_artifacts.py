from __future__ import annotations

import json
import uuid
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.application_user import ApplicationUser
from app.modules.wiki.models import WikiRequest, WikiRequestArtifact
from app.modules.wiki.services.request_workflow import append_request_event


def store_wiki_request_artifact_file(
    *,
    request_id: uuid.UUID,
    artifact_id: uuid.UUID,
    upload: UploadFile,
) -> tuple[str, str | None, str | None]:
    artifact_root = Path(settings.wiki_request_artifacts_path).expanduser() / str(request_id)
    artifact_root.mkdir(parents=True, exist_ok=True)
    suffix = Path(upload.filename or "").suffix or ".bin"
    filename = f"{artifact_id}{suffix}"
    storage_path = artifact_root / filename
    file_bytes = upload.file.read()
    storage_path.write_bytes(file_bytes)
    return str(storage_path), upload.filename, upload.content_type


def create_request_artifacts(
    db: Session,
    *,
    req: WikiRequest,
    current_user: ApplicationUser,
    screenshot: UploadFile | None,
    screenshot_meta: dict[str, object] | None,
    ui_snapshot: dict[str, object] | None,
) -> None:
    artifacts_created = 0

    if screenshot is not None:
        artifact_id = uuid.uuid4()
        storage_path, original_filename, mime_type = store_wiki_request_artifact_file(
            request_id=req.id,
            artifact_id=artifact_id,
            upload=screenshot,
        )
        db.add(
            WikiRequestArtifact(
                id=artifact_id,
                request_id=req.id,
                artifact_type="screenshot",
                filename=original_filename,
                mime_type=mime_type,
                storage_path=storage_path,
                created_by=current_user.username,
            )
        )
        artifacts_created += 1

    if screenshot_meta:
        db.add(
            WikiRequestArtifact(
                id=uuid.uuid4(),
                request_id=req.id,
                artifact_type="screenshot_meta",
                mime_type="application/json",
                payload_json=json.dumps(screenshot_meta, ensure_ascii=True),
                created_by=current_user.username,
            )
        )
        artifacts_created += 1

    if ui_snapshot:
        db.add(
            WikiRequestArtifact(
                id=uuid.uuid4(),
                request_id=req.id,
                artifact_type="ui_snapshot",
                mime_type="application/json",
                payload_json=json.dumps(ui_snapshot, ensure_ascii=True),
                created_by=current_user.username,
            )
        )
        artifacts_created += 1

    if artifacts_created:
        append_request_event(
            db,
            request_id=req.id,
            event_type="snapshot_captured",
            actor_username=current_user.username,
            payload={
                "artifacts_created": artifacts_created,
                "has_screenshot": screenshot is not None,
                "has_ui_snapshot": ui_snapshot is not None,
            },
        )
