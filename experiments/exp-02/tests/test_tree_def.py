import pytest

from ai.statetree import ROOT, Trigger
from ai.tasks import ZoneEvaluator
from ai.tree_def import build_tree, rule_condition

# Copied from the spec's rules table (unchanged from exp-01).
EXPECTED = {
    (None, "NW"): "GoUse(Nearest)",
    (None, "S"): "GoUse(Nearest)",
    (None, "NE"): "GoUse(Nearest)",
    ("A", "NW"): "GoUse(B)",
    ("A", "S"): "GoUse(C)",
    ("A", "NE"): "GoUse(C)",
    ("B", "NW"): "GoUse(A)",
    ("B", "S"): "GoUse(C)",
    ("B", "NE"): "GoUse(A)",
    ("C", "NW"): "GoUse(B)",
    ("C", "S"): "GoUse(B)",
    ("C", "NE"): "GoUse(A)",
}


@pytest.mark.parametrize("last_used, zone", sorted(EXPECTED, key=str))
def test_rules_select_expected_branch(last_used, zone):
    tree = build_tree()
    path = tree.select(tree.root, {"LastUsed": last_used, "Zone": zone})
    assert path[0].name == EXPECTED[(last_used, zone)]
    assert path[-1].name == "ChooseTarget"


def test_tree_shape_matches_spec():
    go_use = lambda name: [name] + [f"{name}/{child}" for child in ("ChooseTarget", "MoveTo", "Search", "Explore", "Interact")]
    assert [state.path for state, _ in build_tree().walk()] == [
        "",
        *go_use("GoUse(A)"),
        *go_use("GoUse(B)"),
        *go_use("GoUse(C)"),
        *go_use("GoUse(Nearest)"),
        "Wander", "Wander/MoveTo", "Wander/Wait",
    ]


def test_condition_names_are_readable():
    tree = build_tree()
    assert [c.name for c in tree.find("GoUse(A)").conditions] == [
        "LastUsed==C & Zone==NE",
        "LastUsed==B & Zone!=S",
    ]
    assert [c.name for c in tree.find("GoUse(Nearest)").conditions] == ["LastUsed==None"]


def test_rule_condition_rejects_unknown_operator():
    with pytest.raises(ValueError):
        rule_condition("A", "<", "NW")


def transitions(tree, path):
    return [
        (t.trigger, t.target, t.condition.name if t.condition is not None else None)
        for t in tree.find(path).transitions
    ]


@pytest.mark.parametrize("name", ["GoUse(A)", "GoUse(B)", "GoUse(C)", "GoUse(Nearest)"])
def test_go_use_transitions_match_spec_in_order(name):
    tree = build_tree()
    assert transitions(tree, f"{name}/ChooseTarget") == [
        (Trigger.ON_CONDITION, f"{name}/Search", "TargetIsRegion"),
        (Trigger.ON_COMPLETED, f"{name}/MoveTo", None),
        (Trigger.ON_FAILED, f"{name}/Explore", None),
    ]
    assert transitions(tree, f"{name}/MoveTo") == [
        (Trigger.ON_CONDITION, f"{name}/Search", "TargetNotPoint"),
        (Trigger.ON_COMPLETED, f"{name}/Interact", None),
        (Trigger.ON_FAILED, "Wander", None),
    ]
    assert transitions(tree, f"{name}/Search") == [
        (Trigger.ON_CONDITION, f"{name}/MoveTo", "TargetIsPoint"),
        (Trigger.ON_FAILED, f"{name}/Explore", None),
    ]
    assert transitions(tree, f"{name}/Explore") == [
        (Trigger.ON_CONDITION, f"{name}/ChooseTarget", "MatchSeen"),
        (Trigger.ON_COMPLETED, f"{name}/Explore", None),
        (Trigger.ON_FAILED, "Wander", None),
    ]
    assert transitions(tree, f"{name}/Interact") == [(Trigger.ON_COMPLETED, ROOT, None), (Trigger.ON_FAILED, ROOT, None)]
    move = tree.find(f"{name}/MoveTo").task
    assert (move.chase, move.claim) == (True, True)


def test_go_use_tag_queries():
    tree = build_tree()
    assert tree.find("GoUse(B)/ChooseTarget").task.tag_query == frozenset({"Object.B"})
    assert tree.find("GoUse(B)/Explore").task.tag_query == frozenset({"Object.B"})
    assert tree.find("GoUse(Nearest)/ChooseTarget").task.tag_query == frozenset()


def test_wander_is_unchanged():
    tree = build_tree()
    move = tree.find("Wander/MoveTo").task
    assert (move.chase, move.claim) == (False, False)


def test_perception_is_ticked_before_the_zone_evaluator():
    perception = object()
    tree = build_tree(perception)
    assert tree.evaluators[0] is perception
    assert isinstance(tree.evaluators[1], ZoneEvaluator)
    assert [type(e) for e in build_tree().evaluators] == [ZoneEvaluator]
