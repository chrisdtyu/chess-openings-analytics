-- Resilient openings vs rating mismatch
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
