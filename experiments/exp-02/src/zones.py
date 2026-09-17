"""The map's three 120-degree zones. Pure geometry, no world state."""

from hexgrid import Tile

ZONES = ("NE", "S", "NW")


def zone_of(tile: Tile) -> str:
    """Three 120-degree sectors, by the largest cube coordinate; ties go q, then r, then s."""
    q, r = tile
    s = -q - r
    if q >= r and q >= s:
        return "NE"
    if r >= s:
        return "S"
    return "NW"
