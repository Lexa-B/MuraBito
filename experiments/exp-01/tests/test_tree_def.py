import pytest

from ai.tree_def import build_tree, rule_condition

# Copied from the spec's rules table.
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
    assert path[-1].name == "FindAndClaim"


def test_tree_shape_matches_spec():
    go_use = lambda name: [name, f"{name}/FindAndClaim", f"{name}/MoveTo", f"{name}/Interact"]
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
