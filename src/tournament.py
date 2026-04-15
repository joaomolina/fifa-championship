"""Tournament logic: group stage scheduling, standings, and bracket management."""
from __future__ import annotations

from itertools import combinations
from typing import Optional

from src.models import (
    Match,
    MatchEvent,
    StandingsRow,
    Team,
    TournamentPhase,
    TournamentState,
    TransferWindow,
)
from src import database as db


def generate_group_matches(teams: list[Team]) -> list[Match]:
    """Generate round-robin matches for the group stage."""
    matches = []
    match_id = 1

    team_ids = [t.id for t in teams]
    pairings = list(combinations(team_ids, 2))

    num_teams = len(team_ids)
    rounds = _round_robin_schedule(team_ids)

    for match_day, round_matches in enumerate(rounds, start=1):
        for home_id, away_id in round_matches:
            matches.append(Match(
                id=match_id,
                phase="group",
                match_day=match_day,
                home_team_id=home_id,
                away_team_id=away_id,
            ))
            match_id += 1

    return matches


def _round_robin_schedule(team_ids: list[int]) -> list[list[tuple[int, int]]]:
    """Generate a balanced round-robin schedule.

    Each round has n/2 matches. Total of n-1 rounds for n teams.
    """
    ids = list(team_ids)
    n = len(ids)
    if n % 2 == 1:
        ids.append(-1)  # bye
        n += 1

    rounds = []
    fixed = ids[0]
    rotating = ids[1:]

    for _ in range(n - 1):
        round_matches = []
        current = [fixed] + rotating
        for i in range(n // 2):
            home = current[i]
            away = current[n - 1 - i]
            if home != -1 and away != -1:
                round_matches.append((home, away))
        rounds.append(round_matches)
        rotating = [rotating[-1]] + rotating[:-1]

    return rounds


def compute_standings(matches: list[Match], teams: list[Team]) -> list[StandingsRow]:
    """Compute group stage standings from match results."""
    team_map = {t.id: t for t in teams}
    rows: dict[int, StandingsRow] = {}

    for t in teams:
        rows[t.id] = StandingsRow(
            team_id=t.id,
            team_name=t.name,
            owner=t.owner,
        )

    for m in matches:
        if not m.played or m.phase != "group":
            continue

        home = rows[m.home_team_id]
        away = rows[m.away_team_id]

        home.played += 1
        away.played += 1
        home.goals_for += m.home_score or 0
        home.goals_against += m.away_score or 0
        away.goals_for += m.away_score or 0
        away.goals_against += m.home_score or 0

        if m.home_score > m.away_score:
            home.wins += 1
            home.points += 3
            away.losses += 1
        elif m.home_score < m.away_score:
            away.wins += 1
            away.points += 3
            home.losses += 1
        else:
            home.draws += 1
            away.draws += 1
            home.points += 1
            away.points += 1

    for r in rows.values():
        r.goal_difference = r.goals_for - r.goals_against

    sorted_rows = sorted(
        rows.values(),
        key=lambda r: (r.points, r.goal_difference, r.goals_for),
        reverse=True,
    )

    for i, r in enumerate(sorted_rows, start=1):
        r.position = i

    return sorted_rows


def get_top_scorers(matches: list[Match], players=None, limit: int = 10) -> list[dict]:
    """Get top scorers from all played matches."""
    goals: dict[int, dict] = {}

    for m in matches:
        if not m.played:
            continue
        for evt in m.events:
            if evt.type == "goal":
                if evt.player_id not in goals:
                    goals[evt.player_id] = {
                        "player_id": evt.player_id,
                        "player_name": evt.player_name,
                        "team_id": evt.team_id,
                        "goals": 0,
                    }
                goals[evt.player_id]["goals"] += 1

    sorted_scorers = sorted(goals.values(), key=lambda x: x["goals"], reverse=True)
    return sorted_scorers[:limit]


def get_top_assisters(matches: list[Match], limit: int = 10) -> list[dict]:
    """Get top assist providers from all played matches."""
    assists: dict[int, dict] = {}

    for m in matches:
        if not m.played:
            continue
        for evt in m.events:
            if evt.type == "assist":
                if evt.player_id not in assists:
                    assists[evt.player_id] = {
                        "player_id": evt.player_id,
                        "player_name": evt.player_name,
                        "team_id": evt.team_id,
                        "assists": 0,
                    }
                assists[evt.player_id]["assists"] += 1

    sorted_assisters = sorted(assists.values(), key=lambda x: x["assists"], reverse=True)
    return sorted_assisters[:limit]


def generate_transfer_windows(num_match_days: int) -> list[TransferWindow]:
    """Generate transfer windows: before start, every 4 match days, and before bracket."""
    windows = [
        TransferWindow(number=1, phase="group", after_match_day=0, max_trades=3),
    ]

    window_num = 2
    for md in range(4, num_match_days + 1, 4):
        windows.append(TransferWindow(
            number=window_num,
            phase="group",
            after_match_day=md,
            max_trades=3,
        ))
        window_num += 1

    windows.append(TransferWindow(
        number=window_num,
        phase="bracket",
        after_match_day=num_match_days,
        max_trades=3,
    ))

    return windows


# --- Bracket Logic ---

BRACKET_PHASES = [
    "quarter_1v4",
    "quarter_2v3",
    "quarter_5v6",
    "upper_semi",
    "lower_r1",
    "lower_r2",
    "lower_final",
    "grand_final",
]


def generate_bracket_matches(standings: list[StandingsRow], start_id: int) -> list[Match]:
    """Generate initial bracket matches from group standings."""
    if len(standings) < 6:
        return []

    pos = {r.position: r.team_id for r in standings}

    matches = [
        Match(id=start_id, phase="quarter_1v4", home_team_id=pos[1], away_team_id=pos[4]),
        Match(id=start_id + 1, phase="quarter_2v3", home_team_id=pos[2], away_team_id=pos[3]),
        Match(id=start_id + 2, phase="quarter_5v6", home_team_id=pos[5], away_team_id=pos[6]),
    ]
    return matches


def advance_bracket(matches: list[Match], standings: list[StandingsRow]) -> list[Match]:
    """Check bracket results and generate next round matches as needed."""
    bracket_matches = {m.phase: m for m in matches if m.phase != "group"}
    new_matches = []
    next_id = max(m.id for m in matches) + 1

    pos_map = {r.team_id: r.position for r in standings}

    def _winner(m: Match) -> Optional[int]:
        if not m.played:
            return None
        if m.home_score > m.away_score:
            return m.home_team_id
        if m.away_score > m.home_score:
            return m.away_team_id
        home_pos = pos_map.get(m.home_team_id, 99)
        away_pos = pos_map.get(m.away_team_id, 99)
        return m.home_team_id if home_pos < away_pos else m.away_team_id

    def _loser(m: Match) -> Optional[int]:
        w = _winner(m)
        if w is None:
            return None
        return m.away_team_id if w == m.home_team_id else m.home_team_id

    q14 = bracket_matches.get("quarter_1v4")
    q23 = bracket_matches.get("quarter_2v3")
    q56 = bracket_matches.get("quarter_5v6")

    if q14 and q23 and _winner(q14) and _winner(q23) and "upper_semi" not in bracket_matches:
        new_matches.append(Match(
            id=next_id, phase="upper_semi",
            home_team_id=_winner(q14), away_team_id=_winner(q23),
        ))
        next_id += 1

    if q56 and q14 and _winner(q56) and _loser(q14) and "lower_r1" not in bracket_matches:
        new_matches.append(Match(
            id=next_id, phase="lower_r1",
            home_team_id=_winner(q56), away_team_id=_loser(q14),
        ))
        next_id += 1

    lower_r1 = bracket_matches.get("lower_r1")
    if lower_r1 and q23 and _winner(lower_r1) and _loser(q23) and "lower_r2" not in bracket_matches:
        new_matches.append(Match(
            id=next_id, phase="lower_r2",
            home_team_id=_winner(lower_r1), away_team_id=_loser(q23),
        ))
        next_id += 1

    upper_semi = bracket_matches.get("upper_semi")
    lower_r2 = bracket_matches.get("lower_r2")
    if upper_semi and lower_r2 and _loser(upper_semi) and _winner(lower_r2) and "lower_final" not in bracket_matches:
        new_matches.append(Match(
            id=next_id, phase="lower_final",
            home_team_id=_loser(upper_semi), away_team_id=_winner(lower_r2),
        ))
        next_id += 1

    lower_final = bracket_matches.get("lower_final")
    if upper_semi and lower_final and _winner(upper_semi) and _winner(lower_final) and "grand_final" not in bracket_matches:
        new_matches.append(Match(
            id=next_id, phase="grand_final",
            home_team_id=_winner(upper_semi), away_team_id=_winner(lower_final),
        ))
        next_id += 1

    return new_matches


def get_bracket_data(matches: list[Match], standings: list[StandingsRow]) -> dict:
    """Build bracket data structure for visualization."""
    bracket = {}
    pos_map = {r.team_id: r.position for r in standings}
    team_map = {t.id: t for t in db.load_teams()}

    for phase in BRACKET_PHASES:
        m = next((m for m in matches if m.phase == phase), None)
        if m:
            def _winner(m):
                if not m.played:
                    return None
                if m.home_score > m.away_score:
                    return m.home_team_id
                if m.away_score > m.home_score:
                    return m.away_team_id
                hp = pos_map.get(m.home_team_id, 99)
                ap = pos_map.get(m.away_team_id, 99)
                return m.home_team_id if hp < ap else m.away_team_id

            bracket[phase] = {
                "match": m,
                "home_team": team_map.get(m.home_team_id),
                "away_team": team_map.get(m.away_team_id),
                "winner_id": _winner(m),
            }
        else:
            bracket[phase] = None

    return bracket


PHASE_LABELS = {
    "quarter_1v4": "Quartas: 1o vs 4o",
    "quarter_2v3": "Quartas: 2o vs 3o",
    "quarter_5v6": "Quartas: 5o vs 6o",
    "upper_semi": "Semifinal (chave superior)",
    "lower_r1": "Chave inferior — 1ª rodada",
    "lower_r2": "Chave inferior — 2ª rodada",
    "lower_final": "Final da chave inferior",
    "grand_final": "Grande final",
}
