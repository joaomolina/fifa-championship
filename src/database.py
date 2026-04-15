from __future__ import annotations

import json
from pathlib import Path
from typing import TypeVar, Type

from pydantic import BaseModel

from src.models import (
    Player,
    Team,
    Match,
    Transfer,
    TransferWindow,
    TournamentState,
)

T = TypeVar("T", bound=BaseModel)

DATA_DIR = Path(__file__).resolve().parent.parent / "docs" / "data"


def _ensure_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _path(name: str) -> Path:
    return DATA_DIR / f"{name}.json"


def _save(name: str, data: list | dict):
    _ensure_dir()
    with open(_path(name), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _load_raw(name: str) -> list | dict:
    path = _path(name)
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_list(name: str, model: Type[T]) -> list[T]:
    raw = _load_raw(name)
    if not isinstance(raw, list):
        return []
    return [model.model_validate(item) for item in raw]


def _save_list(name: str, items: list[BaseModel]):
    _save(name, [item.model_dump() for item in items])


# --- Players ---

def load_players() -> list[Player]:
    return _load_list("players", Player)


def save_players(players: list[Player]):
    _save_list("players", players)


def get_player(player_id: int) -> Player | None:
    for p in load_players():
        if p.id == player_id:
            return p
    return None


# --- Teams ---

def load_teams() -> list[Team]:
    return _load_list("teams", Team)


def save_teams(teams: list[Team]):
    _save_list("teams", teams)


def get_team(team_id: int) -> Team | None:
    for t in load_teams():
        if t.id == team_id:
            return t
    return None


# --- Matches ---

def load_matches() -> list[Match]:
    return _load_list("matches", Match)


def save_matches(matches: list[Match]):
    _save_list("matches", matches)


def get_match(match_id: int) -> Match | None:
    for m in load_matches():
        if m.id == match_id:
            return m
    return None


def update_match(match: Match):
    matches = load_matches()
    for i, m in enumerate(matches):
        if m.id == match.id:
            matches[i] = match
            break
    save_matches(matches)


# --- Transfers ---

def load_transfers() -> list[Transfer]:
    return _load_list("transfers", Transfer)


def save_transfers(transfers: list[Transfer]):
    _save_list("transfers", transfers)


# --- Transfer Windows ---

def load_transfer_windows() -> list[TransferWindow]:
    return _load_list("transfer_windows", TransferWindow)


def save_transfer_windows(windows: list[TransferWindow]):
    _save_list("transfer_windows", windows)


# --- Tournament State ---

def load_tournament_state() -> TournamentState:
    raw = _load_raw("tournament_state")
    if not raw or not isinstance(raw, dict):
        return TournamentState()
    return TournamentState.model_validate(raw)


def save_tournament_state(state: TournamentState):
    _save("tournament_state", state.model_dump())
