# Request for quotation: Manent ring circuit

A small rigid-flex circuit for a wearable ring, with assembly. We are asking for a price and
for your design rules, so that we can adapt the layout to your process before ordering.

The files show the construction and the density we need. **The layout is representative, not
final:** it will be revised to your stackup and rules. Please quote on what is drawn, and tell
us what you would change.

## The board

| Item | Value |
| --- | --- |
| Outline | strip 39.9 x 5.6 mm, plus a rigid test tail 3.4 x 9.6 mm that is cut off after test |
| Type | rigid-flex, flat, bent once into a ring of about 9 mm inner radius at installation |
| Rigid areas | eight along the strip (seven islands with parts and the area of the cell tabs), plus the tail; see the lines on the Dwgs.User layer |
| Copper layers | 6 on the rigid islands |
| Flex | layers 3 and 4 continue through the seven bends (1.0 to 1.4 mm long) as a two-layer flex; layer 3 is a ground plane |
| Island thickness | as thin as your six-layer stackup allows; our model assumes 0.45 mm |
| Track and gap | 0.075 mm on all layers |
| Vias | laser, 0.10 mm hole, 0.20 mm pad; 260 in all |
| Via structure | 146 between adjacent layers, 113 stacked across three to five layers, 1 through all six (any-layer) |
| Via in pad | yes, on three WLCSP parts and on 0201 pads: copper filled and capped |
| Vias in the flex | none, and none within 0.3 mm of a rigid-to-flex line |
| Smallest pitch | 0.30 mm (nRF54L15, WLCSP-47); also 0.42 x 0.44 mm (WLCSP-35) and 0.50 mm (WLCSP-21) |
| Hole to hole | 0.20 mm |
| Copper to edge | 0.15 mm |
| One non-plated hole | 0.60 mm, the sound port of a microphone |
| Finish | ENIG; ENEPIG if you recommend it for the exposed charging pads |
| Solder mask | both faces; no silkscreen |
| Parts | 56 to place, on both faces; smallest passive 0201. The cell is soldered to its tabs by us |

## Quantities

Please quote 20, 100 and 500 pieces, for:

1. bare boards;
2. boards assembled, parts supplied by you where you stock them (bill of materials in `bom.csv`,
   positions in `positions.csv`), with X-ray inspection of the WLCSP joints on both faces.

## Questions

1. What is your minimum laser microvia pad for a 0.10 mm hole? We need 0.20 mm.
2. Can you stack microvias across all six layers inside a rigid-flex? If not: how many levels
   stacked, or staggered only?
3. Do you offer copper-filled, capped via in pad on WLCSP and 0201 pads?
4. What six-layer rigid-flex stackup do you propose with layers 3 and 4 as the flex, and what
   is the finished thickness of the rigid areas?
5. Is 0.075 mm track and gap acceptable on every layer, including the flex? If not, your minimum.
6. Do you prefer a hatched ground plane on the flex layer, and with what pattern?
7. Lead time for 20 pieces, bare and assembled.
8. Tooling and other one-time charges, listed separately.

## Files in this package

| File | What |
| --- | --- |
| `manent.kicad_pcb` | the board, KiCad 10. Its stackup thickness field is a placeholder: use the table above |
| `gerber/` | copper 1 to 6, solder mask, paste, outline; `Dwgs_User` marks islands and bends |
| `drill/` | Excellon files, one per layer pair, with drill maps |
| `positions.csv`, `bom.csv` | placement and parts |

Contact: (to be filled in before sending)
