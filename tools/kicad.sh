#!/bin/sh
# Run KiCad on the generated design: the installed one if present, otherwise the official
# container (docker pull kicad/kicad:10.0).   tools/kicad.sh schematic | board
set -e
cd "$(dirname "$0")/../electrical"
mkdir -p out
if command -v kicad-cli >/dev/null 2>&1; then
  run() { (cd kicad && "$@"); }
  py() { python3 "$@"; }
else
  run() { docker run --rm -u "$(id -u):$(id -g)" -e HOME=/tmp -v "$PWD":/w -w /w/kicad kicad/kicad:10.0 "$@"; }
  py() { docker run --rm -u "$(id -u):$(id -g)" -e HOME=/tmp -v "$PWD":/w -w /w kicad/kicad:10.0 python3 "$@"; }
fi
case "${1:-schematic}" in
schematic)
  run kicad-cli sch erc --format json --severity-all --exit-code-violations -o ../out/erc.json manent.kicad_sch
  run kicad-cli sch export netlist --format kicadxml -o ../out/netlist.xml manent.kicad_sch
  run kicad-cli sch export pdf -o ../out/schematic.pdf manent.kicad_sch
  ;;
board)
  py gen/pcb_build.py
  run kicad-cli pcb drc --format json --severity-all --schematic-parity -o ../out/drc.json manent.kicad_pcb
  run kicad-cli pcb export svg --mode-single --page-size-mode 2 --exclude-drawing-sheet \
    --layers F.Cu,Edge.Cuts,Dwgs.User,Cmts.User -o ../out/board-top.svg manent.kicad_pcb
  run kicad-cli pcb export svg --mode-single --page-size-mode 2 --exclude-drawing-sheet --mirror \
    --layers B.Cu,Edge.Cuts,Dwgs.User -o ../out/board-bottom.svg manent.kicad_pcb
  ;;
esac
