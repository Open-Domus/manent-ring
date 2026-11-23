#!/bin/sh
# Run kicad-cli on the generated schematic: the installed one if present, otherwise the
# official container (docker pull kicad/kicad:10.0).
set -e
cd "$(dirname "$0")/../electrical"
mkdir -p out
if command -v kicad-cli >/dev/null 2>&1; then
  run() { (cd kicad && "$@"); }
else
  run() { docker run --rm -u "$(id -u):$(id -g)" -e HOME=/tmp -v "$PWD":/w -w /w/kicad kicad/kicad:10.0 "$@"; }
fi
run kicad-cli sch erc --format json --severity-all --exit-code-violations -o ../out/erc.json manent.kicad_sch
run kicad-cli sch export netlist --format kicadxml -o ../out/netlist.xml manent.kicad_sch
run kicad-cli sch export pdf -o ../out/schematic.pdf manent.kicad_sch
