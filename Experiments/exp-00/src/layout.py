"""The starting layout for exp-00. All placeholder content: edit freely."""

from hexgrid import DIRECTIONS, add
from smartobjects import Interaction, Slot, SmartObject
from world import World

ACTOR_START = (-10, 4)

WALLS = (
    [(-4, r) for r in range(-4, 5)]  # between A and B
    + [(4, r) for r in range(-5, 4)]  # between B and C
    + [(q, -6) for q in range(-2, 3)]
    + [(q, 7) for q in range(-3, 2)]
    + [(q, 9) for q in range(-6, 0)]
)

# (name, tile, directions from the object to its slots)
OBJECTS = (
    ("A", (-8, 2), (0, 5)),
    ("B", (0, 0), (3, 0)),  # one slot each side of the center column
    ("C", (8, -2), (3, 4)),
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


def make_object(name, tile, slot_directions):
    """Slots sit on the neighbors in `slot_directions`, each facing back at the object."""
    slots = [
        Slot(index=i, tile=add(tile, DIRECTIONS[d]), facing=(d + 3) % 6)
        for i, d in enumerate(slot_directions)
    ]
    return SmartObject(
        name=name,
        tile=tile,
        tags=frozenset({f"Object.{name}"}),
        slots=slots,
        interactions=placeholder_interactions(name),
    )


def build_world() -> World:
    world = World(walls=WALLS)
    for name, tile, slot_directions in OBJECTS:
        world.add_object(make_object(name, tile, slot_directions))
    return world
