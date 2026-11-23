"""Ring envelope parameters. All lengths in millimetres.

The cross-section is the one drawn by the product site (manent-site/assets/ring.js):
a rounded rectangle centred on the mean radius, thicker in the middle of the band
("crown") on both the outer and the inner face.
"""
from dataclasses import dataclass, replace


def inner_diameter(us_size: float) -> float:
    """Inner diameter of a ring of the given US size."""
    return 11.63 + 0.8128 * us_size


@dataclass(frozen=True)
class RingParams:
    name: str
    mean_radius: float      # R: radius of the middle of the wall
    half_width: float       # HY: half of the band width (axial)
    half_wall: float        # HX: half of the wall thickness at the band edges
    crown: float            # extra half-thickness at the band centre
    corner_r: float         # fillet of the cross-section corners
    t_ti: float = 0.40      # titanium shell: outer face and both side walls
    t_skin: float = 0.35    # resin between the cavity and the finger
    gap: float = 0.10       # minimum resin around any part

    @property
    def band_width(self) -> float:
        return 2 * self.half_width

    @property
    def wall_edge(self) -> float:
        return 2 * self.half_wall

    @property
    def wall_centre(self) -> float:
        return 2 * (self.half_wall + self.crown)

    @property
    def inner_diameter_min(self) -> float:
        return 2 * (self.mean_radius - self.half_wall - self.crown)

    @property
    def outer_diameter(self) -> float:
        return 2 * (self.mean_radius + self.half_wall + self.crown)

    def for_size(self, us_size: float) -> "RingParams":
        """Same cross-section on a finger of another size."""
        r = inner_diameter(us_size) / 2 + self.half_wall + self.crown
        return replace(self, mean_radius=r)

    @property
    def us_size(self) -> float:
        return (self.inner_diameter_min - 11.63) / 0.8128


# Envelope A: the numbers in manent-site/assets/ring.js, line 20.
SITE = RingParams("A-site-7.4", mean_radius=10.6, half_width=3.7,
                  half_wall=1.2, crown=0.28, corner_r=0.9)

# Envelope B, the adopted one: 8.0 mm band, 2.6 mm wall at the edges, 3.0 mm at the
# centre, on the same finger as envelope A. A is kept as a comparison.
WIDE = RingParams("B-8.0", mean_radius=SITE.mean_radius - (1.2 + 0.28) + (1.3 + 0.2),
                  half_width=4.0, half_wall=1.3, crown=0.2, corner_r=0.9)

ENVELOPES = {"A": SITE, "B": WIDE}
