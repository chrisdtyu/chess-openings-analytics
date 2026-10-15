-- Stable openings across rating bands
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
