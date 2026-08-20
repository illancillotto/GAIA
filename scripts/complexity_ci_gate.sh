#!/usr/bin/env bash
set -euo pipefail

base_ref="${BASE_REF:-}"
if [[ -z "$base_ref" ]]; then
  if [[ "${GITHUB_EVENT_NAME:-}" == "pull_request" && -n "${GITHUB_BASE_REF:-}" ]]; then
    base_ref="origin/${GITHUB_BASE_REF}"
  elif [[ -n "${GITHUB_BASE_REF:-}" ]]; then
    base_ref="origin/${GITHUB_BASE_REF}"
  elif git rev-parse --verify origin/main >/dev/null 2>&1; then
    base_ref="origin/main"
  else
    echo "::error::BASE_REF is not set and origin/main is unavailable; cannot run GAIA differential complexity gate." >&2
    exit 2
  fi
fi

if ! git rev-parse --verify "$base_ref" >/dev/null 2>&1; then
  if [[ "$base_ref" == origin/* ]]; then
    branch="${base_ref#origin/}"
    git fetch --no-tags --prune --depth=0 origin "$branch" || true
  fi
fi

if ! merge_base="$(git merge-base "$base_ref" HEAD 2>/dev/null)" || [[ -z "$merge_base" ]]; then
  echo "::error::merge-base unavailable for BASE_REF=$base_ref. Ensure actions/checkout uses fetch-depth: 0 or fetch the PR base branch." >&2
  exit 2
fi

echo "GAIA differential complexity gate"
echo "BASE_REF=$base_ref"
echo "MERGE_BASE=$merge_base"

report_json="${REPORT_JSON:-/tmp/gaia-complexity-ci-report.json}"
report_md="${REPORT_MD:-/tmp/gaia-complexity-ci-report.md}"
quality_python="${QUALITY_PYTHON:-python3}"
"$quality_python" tools/code_quality/complexity.py report --json "$report_json" --markdown "$report_md"

# Compare with the baseline committed at the merge-base before consulting the
# PR baseline. This blocks coordinated source regressions and baseline rewrites.
"$quality_python" tools/code_quality/complexity.py ratchet --base-ref "$base_ref"
"$quality_python" tools/code_quality/complexity.py check
"$quality_python" tools/code_quality/complexity.py baseline-verify
"$quality_python" tools/code_quality/complexity.py validate-exceptions

if [[ -n "${GITHUB_STEP_SUMMARY:-}" && -f "$report_md" ]]; then
  {
    echo "## GAIA differential complexity gate"
    echo
    echo "- BASE_REF: \`$base_ref\`"
    echo "- MERGE_BASE: \`$merge_base\`"
    echo "- Report JSON: \`$report_json\`"
    echo
    sed -n '1,80p' "$report_md"
  } >> "$GITHUB_STEP_SUMMARY"
fi
