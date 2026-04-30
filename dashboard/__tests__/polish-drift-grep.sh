#!/usr/bin/env bash
# Polish-drift gates (RMD-06) as a portable shell script — runs the same
# checks as polish-drift.test.ts. Used by Wave 3 verify command.
#
# Exemptions (mirrored in polish-drift.test.ts):
#   - components/ui/        vendored shadcn primitives (UI-SPEC exempt)
#   - components/compare/   in-spec drift palette (changed = amber)
set -euo pipefail
cd "$(dirname "$0")/.."

fail=0

# count_hits PATTERN — emits the count of matches in app/ and components/,
# excluding components/ui (vendored shadcn) and components/compare/ (drift-
# palette in-spec use). app/(dashboard)/compare and app/(dashboard)/scans/
# compare are NOT excluded — those are page surfaces and must obey gates.
count_hits() {
  local pattern="$1"
  # First grep app/ (no exclusions on compare folders — pages must comply).
  local app_hits
  app_hits=$(grep -rEn --include='*.ts' --include='*.tsx' --include='*.js' --include='*.jsx' \
    --exclude-dir=ui \
    "$pattern" app 2>/dev/null | wc -l | tr -d ' ')
  # Then grep components/ excluding ui/ AND compare/ (drift palette).
  local comp_hits
  comp_hits=$(grep -rEn --include='*.ts' --include='*.tsx' --include='*.js' --include='*.jsx' \
    --exclude-dir=ui \
    --exclude-dir=compare \
    "$pattern" components 2>/dev/null | wc -l | tr -d ' ')
  echo $((app_hits + comp_hits))
}

count_in_file() {
  local pattern="$1" file="$2"
  grep -nE "$pattern" "$file" 2>/dev/null | wc -l | tr -d ' '
}

check() {
  local desc="$1" expected="$2" got="$3"
  if [[ "$got" != "$expected" ]]; then
    echo "FAIL: $desc — expected '$expected', got '$got'"
    fail=1
  else
    echo "ok   $desc"
  fi
}

# Typography gates
check "no text-xl"            "0" "$(count_hits '\btext-xl\b')"
check "no text-lg"            "0" "$(count_hits '\btext-lg\b')"

# Color gates
check "no bg-amber-500/600"   "0" "$(count_hits '\bbg-amber-(500|600)\b')"
check "no ring-amber-*"       "0" "$(count_hits '\bring-amber-')"
check "no bg-amber-50"         "0" "$(count_hits '\bbg-amber-50\b')"
check "no text-amber-600"      "0" "$(count_hits '\btext-amber-600\b')"

# Home gutters present (each appears exactly once on the wrapper line)
HOME='app/(dashboard)/page.tsx'
check "home px-8 present"      "1" "$(count_in_file '\bpx-8\b'  "$HOME")"
check "home py-12 present"     "1" "$(count_in_file '\bpy-12\b' "$HOME")"
check "home gap-12 present"    "1" "$(count_in_file '\bgap-12\b' "$HOME")"

# Overview h1 removed
check "no Overview h1"         "0" "$(count_in_file '<h1[^>]*>\s*Overview\s*<' "$HOME")"

exit $fail
