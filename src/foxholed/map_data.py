"""Foxhole hex map layout data.

The world map is a grid of hexagonal regions. Each region has a name and
a column/row position in the hex grid. Odd columns are offset downward
by half a hex height (offset-coordinates / "odd-q" layout).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HexRegion:
    """A single hex region on the world map."""

    name: str
    col: int  # hex column (q)
    row: int  # hex row (r)


# Foxhole world map regions laid out as an offset hex grid.
# Coordinates use odd-q offset: odd columns shift down by +0.5 row.
# This is a representative subset of the canonical map; expand as needed.
REGIONS: list[HexRegion] = [
    # Row 0 (top)
    HexRegion("Oarbreaker Isles", 0, 0),
    HexRegion("Fisherman's Row", 1, 0),
    HexRegion("Stema Landing", 2, 0),
    HexRegion("Nevish Line", 3, 0),
    HexRegion("Callum's Cape", 4, 0),
    HexRegion("Speaking Woods", 5, 0),
    HexRegion("Basin Sionnach", 6, 0),
    HexRegion("Howl County", 7, 0),
    HexRegion("Viper Pit", 8, 0),
    HexRegion("Marban Hollow", 9, 0),
    HexRegion("The Moors", 10, 0),
    # Row 1
    HexRegion("Godcrofts", 0, 1),
    HexRegion("Tempest Island", 1, 1),
    HexRegion("The Linn of Mercy", 2, 1),
    HexRegion("Loch Mór", 3, 1),
    HexRegion("The Heartlands", 4, 1),
    HexRegion("Stonecradle", 5, 1),
    HexRegion("Farranac Coast", 6, 1),
    HexRegion("Westgate", 7, 1),
    HexRegion("Reaching Trail", 8, 1),
    HexRegion("Umbral Wildwood", 9, 1),
    HexRegion("Morgen's Crossing", 10, 1),
    # Row 2
    HexRegion("The Fingers", 0, 2),
    HexRegion("Terminus", 1, 2),
    HexRegion("Acrithia", 2, 2),
    HexRegion("Ash Fields", 3, 2),
    HexRegion("Allod's Bight", 4, 2),
    HexRegion("Weathered Expanse", 5, 2),
    HexRegion("The Clahstra", 6, 2),
    HexRegion("Shackled Chasm", 7, 2),
    HexRegion("Endless Shore", 8, 2),
    HexRegion("Deadlands", 9, 2),
    HexRegion("Origin", 10, 2),
    # Row 3 (bottom)
    HexRegion("Kalokai", 0, 3),
    HexRegion("Red River", 1, 3),
    HexRegion("Great March", 2, 3),
    HexRegion("Sableport", 3, 3),
    HexRegion("Throne of Rain", 4, 3),
]

# Build lookup by name for quick access
REGION_BY_NAME: dict[str, HexRegion] = {r.name: r for r in REGIONS}


def hex_to_pixel(col: int, row: int, hex_size: int) -> tuple[float, float]:
    """Convert odd-q offset hex coordinates to pixel center position.

    Args:
        col: Hex column (q).
        row: Hex row (r).
        hex_size: Distance from hex center to a vertex.

    Returns:
        (x, y) pixel coordinates of the hex center.
    """
    w = hex_size * 3 / 2
    h = hex_size * (3**0.5)
    x = col * w
    y = row * h
    # Odd columns are shifted down by half a hex height
    if col % 2 == 1:
        y += h / 2
    return (x, y)


def get_map_bounds(hex_size: int) -> tuple[float, float, float, float]:
    """Calculate the bounding box of the entire map in pixel coordinates.

    Returns:
        (min_x, min_y, max_x, max_y) with some padding.
    """
    if not REGIONS:
        return (0, 0, 100, 100)

    xs = []
    ys = []
    for region in REGIONS:
        px, py = hex_to_pixel(region.col, region.row, hex_size)
        xs.append(px)
        ys.append(py)

    pad = hex_size * 1.5
    return (min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad)
