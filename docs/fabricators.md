# Fabricators

Who could make the ring's circuit, checked against public capability pages in November 2026.
Pages from the fabricators themselves; several are old or disagree with each other, so every
figure here is to be confirmed in a quote.

## What the circuit asks for

- A flat rigid-flex strip, bent into the ring after assembly (flex-to-install, IPC-2223 Use A).
  Six rigid islands, two-layer flex between them, 5.6 mm wide.
- The nRF54L15 CSP47 has a 0.3 mm pitch. Nordic's reference layout puts a laser microvia in
  every pad: **0.1 mm hole, 0.2 mm pad** (figures reported on Nordic's forum; to be read from the
  reference layout files, CAAA v0.7). A fabricator whose minimum microvia pad is above 0.2 mm
  cannot build that footprint as drawn.
- Microvia aspect ratio about 1:1 or less, so the dielectric under the first layer must be thin.
- Bend radius: inner ring radius about 9 mm. A two-layer flex wants about 10-15 times its
  thickness (PCBWay's rule for multilayer flex), so 1.5-2.5 mm. Not a constraint.
- Assembly of three WLCSP parts on both faces, with X-ray inspection.

## Comparison

| Fabricator | Rigid-flex | Laser microvia | Microvia pad | Assembly | Ordering | Fit |
| --- | --- | --- | --- | --- | --- | --- |
| PCBWay (CN) | Yes, up to 32 layers; HDI rigid-flex examples (2+1+2F+1+2) | 0.076-0.1 mm (old table); 2 mil listed for laser | Not published; 0.35 mm on the plain rigid-flex page | Yes, 3D X-ray (AXI) | Instant quote for basics, sales for HDI | Best candidate for prototypes; confirm the 0.2 mm pad |
| NextPCB (CN) | Yes, 20 rigid / 8 flex layers (catalog says 32 / 6) | 0.075-0.15 mm, 1:1 max | Not published | Yes | Advanced quote form | Second candidate |
| JLCPCB (CN) | **No**: flex only, 1-4 layers; "rigid-flex not yet supported" | No | - | Yes | Instant, from $2 for 5 flex boards | Mechanical dummies only |
| Würth Elektronik / WEdirekt (DE) | Yes, RIGID.flex with HDI | 0.1 mm | 0.275-0.30 mm standard; **0.35 mm** in the online shop | Via partners | Online shop for standard builds | Pad too large for the CSP47 as drawn |
| Eurocircuits (BE) | No polyimide rigid-flex; FR-4 SEMI-FLEX, 4-6 layers, 5 mm bend radius, 5 bends | HDI pool, L1-L2 laser, filled | **0.21-0.23 mm** | Yes | Pool, online | Just too large; SEMI-FLEX is too thick for a ring |
| Multi-CB (DE) | Rigid-flex offered; HDI limits published for rigid only | 0.075 mm "extreme special" | **0.225 mm** | No | Quote | Just too large |
| Sierra Circuits / ProtoExpress (US) | Yes, up to 16 layers; HDI, stacked microvias, 2 mil lines | Yes | Not published | Yes, in house | Custom quote for flex and rigid-flex | Capable; expensive; advises against via-in-pad in multilayer flex (ours is in the rigid islands) |
| Somacis (IT, Castelfidardo) | Yes, HDI rigid-flex up to 50 layers; AC7119/3 HDI accreditation | Yes | Not published | No | Industrial quote | Capable; aimed at aerospace and production volumes |
| Cistelaier (IT, Modena/Genova) | Yes, 3-16 layers, HDI rigid-flex, ESA qualified | Yes | Not published | No | Industrial quote | Capable; aimed at defence and space |

## Recommendation

1. **Now:** two-layer flex from JLCPCB (or PCBWay), same outline and thickness as the real
   strip, with copper dummies for the islands. A few euros. It tests bending, the fit in the
   printed shell and the cell tabs.
2. **First real build:** ask PCBWay and NextPCB for a quote on the full rigid-flex with the
   stackup and the CSP47 footprint attached, and ask three questions explicitly: minimum
   laser microvia pad (need 0.2 mm), filled and capped via-in-pad on the islands, X-ray of
   the WLCSP joints on both faces.
3. **If both refuse or the yield is poor:** Sierra Circuits for a prototype with assembly in
   one place, or Somacis / Cistelaier for a European source, through a direct quote.

## Sources

- [Nordic nRF54L15 reference layout](https://www.nordicsemi.com/Products/nRF54L15/Reference-layout)
- [Nordic forum: CSP47 layout data](https://devzone.nordicsemi.com/f/nordic-q-a/124593/datasheet-for-nrf54l15-csp47-does-not-include-enough-data-to-properly-specify-a-layout)
- [PCBWay rigid-flex](https://www.pcbway.com/fpc-rigid-flex-pcb/rigid-flex-pcb.html),
  [advanced capabilities](https://www.pcbway.com/advanced-pcb-capabilities.html),
  [X-ray inspection](https://pcbway.com/pcb_prototype/Automated_X_Ray_Inspection.html)
- [NextPCB advanced quote](https://www.nextpcb.com/advanced-pcb-quote),
  [HDI capabilities](https://www.nextpcb.com/pcb-type/hdi-pcb)
- [JLCPCB flex capabilities](https://jlcpcb.com/capabilities/flex-pcb-capabilities)
- [Würth RIGID.flex](https://www.we-online.com/en/products/printed-circuit-boards/flex-solutions/rigid-flex),
  [HDI rules poster](https://www.we-online.com/files/pdf1/design-rules-poster-hdi-microvia-cbt-en.pdf),
  [WEdirekt design guide](https://www.we-online.com/files/pdf1/basic_design-guide_110325_en_web.pdf)
- [Eurocircuits HDI pool](https://www.eurocircuits.com/services/hdi-pool/),
  [SEMI-FLEX pool](https://www.eurocircuits.com/blog/semi-flex-pool)
- [Multi-CB HDI](https://www.multi-circuit-boards.eu/en/hdi-printed-circuit-boards.html)
- [Sierra Circuits HDI](https://www.protoexpress.com/products/hdi-pcbs),
  [HDI FAQ](https://www.protoexpress.com/faq/hdi-pcbs/)
- [Somacis profile (AIAD)](https://aiad.it/aziende-federate/somacis-2023/?lang=en)
- [Cistelaier ESA qualification](https://iconnect007.com/article/143381/pcb-fabricator-cistelaier-receives-esa-qualification/143378/design)
