import pytest

from ai.beliefs import (
    LOST,
    LOST_RADIUS,
    POINT,
    POINT_RADIUS,
    PRIOR_SECONDS,
    PRIOR_SPEED,
    RADIUS_FACTOR,
    REGION,
    BeliefStore,
    Observation,
)

DT = 0.1


def obs(tile, name="B", next_tile=None, in_use=False, slots=(0, 3), tags=None):
    return Observation(name, frozenset(tags or {f"Object.{name}"}), tile, next_tile, tuple(slots), in_use)


def tick(store, *observations, tiles=(), walls=()):
    """One perception pass: begin the tick, see `tiles`, then the given observations."""
    store.begin_tick(DT)
    store.observe_tiles(tiles, walls)
    for o in observations:
        store.observe_object(o)
    return store.apply_negative_evidence()


def unseen_for(store, seconds, tiles=()):
    for _ in range(round(seconds / DT)):
        tick(store, tiles=tiles)


def test_placeholder_constants():
    assert (PRIOR_SPEED, PRIOR_SECONDS, RADIUS_FACTOR, POINT_RADIUS, LOST_RADIUS) == (0.3, 10.0, 2.0, 5.0, 13.0)


def test_first_sighting_creates_a_point_belief():
    store = BeliefStore()
    tick(store, obs((-2, 5), next_tile=(-1, 5)))
    belief = store.beliefs["B"]
    assert (belief.datum_tile, belief.datum_next_tile, belief.datum_zone) == ((-2, 5), (-1, 5), "S")
    assert belief.datum_time == pytest.approx(DT)
    assert (belief.observed_seconds, belief.steps, belief.course) == (0.0, 0, None)
    assert store.seen_now == {"B"}
    assert store.uncertainty_radius("B") == 0.0
    assert store.level("B") == POINT
    assert store.confidence("B") == 1.0


def test_speed_is_the_prior_before_any_watching():
    store = BeliefStore()
    tick(store, obs((3, 2)))
    assert store.speed("B") == pytest.approx(PRIOR_SPEED)


def test_speed_blends_toward_the_watched_rate():
    store = BeliefStore()
    tick(store, obs((0, 3)))
    for _ in range(99):  # 9.9 s watched, standing still
        tick(store, obs((0, 3)))
    tick(store, obs((1, 3)))  # one step at 10.0 s
    belief = store.beliefs["B"]
    assert belief.observed_seconds == pytest.approx(10.0)
    assert (belief.steps, belief.course) == (1, 0)
    weight = 10.0 / (10.0 + PRIOR_SECONDS)
    assert store.speed("B") == pytest.approx((1 - weight) * PRIOR_SPEED + weight * 0.1)


def test_in_use_ticks_add_neither_seconds_nor_steps():
    store = BeliefStore()
    tick(store, obs((0, 3)))
    for _ in range(10):
        tick(store, obs((0, 3), in_use=True))
    tick(store, obs((1, 3), in_use=True))
    belief = store.beliefs["B"]
    assert (belief.observed_seconds, belief.steps, belief.course) == (0.0, 0, None)


def test_a_step_seen_after_a_gap_is_not_counted():
    store = BeliefStore()
    tick(store, obs((0, 3)))
    tick(store)  # not seen
    tick(store, obs((1, 3)))
    belief = store.beliefs["B"]
    assert (belief.observed_seconds, belief.steps, belief.course) == (0.0, 0, None)
    assert belief.datum_tile == (1, 3)


def test_course_is_the_last_watched_step():
    store = BeliefStore()
    tick(store, obs((0, 3)))
    tick(store, obs((1, 3)))  # E, direction 0
    tick(store, obs((1, 4)))  # direction 5
    assert (store.beliefs["B"].steps, store.beliefs["B"].course) == (2, 5)


def test_radius_grows_with_speed_and_time_and_sets_the_level():
    store = BeliefStore()
    tick(store, obs((0, 6)))
    unseen_for(store, 8.0)
    assert store.uncertainty_radius("B") == pytest.approx(PRIOR_SPEED * RADIUS_FACTOR * 8.0)  # 4.8
    assert store.level("B") == POINT
    unseen_for(store, 1.0)
    assert store.level("B") == REGION  # 5.4
    unseen_for(store, 13.0)
    assert store.level("B") == LOST  # 13.2
    assert store.confidence("B") == 0.0


def test_level_thresholds_are_inclusive():
    store = BeliefStore()
    tick(store, obs((0, 6)))
    belief = store.beliefs["B"]
    belief.datum_time = store.now - POINT_RADIUS / (PRIOR_SPEED * RADIUS_FACTOR)
    assert store.uncertainty_radius("B") == pytest.approx(POINT_RADIUS)
    belief.radius_floor = POINT_RADIUS
    belief.datum_time = store.now
    assert store.level("B") == POINT
    belief.radius_floor = LOST_RADIUS
    assert store.level("B") == REGION
    belief.radius_floor = LOST_RADIUS + 0.001
    assert store.level("B") == LOST


def test_confidence_falls_linearly_with_the_radius():
    store = BeliefStore()
    tick(store, obs((0, 6)))
    store.beliefs["B"].radius_floor = LOST_RADIUS / 2
    assert store.confidence("B") == pytest.approx(0.5)


def test_ghost_stays_at_the_datum_without_a_course():
    store = BeliefStore()
    tick(store, obs((0, 6)))
    unseen_for(store, 20.0)
    assert store.ghost_tile("B") == (0, 6)


def watched_moving_east(store, start=(-6, 8), steps=3):
    """Watch B step east `steps` times, one tick apart."""
    q, r = start
    for i in range(steps + 1):
        tick(store, obs((q + i, r)))
    return (q + steps, r)


def test_ghost_dead_reckons_along_the_course():
    store = BeliefStore()
    datum = watched_moving_east(store)
    speed = store.speed("B")
    seconds = 2.0 / speed + 0.05  # just past two tiles of travel
    unseen_for(store, seconds)
    assert store.ghost_tile("B") == (datum[0] + 2, datum[1])


def test_ghost_stops_at_a_known_wall():
    store = BeliefStore()
    datum = watched_moving_east(store)
    store.known_walls.add((datum[0] + 2, datum[1]))
    unseen_for(store, 20.0)
    assert store.ghost_tile("B") == (datum[0] + 1, datum[1])


def test_ghost_stops_at_the_zone_edge():
    store = BeliefStore()
    watched_moving_east(store, start=(-6, 3))  # S zone; east along r == 3, (3, 3) is NE
    unseen_for(store, 60.0)
    assert store.ghost_tile("B") == (2, 3)


def test_ghost_stops_at_the_map_edge():
    store = BeliefStore()
    tick(store, obs((0, 10)))
    tick(store, obs((0, 11)))  # moving direction 5 (down), S zone
    unseen_for(store, 60.0)
    assert store.ghost_tile("B") == (0, 12)


def test_slot_tiles_ride_on_the_ghost_and_face_the_object():
    store = BeliefStore()
    tick(store, obs((0, 6), slots=(0, 3)))
    assert store.slot_tiles("B") == [(0, (1, 6)), (1, (-1, 6))]
    assert store.slot_facing("B", 0) == 3
    assert store.slot_facing("B", 1) == 0


def test_negative_evidence_retracts_a_point_belief_in_view():
    store = BeliefStore()
    tick(store, obs((0, 6)))
    retracted = tick(store, tiles=[(0, 6)])  # the ghost tile is in view and B is not seen
    assert retracted == [("B", (0, 6))]
    assert store.level("B") == REGION
    assert tick(store, tiles=[(0, 6)]) == []  # already REGION: no second retraction


def test_absence_outside_the_view_retracts_nothing():
    store = BeliefStore()
    tick(store, obs((0, 6)))
    assert tick(store, tiles=[(0, 5), (1, 6)]) == []
    assert store.level("B") == POINT


def test_a_sighting_clears_the_retraction():
    store = BeliefStore()
    tick(store, obs((0, 6)))
    tick(store, tiles=[(0, 6)])
    assert store.level("B") == REGION
    tick(store, obs((2, 6)))
    assert store.beliefs["B"].radius_floor == 0.0
    assert store.level("B") == POINT


def test_observe_tiles_records_time_and_walls():
    store = BeliefStore()
    tick(store, tiles=[(0, 1), (0, 2)], walls=[(0, 2)])
    assert store.visible_now == {(0, 1), (0, 2)}
    assert store.last_seen == {(0, 1): pytest.approx(DT), (0, 2): pytest.approx(DT)}
    assert store.known_walls == {(0, 2)}
    tick(store)
    assert store.visible_now == set() and store.known_walls == {(0, 2)}


def test_matching_filters_by_every_tag():
    store = BeliefStore()
    tick(store, obs((0, 6), name="B"), obs((-6, 0), name="A"))
    assert store.matching(set()) == ["A", "B"]
    assert store.matching({"Object.B"}) == ["B"]
    assert store.matching({"Object.B", "Other"}) == []
