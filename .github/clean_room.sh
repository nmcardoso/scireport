#!/usr/bin/env bash
# Clean-room check: install scireport the way a consuming project does (from the public git URL, into
# a fresh virtual environment, outside the repository) and render the kitchen-sink example to every
# output that needs no TeX Live. Usage: .github/clean_room.sh REF (a tag, branch or commit).
# SCIREPORT_REPO_URL points at another remote (a file:// URL tests an unpushed commit locally);
# CLEAN_ROOM_PYTHON picks the interpreter (default 3.12).
set -euo pipefail

ref=${1:?usage: clean_room.sh REF}
repo=${SCIREPORT_REPO_URL:-https://github.com/nmcardoso/scireport}
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
cd "$work"

uv venv --quiet --python "${CLEAN_ROOM_PYTHON:-3.12}"
uv pip install --quiet "scireport[pdf,astro] @ git+${repo}@${ref}"
scireport=.venv/bin/scireport
python=.venv/bin/python

"$scireport" --version
"$python" - <<'PY'
from scireport.demo import kitchen_sink_report

kitchen_sink_report().write('kitchen-sink.scireport.zip')
PY
"$scireport" inspect kitchen-sink.scireport.zip > /dev/null
for layout in default modern; do
  "$scireport" render kitchen-sink.scireport.zip -o "out-$layout" -l "$layout" \
    -f md -f html -f tex -f pdf
  for file in md/report.md html/report.html tex/report.tex pdf/report.pdf render-manifest.json; do
    test -s "out-$layout/$file" || { echo "missing out-$layout/$file" >&2; exit 1; }
  done
done
"$scireport" preprocessors | grep -q 'astro.sky_density'
"$python" -c "import astropy, astropy_healpix"
echo "clean room ok: scireport $("$scireport" --version) from ${repo}@${ref}"
