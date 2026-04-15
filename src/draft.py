"""Balanced draft system for distributing players across teams.

Uses a snake draft within each position group, then runs optimization
passes to minimize overall variance between teams.
"""
from __future__ import annotations

import random
from collections import defaultdict
from typing import Sequence

from src.models import (
    Player,
    Team,
    PositionGroup,
    SQUAD_COMPOSITION,
    NUM_TEAMS,
)


def _group_by_position(players: list[Player]) -> dict[PositionGroup, list[Player]]:
    groups: dict[PositionGroup, list[Player]] = defaultdict(list)
    for p in players:
        groups[p.position_group].append(p)
    return groups


def _snake_order(num_teams: int, num_rounds: int) -> list[list[int]]:
    """Generate snake draft order: 0..7, 7..0, 0..7, ..."""
    order = []
    for r in range(num_rounds):
        rng = list(range(num_teams))
        if r % 2 == 1:
            rng.reverse()
        order.append(rng)
    return order


def _team_overall(team_players: list[Player]) -> float:
    if not team_players:
        return 0.0
    return sum(p.overall for p in team_players) / len(team_players)


def _position_group_overall(team_players: list[Player], group: PositionGroup) -> float:
    group_players = [p for p in team_players if p.position_group == group]
    if not group_players:
        return 0.0
    return sum(p.overall for p in group_players) / len(group_players)


def snake_draft(
    players: list[Player],
    num_teams: int = NUM_TEAMS,
    seed: int | None = None,
) -> list[list[Player]]:
    """Distribute players to teams using snake draft per position group.

    Returns a list of lists, where index = team index.
    """
    if seed is not None:
        random.seed(seed)

    groups = _group_by_position(players)
    team_pools: list[list[Player]] = [[] for _ in range(num_teams)]

    for pos_group, count_needed in SQUAD_COMPOSITION.items():
        pool = groups.get(pos_group, [])
        pool.sort(key=lambda p: p.overall, reverse=True)

        total_needed = count_needed * num_teams
        if len(pool) < total_needed:
            raise ValueError(
                f"Not enough {pos_group.value} players: need {total_needed}, have {len(pool)}"
            )

        pool = pool[:total_needed]
        orders = _snake_order(num_teams, count_needed)

        player_idx = 0
        for round_order in orders:
            for team_idx in round_order:
                team_pools[team_idx].append(pool[player_idx])
                player_idx += 1

    return team_pools


def optimize_balance(
    team_pools: list[list[Player]],
    max_iterations: int = 5000,
    seed: int | None = None,
) -> list[list[Player]]:
    """Swap players between teams to reduce overall variance.

    Only swaps players of the same position group.
    """
    if seed is not None:
        random.seed(seed)

    def _variance(pools: list[list[Player]]) -> float:
        avgs = [_team_overall(tp) for tp in pools]
        mean = sum(avgs) / len(avgs)
        return sum((a - mean) ** 2 for a in avgs) / len(avgs)

    def _position_variance(pools: list[list[Player]]) -> float:
        total = 0.0
        for pg in PositionGroup:
            avgs = [_position_group_overall(tp, pg) for tp in pools]
            if not any(avgs):
                continue
            mean = sum(avgs) / len(avgs)
            total += sum((a - mean) ** 2 for a in avgs) / len(avgs)
        return total

    def _combined_score(pools: list[list[Player]]) -> float:
        return _variance(pools) + 0.5 * _position_variance(pools)

    best_score = _combined_score(team_pools)
    num_teams = len(team_pools)

    for _ in range(max_iterations):
        t1, t2 = random.sample(range(num_teams), 2)

        common_groups = set(p.position_group for p in team_pools[t1]) & \
                        set(p.position_group for p in team_pools[t2])
        if not common_groups:
            continue

        pg = random.choice(list(common_groups))
        candidates_t1 = [i for i, p in enumerate(team_pools[t1]) if p.position_group == pg]
        candidates_t2 = [i for i, p in enumerate(team_pools[t2]) if p.position_group == pg]

        if not candidates_t1 or not candidates_t2:
            continue

        idx1 = random.choice(candidates_t1)
        idx2 = random.choice(candidates_t2)

        team_pools[t1][idx1], team_pools[t2][idx2] = team_pools[t2][idx2], team_pools[t1][idx1]

        new_score = _combined_score(team_pools)
        if new_score < best_score:
            best_score = new_score
        else:
            team_pools[t1][idx1], team_pools[t2][idx2] = team_pools[t2][idx2], team_pools[t1][idx1]

    return team_pools


def run_draft(
    players: list[Player],
    team_names: Sequence[tuple[str, str]],
    seed: int | None = 42,
) -> tuple[list[Team], list[Player]]:
    """Run the full draft process.

    Args:
        players: All available players.
        team_names: List of (team_name, owner_name) tuples, one per team.
        seed: Random seed for reproducibility.

    Returns:
        Tuple of (teams, updated_players with team_id assigned).
    """
    if len(team_names) != NUM_TEAMS:
        raise ValueError(f"Expected {NUM_TEAMS} teams, got {len(team_names)}")

    team_pools = snake_draft(players, seed=seed)
    team_pools = optimize_balance(team_pools, seed=seed)

    teams = []
    player_map = {p.id: p for p in players}

    for i, (name, owner) in enumerate(team_names):
        team = Team(id=i + 1, name=name, owner=owner)
        for player in team_pools[i]:
            team.players.append(player.id)
            player_map[player.id].team_id = team.id
        teams.append(team)

    updated_players = list(player_map.values())
    return teams, updated_players


def print_draft_summary(teams: list[Team], players: list[Player]):
    player_map = {p.id: p for p in players}
    print("\n" + "=" * 60)
    print("DRAFT SUMMARY")
    print("=" * 60)

    team_overalls = []
    for team in teams:
        team_players = [player_map[pid] for pid in team.players]
        avg = _team_overall(team_players)
        team_overalls.append(avg)

        print(f"\n{team.name} ({team.owner}) - Avg Overall: {avg:.1f}")
        print("-" * 40)

        for pg in PositionGroup:
            pg_players = sorted(
                [p for p in team_players if p.position_group == pg],
                key=lambda p: p.overall,
                reverse=True,
            )
            pg_avg = _position_group_overall(team_players, pg)
            print(f"  {pg.value} (avg {pg_avg:.1f}):")
            for p in pg_players:
                print(f"    {p.name:<30} {p.position:<4} OVR {p.overall}")

    print("\n" + "=" * 60)
    print("BALANCE CHECK")
    print("=" * 60)
    for team, avg in zip(teams, team_overalls):
        print(f"  {team.name:<20} {avg:.2f}")
    spread = max(team_overalls) - min(team_overalls)
    print(f"\n  Spread: {spread:.2f} (lower is better)")
