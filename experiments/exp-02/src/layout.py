"""The object definitions for exp-02, placed on a random map. All placeholder content: edit freely."""

from mapgen import generate
from smartobjects import Interaction, Slot, SmartObject
from world import Actor, World

# (name, slot directions from the object, home zone, pauses during use, casts shadow)
OBJECTS = (
    ("A", (0, 5), "NW", True, True),
    ("B", (2, 1), "S", True, True),
    ("C", (3, 4), "NE", False, False),
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


def make_object(name, tile, slot_directions, home_zone="", pauses_during_use=True, casts_shadow=False, heading=0):
    return SmartObject(
        name=name,
        tile=tile,
        tags=frozenset({f"Object.{name}"}),
        slots=[Slot(index=i, direction=d) for i, d in enumerate(slot_directions)],
        interactions=placeholder_interactions(name),
        home_zone=home_zone,
        pauses_during_use=pauses_during_use,
        casts_shadow=casts_shadow,
        heading=heading,
    )


def build_world(rng) -> tuple[World, Actor]:
    """A random map from `rng`: walls, the objects in OBJECTS, and the actor."""
    specs = [(home_zone, slot_directions, casts_shadow) for _, slot_directions, home_zone, _, casts_shadow in OBJECTS]
    walls, placed, actor_tile, actor_facing = generate(rng, specs)
    world = World(walls=walls)
    for (name, slot_directions, home_zone, pauses, casts_shadow), (tile, heading) in zip(OBJECTS, placed):
        world.add_object(make_object(name, tile, slot_directions, home_zone, pauses, casts_shadow, heading))
    return world, Actor(tile=actor_tile, facing=actor_facing)
