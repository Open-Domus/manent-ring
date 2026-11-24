# Open questions

## Decisions for the project owner

| Question | Why it matters | Current assumption |
| --- | --- | --- |
| Is a six-layer any-layer build acceptable in cost? | The routing needs stacked microvias and vias in pads; a simpler build means more layers of thought, or a bigger board | six layers |
| More capacity than 15.5 mAh? | The 21.5 mAh cell misses the swelling allowance by 0.02 mm. It needs a wall 0.05 mm thicker, a cell made to order, or a supplier's figure for swelling below 8 % | 15.5 mAh, sizes US 8 to 13 (decided 2026-11-23) |
| Is "about 0.1 mA, wearer only" bright enough outdoors? | It sets a fifth of the recording budget if raised to 0.3 mA | 0.1 mA |
| Solid gold for the five contact slugs? | It is the only material found that solders, is safe on skin and survives grinding flush. It adds a few euros and a precious metal to the bill of materials | 18 kt yellow gold; 316L stainless as fallback |
| Licence for the scripts | Not covered by the hardware or document licences | undecided |

## To confirm from documents

| Item | Where to look |
| --- | --- |
| W25Q128JW WLCSP body size; availability of the special-order package | Winbond |
| Flash /WP and /HOLD termination in single-bit SPI | Winbond |
| nRF54L15 land pad diameter; nPM1304 ball pitch direction; S-82A1A pin order; 32 MHz crystal land pattern | manufacturers' package drawings |
| Cell: height of the tab joint, which the steel keeper overhangs by 1.0 mm | supplier's drawing |
| Cell: exact part codes, curvature per ring size, built-in protection, minimum order | quote from Grepow and one other supplier |
| N-MOSFETs for the light and the protection; 2.2 uH inductor under 0.8 mm tall | distributor search |
| nRF54L15 errata 100, 103 and 114 against the pins and clocks used here | Nordic errata, revision in stock |
| 1.8 V rail tolerance: the buck is +/-5 %, the microphone's absolute maximum is 1.98 V, the microcontroller resets below about 1.75 V, the flash needs 1.70 V | datasheets; choose the set point, and check the drop along 0.075 mm tracks |
| Protector variant against the cell's charge voltage (4.20 or 4.35 V) and the charger's setting | ABLIC selection table, cell datasheet |
| PDM clock: the microphone wants 768 kHz, the microcontroller's dividers may not give it exactly | Nordic PDM documentation |
| 5.5 V one-way protection diode in 0201 for the charging input. Candidate: Nexperia PESD5V5C1UBSF (0201, one-way); its working voltage and leakage were not read | Nexperia datasheet |
| nPM1304: that VBUS is never driven from the cell; charge-end current at an 8 mA setting | Nordic product specification |
| Cell: allowed charge rate (0.5 C assumed) and temperature window | supplier's datasheet |
| Cell: is the catalogue length measured along the arc or as a chord; inner radius as supplied | supplier's drawing |

## To measure, no ring needed (development kit and breakouts)

1. Current while recording: Opus duty cycle, PDM, flash writes.
2. Whether the calibrated internal 32 kHz oscillator is good enough.
3. Light: current needed to be seen through resin.
4. Charging a 15 mAh cell at 8 mA through the power chip; fuel-gauge behaviour.
5. Gold slug soldered to an ENIG pad: joint strength before and after potting; the same in 316L.
6. Slugs and resin ground flush, then a week in artificial sweat, docked wet a few times.
7. Dock, shoe and block as printed (`print-dock-*.stl`, `print-block-*.stl`): whether each bar finds
   its contact over the 17 degrees allowed and never a service contact; the pull of the magnet on a
   piece of steel in the keeper's place, against the 0.25 N estimated. Do this first: it costs an
   afternoon and says whether magnet and keeper earn their place.
8. Contact between a 0.4 mm wire and a flush slug at a fraction of a newton: resistance, and wear of
   both after a few hundred dockings.
9. Delay between a button press and the microcontroller knowing, through the power chip's interrupt.

## To measure on a ring

1. Antenna efficiency and range, potted, on a finger.
2. Button feel through the cap, and sealing.
3. Microphone: handling noise, port sealing.
4. Heat while charging in a closed resin body.
5. Skin contact of the resin; water.

## Not designed yet

A board layout fit for fabrication (the routing in the repository proves connectivity only: see
the Board section of design.md), the dock's electronics board, its springs and the service clip (the dock's body and shoe are modelled: charging.md), the button cap, the antenna and the clearing of the
ground plane under it, firmware changes (pins, power chip
driver, light, gestures), compliance (radio, potted lithium cell).
