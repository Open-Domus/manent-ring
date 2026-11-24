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
| Dock | Socket, fuse, three sprung contact bars, one magnet | Transmitter chip (6 x 6 mm), tuned antenna inside a post, a radio product to certify | Oscillator and tuned coil, also a radio product |
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
  neighbours, on every size. The charging slugs are as wide as the pads allow: a bigger target
  for the dock.
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
  is centred on the row of contacts, where the dock's magnet is, which puts 1.0 mm of it past the end of the island, over
  the bend towards the cell tabs: the height of the tab joint there is not known yet. It
  gives the dock's magnet something to hold: titanium is not magnetic, and without it "magnetic
  charging" has nothing to pull on. Steel, not a magnet, so it works either way round and
  survives potting heat.

## Dock

Modelled in `mechanical/manent_mech/dock.py`. `make cad` writes two printable bodies per ring
size, `print-dock-US*.stl` and `print-dock-shoe-US*.stl`, and a test checks each size.

- A **post** the ring slides onto, 0.5 mm smaller than the bore, so one per size: 17.6 mm for
  US 8 to 21.7 mm for US 13. The ring rests on the base, which puts the contacts at the
  right height whichever way up it goes on.
- A **shoe** in a slot of the post, pushed outwards by two small springs. It stands 0.8 mm
  out when free and presses the ring against the far side of the post.
- **Three contact bars** on the shoe's face: 0.4 mm wire laid along the arc in grooves, 0.15 mm
  proud, each covering 22 degrees either side of the middle. Its two ends turn in through the
  shoe, which holds it and gives somewhere to solder. Gold-plated spring wire, or the same
  gold wire as the slugs.
- **One magnet**, 4 x 4 x 2 mm, in the back of the shoe, behind the middle bar and so
  straight under the keeper.
- **Two grooves** on the base show where the button stops, one for each way round.
- **Electrics**: USB-C socket with 5.1 k on each CC pin, a resettable fuse of the 50 mA class,
  then the bars. The fuse is there because a ring sliding on can join the positive bar to
  ground through its own titanium edge. A pocket under the base takes the socket's board.
- The ring's own light shows that it is charging. The dock needs none.
- A **service clip** for loading firmware into a closed ring needs five points, not bars: the
  same post with five spring pins, placed by eye. Not modelled.

### Why bars and not pins

The first dock had three spring pins. A pin leaves its contact when the ring is turned
3 degrees, half a millimetre at the bore, and two magnets either side of the pins were
meant to find that position. A first-order estimate says they cannot: about 0.1 N each
through 2 mm, against the friction of pins that must push with several times that.

A bar along the arc removes the problem instead of fighting it. The ring may be turned
**17 degrees either way**, 3.7 mm at the button on the smallest size, and the grooves on the
base are enough. Nothing changes in the ring.

What a bar must not do is touch anything else on its way round. The model checks, with the
ring seated 0.25 mm high or low: 0.15 mm to a service contact, 0.75 mm to the next charging
contact and to the titanium. The tight one is the ground bar passing a service contact, which
would be harmless (ground through 100 ohm); the positive bar has 0.1 mm more.

### What the magnet is for now

Not to find the contacts. It pulls the ring onto the bars, adds to the contact force and
gives the snap the product site promises. The estimate is 0.25 N, good to a factor of two:
seven times the ring's weight, so the ring stays on a dock held upside down if the estimate
holds. The keeper is asked for 0.7 T, well under what steel carries. If the trial shows the
magnet adds nothing, magnet and keeper can both go and the ring loses a part.

### The trial

Needs no electronics. `print-block-US*.stl` has a dimple on each contact and a pocket that
puts a piece of steel exactly where the keeper will be. Print a block, a dock and a shoe; add
the magnet, two springs and three wires; check with a meter that each bar finds its dimple
over the whole 17 degrees and never the wrong one.

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
