# FIFA Championship - EA FC 26

Tournament management system for an 8-player EA FC 26 championship.

## Quick Start

```bash
make install          # Install dependencies
make load-data        # Generate sample player data (or use --csv for Kaggle data)
make draft            # Run balanced draft to distribute players
make dev              # Start the web server (development mode with auto-reload)
```

Then open http://localhost:8000

## Architecture

- **Backend**: FastAPI + Jinja2 templates
- **Frontend**: Tailwind CSS + Chart.js
- **Data**: JSON files in `tournament_data/`
- **Player Data**: Sample data or Kaggle CSV

## Using Real Player Data

1. Download from Kaggle:
   - https://www.kaggle.com/datasets/nyagami/ea-sports-fc-25-database-ratings-and-stats
   - https://www.kaggle.com/datasets/mexwell/ea-fc25-player-database
2. Place the CSV in `data/`
3. Run: `python scripts/load_players.py --csv data/your_file.csv`

## Tournament Format

### Group Stage
- 8 teams, single group, all vs all (28 matches, 7 rounds)
- Win = 3pts, Draw = 1pt, Loss = 0pts
- Top 4 qualify for upper bracket, 5th-6th play lower bracket entry

### Bracket (Double Elimination Style)
- **Quarters**: 1v4, 2v3 (upper) + 5v6 (lower entry)
- **Upper Semi**: Winner(1v4) vs Winner(2v3)
- **Lower R1**: Winner(5v6) vs Loser(1v4)
- **Lower R2**: Winner(Lower R1) vs Loser(2v3)
- **Lower Final**: Loser(Upper Semi) vs Winner(Lower R2)
- **Grand Final**: Winner(Upper Semi) vs Winner(Lower Final)
- Tiebreaker: group stage position

### Squad Composition (26 players per team)
- GK: 3 | DEF: 8 | MID: 8 | FWD: 7

### Transfer Windows
- Before tournament starts
- Every 4 match days during group stage
- Final window before bracket phase
- Max 3 trades per window, same position group only

## Project Structure

```
src/
  app.py          # FastAPI application
  models.py       # Pydantic data models
  database.py     # JSON persistence layer
  draft.py        # Balanced draft algorithm
  tournament.py   # Tournament logic
  templates/      # Jinja2 HTML templates
  static/         # CSS, JS
scripts/
  load_players.py # Load/generate player data
  run_draft.py    # Execute the draft
tournament_data/  # JSON data files (generated)
data/             # Raw CSV data (optional)
```
