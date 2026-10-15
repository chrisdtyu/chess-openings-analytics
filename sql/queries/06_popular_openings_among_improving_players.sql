-- Popular openings among players who improved
-- players whose highest observed rating is >=100 Elo above their median rating across all their games
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
