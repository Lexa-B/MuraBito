"""The example StateTree for exp-02. The rules are placeholders: edit freely."""

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

# For each object: (LastUsed, "==" or "!=", Zone) rows that send the actor to it.
# Finishing in the last object's home zone goes forward (A->B->C->A);
# finishing across a border goes backward.
RULES = {
    "A": [("C", "==", "NE"), ("B", "!=", "S")],
    "B": [("A", "==", "NW"), ("C", "!=", "NE")],
    "C": [("B", "==", "S"), ("A", "!=", "NW")],
}


def rule_condition(last_used, op, zone):
    if op == "==":
        test = lambda ctx: ctx.get("LastUsed") == last_used and ctx.get("Zone") == zone
    elif op == "!=":
        test = lambda ctx: ctx.get("LastUsed") == last_used and ctx.get("Zone") != zone
    else:
        raise ValueError(f"unknown zone operator: {op!r}")
    return Condition(f"LastUsed=={last_used} & Zone{op}{zone}", test)


def go_use_state(name, tag_query, conditions, mode):
    return State(name, conditions=conditions, mode=mode, on_exit=release_claim, children=[
        State("FindAndClaim", task=FindAndClaim(tag_query), transitions=[
            Transition(Trigger.ON_COMPLETED, f"{name}/MoveTo"),
            Transition(Trigger.ON_FAILED, "Wander"),
        ]),
        State("MoveTo", task=MoveTo(claimed_slot_goal, chase=True), transitions=[
            Transition(Trigger.ON_COMPLETED, f"{name}/Interact"),
            Transition(Trigger.ON_FAILED, "Wander"),
        ]),
        State("Interact", task=Interact(), transitions=[
            Transition(Trigger.ON_COMPLETED, ROOT),
            Transition(Trigger.ON_FAILED, ROOT),
        ]),
    ])


def build_tree() -> StateTree:
    children = [
        go_use_state(f"GoUse({target})", {f"Object.{target}"}, [rule_condition(*row) for row in rows], Mode.ANY)
        for target, rows in RULES.items()
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
