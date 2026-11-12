-- Opening success by rating band
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
