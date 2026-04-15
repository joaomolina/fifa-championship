"""Run the draft to distribute players across teams.

This script:
1. Loads player data
2. Runs the balanced snake draft + optimization
3. Generates group stage matches
4. Sets up transfer windows
5. Saves everything

Usage:
    python scripts/run_draft.py
    python scripts/run_draft.py --seed 42
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import database as db
from src.models import TournamentPhase, TournamentState
from src.draft import run_draft, print_draft_summary
from src.tournament import generate_group_matches, generate_transfer_windows

DEFAULT_TEAMS = [
    ("Mexico", "Joao Victor Molina"),
    ("Argentina", "Joao Victor Pires"),
    ("Alemanha", "Vinicius Lista"),
    ("Franca", "Igor Vereda"),
    ("USA", "Guilherme Rissi"),
    ("Espanha", "Kaiki Aguiar"),
    ("Portugal", "Felipe Aguiar"),
    ("Inglaterra", "Reinaldo Urbano"),
]


def main():
    parser = argparse.ArgumentParser(description="Run FIFA Championship draft")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for draft")
    args = parser.parse_args()

    players = db.load_players()
    if not players:
        print("No players found. Run 'python scripts/load_players.py' first.")
        sys.exit(1)

    print(f"Found {len(players)} players. Running draft...")
    teams, updated_players = run_draft(players, DEFAULT_TEAMS, seed=args.seed)

    db.save_teams(teams)
    db.save_players(updated_players)

    print_draft_summary(teams, updated_players)

    print("\nGenerating group stage schedule...")
    matches = generate_group_matches(teams)
    db.save_matches(matches)
    print(f"Generated {len(matches)} group stage matches ({len(set(m.match_day for m in matches))} rodadas)")

    print("\nSetting up transfer windows...")
    num_match_days = max(m.match_day for m in matches)
    windows = generate_transfer_windows(num_match_days)
    db.save_transfer_windows(windows)
    for w in windows:
        label = "Antes do torneio" if w.after_match_day == 0 else f"Apos rodada {w.after_match_day}"
        if w.phase == "bracket":
            label = "Antes do bracket"
        print(f"  Janela {w.number}: {label}")

    state = TournamentState(
        phase=TournamentPhase.GROUP_STAGE,
        current_match_day=1,
        current_transfer_window=1,
    )
    db.save_tournament_state(state)

    print("\nDraft completo! Execute 'make run' para iniciar o servidor.")


if __name__ == "__main__":
    main()
