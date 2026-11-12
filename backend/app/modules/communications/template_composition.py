"""Read-only text preparation reports incomplete data separately from dispatch eligibility."""

import re

from . import registry, ruolo_source
from .policy import Conflict, pdf_pages, render_template, sha256


def preview_composition(db, identity, template_id, channel):
    template = registry.approved_template(db, template_id, channel)
    source = ruolo_source.source_item(db, identity)
    if source.status != "generated" or source.years_json != [2021]:
        raise Conflict("Anteprima disponibile solo per PDF definitivi 2021")
    content = ruolo_source.read_pdf(source)
    pdf_pages(content)
    digest = sha256(content)
    variables = ruolo_source.template_variables(source)
    required = set(re.findall(r"\{\{\s*([a-z_]+)\s*\}\}", template.subject + template.body))
    missing = sorted(required - variables.keys())
    prepared = {**variables, **{key: f"[Da verificare: {key}]" for key in missing}}
    return {
        "subject": render_template(template.subject, prepared),
        "body": render_template(template.body, prepared),
        "source_sha256": digest,
        "missing_variables": missing,
        "send_blockers": send_blockers(db, identity, digest),
    }


def send_blockers(db, identity, expected_sha):
    try:
        _, _, content, _ = ruolo_source.inspect(db, identity)
        if sha256(content) != expected_sha:
            raise Conflict("PDF cambiato durante la composizione: riaprire l'avviso")
    except Conflict as exc:
        return [str(exc)]
    return []
