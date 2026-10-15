from __future__ import annotations

import argparse
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

import chess.pgn

from src.db import get_conn

ECO_RE = re.compile(r"([A-E][0-9]{2})")

RESULT_TO_WINNER = {"1-0": "white", "0-1": "black", "1/2-1/2": "draw"}


def parse_rating(value: Optional[str]) -> Optional[int]:
    """Return the rating as an int, or None if it is missing or unknown ("?")."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def parse_played_at(date: str, time: str) -> Optional[datetime]:
    """Combine the PGN UTCDate (YYYY.MM.DD) and UTCTime (HH:MM:SS) headers."""
    try:
        return datetime.strptime(f"{date} {time}", "%Y.%m.%d %H:%M:%S")
    except ValueError:
        return None


def opening_family(name: str) -> str:
    """Group variations under their parent opening, e.g. "Sicilian Defense: Alapin Variation"
    -> "Sicilian Defense"."""
    return name.split(":")[0].strip()


def upsert_player(cur, username: str, rating: Optional[int]) -> int:
    cur.execute(
        """
        INSERT INTO players(username, highest_rating)
        VALUES(%s, %s)
        ON CONFLICT(username) DO UPDATE
            SET highest_rating = GREATEST(players.highest_rating, EXCLUDED.highest_rating)
        RETURNING player_id;
        """,
        (username, rating),
    )
    return cur.fetchone()[0]


def upsert_opening(cur, eco: str, name: str) -> int:
    # Many opening names share one ECO code, so openings are keyed on name, not eco.
    # The no-op update is there so RETURNING also yields the id of an existing row.
    cur.execute(
        """
        INSERT INTO openings(eco, name, family)
        VALUES(%s, %s, %s)
        ON CONFLICT (name) DO UPDATE SET eco = EXCLUDED.eco
        RETURNING opening_id;
        """,
        (eco, name, opening_family(name)),
    )
    return cur.fetchone()[0]


def insert_game(cur, game_dict: Dict) -> bool:
    """Insert a game; returns False if it was already loaded."""
    cur.execute(
        """
        INSERT INTO games(
            game_id, played_at, white_id, black_id, white_rating, black_rating,
            winner, termination, ply_count, opening_id, rating_diff)
        VALUES (
            %(game_id)s, %(played_at)s, %(white_id)s, %(black_id)s,
            %(white_rating)s, %(black_rating)s, %(winner)s, %(termination)s,
            %(ply_count)s, %(opening_id)s, %(rating_diff)s)
        ON CONFLICT (game_id) DO NOTHING;
        """,
        game_dict,
    )
    return cur.rowcount == 1


def process_pgn(pgn_path: Path) -> None:
    processed = inserted = skipped = 0
    with get_conn() as conn, conn.cursor() as cur:
        with pgn_path.open("r", encoding="utf-8") as handle:
            while True:
                game = chess.pgn.read_game(handle)
                if game is None:
                    break
                processed += 1
                headers = game.headers

                # skip games we can't key or date instead of loading bad rows
                game_id = headers.get("Site", "").split("/")[-1]
                played_at = parse_played_at(headers.get("UTCDate", ""), headers.get("UTCTime", ""))
                if not game_id or played_at is None:
                    skipped += 1
                    continue

                eco = headers.get("ECO", "?")
                opening_name = headers.get("Opening", "Unknown")
                opening_id = upsert_opening(cur, eco, opening_name)

                white_rating = parse_rating(headers.get("WhiteElo"))
                black_rating = parse_rating(headers.get("BlackElo"))

                white_id = upsert_player(cur, headers.get("White", "?"), white_rating)
                black_id = upsert_player(cur, headers.get("Black", "?"), black_rating)

                rating_diff = None
                if white_rating is not None and black_rating is not None:
                    rating_diff = abs(white_rating - black_rating)

                game_dict = {
                    "game_id": game_id,
                    "played_at": played_at,
                    "white_id": white_id,
                    "black_id": black_id,
                    "white_rating": white_rating,
                    "black_rating": black_rating,
                    "winner": RESULT_TO_WINNER.get(headers.get("Result", "*")),
                    "termination": headers.get("Termination", "?"),
                    "ply_count": game.end().ply(),
                    "opening_id": opening_id,
                    "rating_diff": rating_diff,
                }
                if insert_game(cur, game_dict):
                    inserted += 1
                if processed % 1000 == 0:
                    print(f"Processed {processed} games…", flush=True)
    print(f"Finished. Processed {processed}, inserted {inserted}, "
          f"skipped {skipped}, already loaded {processed - inserted - skipped}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("pgn_file", help="PGN file to load into database")
    args = parser.parse_args()
    process_pgn(Path(args.pgn_file))


if __name__ == "__main__":
    main()
