# Open questions

## Decisions for the project owner

| Question | Why it matters | Current assumption |
| --- | --- | --- |
| Which ring sizes to offer | Below US 7 nothing fits; capacity grows with size | US 7 to 13 |
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
| nRF54L15 errata for P1.04-P1.07 at power-on | Nordic errata, revision in stock |

## To measure, no ring needed (development kit and breakouts)

1. Current while recording: Opus duty cycle, PDM, flash writes.
2. Whether the calibrated internal 32 kHz oscillator is good enough.
3. Light: current needed to be seen through resin.
4. Charging a 15 mAh cell at 8 mA through the power chip; fuel-gauge behaviour.

## To measure on a ring

1. Antenna efficiency and range, potted, on a finger.
2. Button feel through the cap, and sealing.
3. Microphone: handling noise, port sealing.
4. Heat while charging in a closed resin body.
5. Skin contact of the resin; water.

## Not designed yet

Board routing and layer stack (parts are placed, no track is drawn), the dock, the button cap, the antenna, firmware changes (pins, power chip
driver, light, gestures), compliance (radio, potted lithium cell).
