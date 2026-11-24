# Open questions

## Decisions for the project owner

| Question | Why it matters | Current assumption |
| --- | --- | --- |
| Is a six-layer any-layer build acceptable in cost? | The routing needs stacked microvias and vias in pads; a simpler build means more layers of thought, or a bigger board | six layers |
| More capacity than 15.5 mAh? | The 21.5 mAh cell misses the swelling allowance by 0.02 mm. It needs a wall 0.05 mm thicker, a cell made to order, or a supplier's figure for swelling below 8 % | 15.5 mAh, sizes US 8 to 13 (decided 2026-11-23) |
| Is "about 0.1 mA, wearer only" bright enough outdoors? | It sets a fifth of the recording budget if raised to 0.3 mA | 0.1 mA |
| Licence for the scripts | Not covered by the hardware or document licences | undecided |

## To confirm from documents

| Item | Where to look |
| --- | --- |
| nPM1304: what to do with SW2, VOUT2, LED0-2, GPIO2-3 when unused; which capacitor on which net | Nordic's reference design files for configuration 2 |
| W25Q128JW WLCSP body size; availability of the special-order package | Winbond |
| Flash /WP and /HOLD termination in single-bit SPI | Winbond |
| nRF54L15 land pad diameter; nPM1304 ball pitch direction; S-82A1A pin order; 32 MHz crystal land pattern | manufacturers' package drawings |
| Cell: exact part codes, curvature per ring size, built-in protection, minimum order | quote from Grepow and one other supplier |
| N-MOSFETs for the light and the protection; 2.2 uH inductor under 0.8 mm tall | distributor search |
| nRF54L15 errata 100, 103 and 114 against the pins and clocks used here | Nordic errata, revision in stock |
| 1.8 V rail tolerance: the buck is +/-5 %, the microphone's absolute maximum is 1.98 V, the microcontroller resets below about 1.75 V, the flash needs 1.70 V | datasheets; choose the set point, and check the drop along 0.075 mm tracks |
| Protector variant against the cell's charge voltage (4.20 or 4.35 V) and the charger's setting | ABLIC selection table, cell datasheet |
| PDM clock: the microphone wants 768 kHz, the microcontroller's dividers may not give it exactly | Nordic PDM documentation |
| 5.5 V one-way protection diode in 0201 for the charging input | distributor search |
| Cell: is the catalogue length measured along the arc or as a chord; inner radius as supplied | supplier's drawing |

## To measure, no ring needed (development kit and breakouts)

1. Current while recording: Opus duty cycle, PDM, flash writes.
2. Whether the calibrated internal 32 kHz oscillator is good enough.
3. Light: current needed to be seen through resin.
4. Charging a 15 mAh cell at 8 mA through the power chip; fuel-gauge behaviour.
5. Delay between a button press and the microcontroller knowing, through the power chip's interrupt.

## To measure on a ring

1. Antenna efficiency and range, potted, on a finger.
2. Button feel through the cap, and sealing.
3. Microphone: handling noise, port sealing.
4. Heat while charging in a closed resin body.
5. Skin contact of the resin; water.

## Not designed yet

A board layout fit for fabrication (the routing in the repository proves connectivity only: see
the Board section of design.md), the dock, the button cap, the antenna and the clearing of the
ground plane under it, the contacts that bring the charging pads up to the inner surface, firmware changes (pins, power chip
driver, light, gestures), compliance (radio, potted lithium cell).
