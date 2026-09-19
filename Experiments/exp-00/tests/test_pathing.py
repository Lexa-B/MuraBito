from ai.pathing import astar
from hexgrid import DIRECTIONS, add, distance
from world import World


def assert_connected(path):
    for a, b in zip(path, path[1:]):
        assert distance(a, b) == 1


def test_straight_path_on_open_map():
    path = astar(World(), (0, 0), {(5, 0)})
    assert path[0] == (0, 0) and path[-1] == (5, 0)
    assert len(path) == distance((0, 0), (5, 0)) + 1
    assert_connected(path)


def test_path_routes_around_a_wall_segment():
    wall = [(0, r) for r in range(-4, 5)]
    world = World(walls=wall)
    path = astar(world, (-3, 0), {(3, 0)})
    assert path is not None
    assert not set(path) & set(wall)
    assert len(path) - 1 > distance((-3, 0), (3, 0))
    assert_connected(path)


def test_unreachable_goal_returns_none():
    goal = (5, 0)
    world = World(walls=[add(goal, d) for d in DIRECTIONS])
    assert astar(world, (0, 0), {goal}) is None


def test_multiple_goals_path_ends_at_nearest():
    path = astar(World(), (0, 0), {(3, 0), (-8, 0)})
    assert path[-1] == (3, 0)


def test_start_already_at_goal():
    assert astar(World(), (2, 2), {(2, 2)}) == [(2, 2)]


def test_empty_goals_returns_none():
    assert astar(World(), (0, 0), set()) is None
