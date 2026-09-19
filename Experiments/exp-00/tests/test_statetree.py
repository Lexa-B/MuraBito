import pytest

from ai.statetree import (
    ROOT,
    Condition,
    Evaluator,
    Mode,
    State,
    StateTree,
    Status,
    Task,
    Transition,
    Trigger,
)


class ScriptedTask(Task):
    """Returns the given statuses in order, then RUNNING forever."""

    def __init__(self, *statuses):
        self.statuses = list(statuses)
        self.entered = 0
        self.exited = 0

    def enter(self, ctx):
        self.entered += 1

    def tick(self, ctx, dt):
        return self.statuses.pop(0) if self.statuses else Status.RUNNING

    def exit(self, ctx):
        self.exited += 1


def flag(key):
    return Condition(key, lambda ctx: ctx.get(key, False))


def leaf(name, *statuses, **kwargs):
    return State(name, task=ScriptedTask(*statuses), **kwargs)


def test_selects_first_child_whose_conditions_pass():
    tree = StateTree(State("Root", children=[
        leaf("A", conditions=[flag("a")]),
        leaf("B", conditions=[flag("b")]),
        leaf("C", conditions=[flag("c")]),
    ]))
    tree.tick({"b": True, "c": True}, 0.1)
    assert tree.leaf.path == "B"


def test_falls_back_to_next_sibling_when_a_subtree_fails():
    tree = StateTree(State("Root", children=[
        State("P", children=[leaf("X", conditions=[flag("x")])]),
        leaf("Q"),
    ]))
    tree.tick({}, 0.1)
    assert [s.path for s in tree.active] == ["Q"]


def test_any_mode_passes_when_one_condition_passes():
    tree = StateTree(State("Root", children=[
        leaf("A", conditions=[flag("a"), flag("b")], mode=Mode.ANY),
        leaf("Z"),
    ]))
    tree.tick({"b": True}, 0.1)
    assert tree.leaf.path == "A"


def test_all_mode_fails_when_one_condition_fails():
    tree = StateTree(State("Root", children=[
        leaf("A", conditions=[flag("a"), flag("b")], mode=Mode.ALL),
        leaf("Z"),
    ]))
    tree.tick({"b": True}, 0.1)
    assert tree.leaf.path == "Z"


@pytest.mark.parametrize("status, expected", [(Status.SUCCEEDED, "Done"), (Status.FAILED, "Broken")])
def test_completed_and_failed_transitions(status, expected):
    tree = StateTree(State("Root", children=[
        leaf("Start", status, transitions=[
            Transition(Trigger.ON_COMPLETED, "Done"),
            Transition(Trigger.ON_FAILED, "Broken"),
        ]),
        leaf("Done"),
        leaf("Broken"),
    ]))
    tree.tick({}, 0.1)
    assert tree.leaf.path == expected


def test_parent_transition_used_when_leaf_has_no_match():
    tree = StateTree(State("Root", children=[
        State("P", transitions=[Transition(Trigger.ON_COMPLETED, "Z")], children=[leaf("L", Status.SUCCEEDED)]),
        leaf("Z"),
    ]))
    tree.tick({}, 0.1)
    assert tree.leaf.path == "Z"


def test_condition_transition_fires_while_running():
    tree = StateTree(State("Root", children=[
        leaf("A", transitions=[Transition(Trigger.ON_CONDITION, "B", condition=flag("go"))]),
        leaf("B"),
    ]))
    ctx = {}
    tree.tick(ctx, 0.1)
    assert tree.leaf.path == "A"
    ctx["go"] = True
    tree.tick(ctx, 0.1)
    assert tree.leaf.path == "B"


def test_finished_task_without_any_transition_returns_to_root():
    task = ScriptedTask(Status.SUCCEEDED)
    tree = StateTree(State("Root", children=[State("A", task=task)]))
    tree.tick({}, 0.1)
    assert tree.leaf.path == "A"
    assert (task.entered, task.exited) == (2, 1)


def test_unselectable_target_reselects_from_root():
    class FinishOnce(Task):
        def tick(self, ctx, dt):
            ctx["first"] = False
            return Status.SUCCEEDED

    tree = StateTree(State("Root", children=[
        State("A", task=FinishOnce(), conditions=[flag("first")],
              transitions=[Transition(Trigger.ON_COMPLETED, "B")]),
        leaf("B", conditions=[flag("b")]),
        leaf("C"),
    ]))
    tree.tick({"first": True}, 0.1)
    assert tree.leaf.path == "C"
    assert "B not selectable, reselecting from ROOT" in [text for _, text in tree.log]


def test_unselectable_target_falls_back_to_root_for_on_exit():
    exits = []
    tree = StateTree(State("Root", children=[
        State("P", on_exit=lambda ctx: exits.append("P"), children=[
            leaf("L1", Status.SUCCEEDED, transitions=[Transition(Trigger.ON_COMPLETED, "P/L2")]),
            leaf("L2", conditions=[flag("go")]),
        ]),
    ]))
    tree.tick({}, 0.1)
    assert exits == ["P"]
    assert "P/L2 not selectable, reselecting from ROOT" in [text for _, text in tree.log]
    assert tree.leaf.path == "P/L1"


def test_select_log_line_precedes_leaf_enter_side_effects():
    class LoggingTask(Task):
        def enter(self, ctx):
            ctx["log"]("entered")

        def tick(self, ctx, dt):
            return Status.RUNNING

    tree = StateTree(State("Root", children=[State("A", task=LoggingTask())]))
    ctx = {"log": tree.write_log}
    tree.tick(ctx, 0.1)
    assert [text for _, text in tree.log] == ["select -> A", "entered"]


def test_reset_clears_idle_logged_flag():
    tree = StateTree(State("Root", children=[leaf("A", conditions=[flag("a")])]))
    tree.tick({}, 0.1)
    tree.tick({}, 0.1)
    assert [text for _, text in tree.log] == ["error: no state selectable, idle"]
    tree.reset({})
    tree.tick({}, 0.1)
    assert [text for _, text in tree.log] == [
        "error: no state selectable, idle",
        "error: no state selectable, idle",
    ]


def test_evaluators_run_before_selection_and_tasks():
    seen = []

    class Mark(Evaluator):
        def tick(self, ctx, dt):
            ctx["evaluated"] = True

    class Probe(Task):
        def tick(self, ctx, dt):
            seen.append(ctx.get("evaluated", False))
            return Status.RUNNING

    tree = StateTree(
        State("Root", children=[State("A", task=Probe(), conditions=[flag("evaluated")]), leaf("Z")]),
        evaluators=[Mark()],
    )
    tree.tick({}, 0.1)
    assert tree.leaf.path == "A"
    assert seen == [True]


def test_condition_results_are_recorded():
    a, b, c = flag("a"), flag("b"), flag("c")
    tree = StateTree(State("Root", children=[
        leaf("A", conditions=[a]),
        leaf("B", conditions=[b]),
        leaf("C", conditions=[c]),
    ]))
    tree.tick({"b": True}, 0.1)
    assert (a.last_result, b.last_result, c.last_result) == (False, True, None)


def test_on_exit_runs_deepest_first_and_root_target_reenters_same_branch():
    exits = []
    tree = StateTree(State("Root", children=[
        State("P", on_exit=lambda ctx: exits.append("P"), children=[
            State("Q", on_exit=lambda ctx: exits.append("Q"), children=[
                leaf("L", Status.SUCCEEDED, transitions=[Transition(Trigger.ON_COMPLETED, ROOT)]),
            ]),
        ]),
    ]))
    tree.tick({}, 0.1)
    assert exits == ["Q", "P"]
    assert tree.leaf.path == "P/Q/L"


def test_sibling_leaf_transition_keeps_parent_active():
    exits = []
    first, second = ScriptedTask(Status.SUCCEEDED), ScriptedTask()
    tree = StateTree(State("Root", children=[
        State("P", on_exit=lambda ctx: exits.append("P"), children=[
            State("L1", task=first, transitions=[Transition(Trigger.ON_COMPLETED, "P/L2")]),
            State("L2", task=second),
        ]),
    ]))
    tree.tick({}, 0.1)
    assert tree.leaf.path == "P/L2"
    assert exits == []
    assert (first.exited, second.entered) == (1, 1)


def test_reset_exits_the_whole_active_path():
    exits = []
    task = ScriptedTask()
    tree = StateTree(State("Root", children=[
        State("P", on_exit=lambda ctx: exits.append("P"), children=[
            State("Q", on_exit=lambda ctx: exits.append("Q"), children=[State("L", task=task)]),
        ]),
    ]))
    tree.tick({}, 0.1)
    tree.reset({})
    assert exits == ["Q", "P"]
    assert task.exited == 1
    assert tree.active == [] and tree.leaf is None and tree.last_status is None


def test_log_records_selection_and_transitions_with_time():
    tree = StateTree(State("Root", children=[
        leaf("Start", Status.SUCCEEDED, transitions=[Transition(Trigger.ON_COMPLETED, "Done")]),
        leaf("Done"),
    ]))
    tree.tick({}, 0.5)
    assert list(tree.log) == [(0.5, "select -> Start"), (0.5, "Start -> Succeeded"), (0.5, "select -> Done")]


def test_idle_error_logged_once():
    tree = StateTree(State("Root", children=[leaf("A", conditions=[flag("a")])]))
    tree.tick({}, 0.1)
    tree.tick({}, 0.1)
    assert [text for _, text in tree.log] == ["error: no state selectable, idle"]
    assert tree.leaf is None


def test_walk_is_depth_first_in_child_order():
    tree = StateTree(State("Root", children=[State("P", children=[leaf("X"), leaf("Y")]), leaf("Q")]))
    assert [(s.path, d) for s, d in tree.walk()] == [("", 0), ("P", 1), ("P/X", 2), ("P/Y", 2), ("Q", 1)]


def test_construction_checks():
    with pytest.raises(KeyError):
        StateTree(State("Root", children=[leaf("A", transitions=[Transition(Trigger.ON_COMPLETED, "Nope")])]))
    with pytest.raises(ValueError):
        State("Bad", task=ScriptedTask(), children=[leaf("X")])
    with pytest.raises(ValueError):
        Transition(Trigger.ON_CONDITION, ROOT)
    with pytest.raises(ValueError):
        StateTree(State("Root", children=[leaf("A"), leaf("A")]))
