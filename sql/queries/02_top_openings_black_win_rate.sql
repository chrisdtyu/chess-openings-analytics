-- Top 10 openings by win rate (Black <= 1200)
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
