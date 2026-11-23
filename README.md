# Manent ring: hardware

Hardware design of the Manent ring: a ring with one button that records what you say
and hands it to your phone over Bluetooth LE. Firmware and radio protocol live in the
`mnemo-band` repository; the public description is the `manent-site` repository.

Nothing here has been built or measured. This is a design on paper, checked by scripts.

| What | Where |
| --- | --- |
| Design document: requirements, architecture, decisions | [docs/design.md](docs/design.md) |
| Does it fit? Envelope, islands, cell, ring sizes | [docs/space-budget.md](docs/space-budget.md) |
| How long does it last? | [docs/power-budget.md](docs/power-budget.md) |
| What is unknown, and what would settle it | [docs/open-questions.md](docs/open-questions.md) |
| Parts with sizes and how far each is verified | [parts/parts.yaml](parts/parts.yaml) |
| Circuit, as data | [electrical/gen/design.py](electrical/gen/design.py) |
| Schematic (KiCad 10), PDF, netlist, bill of materials | `electrical/kicad/`, `electrical/out/` |
| Board: placed and routed (connectivity proof, not a fabrication layout) | `electrical/kicad/manent.kicad_pcb`, `electrical/out/board-*.svg` |
| Fit model, drawings, STEP | `mechanical/`, `mechanical/out/` |

## Build

Needs `uv`, and either KiCad 10 or Docker (`docker pull kicad/kicad:10.0`).

```
make all        # schematic, board, checks, tests, fit report, drawings, budgets, STEP
make test       # tests only
make route      # route the board again from scratch (several minutes)
```

The schematic and the board are generated: edit `electrical/gen/design.py` and the fit
model, never the `.kicad_sch` or `.kicad_pcb` files.
Every pin carries a label with its net name instead of drawn wires. `make schematic` runs
KiCad's rule check and compares the netlist KiCad reads with the one in `design.py`.

## Licences

Following the proposal on the product site: hardware under CERN-OHL-S v2 (`LICENSE`),
documents under CC BY-SA 4.0 (`LICENSE-docs`). The licence of the scripts is not decided.
