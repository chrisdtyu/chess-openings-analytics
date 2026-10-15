# Entity-Relationship Diagram

The diagram below visualises the three-table schema used throughout the project.

```mermaid
erDiagram
    players ||--o{ games : plays_white
    players ||--o{ games : plays_black
    openings ||--o{ games : features

    players {
        SERIAL player_id PK
        TEXT   username  "unique"
        INT    highest_rating
    }
    openings {
        SERIAL opening_id PK
        TEXT   eco
        TEXT   name  "unique"
        TEXT   family
    }
    games {
        TEXT   game_id PK
        TIMESTAMP played_at
        INT    white_id FK
        INT    black_id FK
        INT    white_rating
        INT    black_rating
        TEXT   winner "white, black, or draw"
        TEXT   termination
        INT    ply_count
        INT    opening_id FK
        INT    rating_diff
    }
```

## How to read this ERD

- **players** has a one-to-many relationship to **games** twice: `plays_white` and `plays_black`, capturing each colour
- **openings** has a one-to-many relationship to **games** (`features`), indicating which opening was played; `name` is unique, so each opening is stored once (several names can share an ECO code)
- Surrogate keys (`player_id`, `opening_id`) keep joins fast and compact
- `winner` is limited to `white`, `black`, or `draw` (`NULL` for unfinished games)
- Indexes on `opening_id`, `played_at`, `white_id`, and `black_id` support the joins and date filters used in the queries
- `rating_diff` is a derived metric used for “upset” queries (not a foreign key)

These three tables contain every column referenced by the analytical queries in `README.md`.
