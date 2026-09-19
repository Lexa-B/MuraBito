"""The example StateTree for exp-00. The rules are placeholders: edit freely."""

from ai.statetree import ROOT, Condition, Mode, State, StateTree, Transition, Trigger
from ai.tasks import (
    FindAndClaim,
    Interact,
    MoveTo,
    Wait,
    ZoneEvaluator,
    claimed_slot_goal,
    random_tile_goal,
    release_claim,
)

# For each object: the (LastUsed, Zone) pairs that send the actor to it.
RULES = {
    "A": [("C", "West"), ("B", "East")],
    "B": [("A", "West"), ("C", "East")],
    "C": [("B", "West"), ("A", "East")],
}


def rule_condition(last_used, zone):
    return Condition(
        f"LastUsed=={last_used} & Zone=={zone}",
        lambda ctx: ctx.get("LastUsed") == last_used and ctx.get("Zone") == zone,
    )


def go_use_state(name, tag_query, conditions, mode):
    return State(name, conditions=conditions, mode=mode, on_exit=release_claim, children=[
        State("FindAndClaim", task=FindAndClaim(tag_query), transitions=[
            Transition(Trigger.ON_COMPLETED, f"{name}/MoveTo"),
            Transition(Trigger.ON_FAILED, "Wander"),
        ]),
        State("MoveTo", task=MoveTo(claimed_slot_goal), transitions=[
            Transition(Trigger.ON_COMPLETED, f"{name}/Interact"),
            Transition(Trigger.ON_FAILED, "Wander"),
        ]),
        State("Interact", task=Interact(), transitions=[
            Transition(Trigger.ON_COMPLETED, ROOT),
        ]),
    ])


def build_tree() -> StateTree:
    children = [
        go_use_state(f"GoUse({target})", {f"Object.{target}"}, [rule_condition(*pair) for pair in pairs], Mode.ANY)
        for target, pairs in RULES.items()
    ]
    children.append(go_use_state(
        "GoUse(Nearest)", set(),
        [Condition("LastUsed==None", lambda ctx: ctx.get("LastUsed") is None)], Mode.ALL,
    ))
    children.append(State("Wander", children=[
        State("MoveTo", task=MoveTo(random_tile_goal), transitions=[
            Transition(Trigger.ON_COMPLETED, "Wander/Wait"),
            Transition(Trigger.ON_FAILED, ROOT),
        ]),
        State("Wait", task=Wait(1.0), transitions=[
            Transition(Trigger.ON_COMPLETED, ROOT),
        ]),
    ]))
    return StateTree(State("Root", children=children), evaluators=[ZoneEvaluator()])
