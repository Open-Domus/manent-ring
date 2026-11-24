# Charging

Status: decided on paper on 2026-11-24. Nothing built or measured. The fit model checks the
geometry (`make fit`); the rest is argument and estimate, and each table says which.

## Decision

The ring charges through **three contacts on its inner face**, from a dock that holds no
electronics beyond a USB socket and a fuse. Wireless charging was weighed and set aside for
this revision. It can be added later without touching the charger: see the last section.

## The three ways compared

| | Contacts (chosen) | Wireless at 13.56 MHz (NFC charging) | Wireless at 6.78 MHz (the Oura way) |
| --- | --- | --- | --- |
| Added to the ring | Three metal slugs, one steel plate. No electronic part | Receiver chip 2.28 x 2.56 mm (Rohm ML7670), its matching parts, a coil on the inner face | Coil, matching capacitor, rectifier, clamp, smoothing capacitors |
| Does it fit | Yes, checked by the model on every size | The chip would. The coil has nowhere to go: every part of the inner face has the cell or a ground plane 0.35 mm behind it, and titanium on both sides | Same coil problem |
| Charger in the ring | The nPM1304 already there | The same nPM1304: the receiver only supplies its 5 V | The same |
| Dock | Socket, fuse, three spring pins, two magnets | Transmitter chip (6 x 6 mm), tuned antenna inside a post, a radio product to certify | Oscillator and tuned coil, also a radio product |
| Heat in the ring | 10 to 20 mW (power-budget.md) | The same, plus the receiver's losses: the pair is rated 45 % at best | Unknown |
| What must be tuned | Nothing | Two antennas against each other, with titanium and a cell beside one of them, for six ring sizes | Same |
| Weak point | Metal on the skin: corrosion, sealing, wear, alignment | Space and tuning; nothing touches the skin | Same |
| Who uses it | Amazon Echo Loop (three contacts) | Soxai Ring 2 | Oura, by one teardown. The Galaxy Ring is inductive too, coil on the cell; frequency not found |

Sources: Rohm's ML7670 datasheet (package, 250 mW, 5 V output for an external charging
chip) and press release (45 %, Soxai); iFixit on the Galaxy Ring; the Memfault "Smart ring
development" articles on Oura, the Echo Loop and what makes contacts hard. Links:
[ML7670](https://fscdn.rohm.com/lapis/en/products/databook/datasheet/ic/wpt/FEDL7670.pdf),
[Rohm chipset](https://www.eenewseurope.com/en/rohm-targets-smart-rings-with-ultra-compact-nfc-wireless-power-chipset/),
[iFixit](https://www.ifixit.com/News/98423/samsungs-galaxy-ring-revealed),
[Memfault 1](https://interrupt.memfault.com/blog/smart-ring-development-part-1),
[Memfault 2](https://interrupt.memfault.com/blog/smart-ring-development-part-2). The coil
judgement is ours, from the fit model, not from a trial.

Why contacts win here, in order of weight:

1. **Room.** The reference ring has 1.1 mm of arc left over and 0.12 mm of margin on its
   tightest island. A coil with its ferrite on top of the cell needs about 0.2 mm of wall
   that the cell's swelling allowance has already taken.
2. **The current is tiny.** A 15.5 mAh cell charges at 8 mA. What makes contacts hard in a
   watch (hundreds of milliamps through a small sprung point) does not apply: an ohm of
   contact resistance costs 8 mV.
3. **Nothing new to get wrong.** The circuit and the routed board stay exactly as they are.
   A first prototype can be charged with two wires.
4. **The dock stays something anyone can make.** No chip, no firmware, no radio approval.

What is given up: a ring with no metal on the inside, and a dock one drops the ring onto
without looking.

## Contacts in the ring

- **Layout.** Ground, positive, ground in one line across the band, 1.9 mm apart, on the
  contacts island, 21 to 25 degrees from the button towards the palm, depending on the size. The ring can go on the dock
  facing either way. Two smaller service contacts (SWDIO, SWDCLK) sit 1.55 mm further along.
- **Slugs.** Each pad is 0.45 to 0.51 mm below the inner surface. A round slug is soldered on
  it before potting: 1.4 mm across on the 1.5 mm charging pads, 0.6 mm on the 0.8 mm service
  pads, cut 0.7 mm long. After potting the inner face is ground and polished, slugs and
  resin together. They end flush, with nothing for dirt to collect in, and the resin seals
  round them. The model checks height, 0.5 mm of resin to the titanium, and 0.5 mm between
  neighbours, on every size. The charging slugs are as wide as the pads allow, because their
  width is the dock's tolerance.
- **Material.** Grinding removes any plating, so the slug must be right all the way through:
  solderable, harmless on skin, and not corroded by sweat. Proposed: **solid 18 kt yellow
  gold wire**, a jeweller's stock item. Five slugs are about 0.04 g in all, a few euros
  (estimate). No nickel anywhere at the surface. To test: the solder joint (gold dissolves
  into solder and can make it brittle; here it carries no load once potted). Fallback: 316L
  stainless, which needs a plated foot to solder.
- **No voltage on the skin.** The positive contact is an input. Off the dock it carries
  nothing, so sweat between the contacts has nothing to drive corrosion with. To confirm:
  that the power chip never feeds its input backwards, and that the 5.5 V protection diode
  leaks nothing that matters.
- **Steel keeper.** A plate of soft magnetic steel, 4.2 x 4.6 x 0.3 mm, 0.05 g, sits in the
  resin above the protection parts, 0.1 mm clear of them and 0.33 mm under the titanium. It
  is centred on the row of contacts, which puts 1.0 mm of it past the end of the island, over
  the bend towards the cell tabs: the height of the tab joint there is not known yet. It
  gives the dock's magnets something to hold: titanium is not magnetic, and without it "magnetic
  charging" has nothing to pull on. Steel, not a magnet, so it works either way round and
  survives potting heat.

## Dock

Modelled in `mechanical/manent_mech/dock.py`; `make cad` writes one printable body per ring
size (`mechanical/out/print-dock-US*.stl`), and a test checks each of them.

- A **post** the ring slides onto, 0.5 mm smaller than the bore, so one per size: 17.6 mm for
  US 8 to 21.7 mm for US 13. The ring rests on the base, which puts the three pins on the
  middle of the band whichever way up it goes on.
- **Three spring pins** in a row up the post, 1.0 mm body in a 1.05 mm hole, tip 0.4 mm so
  that none can bridge two contacts. They stand 0.8 mm out and push the ring against the far
  side of the post: the contact force comes from the fit, not from the magnets. The pin part
  is not chosen.
- **Two magnets**, one on each side of the pins, 1.9 mm away, behind 0.4 mm of plastic; they
  go in from the hollow middle of the post. Each pocket takes two 2 x 3 mm discs or one block.
- **Two grooves** on the base show where the button stops, one for each way round.
- **Electrics**: USB-C socket with 5.1 k on each CC pin, a resettable fuse of the 50 mA class,
  then the pins. The fuse is there because a ring put on askew can join the positive pin to
  ground through its own titanium edge. A pocket under the base takes the socket's board.
- The ring's own light shows that it is charging. The dock needs none.
- A **service clip** with five pins, for loading firmware into a closed ring, is the same
  post with two more pins and no magnet on their side. Not modelled.

### What the numbers say about finding the contacts

The ring may be turned 3 degrees either way from true before a pin leaves its contact: half
a millimetre at the bore, 0.6 mm at the button. The grooves alone ask for a steady hand.

The magnets are meant to do it instead, and the model is not kind to them: they are 2.0 mm
from the keeper, and only 60 % of each is under it, because the pins take the middle. Expect
a weak pull, a detent at best. Two things would strengthen it and both have room: a keeper
0.5 mm thick instead of 0.3, and taller magnets.

This is the first thing to try, and it needs no electronics: `print-block-US*.stl` now has a
dimple on each contact and a pocket that puts a piece of steel exactly where the keeper will
be. Print a block and its dock, add magnets, and see whether the ring turns itself onto the
pins. If it does not, the choices are a wider contact (long pads need the board routed
again), a dock that clips on at the button, or accepting the grooves.

## Settings for the power chip

| Setting | Value | Why |
| --- | --- | --- |
| Charge current | 8.0 mA (0.5 C) | Safe guess until the cell's datasheet; 1 C would halve the time |
| End voltage | 4.20 V | The protector fitted trips at 4.23 V; a 4.35 V cell needs another variant |
| Input limit | 100 mA, the default with the CC pins grounded | Far above need; nothing to raise |
| Temperature window | 0 to 45 degrees, from the thermistor at the cell tabs | Cell limits; to confirm |

Empty to full takes about two and a half hours, and at half an hour of recording a day that
is once every ten days (power-budget.md).

## If wireless is wanted later

The ML7670 puts out 5 V for an external charging chip, which is what the contacts deliver.
It could take the place of the charging pads on the contacts island and feed the same VBUS
net. The open problem is not the chip but the coil: it needs a ring about 0.2 mm thicker over
the cell, or a shorter cell. That is a second design, worth doing only after a ring with
contacts has shown what the contacts cost in real use.
