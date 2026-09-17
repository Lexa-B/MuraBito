"""A small StateTree engine modeled on UE5's StateTree: hierarchical states with
enter conditions, leaf tasks, transitions, and evaluators writing to a shared context."""

from collections import deque
from enum import Enum

ROOT = "ROOT"


class Status(Enum):
    RUNNING = "Running"
    SUCCEEDED = "Succeeded"
    FAILED = "Failed"


class Trigger(Enum):
    ON_COMPLETED = "OnCompleted"
    ON_FAILED = "OnFailed"
    ON_CONDITION = "OnCondition"


class Mode(Enum):
    ALL = "all"
    ANY = "any"


class Condition:
    def __init__(self, name, test):
        self.name = name
        self.test = test
        self.last_result: bool | None = None  # read by the brain panel

    def evaluate(self, ctx) -> bool:
        self.last_result = bool(self.test(ctx))
        return self.last_result


class Task:
    def enter(self, ctx):
        pass

    def tick(self, ctx, dt) -> Status:
        return Status.SUCCEEDED

    def exit(self, ctx):
        pass


class Evaluator:
    def tick(self, ctx, dt):
        pass


class Transition:
    def __init__(self, trigger: Trigger, target: str, condition: Condition | None = None):
        if (trigger is Trigger.ON_CONDITION) != (condition is not None):
            raise ValueError("ON_CONDITION transitions need a condition; other triggers must not have one")
        self.trigger = trigger
        self.target = target
        self.condition = condition

    def matches(self, status: Status, ctx) -> bool:
        if self.trigger is Trigger.ON_CONDITION:
            return self.condition.evaluate(ctx)
        if self.trigger is Trigger.ON_COMPLETED:
            return status is Status.SUCCEEDED
        return status is Status.FAILED

    def describe(self, status: Status) -> str:
        return self.condition.name if self.condition is not None else status.value


class State:
    def __init__(self, name, children=(), conditions=(), mode=Mode.ALL, task=None, transitions=(), on_exit=None):
        if task is not None and children:
            raise ValueError(f"{name}: only leaf states can have a task")
        self.name = name
        self.children = list(children)
        self.conditions = list(conditions)
        self.mode = mode
        self.task = task
        self.transitions = list(transitions)
        self.on_exit = on_exit
        self.parent: State | None = None
        for child in self.children:
            child.parent = self

    @property
    def path(self) -> str:
        names = []
        state = self
        while state.parent is not None:
            names.append(state.name)
            state = state.parent
        return "/".join(reversed(names))

    def conditions_pass(self, ctx) -> bool:
        # Evaluate every condition (no short-circuit) so the panel can mark each one.
        results = [condition.evaluate(ctx) for condition in self.conditions]
        if not results:
            return True
        return all(results) if self.mode is Mode.ALL else any(results)

    def is_at_or_below(self, other: "State") -> bool:
        state = self
        while state is not None:
            if state is other:
                return True
            state = state.parent
        return False


class StateTree:
    def __init__(self, root: State, evaluators=(), log_size: int = 200):
        self.root = root
        self.evaluators = list(evaluators)
        self.active: list[State] = []
        self.last_status: Status | None = None
        self.time = 0.0
        self.log: deque[tuple[float, str]] = deque(maxlen=log_size)
        self._idle_logged = False
        self._states: dict[str, State] = {}
        for state, _ in self.walk():
            if state.path in self._states:
                raise ValueError(f"duplicate state path: {state.path}")
            self._states[state.path] = state
        for state, _ in self.walk():
            for transition in state.transitions:
                self.find(transition.target)

    @property
    def leaf(self) -> State | None:
        return self.active[-1] if self.active else None

    def write_log(self, text: str) -> None:
        self.log.append((self.time, text))

    def find(self, path: str) -> State:
        if path == ROOT:
            return self.root
        if path not in self._states or path == "":
            raise KeyError(f"unknown state path: {path!r}")
        return self._states[path]

    def walk(self):
        stack = [(self.root, 0)]
        while stack:
            state, depth = stack.pop()
            yield state, depth
            stack.extend((child, depth + 1) for child in reversed(state.children))

    def select(self, state: State, ctx) -> list[State] | None:
        if state is not self.root and not state.conditions_pass(ctx):
            return None
        if not state.children:
            return None if state is self.root else [state]
        for child in state.children:
            selected = self.select(child, ctx)
            if selected is not None:
                return selected if state is self.root else [state] + selected
        return None

    def tick(self, ctx, dt: float) -> None:
        self.time += dt
        for evaluator in self.evaluators:
            evaluator.tick(ctx, dt)

        if not self.active:
            self._activate(self._select_from(self.root, ctx), ctx)
            if not self.active:
                return

        leaf = self.leaf
        status = leaf.task.tick(ctx, dt) if leaf.task is not None else Status.SUCCEEDED
        self.last_status = status

        transition = self._find_transition(status, ctx)
        if transition is not None:
            self.write_log(f"{leaf.path} -> {transition.describe(status)}")
            self._take(self.find(transition.target), ctx)
        elif status is not Status.RUNNING:
            self.write_log(f"{leaf.path} -> {status.value} (no transition, back to ROOT)")
            self._take(self.root, ctx)

    def reset(self, ctx) -> None:
        if self.active:
            leaf = self.leaf
            if leaf.task is not None:
                leaf.task.exit(ctx)
            for state in reversed(self.active):
                if state.on_exit is not None:
                    state.on_exit(ctx)
        self.active = []
        self.last_status = None

    def _find_transition(self, status: Status, ctx) -> Transition | None:
        for state in [*reversed(self.active), self.root]:
            for transition in state.transitions:
                if transition.matches(status, ctx):
                    return transition
        return None

    def _ancestors(self, state: State) -> list[State]:
        """States between root and `state`, top-down, excluding both."""
        chain = []
        parent = state.parent
        while parent is not None and parent is not self.root:
            chain.append(parent)
            parent = parent.parent
        return chain[::-1]

    def _select_from(self, target: State, ctx) -> list[State]:
        selected = self.select(target, ctx)
        if selected is not None:
            return self._ancestors(target) + selected
        if target is not self.root:
            self.write_log(f"{target.path} not selectable, reselecting from ROOT")
            return self.select(self.root, ctx) or []
        return []

    def _take(self, target: State, ctx) -> None:
        old = self.active
        if old[-1].task is not None:
            old[-1].task.exit(ctx)
        new = self._select_from(target, ctx)
        for state in reversed(old):
            # Targeting a state re-enters it, so everything at or below the target exits.
            if state not in new or state.is_at_or_below(target):
                if state.on_exit is not None:
                    state.on_exit(ctx)
        self.last_status = None
        self.active = []
        self._activate(new, ctx)

    def _activate(self, path: list[State], ctx) -> None:
        self.active = path
        if path:
            self._idle_logged = False
            if path[-1].task is not None:
                path[-1].task.enter(ctx)
            self.write_log(f"select -> {path[-1].path}")
        elif not self._idle_logged:
            self._idle_logged = True
            self.write_log("error: no state selectable, idle")
