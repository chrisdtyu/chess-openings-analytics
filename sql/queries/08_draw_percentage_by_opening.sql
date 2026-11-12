-- Draw percentage by opening (both players <= 1200)
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
