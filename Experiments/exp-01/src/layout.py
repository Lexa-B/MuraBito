"""The starting layout for exp-01. All placeholder content: edit freely."""

from smartobjects import Interaction, Slot, SmartObject
from world import World

ACTOR_START = (-8, 2)  # NW

# Short segments inside each zone, none on or next to a zone border.
WALLS = (
    [(-8, r) for r in range(-2, 2)] + [(q, -7) for q in range(-2, 2)]  # NW
    + [(-6, 6), (-5, 5), (-4, 4), (-3, 3)]  # S
    + [(q, 8) for q in range(-6, -2)] + [(3, r) for r in range(6, 10)]  # S
    + [(-7, 10), (-6, 10), (-5, 10), (-4, 10)]  # S
    + [(8, r) for r in range(-6, -2)] + [(q, -9) for q in range(6, 10)]  # NE
    + [(5, 1), (6, 0), (7, -1), (8, 0)]  # NE (three-tile segment plus a lone pillar)
)

# (name, start tile, slot directions from the object, home zone, pauses during use)
OBJECTS = (
    ("A", (-5, -2), (0, 5), "NW", True),
    ("B", (-2, 5), (2, 1), "S", True),
    ("C", (5, -2), (3, 4), "NE", False),
)


def set_last_used(name):
    def effect(ctx):
        ctx["LastUsed"] = name
    return effect


def placeholder_interactions(name):
    return [
        Interaction(f"{name}.Short", 1.5, (set_last_used(name),)),
        Interaction(f"{name}.Long", 3.0, (set_last_used(name),)),
    ]


def make_object(name, tile, slot_directions, home_zone="", pauses_during_use=True):
    return SmartObject(
        name=name,
        tile=tile,
        tags=frozenset({f"Object.{name}"}),
        slots=[Slot(index=i, direction=d) for i, d in enumerate(slot_directions)],
        interactions=placeholder_interactions(name),
        home_zone=home_zone,
        pauses_during_use=pauses_during_use,
    )


def build_world() -> World:
    world = World(walls=WALLS)
    for name, tile, slot_directions, home_zone, pauses in OBJECTS:
        world.add_object(make_object(name, tile, slot_directions, home_zone, pauses))
    return world
