"""Load player data from the EA FC 26 dataset.

Usage:
    python scripts/load_players.py                              # Generate sample data
    python scripts/load_players.py --csv data/ea_fc26_players.csv  # Load from CSV

Dataset source:
    https://www.kaggle.com/datasets/justdhia/ea-sports-fc-26-player-ratings/data
"""
import argparse
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from src.models import Player, PositionGroup, POSITION_GROUP_MAP, SQUAD_COMPOSITION, NUM_TEAMS, SUB_POSITION_MINIMUMS
from src import database as db


def _safe_int(value, default: int = 0) -> int:
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def load_from_csv(csv_path: str) -> list[Player]:
    """Load players from the EA FC 26 CSV (ea_fc26_players.csv)."""
    df = pd.read_csv(csv_path)

    col_map = _detect_columns(df)

    if "name" not in col_map or "overall" not in col_map or "position" not in col_map:
        print(f"Could not find required columns. Available: {list(df.columns)}")
        sys.exit(1)

    players = []
    for idx, row in df.iterrows():
        pos_raw = str(row[col_map["position"]]).strip().upper()
        if pos_raw not in POSITION_GROUP_MAP:
            continue

        name = _resolve_name(row, col_map)

        players.append(Player(
            id=idx + 1,
            name=name,
            overall=int(row[col_map["overall"]]),
            position=pos_raw,
            position_group=POSITION_GROUP_MAP[pos_raw],
            nationality=str(row.get(col_map.get("nationality", ""), "")) if "nationality" in col_map else "",
            club=str(row.get(col_map.get("club", ""), "")) if "club" in col_map else "",
            pace=_safe_int(row.get(col_map.get("pace", ""), 0)) if "pace" in col_map else 0,
            shooting=_safe_int(row.get(col_map.get("shooting", ""), 0)) if "shooting" in col_map else 0,
            passing=_safe_int(row.get(col_map.get("passing", ""), 0)) if "passing" in col_map else 0,
            dribbling=_safe_int(row.get(col_map.get("dribbling", ""), 0)) if "dribbling" in col_map else 0,
            defending=_safe_int(row.get(col_map.get("defending", ""), 0)) if "defending" in col_map else 0,
            physical=_safe_int(row.get(col_map.get("physical", ""), 0)) if "physical" in col_map else 0,
        ))

    players.sort(key=lambda p: p.overall, reverse=True)

    needed = {pg: count * NUM_TEAMS for pg, count in SQUAD_COMPOSITION.items()}
    selected: list[Player] = []
    selected_ids: set[int] = set()

    for pg, total in needed.items():
        if pg in SUB_POSITION_MINIMUMS:
            sub_reqs = SUB_POSITION_MINIMUMS[pg]
            reserved: list[Player] = []
            for sub_pos, min_count in sub_reqs.items():
                sub_pool = [p for p in players if p.position == sub_pos and p.id not in selected_ids]
                take = min_count * NUM_TEAMS
                for p in sub_pool[:take]:
                    reserved.append(p)
                    selected_ids.add(p.id)

            remaining_slots = total - len(reserved)
            fill_pool = [p for p in players if p.position_group == pg and p.id not in selected_ids]
            for p in fill_pool[:remaining_slots]:
                reserved.append(p)
                selected_ids.add(p.id)
            selected.extend(reserved)
        else:
            pool = [p for p in players if p.position_group == pg and p.id not in selected_ids]
            for p in pool[:total]:
                selected.append(p)
                selected_ids.add(p.id)

    for i, p in enumerate(selected):
        p.id = i + 1

    return selected


def _detect_columns(df: pd.DataFrame) -> dict[str, str]:
    """Auto-detect column names across different CSV formats."""
    col_map: dict[str, str] = {}
    for col in df.columns:
        low = col.lower().strip()
        if low in ("commonname", "name", "long_name", "player_name", "known_as"):
            col_map.setdefault("name", col)
        elif low in ("overallrating", "overall", "ovr", "overall_rating"):
            col_map.setdefault("overall", col)
        elif low in ("position", "player_positions", "best_position", "pos"):
            col_map.setdefault("position", col)
        elif low in ("nationality", "nationality_name", "nation"):
            col_map.setdefault("nationality", col)
        elif low in ("club", "club_name", "team"):
            col_map.setdefault("club", col)
        elif low in ("pace", "pac"):
            col_map.setdefault("pace", col)
        elif low in ("shooting", "sho"):
            col_map.setdefault("shooting", col)
        elif low in ("passing", "pas"):
            col_map.setdefault("passing", col)
        elif low in ("dribbling", "dri"):
            col_map.setdefault("dribbling", col)
        elif low in ("defending", "def"):
            col_map.setdefault("defending", col)
        elif low in ("physical", "phy", "physicality"):
            col_map.setdefault("physical", col)
        elif low in ("firstname",):
            col_map.setdefault("first_name", col)
        elif low in ("lastname",):
            col_map.setdefault("last_name", col)
    return col_map


def _resolve_name(row: pd.Series, col_map: dict[str, str]) -> str:
    """Pick the best display name: commonName > firstName+lastName."""
    if "name" in col_map:
        val = row.get(col_map["name"])
        if pd.notna(val) and str(val).strip():
            return str(val).strip()

    first = str(row.get(col_map.get("first_name", ""), "")).strip()
    last = str(row.get(col_map.get("last_name", ""), "")).strip()
    full = f"{first} {last}".strip()
    return full if full else "Unknown"


SAMPLE_PLAYERS = {
    PositionGroup.GK: [
        ("Donnarumma", 89, "ITA"), ("Courtois", 89, "BEL"), ("Alisson", 89, "BRA"),
        ("Ederson", 88, "BRA"), ("Neuer", 87, "GER"), ("Oblak", 87, "SVN"),
        ("ter Stegen", 87, "GER"), ("Maignan", 86, "FRA"), ("Diogo Costa", 85, "POR"),
        ("Sommer", 85, "SUI"), ("Szczesny", 84, "POL"), ("Navas", 84, "CRC"),
        ("Mendy", 83, "SEN"), ("Raya", 84, "ESP"), ("Sa", 83, "POR"),
        ("Livakovic", 83, "CRO"), ("Martinez", 84, "ARG"), ("Mamardashvili", 82, "GEO"),
        ("Vicario", 83, "ITA"), ("Schmeichel", 82, "DEN"), ("Ramsdale", 81, "ENG"),
        ("Kobel", 83, "SUI"), ("Pope", 81, "ENG"), ("Onana", 82, "CMR"),
    ],
    PositionGroup.DEF: [
        ("Virgil van Dijk", 90, "NED"), ("Dias", 88, "POR"), ("Marquinhos", 87, "BRA"),
        ("Rudiger", 87, "GER"), ("Saliba", 86, "FRA"), ("Bastoni", 86, "ITA"),
        ("Kim Min-jae", 85, "KOR"), ("Kounde", 85, "FRA"), ("Araujo", 85, "URU"),
        ("Gvardiol", 84, "CRO"), ("Militao", 84, "BRA"), ("Romero", 84, "ARG"),
        ("Laporte", 84, "ESP"), ("Upamecano", 83, "FRA"), ("Stones", 83, "ENG"),
        ("Bremer", 83, "BRA"), ("Akanji", 83, "SUI"), ("Lisandro Martinez", 83, "ARG"),
        ("Robertson", 87, "SCO"), ("Theo Hernandez", 86, "FRA"), ("Alexander-Arnold", 86, "ENG"),
        ("Cancelo", 86, "POR"), ("Davies", 85, "CAN"), ("Hakimi", 85, "MAR"),
        ("Grimaldo", 84, "ESP"), ("Mendy F.", 83, "FRA"), ("Walker", 83, "ENG"),
        ("Frimpong", 82, "NED"), ("Reece James", 82, "ENG"), ("Nuno Mendes", 82, "POR"),
        ("Gaya", 82, "ESP"), ("Perisic", 81, "CRO"), ("Pavard", 82, "FRA"),
        ("Acuna", 82, "ARG"), ("Tierney", 81, "SCO"), ("Cash", 80, "POL"),
        ("Cucurella", 81, "ESP"), ("Diogo Dalot", 82, "POR"), ("Kohlert", 79, "NED"),
        ("Mazraoui", 81, "MAR"), ("Zinchenko", 81, "UKR"), ("Digne", 80, "FRA"),
        ("Dest", 78, "USA"), ("Emerson", 79, "BRA"), ("Molina", 81, "ARG"),
        ("Porro", 82, "ESP"), ("Tsimikas", 79, "GRE"), ("Clauss", 80, "FRA"),
        ("Calafat", 78, "ESP"), ("Timber", 82, "NED"), ("Gabriel", 84, "BRA"),
        ("Kimpembe", 81, "FRA"), ("de Ligt", 82, "NED"), ("Skriniar", 83, "SVK"),
        ("Schlotterbeck", 82, "GER"), ("Todibo", 80, "FRA"), ("Hermoso", 80, "ESP"),
        ("Lenglet", 79, "FRA"), ("Christensen", 80, "DEN"), ("Kounde J.", 79, "FRA"),
        ("Ake", 82, "NED"), ("Dier", 80, "ENG"), ("Maguire", 79, "ENG"),
        ("Tomori", 81, "ENG"), ("Pau Torres", 82, "ESP"),
    ],
    PositionGroup.MID: [
        ("De Bruyne", 91, "BEL"), ("Modric", 88, "CRO"), ("Kroos", 88, "GER"),
        ("Pedri", 87, "ESP"), ("Bellingham", 88, "ENG"), ("Valverde", 87, "URU"),
        ("Barella", 86, "ITA"), ("Bruno Fernandes", 86, "POR"), ("Gundogan", 85, "GER"),
        ("Kimmich", 86, "GER"), ("Rodri", 89, "ESP"), ("Tonali", 84, "ITA"),
        ("Bernardo Silva", 87, "POR"), ("Saka", 86, "ENG"), ("Foden", 87, "ENG"),
        ("De Jong", 85, "NED"), ("Tchouameni", 85, "FRA"), ("Rice", 85, "ENG"),
        ("Gavi", 83, "ESP"), ("Mount", 82, "ENG"), ("Aouar", 80, "FRA"),
        ("Mac Allister", 83, "ARG"), ("Zielinski", 82, "POL"), ("Paqueta", 84, "BRA"),
        ("Szoboszlai", 82, "HUN"), ("Camavinga", 83, "FRA"), ("Rabiot", 82, "FRA"),
        ("Verratti", 84, "ITA"), ("Kante", 82, "FRA"), ("Odegaard", 87, "NOR"),
        ("Kokcu", 81, "TUR"), ("Lo Celso", 81, "ARG"), ("Caicedo", 82, "ECU"),
        ("Sabitzer", 81, "AUT"), ("Renato Sanches", 79, "POR"), ("Thiago", 81, "ESP"),
        ("Henderson", 79, "ENG"), ("Parejo", 83, "ESP"), ("Xhaka", 83, "SUI"),
        ("Jorginho", 80, "ITA"), ("Fred", 79, "BRA"), ("Phillips", 79, "ENG"),
        ("Locatelli", 80, "ITA"), ("Nkunku", 84, "FRA"), ("Amrabat", 80, "MAR"),
        ("Ndidi", 80, "NGA"), ("Bissouma", 79, "MLI"), ("Douglas Luiz", 80, "BRA"),
        ("Zakaria", 79, "SUI"), ("Fabian Ruiz", 82, "ESP"), ("Florentino", 80, "POR"),
        ("Gravenberch", 80, "NED"), ("Kudus", 80, "GHA"), ("Musah", 78, "USA"),
        ("Reijnders", 80, "NED"), ("Witsel", 79, "BEL"), ("Kovacic", 81, "CRO"),
        ("Tielemans", 80, "BEL"), ("Ward-Prowse", 79, "ENG"), ("Herrera", 78, "MEX"),
        ("Olmo", 83, "ESP"), ("Aouar H.", 79, "FRA"), ("Calhanoglu", 84, "TUR"),
        ("Brozovic", 82, "CRO"), ("Goretzka", 82, "GER"),
    ],
    PositionGroup.FWD: [
        ("Mbappe", 91, "FRA"), ("Haaland", 91, "NOR"), ("Vinicius Jr", 90, "BRA"),
        ("Salah", 89, "EGY"), ("Lewandowski", 89, "POL"), ("Son", 88, "KOR"),
        ("Messi", 88, "ARG"), ("Neymar", 87, "BRA"), ("Kane", 88, "ENG"),
        ("Lautaro Martinez", 87, "ARG"), ("Osimhen", 86, "NGA"), ("Griezmann", 86, "FRA"),
        ("Dembele", 85, "FRA"), ("Rafael Leao", 85, "POR"), ("Rashford", 84, "ENG"),
        ("Felix", 83, "POR"), ("Diaby", 83, "FRA"), ("Diaz", 83, "COL"),
        ("Darwin Nunez", 84, "URU"), ("Alvarez", 83, "ARG"), ("Coman", 83, "FRA"),
        ("Havertz", 83, "GER"), ("Isak", 84, "SWE"), ("Chiesa", 82, "ITA"),
        ("Sane", 83, "GER"), ("Sterling", 82, "ENG"), ("Richarlison", 82, "BRA"),
        ("Gnabry", 82, "GER"), ("Kulusevski", 81, "SWE"), ("Jesus", 82, "BRA"),
        ("Jota", 83, "POR"), ("Werner", 80, "GER"), ("Morata", 82, "ESP"),
        ("Firmino", 82, "BRA"), ("Giroud", 81, "FRA"), ("Pulisic", 81, "USA"),
        ("Depay", 81, "NED"), ("Lozano", 80, "MEX"), ("Correa", 81, "ARG"),
        ("Thuram", 82, "FRA"), ("Martial", 79, "FRA"), ("Mitrovic", 80, "SRB"),
        ("Watkins", 82, "ENG"), ("Moussa Diaby", 81, "FRA"), ("Vlahovic", 82, "SRB"),
        ("Oyarzabal", 82, "ESP"), ("Torres F.", 80, "ESP"), ("Asensio", 80, "ESP"),
        ("Madueke", 79, "ENG"), ("Reus", 79, "GER"), ("Calvert-Lewin", 79, "ENG"),
        ("Doku", 80, "BEL"), ("Weah", 78, "USA"), ("Enciso", 78, "PAR"),
        ("Garnacho", 79, "ARG"), ("Olise", 80, "FRA"),
    ],
}

SPECIFIC_POSITIONS = {
    PositionGroup.DEF: ["CB", "CB", "CB", "CB", "LB", "RB", "LWB", "RWB"],
    PositionGroup.MID: ["CDM", "CDM", "CM", "CM", "CAM", "CAM", "RM", "LM"],
    PositionGroup.FWD: ["ST", "ST", "ST", "LW", "RW", "CF", "RW"],
}


def generate_sample_data() -> list[Player]:
    """Generate sample player data inspired by real EA FC ratings."""
    random.seed(42)
    players = []
    pid = 1

    for pg, player_list in SAMPLE_PLAYERS.items():
        for i, (name, overall, nat) in enumerate(player_list):
            if pg == PositionGroup.GK:
                pos = "GK"
            else:
                positions = SPECIFIC_POSITIONS[pg]
                pos = positions[i % len(positions)]

            variation = lambda base: max(40, min(99, base + random.randint(-5, 5)))

            players.append(Player(
                id=pid,
                name=name,
                overall=overall,
                position=pos,
                position_group=pg,
                nationality=nat,
                pace=variation(overall) if pg != PositionGroup.GK else random.randint(30, 60),
                shooting=variation(overall) if pg in (PositionGroup.FWD, PositionGroup.MID) else random.randint(30, 60),
                passing=variation(overall - 3),
                dribbling=variation(overall - 2) if pg != PositionGroup.GK else random.randint(20, 50),
                defending=variation(overall) if pg in (PositionGroup.DEF, PositionGroup.GK) else random.randint(30, 65),
                physical=variation(overall - 3),
            ))
            pid += 1

    needed = {pg: count * NUM_TEAMS for pg, count in SQUAD_COMPOSITION.items()}
    available = {pg: [p for p in players if p.position_group == pg] for pg in PositionGroup}

    selected = []
    for pg, count in needed.items():
        pool = sorted(available[pg], key=lambda p: p.overall, reverse=True)[:count]
        selected.extend(pool)

    for i, p in enumerate(selected):
        p.id = i + 1

    return selected


def main():
    parser = argparse.ArgumentParser(description="Load EA FC player data")
    parser.add_argument("--csv", type=str, help="Path to Kaggle CSV file")
    args = parser.parse_args()

    if args.csv:
        print(f"Loading players from {args.csv}...")
        players = load_from_csv(args.csv)
    else:
        print("Generating sample player data...")
        players = generate_sample_data()

    db.save_players(players)

    counts = {pg: 0 for pg in PositionGroup}
    for p in players:
        counts[p.position_group] += 1

    print(f"\nLoaded {len(players)} players:")
    for pg, count in counts.items():
        print(f"  {pg.value}: {count}")
    print(f"\nData saved to {db.DATA_DIR / 'players.json'}")


if __name__ == "__main__":
    main()
