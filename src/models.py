from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class PositionGroup(str, Enum):
    GK = "GK"
    DEF = "DEF"
    MID = "MID"
    FWD = "FWD"


POSITION_GROUP_MAP = {
    "GK": PositionGroup.GK,
    "CB": PositionGroup.DEF,
    "LB": PositionGroup.DEF,
    "RB": PositionGroup.DEF,
    "LWB": PositionGroup.DEF,
    "RWB": PositionGroup.DEF,
    "CDM": PositionGroup.MID,
    "CM": PositionGroup.MID,
    "CAM": PositionGroup.MID,
    "LM": PositionGroup.MID,
    "RM": PositionGroup.MID,
    "ST": PositionGroup.FWD,
    "CF": PositionGroup.FWD,
    "LW": PositionGroup.FWD,
    "RW": PositionGroup.FWD,
    "LF": PositionGroup.FWD,
    "RF": PositionGroup.FWD,
}

SQUAD_COMPOSITION = {
    PositionGroup.GK: 3,
    PositionGroup.DEF: 8,
    PositionGroup.MID: 8,
    PositionGroup.FWD: 7,
}

SQUAD_SIZE = sum(SQUAD_COMPOSITION.values())  # 26
NUM_TEAMS = 8

SUB_POSITION_MINIMUMS: dict["PositionGroup", dict[str, int]] = {
    PositionGroup.DEF: {"CB": 1, "LB": 1, "RB": 1},
    PositionGroup.MID: {"CDM": 1, "CM": 1, "CAM": 1, "LM": 1, "RM": 1},
    PositionGroup.FWD: {"ST": 1, "LW": 1, "RW": 1},
}

TEAM_FLAGS = {
    "Franca": "\U0001f1eb\U0001f1f7",
    "Espanha": "\U0001f1ea\U0001f1f8",
    "Alemanha": "\U0001f1e9\U0001f1ea",
    "Argentina": "\U0001f1e6\U0001f1f7",
    "Portugal": "\U0001f1f5\U0001f1f9",
    "Inglaterra": "\U0001f3f4\U000e0067\U000e0062\U000e0065\U000e006e\U000e0067\U000e007f",
    "Mexico": "\U0001f1f2\U0001f1fd",
    "USA": "\U0001f1fa\U0001f1f8",
}

TEAM_COLORS = {
    "Franca": "#002395",
    "Espanha": "#C8102E",
    "Alemanha": "#000000",
    "Argentina": "#75AADB",
    "Portugal": "#006600",
    "Inglaterra": "#CF081F",
    "Mexico": "#006847",
    "USA": "#002868",
}


class Player(BaseModel):
    id: int
    name: str
    overall: int
    position: str
    position_group: PositionGroup
    nationality: str = ""
    club: str = ""
    pace: int = 0
    shooting: int = 0
    passing: int = 0
    dribbling: int = 0
    defending: int = 0
    physical: int = 0
    photo_url: str = ""
    team_id: Optional[int] = None


class Team(BaseModel):
    id: int
    name: str
    owner: str
    logo_url: str = ""
    players: list[int] = Field(default_factory=list)

    @property
    def flag(self) -> str:
        return TEAM_FLAGS.get(self.name, "")

    @property
    def color(self) -> str:
        return TEAM_COLORS.get(self.name, "#10b981")


class MatchEvent(BaseModel):
    type: str  # goal, assist, yellow_card, red_card, own_goal
    player_id: int
    player_name: str = ""
    team_id: int
    minute: Optional[int] = None
    related_event_id: Optional[int] = None


class MatchStats(BaseModel):
    home_possession: Optional[float] = None
    away_possession: Optional[float] = None
    home_shots: Optional[int] = None
    away_shots: Optional[int] = None
    home_shots_on_target: Optional[int] = None
    away_shots_on_target: Optional[int] = None
    home_corners: Optional[int] = None
    away_corners: Optional[int] = None
    home_fouls: Optional[int] = None
    away_fouls: Optional[int] = None


class Match(BaseModel):
    id: int
    phase: str
    match_day: int = 0
    home_team_id: int
    away_team_id: int
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    played: bool = False
    events: list[MatchEvent] = Field(default_factory=list)
    stats: MatchStats = Field(default_factory=MatchStats)


class Transfer(BaseModel):
    id: int
    window: int
    team_a_id: int
    team_b_id: int
    player_a_id: int
    player_b_id: int
    timestamp: str = ""


class TransferWindow(BaseModel):
    number: int
    phase: str
    after_match_day: int
    is_open: bool = False
    is_completed: bool = False
    max_trades: int = 3


class StandingsRow(BaseModel):
    team_id: int
    team_name: str
    owner: str
    played: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0
    goals_for: int = 0
    goals_against: int = 0
    goal_difference: int = 0
    points: int = 0
    position: int = 0


class TournamentPhase(str, Enum):
    DRAFT = "draft"
    GROUP_STAGE = "group_stage"
    BRACKET = "bracket"
    FINISHED = "finished"


class TournamentState(BaseModel):
    phase: TournamentPhase = TournamentPhase.DRAFT
    current_match_day: int = 0
    current_transfer_window: int = 0
    bracket_results: dict = Field(default_factory=dict)
