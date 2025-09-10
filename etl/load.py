from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Dict, Tuple

import chess.pgn

from src.db import get_conn

ECO_RE = re.compile(r"([A-E][0-9]{2})")


def upsert_player(cur, username: str, rating: int) -> int:
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
    family = name.split(":")[0] if ":" in name else name.split()[0]
    cur.execute(
        """
        INSERT INTO openings(eco, name, family)
        VALUES(%s, %s, %s)
        ON CONFLICT (eco) DO UPDATE SET name = EXCLUDED.name
        RETURNING opening_id;
        """,
        (eco, name, family),
    )
    return cur.fetchone()[0]


def insert_game(cur, game_dict: Dict) -> None:
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


def process_pgn(pgn_path: Path) -> None:
    game_ct = 0
    with get_conn() as conn, conn.cursor() as cur:
        with pgn_path.open("r", encoding="utf-8") as handle:
            while True:
                game = chess.pgn.read_game(handle)
                if game is None:
                    break
                headers = game.headers
                eco = headers.get("ECO", "?")
                opening_name = headers.get("Opening", "Unknown")
                opening_id = upsert_opening(cur, eco, opening_name)

                white_username = headers.get("White", "?")
                black_username = headers.get("Black", "?")
                white_rating = int(headers.get("WhiteElo", 0))
                black_rating = int(headers.get("BlackElo", 0))

                white_id = upsert_player(cur, white_username, white_rating)
                black_id = upsert_player(cur, black_username, black_rating)

                game_dict = {
                    "game_id": headers.get("Site", "").split("/")[-1],
                    "played_at": headers.get("UTCDate", "1970.01.01") + " " + headers.get("UTCTime", "00:00:00"),
                    "white_id": white_id,
                    "black_id": black_id,
                    "white_rating": white_rating,
                    "black_rating": black_rating,
                    "winner": headers.get("Result", "*").replace("1-0", "white").replace("0-1", "black").replace("1/2-1/2", "draw"),
                    "termination": headers.get("Termination", "?"),
                    "ply_count": game.end().ply(),
                    "opening_id": opening_id,
                    "rating_diff": abs(white_rating - black_rating),
                }
                insert_game(cur, game_dict)
                game_ct += 1
                if game_ct % 1000 == 0:
                    print(f"Inserted {game_ct} games…", flush=True)
    print(f"Finished. Total games processed: {game_ct}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("pgn_file", help="PGN file to load into database")
    args = parser.parse_args()
    process_pgn(Path(args.pgn_file))


if __name__ == "__main__":
    main()
