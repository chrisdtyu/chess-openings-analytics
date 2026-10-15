-- Quickest decisive games
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
