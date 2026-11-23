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
| Rechargeable; two magnetic charging contacts on the inner face | product site (three pads here, see below) |
| Outer case in metal, titanium preferred | product site |
| Band 8.0 mm wide, wall 2.6 mm at the edges and 3.0 mm at the centre | decided 2026-11-23, from the space budget |
| Assembled by hand in small series; full bill of materials public | product site |

Four of these differ from what the site says today: it promises a vibration, a light that
"tells everyone", draws button and light as one piece, and speaks of seven millimetres.
The site needs correcting.

## Button

| Gesture | Meaning | Handled by |
| --- | --- | --- |
| Short press | Start recording, or stop it | firmware |
| Hold while recording (about 1 s) | Mark this moment | firmware |
| Press while in ship mode (96 ms) | Wake from storage | power chip |
| Hold 10 s | Power cycle: the way out of a hung firmware | power chip |

The `mnemo-band` gestures (short press marks, 2 s mutes) belong to an always-listening
band and do not carry over. A ring that records only on request has no separate mute.

## Light

A single red LED on the back of the finger, behind the resin, at about 0.1 mA. Its switch
is driven by the microphone's supply rail, not by firmware: if the microphone has power,
the light is on, and there is no code path that can record in the dark. A second switch
lets firmware blink it for errors and charging.

Without vibration the confirmation is visual only. With the hands busy and the eyes
elsewhere, the wearer has the click of the switch and nothing more. This is a known limit.

## Blocks

```
charge pads --TVS-- VBUS --> [ nPM1304 ] <--> cell (+ protection)
                              |  |  |
                 1.8 V buck --+  |  +-- load switch 2 --> flash supply
                              |  +----- load switch 1 --> microphone supply --> light
                              v
   button --+--> SHPHLD    [ nRF54L15 ] --PDM--> T5838 microphone
            +-|<|-> wake        |  |
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
| Flash | Winbond W25Q128JW, WLCSP-21 | height 0.46 or 0.30; body not published | 128 Mbit holds about 1 h 44 min not yet uploaded | pinout verified; special-order package |
| Microphone | TDK T5838 | 3.5 x 2.65 x 0.98 | Already planned by the firmware; 120 uA at a 768 kHz clock | verified |
| Button | Panasonic EVP-BB, 1.6 N | 2.6 x 1.6 x 0.53 | 0.11 mm travel, sealed to IP67 | datasheet from a distributor |
| Light | Rohm SML-P11VT | 1.0 x 0.6 x 0.2 | Specified at 1 mA | verified at 1 mA; dimmer is from curves |
| Cell protection | ABLIC S-82A1A | 1.4 x 1.4 | Trip current set by a resistor, so it can be low enough for a tiny cell | verified; fit only if the cell has none |
| Charging input | Infineon ESD230-B1-W0201 | 0.58 x 0.28 | Exposed pads need ESD protection | verified |
| Cell | Grepow curved LiPo | 1.6-1.7 thick | See the space budget | catalogue only |

The full list with part numbers is `electrical/out/bom.csv`.

### Microcontroller pins

| Signal | Pin | Rule it satisfies |
| --- | --- | --- |
| Microphone clock, data | P1.04, P1.05 | PDM lives on port 1; the clock is on a clock pin |
| Microphone threshold, wake | P1.06, P1.07 | port 1 can wake the chip |
| Microphone power request | P1.13 | to the power chip's GPIO1, which drives load switch 1 |
| Flash clock, out, in, select | P2.01, P2.02, P2.04, P2.05 | the dedicated fast-SPI pins |
| Power chip clock, data, interrupt | P0.03, P0.02, P0.01 | clock on a clock pin; port 0 can wake the chip |
| Button | P0.00 | port 0 can wake the chip |
| Light, firmware side | P0.04 | |
| Test serial port | P1.14, P1.15 | on the tail that is cut off |
| Optional 32.768 kHz crystal | P1.00, P1.01 | not fitted |

`electrical/gen/checks.py` enforces these rules on every build.

### Choices worth explaining

- **Button to two chips.** The button goes to the power chip's ship-mode input, which pulls
  it up towards the cell voltage. A diode keeps that voltage off the 1.8 V microcontroller
  pin while still letting a press pull the pin low. The switch is rated from 2 V up, so the
  higher pull-up also keeps it within its rating.
- **Three charging pads, ground-positive-ground.** The ring can sit in its dock either way
  round without reversing polarity, so no series diode is needed. Magnets go in the dock.
- **Two service pads on the inner face** (SWDIO, SWDCLK). Once potted, the ring can still
  be reprogrammed from outside. A longer tail with reset, serial port and supplies is used
  for the factory test and cut off before potting.
- **Flash behind a load switch.** It gives the flash a hard reset and removes its standby
  current. Firmware must release the SPI pins before switching it off.
- **No 32.768 kHz crystal at first.** The internal oscillator, calibrated, is within what
  Bluetooth LE needs; the footprint stays in case the receive-window cost is too high.

## Case and assembly

- Titanium on the outside and the two side walls only, 0.40 mm. The inner face is resin:
  a radio cannot work inside a closed metal tube. Titanium inside and out is not an option.
- The resin must be opaque around the two chip-scale packages, which are sensitive to
  light, and clear only in front of the LED.
- Openings in the titanium: one hole for the microphone (0.5-1.0 mm in the board under a
  0.375 mm port), one small hole or thinned window for the light, one for the button.
- Layout: six islands, parts on both faces. Flash sits behind the microcontroller, the small
  power parts behind the power chip, the cell protection behind the charging pads. This
  keeps the electronics to about 35 mm of arc and leaves the rest to the cell.
- Circuit: rigid islands for the fine-pitch chips joined by two-layer flex. The 0.3 mm
  pitch of the microcontroller package needs microvias under the chip; Nordic's own
  reference board is an eight-layer build. This is work for a specialist fabricator and
  an assembler with X-ray inspection. "Assembled by hand" can truthfully cover folding,
  joining the cell, potting and finishing.

Whether it all fits is in [space-budget.md](space-budget.md). In short: everything fits
in the 8.0 mm band, which is the one adopted. In the 7.4 mm envelope neither the cell nor
the microcontroller island has enough room; it stays in the model as a comparison.

## Board

`electrical/kicad/manent.kicad_pcb` is the circuit unrolled flat: a strip 5.6 mm wide and
about 34 mm long, X along the arc from the cell tabs, Y across the band. Top copper faces
the titanium, bottom copper faces the finger. A narrow tail with seven test pads leaves
the microcontroller island and is cut off after the factory test.

What is done:

- Every part of the schematic has a footprint and a place, the same place the fit model
  uses, so the board and the model cannot drift apart.
- Every pad carries its net. KiCad's check finds no difference between board and schematic
  and no rule violation in the placement.
- Footprints are in `electrical/kicad/manent.pretty`. The chip-scale packages, microphone,
  switch and protector are drawn from the manufacturers' land patterns; each footprint's
  description says what was verified and what was assumed.

What is not done: **no track is routed.** All 154 connections are still open. Routing the
0.3 mm pitch microcontroller needs microvias under the chip on a rigid island of at least
six layers, and the layer stack has to be agreed with the fabricator first: the board file
uses a plain four-layer stack as a stand-in. The rules set in the project file (0.075 mm
track and gap, 0.2 mm microvia) are an assumption about that fabricator, not a quote.

Courtyard checks are switched off: stock courtyards leave rework room this board does not
have. Spacing is enforced by the packer instead, 0.15 mm between land patterns and 0.3 mm
around the fine-pitch packages.

## Radio

Unknown until measured. Inside a metal shell on a finger, expect the antenna to lose 15 to
25 dB (an estimate). The design keeps a tuning network next to the antenna, puts the
antenna on the side away from the cell, and leaves the antenna type open. If the link is
poor at 2 Mbit/s the firmware can fall back to 1 Mbit/s.

## Prior art

| Product | What it shows |
| --- | --- |
| Pebble Index 01 | The same idea, a button and a microphone in a ring, solved with non-rechargeable cells and five minutes of storage. Charging and a curved cell are what they chose to avoid |
| Oura, Ultrahuman, Galaxy Ring | 7.0-8.1 mm wide, 2.5-2.9 mm thick, 15-22 mAh, resin towards the finger |
| Omi | The T5838 microphone and its wake-on-sound driver, used by `mnemo-band` |

These come from product pages and teardown summaries, not from our own measurements.
