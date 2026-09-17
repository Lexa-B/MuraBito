import pytest

from ai.beliefs import CLEAR_DISTANCE, EXPLORE_MIN_DISTANCE, PRIOR_SPEED, RADIUS_FACTOR, BeliefStore, Observation
from hexgrid import all_tiles, distance

DT = 0.1


def obs(tile, name="B", next_tile=None, slots=(0, 3)):
    return Observation(name, frozenset({f"Object.{name}"}), tile, next_tile, tuple(slots), False)


def tick(store, *observations, tiles=(), walls=()):
    store.begin_tick(DT)
    store.observe_tiles(tiles, walls)
    for o in observations:
        store.observe_object(o)
    return store.apply_negative_evidence()


def test_placeholder_constants():
    assert (CLEAR_DISTANCE, EXPLORE_MIN_DISTANCE) == (2.0, 3)


def test_never_seen_tiles_are_walkable_and_known_walls_are_not():
    store = BeliefStore()
    assert store.is_walkable((3, 3))
    tick(store, tiles=[(3, 3)], walls=[(3, 3)])
    assert not store.is_walkable((3, 3))
    assert not store.is_walkable((13, 0))


def test_point_ghosts_block_and_region_ghosts_do_not():
    store = BeliefStore()
    tick(store, obs((0, 6)))
    assert not store.is_walkable((0, 6))
    store.beliefs["B"].radius_floor = 6.0  # REGION
    assert store.is_walkable((0, 6))


def test_next_tile_blocks_only_while_the_object_is_seen():
    store = BeliefStore()
    tick(store, obs((0, 6), next_tile=(1, 6)))
    assert not store.is_walkable((1, 6))
    tick(store)  # not seen this tick: the next tile is stale
    assert store.is_walkable((1, 6))
    assert not store.is_walkable((0, 6))  # the datum is still a POINT ghost


def test_walkable_tiles_matches_is_walkable():
    store = BeliefStore()
    tick(store, obs((0, 6), next_tile=(1, 6)), tiles=[(4, -4)], walls=[(4, -4)])
    walkable = store.walkable_tiles()
    assert len(walkable) == len(all_tiles()) - 3
    assert all(store.is_walkable(t) for t in walkable)


def region_belief(store, datum=(-3, 8), unseen_seconds=10.0):
    """A REGION belief about B, last seen at `datum` (S zone), not seen since."""
    tick(store, obs(datum))
    for _ in range(round(unseen_seconds / DT)):
        tick(store)
    return datum


def test_search_area_is_the_radius_around_the_ghost_in_the_zone():
    store = BeliefStore()
    datum = region_belief(store)
    radius = store.uncertainty_radius("B")
    assert radius == pytest.approx(PRIOR_SPEED * RADIUS_FACTOR * 10.0)  # 6.0
    area = store.search_area("B")
    from zones import zone_of

    expected = {t for t in all_tiles() if distance(t, datum) <= radius and zone_of(t) == "S"}
    assert set(area) == expected
    assert area[0] == datum
    assert [distance(t, datum) for t in area] == sorted(distance(t, datum) for t in area)


def test_search_area_excludes_known_walls():
    store = BeliefStore()
    datum = region_belief(store)
    store.known_walls.add((datum[0] + 1, datum[1]))
    assert (datum[0] + 1, datum[1]) not in store.search_area("B")


def test_tiles_seen_after_the_sighting_are_cleared_until_they_expire():
    store = BeliefStore()
    datum = region_belief(store)
    tick(store, tiles=[datum])  # seen empty now
    assert store.is_cleared("B", datum)
    assert datum not in store.search_area("B")
    expiry = CLEAR_DISTANCE / (store.speed("B") * RADIUS_FACTOR)  # about 3.3 s
    for _ in range(round(expiry / DT) + 1):
        tick(store)
    assert not store.is_cleared("B", datum)


def test_tiles_seen_before_the_sighting_are_not_cleared():
    store = BeliefStore()
    tick(store, tiles=[(-2, 8)])
    region_belief(store)
    assert not store.is_cleared("B", (-2, 8))


def test_frontier_prefers_never_seen_tiles_at_least_three_away():
    store = BeliefStore()
    actor = (0, 0)
    tick(store, tiles=[])
    # Nothing has been seen, so tiles at distance 1 and 2 are candidates too, but they're skipped.
    assert store.frontier(actor) == min(t for t in all_tiles() if distance(t, actor) == EXPLORE_MIN_DISTANCE)


def test_frontier_falls_back_to_near_never_seen_tiles_then_the_oldest_seen():
    store = BeliefStore()
    actor = (0, 0)
    far = [t for t in all_tiles() if distance(t, actor) >= 3]
    tick(store, tiles=far)  # everything far is seen at t=0.1
    target = store.frontier(actor)
    assert 1 <= distance(target, actor) <= 2
    tick(store, tiles=[t for t in all_tiles() if distance(t, actor) <= 2 and t != (1, 0)])
    assert store.frontier(actor) == (1, 0)
    tick(store, tiles=[(1, 0)])  # now every tile has been seen
    tick(store, tiles=[t for t in all_tiles() if t != (5, -5)])  # (5, -5) is the oldest, seen at t=0.1
    assert store.frontier(actor) == (5, -5)


def test_frontier_never_picks_a_tile_in_view():
    store = BeliefStore()
    everything = all_tiles()
    tick(store, tiles=everything)
    assert store.frontier((0, 0)) is None
