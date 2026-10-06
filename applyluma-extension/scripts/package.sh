#!/usr/bin/env bash
# Builds the store upload zip for the ApplyLuma extension.
#
#   ./scripts/package.sh            -> dist/applyluma-extension-<version>.zip
#   ./scripts/package.sh --check    -> run the checks only, no zip
#
# The same zip is accepted by the Chrome Web Store and Firefox Add-ons (AMO).
# Only runtime files go in: README, store docs, scripts and dist stay out.
set -euo pipefail

cd "$(dirname "$0")/.."

RUNTIME_FILES=(manifest.json background.js content popup icons)

fail() { echo "package: $*" >&2; exit 1; }

# 1. Manifest parses and has the fields the stores require.
VERSION=$(node -e '
  const m = JSON.parse(require("fs").readFileSync("manifest.json", "utf8"));
  for (const k of ["manifest_version", "name", "version", "description", "icons"]) {
    if (!m[k]) { console.error(`manifest.json is missing "${k}"`); process.exit(1); }
  }
  if (m.manifest_version !== 3) { console.error("manifest_version must be 3"); process.exit(1); }
  if (!/^\d+(\.\d+){0,3}$/.test(m.version)) { console.error(`invalid version "${m.version}"`); process.exit(1); }
  if (m.description.length > 132) { console.error("description exceeds the 132-char store limit"); process.exit(1); }
  console.log(m.version);
') || fail "manifest.json failed validation"

# 2. Every file the manifest references exists.
node -e '
  const fs = require("fs");
  const m = JSON.parse(fs.readFileSync("manifest.json", "utf8"));
  const refs = [
    m.background.service_worker,
    ...(m.background.scripts || []),
    m.action.default_popup,
    ...Object.values(m.icons),
    ...Object.values(m.action.default_icon || {}),
    ...m.content_scripts.flatMap((c) => c.js || []),
  ];
  const missing = refs.filter((f) => !fs.existsSync(f));
  if (missing.length) { console.error("missing files: " + missing.join(", ")); process.exit(1); }
' || fail "manifest references missing files"

# 3. All scripts parse.
while IFS= read -r f; do
  node --check "$f" || fail "syntax error in $f"
done < <(find background.js content popup -name '*.js')

echo "package: checks passed (v$VERSION)"
[[ "${1:-}" == "--check" ]] && exit 0

command -v zip >/dev/null || fail "zip is not installed"
mkdir -p dist
OUT="dist/applyluma-extension-$VERSION.zip"
rm -f "$OUT"
zip -qr -X "$OUT" "${RUNTIME_FILES[@]}" -x '*.DS_Store'
echo "package: wrote $OUT ($(du -h "$OUT" | cut -f1))"
