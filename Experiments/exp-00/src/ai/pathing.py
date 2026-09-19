"""A* on the hex grid."""

import heapq

from hexgrid import Tile, distance, neighbors


def astar(world, start: Tile, goals) -> list[Tile] | None:
    """Shortest path from start to the cheapest-to-reach goal, inclusive of both ends."""
    goals = set(goals)
    if not goals:
        return None

    def heuristic(tile: Tile) -> int:
        return min(distance(tile, goal) for goal in goals)

    came_from: dict[Tile, Tile | None] = {start: None}
    cost: dict[Tile, int] = {start: 0}
    counter = 0  # tie-breaker so the heap never compares tiles
    frontier = [(heuristic(start), 0, counter, start)]

    while frontier:
        _, g, _, current = heapq.heappop(frontier)
        if g > cost[current]:
            continue
        if current in goals:
            path = [current]
            while came_from[path[-1]] is not None:
                path.append(came_from[path[-1]])
            return path[::-1]
        for nxt in neighbors(current, world.radius):
            if not world.is_walkable(nxt):
                continue
            new_cost = g + 1
            if new_cost < cost.get(nxt, new_cost + 1):
                cost[nxt] = new_cost
                came_from[nxt] = current
                counter += 1
                heapq.heappush(frontier, (new_cost + heuristic(nxt), new_cost, counter, nxt))
    return None
