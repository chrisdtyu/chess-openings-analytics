-- Most popular openings, last 6 months
SELECT
        o.name,
        COUNT(*) AS games
FROM    games g
JOIN    openings o ON o.opening_id = g.opening_id
WHERE   g.played_at >= CURRENT_DATE - INTERVAL '6 months'
GROUP BY 1
ORDER BY 2 DESC
LIMIT 15;
