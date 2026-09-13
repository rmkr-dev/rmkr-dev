#!/usr/bin/env bash
# Fail if the profile README contains personal/contact or career-resume patterns.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
README="${ROOT}/README.md"
if [[ ! -f "$README" ]]; then
  echo "README.md missing" >&2
  exit 1
fi

# Patterns we never want on the public profile homepage.
PATTERNS=(
  'linkedin\.com'
  'mailto:'
  '[0-9]{10}'
  '@gmail\.com'
  'Principal (Software|Engineer)'
  'Lead AI'
  'years of experience'
  'Career (Highlights|Timeline)'
  'PHI/?PII'
  'Technology Leadership'
  'Contact & Links'
)

failed=0
for pat in "${PATTERNS[@]}"; do
  if grep -Eiq -- "$pat" "$README"; then
    echo "Hygiene fail: matched /$pat/" >&2
    failed=1
  fi
done

if [[ "$failed" -ne 0 ]]; then
  exit 1
fi
echo "README hygiene OK"
