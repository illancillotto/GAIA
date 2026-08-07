from __future__ import annotations

import argparse
import asyncio
import csv
import json
import os
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from app.core.database import SessionLocal
from app.services.elaborazioni_capacitas import pick_credential
from app.modules.elaborazioni.capacitas.session import CapacitasSessionManager
from app.modules.elaborazioni.capacitas.apps.incass.client import InCassClient
from app.modules.ruolo.services.capacitas_role_codes import (
    CAPACITAS_ROLE_KIND_UNCLASSIFIED,
    classify_capacitas_role_code,
    sort_capacitas_role_codes,
)

DEFAULT_INPUT = Path('/home/cbo/CursorProjects/GAIA/reports/ana-subjects-roles-coverage-20260806/ana_subjects_role_coverage.csv')
DEFAULT_OUTDIR = Path('/home/cbo/CursorProjects/GAIA/reports/ana-subjects-capacitas-live-20260806')


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def norm(s: object) -> str:
    return str(s or '').strip().upper()


def row_to_dict(row):
    return row.model_dump(mode='json') if hasattr(row, 'model_dump') else dict(row)


def load_done(path: Path) -> set[str]:
    if not path.exists() or path.stat().st_size == 0:
        return set()
    done: set[str] = set()
    with path.open(encoding='utf-8', newline='') as f:
        for r in csv.DictReader(f):
            sid = r.get('subject_id')
            if sid:
                done.add(sid)
    return done


def summarize(results_path: Path, summary_path: Path, *, total_input: int, total_queryable: int, finished: bool = False) -> dict:
    counts = Counter()
    raw_code_counts: dict[str, int] = defaultdict(int)
    ordinary_year_counts: dict[str, int] = defaultdict(int)
    special_code_counts: dict[str, int] = defaultdict(int)
    special_kind_counts: dict[str, int] = defaultdict(int)
    unclassified_code_counts: dict[str, int] = defaultdict(int)
    rows_done = 0
    if results_path.exists() and results_path.stat().st_size > 0:
        with results_path.open(encoding='utf-8', newline='') as f:
            for r in csv.DictReader(f):
                rows_done += 1
                counts[r.get('live_status') or ''] += 1
                row_special_kinds: set[str] = set()
                for code in (r.get('live_years') or '').split(','):
                    code = code.strip()
                    if not code:
                        continue
                    raw_code_counts[code] += 1
                    classification = classify_capacitas_role_code(code)
                    if classification.is_ordinary_role and classification.ordinary_year is not None:
                        ordinary_year_counts[str(classification.ordinary_year)] += 1
                    elif classification.is_known_special:
                        special_code_counts[classification.code] += 1
                        row_special_kinds.add(classification.kind)
                    elif classification.kind == CAPACITAS_ROLE_KIND_UNCLASSIFIED:
                        unclassified_code_counts[classification.code] += 1
                for kind in row_special_kinds:
                    special_kind_counts[kind] += 1
    summary = {
        'updated_at': now_iso(),
        'finished': finished,
        'total_input_subjects': total_input,
        'total_queryable_subjects': total_queryable,
        'processed_queryable_subjects': rows_done,
        'remaining_queryable_subjects': max(total_queryable - rows_done, 0),
        'status_counts': dict(counts),
        'live_year_subject_counts': dict(sorted(raw_code_counts.items())),
        'live_raw_code_subject_counts': dict(sorted(raw_code_counts.items())),
        'live_ordinary_year_subject_counts': dict(sorted(ordinary_year_counts.items())),
        'live_special_code_subject_counts': dict(sorted(special_code_counts.items())),
        'live_special_kind_subject_counts': dict(sorted(special_kind_counts.items())),
        'live_unclassified_code_subject_counts': dict(sorted(unclassified_code_counts.items())),
        'results_csv': str(results_path),
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    return summary


async def run(args: argparse.Namespace) -> int:
    input_path = Path(args.input)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    results_path = outdir / 'ana_subjects_capacitas_live_results.csv'
    summary_path = outdir / 'summary.json'
    errors_path = outdir / 'errors.csv'
    skipped_path = outdir / 'skipped_no_identifier.csv'

    all_rows = list(csv.DictReader(input_path.open(encoding='utf-8', newline='')))
    queryable = [r for r in all_rows if norm(r.get('primary_identifier'))]
    if args.only_no_local_roles:
        queryable = [r for r in queryable if r.get('status') == 'no_roles_any_year']
    if args.requires_review_false:
        queryable = [r for r in queryable if str(r.get('requires_review')).lower() in {'false', '0', ''}]
    if args.limit:
        queryable = queryable[: args.limit]

    # Persist skipped once for traceability.
    if not skipped_path.exists():
        skipped = [r for r in all_rows if not norm(r.get('primary_identifier'))]
        with skipped_path.open('w', encoding='utf-8', newline='') as f:
            fields = list(all_rows[0].keys()) if all_rows else ['empty']
            w = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
            w.writeheader(); w.writerows(skipped)

    fieldnames = [
        'checked_at', 'subject_id', 'subject_type', 'requires_review', 'display_name',
        'primary_identifier', 'secondary_company_cf', 'local_years_with_role', 'local_years_missing_role',
        'live_status', 'live_total_rows', 'live_years', 'live_ordinary_years', 'live_special_codes',
        'live_unclassified_codes', 'live_rows_by_year_json', 'live_avvisi_by_year_json',
        'live_special_codes_json', 'live_denominazioni_sample', 'error',
    ]
    if not results_path.exists() or results_path.stat().st_size == 0:
        with results_path.open('w', encoding='utf-8', newline='') as f:
            csv.DictWriter(f, fieldnames=fieldnames).writeheader()
    if not errors_path.exists() or errors_path.stat().st_size == 0:
        with errors_path.open('w', encoding='utf-8', newline='') as f:
            csv.DictWriter(f, fieldnames=fieldnames).writeheader()

    done = load_done(results_path)
    pending = [r for r in queryable if r.get('subject_id') not in done]
    print(f'input={len(all_rows)} queryable={len(queryable)} already_done={len(done)} pending={len(pending)} outdir={outdir}', flush=True)

    db = SessionLocal()
    manager = None
    try:
        credential, password = pick_credential(db, None)
        manager = CapacitasSessionManager(credential.username, password)
        await manager.login()
        await manager.activate_app('incass')
        await manager.start_keepalive('incass')
        client = InCassClient(manager)
        await client.warmup_search_page()

        processed_this_run = 0
        for idx, r in enumerate(pending, start=1):
            identifier = norm(r.get('primary_identifier'))
            base = {
                'checked_at': now_iso(),
                'subject_id': r.get('subject_id', ''),
                'subject_type': r.get('subject_type', ''),
                'requires_review': r.get('requires_review', ''),
                'display_name': r.get('display_name', ''),
                'primary_identifier': identifier,
                'secondary_company_cf': norm(r.get('secondary_company_cf')),
                'local_years_with_role': r.get('years_with_role', ''),
                'local_years_missing_role': r.get('years_missing_role', ''),
                'live_status': '',
                'live_total_rows': 0,
                'live_years': '',
                'live_ordinary_years': '',
                'live_special_codes': '',
                'live_unclassified_codes': '',
                'live_rows_by_year_json': '{}',
                'live_avvisi_by_year_json': '{}',
                'live_special_codes_json': '{}',
                'live_denominazioni_sample': '',
                'error': '',
            }
            try:
                search = await client.search_notices(identifier)
                live_rows = [row_to_dict(x) for x in search.rows]
                by_year: dict[str, list[dict]] = defaultdict(list)
                for lr in live_rows:
                    year = str(lr.get('anno') or '').strip()
                    if year:
                        by_year[year].append(lr)
                years = sorted(by_year.keys())
                avvisi_by_year = {
                    y: [str(x.get('avviso') or '') for x in vals[:20]]
                    for y, vals in by_year.items()
                }
                classifications = {y: classify_capacitas_role_code(y) for y in years}
                ordinary_years = sorted({
                    str(c.ordinary_year)
                    for c in classifications.values()
                    if c.is_ordinary_role and c.ordinary_year is not None
                })
                special_codes = sort_capacitas_role_codes(
                    c.code for c in classifications.values() if c.is_known_special
                )
                unclassified_codes = sort_capacitas_role_codes(
                    c.code for c in classifications.values() if c.kind == CAPACITAS_ROLE_KIND_UNCLASSIFIED
                )
                special_codes_json = {
                    y: {
                        **classifications[y].to_dict(),
                        'rows': len(by_year[y]),
                        'avvisi': avvisi_by_year.get(y, []),
                    }
                    for y in [*special_codes, *unclassified_codes]
                }
                base.update({
                    'live_status': 'present_live' if live_rows else 'not_found_live',
                    'live_total_rows': len(live_rows),
                    'live_years': ','.join(years),
                    'live_ordinary_years': ','.join(ordinary_years),
                    'live_special_codes': ','.join(special_codes),
                    'live_unclassified_codes': ','.join(unclassified_codes),
                    'live_rows_by_year_json': json.dumps({y: len(v) for y, v in by_year.items()}, ensure_ascii=False, sort_keys=True),
                    'live_avvisi_by_year_json': json.dumps(avvisi_by_year, ensure_ascii=False, sort_keys=True),
                    'live_special_codes_json': json.dumps(special_codes_json, ensure_ascii=False, sort_keys=True),
                    'live_denominazioni_sample': '; '.join(str(x.get('denominazione') or '') for x in live_rows[:5]),
                })
            except Exception as exc:
                base['live_status'] = 'error'
                base['error'] = f'{type(exc).__name__}: {exc}'[:1000]
                with errors_path.open('a', encoding='utf-8', newline='') as f:
                    csv.DictWriter(f, fieldnames=fieldnames).writerow(base)
                try:
                    await client.refresh_session()
                except Exception:
                    pass
            with results_path.open('a', encoding='utf-8', newline='') as f:
                csv.DictWriter(f, fieldnames=fieldnames).writerow(base)
            processed_this_run += 1
            if processed_this_run % args.summary_every == 0:
                summary = summarize(results_path, summary_path, total_input=len(all_rows), total_queryable=len(queryable), finished=False)
                print(f"progress this_run={processed_this_run} total_done={summary['processed_queryable_subjects']}/{summary['total_queryable_subjects']} counts={summary['status_counts']}", flush=True)
            await asyncio.sleep(args.throttle_ms / 1000)
    finally:
        if manager is not None:
            await manager.close()
        db.close()

    summary = summarize(results_path, summary_path, total_input=len(all_rows), total_queryable=len(queryable), finished=True)
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
    return 0


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument('--input', default=str(DEFAULT_INPUT))
    p.add_argument('--outdir', default=str(DEFAULT_OUTDIR))
    p.add_argument('--limit', type=int, default=0)
    p.add_argument('--throttle-ms', type=int, default=800)
    p.add_argument('--summary-every', type=int, default=100)
    p.add_argument('--only-no-local-roles', action='store_true')
    p.add_argument('--requires-review-false', action='store_true')
    return p.parse_args()


if __name__ == '__main__':
    raise SystemExit(asyncio.run(run(parse_args())))
