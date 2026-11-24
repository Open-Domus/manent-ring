# Manent ring: design

Status: design on paper. No board, no case, no measurement. Numbers are either from
manufacturers' documents or estimates, and each table says which.

## What the ring does

Press the button, speak, and the words reach your phone as audio, to be turned into text
there. The ring keeps a recording only until the phone confirms it has it.

## Requirements

| Requirement | Source |
| --- | --- |
| Records only when the wearer starts it | product site |
| One button; no screen | product site |
| A light tells **the wearer** that it is recording. Nobody else needs to see it | decided 2026-11-23 |
| The light is separate from the button, on the back of the finger; the button is on the thumb side | decided 2026-11-23 |
| No vibration motor | decided 2026-11-23 |
| Digital MEMS microphone, 16 kHz mono, Opus at about 16 kbit/s encoded on the ring | product site, `mnemo-band` |
| Bluetooth LE; store and forward; no server of ours | product site, `mnemo-band` |
| Firmware the owner can rebuild and load | product site |
| Rechargeable; three magnetic charging contacts on the inner face | product site; method confirmed 2026-11-24, see [charging.md](charging.md) |
| Outer case in metal, titanium preferred | product site |
| Band 8.0 mm wide, wall 2.6 mm at the edges and 3.0 mm at the centre | decided 2026-11-23, from the space budget |
| Ring sizes US 8 to 13 | decided 2026-11-23: below 8 the cell does not fit the arc left by the electronics |
| Assembled by hand in small series; full bill of materials public | product site |

The product site was brought in line with these on 2026-11-23.

## Button

| Gesture | Meaning | Handled by |
| --- | --- | --- |
| Short press | Start recording, or stop it | firmware, told by the power chip |
| Hold while recording (about 1 s) | Mark this moment | firmware, told by the power chip |
| Press while in ship mode (96 ms) | Wake from storage | power chip |
| Hold 10 s | Power cycle: the way out of a hung firmware | power chip |

The `mnemo-band` gestures (short press marks, 2 s mutes) belong to an always-listening
band and do not carry over. A ring that records only on request has no separate mute.

## Light

A single red LED on the back of the finger, behind the resin, at about 0.1 mA. Its switch
is driven by the microphone's supply rail, not by a firmware output of its own: while the
microphone has power the light is on. A resistor discharges that rail when it is switched
off, so the light goes out with the microphone. A second switch lets firmware blink the
light for errors and charging.

What this does and does not guarantee: firmware cannot power the microphone with the light
off. Firmware does decide when the microphone is powered, and the light cannot tell
recording from a microphone that is merely on. It is a hardware tie between two things,
not a proof of what the firmware does with the sound.

Without vibration the confirmation is visual only. With the hands busy and the eyes
elsewhere, the wearer has the click of the switch and nothing more. This is a known limit.

## Blocks

```
charge pads --TVS-- VBUS --> [ nPM1304 ] <--> cell (+ protection)
                              |  |  |
                 1.8 V buck --+  |  +-- load switch 2 --> flash supply
                              |  +----- load switch 1 --> microphone supply --> light
                              v
   button -----> SHPHLD    [ nRF54L15 ] --PDM--> T5838 microphone
   (read over I2C)              |  |
                           SPI --+  +-- matching -- tuning -- antenna
                            v
                       128 Mbit flash
```

One logic rail at 1.8 V: the microphone accepts nothing higher (1.98 V absolute maximum),
and it spares level shifters.

## Parts

| Block | Part | Size (mm) | Why | Confidence |
| --- | --- | --- | --- | --- |
| Microcontroller | Nordic nRF54L15, CSP47 | 2.45 x 2.25 x 0.42 | The firmware targets it; its PDM clock suits the microphone | pinout and reference circuit verified |
| Power | Nordic nPM1304, CSP35 | 3.08 x 2.38 x 0.46 | Charges from 4 mA in 0.5 mA steps, which a 15 mAh cell needs; 1.8 V buck; ship mode at 370 nA | pinout verified; some terminations not |
| Flash | Winbond W25Q128JW, WLCSP-21 | about 3.4 x 3.0 x 0.46 (body estimated; not published) | 128 Mbit holds about 2 h 20 min not yet uploaded | pinout verified; special-order package |
| Microphone | TDK T5838 | 3.5 x 2.65 x 0.98 | Already planned by the firmware; 120 uA at a 768 kHz clock | verified |
| Button | Panasonic EVP-BB, 1.6 N | 2.6 x 1.6 x 0.53 | 0.11 mm travel, sealed to IP67 | datasheet from a distributor |
| Light | Rohm SML-P11VT | 1.0 x 0.6 x 0.2 | Specified at 1 mA | verified at 1 mA; dimmer is from curves |
| Cell protection | ABLIC S-82A1A | 1.4 x 1.4 | Trip current set by a resistor, so it can be low enough for a tiny cell | verified; fit only if the cell has none |
| Charging input | 5.5 V one-way protection diode, 0201 | 0.6 x 0.3 | Exposed pads need protection from static and from a reversed supply | part not chosen |
| Cell | Grepow GRP160626, curved LiPo, 15.5 mAh | 26 x 6.0 x 1.6 | The only catalogue cell that fits with room to swell | catalogue only: curvature and how the length is measured are not confirmed |

The full list with part numbers is `electrical/out/bom.csv`.

### Microcontroller pins

| Signal | Pin | Rule it satisfies |
| --- | --- | --- |
| Microphone clock, data | P1.04, P1.05 | PDM lives on port 1; the clock is on a clock pin |
| Microphone threshold, wake | P1.06, P1.07 | port 1 can wake the chip |
| Microphone power request | P1.13 | to the power chip's GPIO1, which drives load switch 1 |
| Flash clock, out, in, select | P2.01, P2.02, P2.04, P2.05 | the dedicated fast-SPI pins |
| Power chip clock, data, interrupt | P0.03, P0.02, P0.01 | clock on a clock pin; port 0 can wake the chip. The button arrives through this interrupt |
| Light, firmware side | P0.04 | |
| Test serial port | P1.14, P1.15 | on the tail that is cut off |
| Optional 32.768 kHz crystal | P1.00, P1.01 | not fitted |

`electrical/gen/checks.py` enforces these rules on every build.

### Choices worth explaining

- **Button to the power chip only.** The button goes to the power chip's ship-mode input,
  which pulls it up towards the cell voltage; the microcontroller learns of a press from the
  power chip's interrupt and reads it over I2C. No 1.8 V pin ever sees the cell voltage, and
  the switch, rated from 2 V up, stays within its rating. The cost is a few milliseconds of
  delay on each press, to be measured.
- **Thermistor on the cell.** A 10 k thermistor next to the cell tabs lets the charger stop
  outside the cell's temperature range.
- **Three charging pads, ground-positive-ground.** The ring can sit in its dock either way
  round without reversing polarity, so no series diode is needed. Magnets go in the dock, a
  steel plate for them to hold goes in the ring. Why contacts and not wireless charging, the
  slugs, the dock and the charger settings are in [charging.md](charging.md).
- **Two service pads on the inner face** (SWDIO, SWDCLK). Once potted, the ring can still
  be reprogrammed from outside; 100 ohm in series protects the pins. A longer tail with
  reset, serial port and supplies is used for the factory test and cut off before potting.
  Only dead-end branches run onto the tail, so cutting it opens no connection.
- **Flash behind a load switch.** It gives the flash a hard reset and removes its standby
  current. Firmware must release the SPI pins before switching it off.
- **No 32.768 kHz crystal at first.** The internal oscillator, calibrated, is within what
  Bluetooth LE needs; the footprint stays in case the receive-window cost is too high.

## Case and assembly

- Titanium on the outside, the two side walls and round the four corners, 0.40 mm. The inner
  face between the corners is resin: a radio cannot work inside a closed metal tube.
  Titanium inside and out is not an option.
- The resin must be opaque around the chip-scale packages, which are sensitive to light,
  and clear only in front of the LED.
- Openings in the titanium: one hole for the microphone (a 0.6 mm hole in the board under
  the port), one small hole or thinned window for the light, one for the button.
- The charging and service pads are on the board, 0.45 to 0.51 mm below the inner surface.
  A slug soldered to each one is ground flush with the resin after potting; a steel plate
  above the same island gives the dock's magnets a hold. Sizes, material, the checks and
  the dock are in [charging.md](charging.md).
- Layout: seven islands, parts on both faces, in this order from the cell tabs: charging
  contacts and cell protection, button, power, microcontroller, microphone and light,
  flash, antenna. The electronics take about 38 mm of arc and leave the rest to the cell.
- Circuit: the seven rigid islands and the cell-tab area are joined by seven bends of
  two-layer flex. The 0.3 mm pitch of the microcontroller package needs microvias under the
  chip; Nordic's own reference board is an eight-layer build. This is work for a specialist
  fabricator and an assembler with X-ray inspection. "Assembled by hand" can truthfully
  cover folding, joining the cell, potting and finishing.

Whether it all fits is in [space-budget.md](space-budget.md). In short: in the 8.0 mm
band, the one adopted, everything fits with the 15.5 mAh cell, on sizes US 8 to 13. The
tightest island keeps 0.12 mm beyond the rule, and still fits if the board turns out 0.60 mm
thick instead of 0.45. The thicker 1.7 mm cells (up to 21.5 mAh) miss the swelling allowance
by 0.02 mm. In the 7.4 mm envelope the cell does not fit; it stays in the model as a
comparison.

## Board

`electrical/kicad/manent.kicad_pcb` is the circuit unrolled flat: a strip 5.6 mm wide and
about 40 mm long, X along the arc from the cell tabs, Y across the band. Top copper faces
the titanium, bottom copper faces the finger. A tail 3.4 mm wide with seven test pads
leaves the microcontroller island and is cut off after the factory test.

### Construction assumed

| Item | Value | Where it comes from |
| --- | --- | --- |
| Islands | rigid, six copper layers, about 0.45 mm | estimate; the fabricator's stackup replaces it |
| Bends | the two middle layers only (3 and 4), as a two-layer flex | rigid-flex practice |
| Layer 3 | ground plane from one end of the strip to the other | design choice |
| Layer 4 | the signals that cross from island to island | design choice |
| Vias | laser, 0.1 mm hole in a 0.2 mm pad, allowed inside pads, stacked across any span | [fabricators.md](fabricators.md) |
| Track and gap | 0.075 mm | assumption, right at the published limit of the candidate fabricators |
| Vias in the bends | none | [fabricators.md](fabricators.md) |

### What is done

- Every part has a footprint and a place, the same place the fit model uses.
- **Every connection is routed**: 244 tracks, 509 mm of copper in all, and 260 vias, of which
  146 join two neighbouring layers, 113 are stacks across three to five and one goes through
  all six. `tools/board_facts.py` prints these numbers.
- KiCad's check on the routed board finds no rule violation, no open connection and no
  difference from the schematic. `make board` repeats that check; `make route` routes again
  from scratch.
- The grid packages fan out ring by ring: the outer balls leave on the surface (ground balls
  may drop straight to the plane), each ring further in drops one layer deeper, so no ball
  is walled in. A via that touches a pad of these packages sits on its centre.
- No via is closer than 0.3 mm to the line where an island ends and the flex begins.
- Only dead-end branches run onto the test tail: cutting it opens no other connection.
- There is no copper under the body of the switch.
- The tests in `tests/test_electrical.py` check each of these claims on the routed board.

### What this routing is, and is not

It was drawn by a small maze router written for this board (`electrical/gen/router.py`), which
only knows the clearance rules. The router does not always finish: of 22 attempts with different
net orders, one connected everything and the others left 2 to 18 connections open. That is how
little room there is. It shows that the circuit can be connected in six layers with
two layers across the bends. It is **not a layout to send to a fabricator**:

- All tracks are 0.075 mm wide, the cell and supply tracks included.
- Nothing is impedance controlled: the antenna feed and the matching network need it.
- Parts are packed for space, not by function. Decoupling capacitors are on the right
  island but not necessarily next to the pin they serve, and the loop of the 1.8 V
  converter was not kept small.
- The antenna feed runs from the microcontroller island across three bends to the antenna.
- The ground plane runs under the antenna.
- The ground plane on a flex layer is solid; a flex that bends usually wants it hatched.
- Stacked microvias across up to six layers, and vias inside the pads of the small passives,
  need an any-layer build with filled and capped vias: the most expensive kind.
- A second reviewer, human, has not looked at it.

Footprints are in `electrical/kicad/manent.pretty`. The chip-scale packages, microphone,
switch and protector are drawn from the manufacturers' land patterns; each footprint's
description says what was verified and what was assumed.

Courtyard checks are switched off: stock courtyards leave rework room this board does not
have. Spacing is enforced by the packer instead, 0.15 mm between land patterns and 0.3 to
0.45 mm around the fine-pitch packages.

## Radio

Unknown until measured. Inside a metal shell on a finger, expect the antenna to lose 15 to
25 dB (an estimate). The design keeps a tuning network next to the antenna and leaves the
antenna type open. The antenna island is the last one, which puts it next to the far end of
the cell: the worst neighbour it could have, and a reason to expect the low end of that
range. The ground plane is not yet cleared from under the antenna. If the link is
poor at 2 Mbit/s the firmware can fall back to 1 Mbit/s.

## Prior art

| Product | What it shows |
| --- | --- |
| Pebble Index 01 | The same idea, a button and a microphone in a ring, solved with non-rechargeable cells and five minutes of storage. Charging and a curved cell are what they chose to avoid |
| Amazon Echo Loop | A ring with a microphone charged through three contacts; the charger is trivial, the problems are wear and mechanics |
| Oura, Ultrahuman, Galaxy Ring | 7.0-8.1 mm wide, 2.5-2.9 mm thick, 15-22 mAh, resin towards the finger |
| Omi | The T5838 microphone and its wake-on-sound driver, used by `mnemo-band` |

These come from product pages and teardown summaries, not from our own measurements.
