#!/bin/sh
# Run KiCad on the generated design: the installed one if present, otherwise the official
# container (docker pull kicad/kicad:10.0).   tools/kicad.sh schematic | board | route | quote
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
  # Places the parts, then adds the tracks saved in out/routes.json.
  py gen/pcb_build.py
  py gen/pcb_route.py
  run kicad-cli pcb drc --format json --severity-all --schematic-parity --exit-code-violations -o ../out/drc.json manent.kicad_pcb
  for layer in F.Cu In1.Cu In2.Cu In3.Cu In4.Cu B.Cu; do
    run kicad-cli pcb export svg --mode-single --page-size-mode 2 --exclude-drawing-sheet \
      --layers "$layer,Edge.Cuts,Dwgs.User" -o "../out/board-$layer.svg" manent.kicad_pcb
  done
  ;;
quote)
  # Fabrication files for a quote request, zipped in quote/manent-ring-quote.zip.
  rm -rf out/quote && mkdir -p out/quote/gerber out/quote/drill
  run kicad-cli pcb export gerbers --no-protel-ext --subtract-soldermask \
    --layers F.Cu,In1.Cu,In2.Cu,In3.Cu,In4.Cu,B.Cu,F.Mask,B.Mask,F.Paste,B.Paste,Edge.Cuts,Dwgs.User \
    -o ../out/quote/gerber/ manent.kicad_pcb
  run kicad-cli pcb export drill --format excellon --excellon-separate-th --generate-map --map-format pdf \
    -o ../out/quote/drill/ manent.kicad_pcb
  run kicad-cli pcb export pos --format csv --units mm --side both --exclude-dnp -o ../out/quote/positions.csv manent.kicad_pcb
  cp out/bom.csv out/quote/bom.csv
  cp ../quote/request.md out/quote/README.md
  cp kicad/manent.kicad_pcb kicad/manent.kicad_pro kicad/manent.kicad_dru out/quote/
  (cd out/quote && rm -f ../../../quote/manent-ring-quote.zip && zip -qr ../../../quote/manent-ring-quote.zip .)
  ;;
route)
  # Routes from scratch: several minutes. Needs the pad geometry of the placed board.
  py gen/pcb_build.py
  py gen/pcb_dump.py
  (cd .. && uv run python -u -m electrical.gen.router)
  ;;
esac
