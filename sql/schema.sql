CREATE TABLE IF NOT EXISTS players (
    player_id      SERIAL PRIMARY KEY,
    username       TEXT UNIQUE NOT NULL,
    highest_rating INTEGER
);

CREATE TABLE IF NOT EXISTS openings (
    opening_id SERIAL PRIMARY KEY,
    eco        TEXT NOT NULL,
    name       TEXT NOT NULL,
    family     TEXT
);

CREATE TABLE IF NOT EXISTS games (
    game_id      TEXT PRIMARY KEY,
    played_at    TIMESTAMP NOT NULL,
    white_id     INTEGER REFERENCES players(player_id),
    black_id     INTEGER REFERENCES players(player_id),
    white_rating INTEGER,
    black_rating INTEGER,
    winner       TEXT,
    termination  TEXT,
    ply_count    INTEGER,
    opening_id   INTEGER REFERENCES openings(opening_id),
    rating_diff  INTEGER
);

CREATE INDEX IF NOT EXISTS idx_games_opening ON games(opening_id);
CREATE INDEX IF NOT EXISTS idx_games_played_at ON games(played_at);
