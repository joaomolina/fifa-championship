from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src import database as db
from src.models import (
    Match,
    MatchEvent,
    MatchStats,
    Player,
    PositionGroup,
    StandingsRow,
    TournamentPhase,
    Transfer,
    TEAM_FLAGS,
    TEAM_COLORS,
)
from src.tournament import (
    compute_standings,
    get_top_scorers,
    get_top_assisters,
    get_bracket_data,
    advance_bracket,
    generate_bracket_matches,
    PHASE_LABELS,
)

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(title="Copa EA FC 26")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def _context(request: Request, **kwargs) -> dict:
    state = db.load_tournament_state()
    return {
        "request": request,
        "state": state,
        "phase_labels": PHASE_LABELS,
        "team_flags": TEAM_FLAGS,
        "team_colors": TEAM_COLORS,
        **kwargs,
    }


# --- Dashboard ---

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    teams = db.load_teams()
    matches = db.load_matches()
    state = db.load_tournament_state()

    standings = compute_standings(matches, teams) if teams else []
    recent_matches = [m for m in matches if m.played][-5:]
    upcoming_matches = [m for m in matches if not m.played][:5]
    top_scorers = get_top_scorers(matches, limit=5)
    top_assisters = get_top_assisters(matches, limit=5)

    team_map = {t.id: t for t in teams}

    return templates.TemplateResponse("index.html", _context(
        request,
        teams=teams,
        standings=standings[:8],
        recent_matches=recent_matches,
        upcoming_matches=upcoming_matches,
        top_scorers=top_scorers,
        top_assisters=top_assisters,
        team_map=team_map,
        total_matches=len(matches),
        played_matches=len([m for m in matches if m.played]),
    ))


# --- Standings ---

@app.get("/standings", response_class=HTMLResponse)
async def standings(request: Request):
    teams = db.load_teams()
    matches = db.load_matches()
    standings = compute_standings(matches, teams)
    return templates.TemplateResponse("standings.html", _context(
        request, standings=standings,
    ))


# --- Teams ---

@app.get("/teams", response_class=HTMLResponse)
async def teams_list(request: Request):
    teams = db.load_teams()
    players = db.load_players()
    player_map = {p.id: p for p in players}

    teams_data = []
    for team in teams:
        team_players = [player_map[pid] for pid in team.players if pid in player_map]
        avg_overall = sum(p.overall for p in team_players) / len(team_players) if team_players else 0

        by_group = {}
        for pg in PositionGroup:
            pg_players = sorted(
                [p for p in team_players if p.position_group == pg],
                key=lambda p: p.overall, reverse=True,
            )
            pg_avg = sum(p.overall for p in pg_players) / len(pg_players) if pg_players else 0
            by_group[pg.value] = {"players": pg_players, "avg": pg_avg}

        teams_data.append({
            "team": team,
            "avg_overall": avg_overall,
            "num_players": len(team_players),
            "by_group": by_group,
        })

    return templates.TemplateResponse("teams.html", _context(
        request, teams_data=teams_data,
    ))


@app.get("/teams/{team_id}", response_class=HTMLResponse)
async def team_detail(request: Request, team_id: int):
    team = db.get_team(team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Time nao encontrado")

    players = db.load_players()
    player_map = {p.id: p for p in players}
    team_players = [player_map[pid] for pid in team.players if pid in player_map]
    matches = db.load_matches()

    team_matches = [m for m in matches if m.home_team_id == team_id or m.away_team_id == team_id]
    played = [m for m in team_matches if m.played]

    player_stats = {}
    for p in team_players:
        player_stats[p.id] = {"goals": 0, "assists": 0}

    for m in played:
        for evt in m.events:
            if evt.team_id == team_id and evt.player_id in player_stats:
                if evt.type == "goal":
                    player_stats[evt.player_id]["goals"] += 1
                elif evt.type == "assist":
                    player_stats[evt.player_id]["assists"] += 1

    by_group = {}
    for pg in PositionGroup:
        by_group[pg.value] = sorted(
            [p for p in team_players if p.position_group == pg],
            key=lambda p: p.overall, reverse=True,
        )

    avg_overall = sum(p.overall for p in team_players) / len(team_players) if team_players else 0

    return templates.TemplateResponse("team_detail.html", _context(
        request,
        team=team,
        by_group=by_group,
        avg_overall=avg_overall,
        player_stats=player_stats,
        team_matches=team_matches,
        team_map={t.id: t for t in db.load_teams()},
    ))


# --- Matches ---

@app.get("/matches", response_class=HTMLResponse)
async def matches_list(request: Request):
    matches = db.load_matches()
    teams = db.load_teams()
    team_map = {t.id: t for t in teams}

    group_matches = [m for m in matches if m.phase == "group"]
    bracket_matches = [m for m in matches if m.phase != "group"]

    match_days: dict[int, list[Match]] = {}
    for m in group_matches:
        match_days.setdefault(m.match_day, []).append(m)

    return templates.TemplateResponse("matches.html", _context(
        request,
        match_days=match_days,
        bracket_matches=bracket_matches,
        team_map=team_map,
    ))


@app.get("/matches/{match_id}", response_class=HTMLResponse)
async def match_detail(request: Request, match_id: int):
    match = db.get_match(match_id)
    if not match:
        raise HTTPException(status_code=404, detail="Jogo nao encontrado")

    teams = db.load_teams()
    team_map = {t.id: t for t in teams}
    players = db.load_players()
    player_map = {p.id: p for p in players}

    return templates.TemplateResponse("match_detail.html", _context(
        request,
        match=match,
        team_map=team_map,
        player_map=player_map,
    ))


# --- Bracket ---

@app.get("/bracket", response_class=HTMLResponse)
async def bracket(request: Request):
    matches = db.load_matches()
    teams = db.load_teams()
    standings = compute_standings(matches, teams)
    bracket_data = get_bracket_data(matches, standings)
    team_map = {t.id: t for t in teams}

    return templates.TemplateResponse("bracket.html", _context(
        request,
        bracket=bracket_data,
        team_map=team_map,
    ))


# --- Transfers ---

@app.get("/transfers", response_class=HTMLResponse)
async def transfers(request: Request):
    transfers = db.load_transfers()
    windows = db.load_transfer_windows()
    teams = db.load_teams()
    players = db.load_players()
    team_map = {t.id: t for t in teams}
    player_map = {p.id: p for p in players}

    return templates.TemplateResponse("transfers.html", _context(
        request,
        transfers=transfers,
        windows=windows,
        team_map=team_map,
        player_map=player_map,
    ))


# --- Stats ---

@app.get("/stats", response_class=HTMLResponse)
async def stats(request: Request):
    matches = db.load_matches()
    teams = db.load_teams()
    players = db.load_players()
    team_map = {t.id: t for t in teams}

    standings = compute_standings(matches, teams)
    top_scorers = get_top_scorers(matches, limit=20)
    top_assisters = get_top_assisters(matches, limit=20)

    played_matches = [m for m in matches if m.played]
    team_stats = {}
    for t in teams:
        t_matches = [m for m in played_matches if m.home_team_id == t.id or m.away_team_id == t.id]
        total_possession = 0
        total_shots = 0
        count = 0
        for m in t_matches:
            if m.stats.home_possession is not None:
                count += 1
                if m.home_team_id == t.id:
                    total_possession += m.stats.home_possession
                    total_shots += m.stats.home_shots or 0
                else:
                    total_possession += m.stats.away_possession
                    total_shots += m.stats.away_shots or 0

        team_stats[t.id] = {
            "avg_possession": total_possession / count if count else 0,
            "total_shots": total_shots,
            "matches": len(t_matches),
        }

    return templates.TemplateResponse("stats.html", _context(
        request,
        standings=standings,
        top_scorers=top_scorers,
        top_assisters=top_assisters,
        team_stats=team_stats,
        team_map=team_map,
        played_matches=played_matches,
    ))


# --- API Endpoints (for programmatic updates) ---

@app.get("/api/standings")
async def api_standings():
    teams = db.load_teams()
    matches = db.load_matches()
    return [r.model_dump() for r in compute_standings(matches, teams)]


@app.get("/api/teams")
async def api_teams():
    return [t.model_dump() for t in db.load_teams()]


@app.get("/api/matches")
async def api_matches():
    return [m.model_dump() for m in db.load_matches()]


@app.get("/api/top-scorers")
async def api_top_scorers():
    matches = db.load_matches()
    return get_top_scorers(matches, limit=20)
