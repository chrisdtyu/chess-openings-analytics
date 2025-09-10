# **Chess Openings Analytics**

---

## **Project Overview**

This project analyzes **over 20 000 rapid & blitz games** collected through the **[Lichess API](https://lichess.org/api)** to uncover insights about opening performance at the beginner (≤ 1200 Elo) level.

Using PostgreSQL, I designed a fully-normalized schema, built an automated Python ETL pipeline to ingest raw PGN/JSON game data, and performed in-depth SQL querying to evaluate **opening win rates, popularity trends, and strategic recommendations**.

---

## **Data Pipeline & Database Design**

1. **Data Collection (Extract)**  
   - Utilized the Lichess *games/export* endpoint via the `berserk` Python SDK to stream player game data in batches of 300 games  
   - Filters applied: **time-class = rapid/blitz**, **since 2020-01-01** (configurable), **rated only**. The ≤ 1200 rating scope is enforced by curating the player list itself
   - The collector saves the raw PGN stream to `data/beginner_games.pgn`

2. **Data Transformation (Transform)**  
   - Parsed PGN headers to extract: `white_elo`, `black_elo`, `opening_name`, `opening_eco`, `termination`, `winner`, `time_control`, `moves`  
   - Normalized openings with ECO codes using the official ECO reference list  
   - Added derived metrics: `rating_diff`, `is_upset`, `ply_count`

3. **Data Loading (Load)**  
   - Loaded curated tables into PostgreSQL:
     - `players(player_id, username, highest_rating)`  
     - `games(game_id, played_at, white_id, black_id, winner, termination, ply_count, opening_id, rating_diff)`  
     - `openings(opening_id, eco, name, family)`



> See `ERD.md` for a full Entity-Relationship Diagram of the schema.

---

## **Objective**

The primary objective is to recommend strong, practical openings for beginner chess players. This recommendation is grounded in empirical game data rather than anecdotal advice.

Key questions addressed:

- Which openings yield the **highest win rate** for White and Black?  
- How does **average game length** vary across openings?  
- What are the **most common trap lines** beginners fall into?  
- How has opening popularity **trended** over the last 18 months?

---

## **Analytical Queries & Insights**

Below are selected SQL queries that power the analysis. 

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
HAVING  COUNT(*) > 1000  
ORDER BY 3 DESC
LIMIT 10;
```

2. **Opening Success by Rating Band**

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

3. **Most Popular Openings Last 6 Months**

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

4. **Quickest Decisive Games**

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

5. **Resilient Openings vs Rating Mismatch**

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

6. **Popular Openings Among Improving Players**

```sql
-- players whose current rating is ≥100 Elo higher than their historical median
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

7. **Draw Percentage by Opening (≤1200)**

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

8. **Stable Openings Across Rating Bands**
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

- Built a production-grade **Python ETL pipeline**
- Cleaned and preprocessed **real-world datasets** for analysis 
- Designed and implemented a **normalized relational schema** to optimize query performance  
- Applied advanced **SQL operations** (window functions, subqueries, joins, CTEs) to derive insights



---

## **Conclusion**

This project demonstrates how data engineering and SQL analytics can transform raw chess game data into actionable opening recommendations for beginners.  

