-- Top 10 openings by win rate (White <= 1200)
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
