# **Chess Openings Analytics**

---

## **Project Overview**

This project analyzes **over 20 000 rapid & blitz games** collected through the **[Lichess API](https://lichess.org/api)** to uncover insights about opening performance at the beginner (≤ 1200 Elo) level.

Using PostgreSQL, I designed a relational schema (players, games, openings), built a Python ETL pipeline to ingest raw PGN game data, and wrote SQL queries to evaluate **opening win rates, popularity, draw rates, and upset rates**.

---

## **How the Pipeline Works**

```
Lichess API ──► etl/collector.py ──► raw PGN file ──► etl/load.py ──► PostgreSQL ──► SQL queries
  (berserk)       export games        data/*.pgn      parse, clean,    players /       sql/queries/
                                                      and load         games /
                                                                       openings
```

1. **Extract** (`etl/collector.py`)  
   - Reads a list of usernames and uses the Lichess *games/export* endpoint via the `berserk` Python SDK to download up to 300 games per player  
   - Filters applied: **rapid/blitz only**, **rated only**, **since 2020-01-01** (set by a constant in the collector). The ≤ 1200 rating scope is enforced by curating the player list itself  
   - Writes the raw PGN stream to the output file you give it (e.g. `data/beginner_games.pgn`)

2. **Transform + Load** (`etl/load.py`)  
   - Parses each game with `python-chess` and extracts: player usernames, `WhiteElo`, `BlackElo`, `Opening`, `ECO`, `Termination`, `Result`, and the game ID and timestamp  
   - Opening names and ECO codes come directly from Lichess's PGN headers  
   - Cleans the fields (see Data Cleaning below) and derives `rating_diff` and `ply_count`  
   - Upserts players, openings, and games into PostgreSQL

3. **Analyze** (`sql/queries/`)  
   - The analytical queries below are also saved as standalone `.sql` files

---

## **Data Cleaning**

- **Duplicate games:** the same game can appear in two players' exports, so games are keyed on the Lichess game ID and re-inserts are ignored
- **Players:** upserted by username, keeping the highest rating seen across their games
- **Openings:** deduplicated by name, since many opening names share one ECO code; `family` is the part of the name before the colon (e.g. "Sicilian Defense: Alapin Variation" → "Sicilian Defense")
- **Missing ratings:** missing or unknown (`?`) ratings are stored as `NULL` instead of crashing the load, so they don't count as very low ratings in rating filters; `rating_diff` is `NULL` when either rating is missing
- **Results:** PGN results (`1-0`, `0-1`, `1/2-1/2`) are mapped to `white`, `black`, and `draw`; unfinished games are stored as `NULL`
- **Timestamps:** the PGN `UTCDate` and `UTCTime` headers are parsed into one timestamp
- **Bad rows:** games with no game ID or an unparseable date are skipped and counted in the load summary

---

## **Database Design**

`sql/schema.sql` creates three tables, with indexes on the columns used for joins and filters:

- `players(player_id, username, highest_rating)`  
- `games(game_id, played_at, white_id, black_id, white_rating, black_rating, winner, termination, ply_count, opening_id, rating_diff)`  
- `openings(opening_id, eco, name, family)`

> See `ERD.md` for a full Entity-Relationship Diagram of the schema.

---

## **Objective**

The primary objective is to find which openings perform well for beginner chess players, grounded in game data rather than anecdotal advice.

Key questions addressed:

- Which openings yield the **highest win rate** for White and for Black?  
- How does opening success **differ across rating bands**, and which openings are **stable** across them?  
- Which openings have been **most popular recently**, including among improving players?  
- Which openings lead to the **quickest decisive games**, the most **draws**, and the most **upset wins**?

---

## **Analytical Queries & Insights**

Below are the SQL queries that power the analysis. They are also saved as standalone files in `sql/queries/`.

1. **Top 10 Openings by Win Rate (White ≤ 1200)**

```sql
SELECT
        o.name AS opening,
        COUNT(*) AS games_played,
        SUM(CASE WHEN g.winner = 'white' THEN 1 END)::decimal / COUNT(*) * 100 AS white_win_rate
FROM    games g
JOIN    openings o ON o.opening_id = g.opening_id
WHERE   g.white_rating <= 1200
GROUP BY 1
HAVING  COUNT(*) > 100  
ORDER BY 3 DESC
LIMIT 10;
```

2. **Top 10 Openings by Win Rate (Black ≤ 1200)**

```sql
SELECT
        o.name AS opening,
        COUNT(*) AS games_played,
        ROUND(SUM(CASE WHEN g.winner = 'black' THEN 1 ELSE 0 END)::numeric / COUNT(*) * 100, 2) AS black_win_rate
FROM    games g
JOIN    openings o ON o.opening_id = g.opening_id
WHERE   g.black_rating <= 1200
GROUP BY 1
HAVING  COUNT(*) > 100
ORDER BY 3 DESC
LIMIT 10;
```

3. **Opening Success by Rating Band**

```sql
WITH banded AS (
    SELECT
            g.*,
            NTILE(3) OVER (ORDER BY (white_rating + black_rating) / 2) AS rating_band
    FROM    games g
)
SELECT
        rating_band,
        o.family,
        COUNT(*) AS games,
        ROUND(SUM(CASE WHEN winner = 'white' THEN 1 ELSE 0 END)::numeric / COUNT(*) * 100, 2) AS white_win_pct
FROM    banded b
JOIN    openings o ON o.opening_id = b.opening_id
GROUP BY 1, 2
ORDER BY 1, 4 DESC;
```

4. **Most Popular Openings Last 6 Months**

```sql
SELECT
        o.name,
        COUNT(*) AS games
FROM    games g
JOIN    openings o ON o.opening_id = g.opening_id
WHERE   g.played_at >= CURRENT_DATE - INTERVAL '6 months'
GROUP BY 1
ORDER BY 2 DESC
LIMIT 15;
```

5. **Quickest Decisive Games**

```sql
SELECT
        g.game_id,
        o.name,
        g.ply_count,
        g.winner
FROM    games g
JOIN    openings o ON o.opening_id = g.opening_id
WHERE   g.ply_count < 30  -- less than 15 moves per player
ORDER BY g.ply_count ASC
LIMIT 20;
```

6. **Resilient Openings vs Rating Mismatch**

```sql
-- upset wins = lower-rated player beats higher-rated player (>=150 Elo gap)
SELECT
        o.family,
        COUNT(*) AS games,
        ROUND(
          SUM(
            CASE
              WHEN (white_rating < black_rating AND winner = 'white')
                OR (black_rating < white_rating AND winner = 'black')
              THEN 1
            END
          )::numeric / COUNT(*) * 100, 2
        ) AS upset_win_pct
FROM    games g
JOIN    openings o ON o.opening_id = g.opening_id
WHERE   rating_diff >= 150
GROUP BY 1
HAVING  COUNT(*) > 200
ORDER BY upset_win_pct DESC
LIMIT 10;
```

7. **Popular Openings Among Players Who Improved**

```sql
-- players whose highest observed rating is ≥100 Elo above their median rating across all their games
WITH improvers AS (
    SELECT
        p.player_id
    FROM    players p
    JOIN    games g ON p.player_id = g.white_id OR p.player_id = g.black_id
    GROUP BY p.player_id, p.highest_rating
    HAVING  p.highest_rating - PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY
            CASE WHEN p.player_id = g.white_id THEN white_rating ELSE black_rating END) >= 100
)
SELECT
        o.family, COUNT(*) AS games
FROM    games g
JOIN    openings o ON o.opening_id = g.opening_id
WHERE   (g.white_id IN (SELECT player_id FROM improvers)
         OR g.black_id IN (SELECT player_id FROM improvers))
GROUP BY 1
ORDER BY games DESC
LIMIT 10;
```

8. **Draw Percentage by Opening (≤1200)**

```sql
SELECT
        o.family,
        COUNT(*) AS games,
        ROUND(SUM(CASE WHEN winner = 'draw' THEN 1 END)::numeric / COUNT(*) * 100, 2) AS draw_pct
FROM    games g
JOIN    openings o ON o.opening_id = g.opening_id
WHERE   white_rating <= 1200 AND black_rating <= 1200
GROUP BY 1
HAVING  COUNT(*) > 200
ORDER BY draw_pct DESC
LIMIT 10;
```

9. **Stable Openings Across Rating Bands**
```sql
WITH tiered AS (
    SELECT
        o.name,
            winner,
            CASE
               WHEN white_rating <= 1000 AND black_rating <= 1000 THEN 'U1000'
               WHEN white_rating <= 1200 AND black_rating <= 1200 THEN '1000-1200'
            END AS band
    FROM    games g JOIN openings o ON o.opening_id = g.opening_id
)
, agg AS (
    SELECT
        name, band,
            SUM(CASE WHEN winner='white' THEN 1 END)::numeric/COUNT(*)*100 AS white_win_pct
    FROM    tiered
    WHERE   band IS NOT NULL
    GROUP BY 1,2 HAVING COUNT(*) > 200
)
SELECT
        a1.name,
        ROUND(ABS(a1.white_win_pct - a2.white_win_pct),2) AS pct_diff
FROM    agg a1 JOIN agg a2 ON a1.name=a2.name AND a1.band='U1000' AND a2.band='1000-1200'
ORDER BY pct_diff ASC
LIMIT 10;
```

---

## **Learning Outcomes**

- Built a **Python ETL pipeline** that collects, cleans, and loads game data
- Cleaned and preprocessed **real-world datasets** for analysis 
- Designed a **relational schema** with indexes on the columns used for joins and filters
- Applied advanced **SQL operations** (window functions, subqueries, joins, CTEs) to derive insights

---

## **Conclusion**

This project shows how data engineering and SQL analytics can turn raw chess game data into evidence about which openings work well for beginners.
