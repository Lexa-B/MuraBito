"""The example StateTree for exp-02. The rules are placeholders: edit freely."""

from ai.beliefs import LOST, POINT, REGION
from ai.statetree import ROOT, Condition, Mode, State, StateTree, Transition, Trigger
from ai.tasks import (
    ChooseTarget,
    Explore,
    Interact,
    MoveTo,
    Search,
    Wait,
    ZoneEvaluator,
    random_tile_goal,
    release_claim,
    target_goal,
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


def target_level(name, levels):
    """True when the current target has a belief at one of `levels`."""
    def test(ctx):
        target, beliefs = ctx.get("Target"), ctx["beliefs"]
        return target is not None and target in beliefs.beliefs and beliefs.level(target) in levels
    return Condition(name, test)


def match_seen(tag_query):
    """True when an object matching the tag query was seen this tick."""
    def test(ctx):
        beliefs = ctx["beliefs"]
        return any(name in beliefs.seen_now for name in beliefs.matching(tag_query))
    return Condition("MatchSeen", test)


def go_use_state(name, tag_query, conditions, mode):
    tags = frozenset(tag_query)
    return State(name, conditions=conditions, mode=mode, on_exit=release_claim, children=[
        State("ChooseTarget", task=ChooseTarget(tags), transitions=[
            Transition(Trigger.ON_CONDITION, f"{name}/Search", target_level("TargetIsRegion", {REGION})),
            Transition(Trigger.ON_COMPLETED, f"{name}/MoveTo"),
            Transition(Trigger.ON_FAILED, f"{name}/Explore"),
        ]),
        State("MoveTo", task=MoveTo(target_goal, chase=True, claim=True), transitions=[
            Transition(Trigger.ON_CONDITION, f"{name}/Search", target_level("TargetNotPoint", {REGION, LOST})),
            Transition(Trigger.ON_COMPLETED, f"{name}/Interact"),
            Transition(Trigger.ON_FAILED, "Wander"),
        ]),
        State("Search", task=Search(), transitions=[
            Transition(Trigger.ON_CONDITION, f"{name}/MoveTo", target_level("TargetIsPoint", {POINT})),
            Transition(Trigger.ON_FAILED, f"{name}/Explore"),
        ]),
        State("Explore", task=Explore(tags), transitions=[
            Transition(Trigger.ON_CONDITION, f"{name}/ChooseTarget", match_seen(tags)),
            Transition(Trigger.ON_COMPLETED, f"{name}/Explore"),
            Transition(Trigger.ON_FAILED, "Wander"),
        ]),
        State("Interact", task=Interact(), transitions=[
            Transition(Trigger.ON_COMPLETED, ROOT),
            Transition(Trigger.ON_FAILED, ROOT),
        ]),
    ])


def build_tree(perception=None) -> StateTree:
    """The example tree. `perception`, if given, is ticked first, before the zone evaluator."""
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
    evaluators = ([perception] if perception is not None else []) + [ZoneEvaluator()]
    return StateTree(State("Root", children=children), evaluators=evaluators)
