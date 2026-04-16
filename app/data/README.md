# Data files

## `ai_personalities.csv`

This CSV drives the word-cloud endpoint. It maps planet × sign (or
planet × house) combinations to positive and negative trait keywords.

Expected columns:

| Column           | Description                                           |
|------------------|-------------------------------------------------------|
| `Planet`         | Sun, Moon, Mercury, …                                 |
| `SignsAndHouses` | A sign name (e.g. `Aries`) or house number (`1`–`12`) |
| `Positives`      | Comma-separated positive trait keywords               |
| `Negatives`      | Comma-separated negative trait keywords               |

Matching is done after stripping spaces from every cell, so
`"self-assertive, bold"` becomes `"self-assertive,bold"` at load time.

This file is **not** bundled with the repo because the trait text is
author-specific. Copy your own `ai_personalities.csv` into this
directory (or point `PERSONALITIES_CSV` at a different path).

A toy example is provided as `ai_personalities.sample.csv` so the
`/chart/wordcloud` endpoint returns something in local dev.
