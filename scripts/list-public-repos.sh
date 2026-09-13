#!/usr/bin/env bash
# List public repositories for rmkr-dev (or $GITHUB_OWNER).
set -euo pipefail
OWNER="${GITHUB_OWNER:-rmkr-dev}"
gh repo list "$OWNER" --limit 200 --json name,description,url,primaryLanguage,updatedAt,isPrivate \
  --jq '[.[] | select(.isPrivate == false) | {name, description, url, language: (.primaryLanguage.name // null), updatedAt}]'
