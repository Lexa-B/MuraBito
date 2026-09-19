import pytest

from ai.tree_def import build_tree

# Copied from the spec's rules table.
EXPECTED = {
    (None, "West"): "GoUse(Nearest)",
    (None, "East"): "GoUse(Nearest)",
    ("A", "West"): "GoUse(B)",
    ("A", "East"): "GoUse(C)",
    ("B", "West"): "GoUse(C)",
    ("B", "East"): "GoUse(A)",
    ("C", "West"): "GoUse(A)",
    ("C", "East"): "GoUse(B)",
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
        "LastUsed==C & Zone==West",
        "LastUsed==B & Zone==East",
    ]
    assert [c.name for c in tree.find("GoUse(Nearest)").conditions] == ["LastUsed==None"]
