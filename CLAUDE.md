# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MASBills is a data inventory of Singapore Monetary Authority of Singapore (MAS) Bill auction records. This is a data-only repository with no application code, build system, or tests.

## Data

The sole data file is `inventory/MAS Bills - MAS Bills.csv` containing MAS Bill auction records with the following columns:

| Column | Description |
|---|---|
| Announcement Date | When the bill auction is announced (DD/MM/YYYY) |
| Auction Date | When bidding occurs (DD/MM/YYYY) |
| Issue Date | When the bill is issued (DD/MM/YYYY) |
| Maturity Date | When the bill matures (DD/MM/YYYY) |
| Tenor | Duration: 4-week, 12-week, or 36-week |
| Issue Code | MAS identifier (e.g., MD26101F for 4-week, ML26101A for 12-week, MA26100V for 36-week) |
| ISIN Code | International Securities Identification Number (SGX-prefixed) |
| Status | "Closed" or "Upcoming" |

Issue code prefixes: **MD** = 4-week, **ML** = 12-week, **MA** = 36-week.

Dates use **DD/MM/YYYY** format. The CSV includes a UTF-8 BOM marker.

## Scripts

| Script | Purpose |
|---|---|
| `scraper.py` | Scrapes Cut-off Yield for all closed bills from MAS website (Selenium) |
| `export_excel.py` | Exports CSV to `inventory/MAS Bills - MAS Bills.xlsx` |
| `scrape_upcoming.py` | Scrapes upcoming bills up to a given date, updates CSV |
| `post_to_roam.py` | Posts auction results to Roam Research daily pages |

## Roam Research Integration

Credentials are stored in the `Roam_Research` file (not committed). See `ROAM_API_NOTES.md` for known API quirks that must be handled in code.

Key implementation details for `post_to_roam.py`:
- **Auth on redirects:** Roam's API redirects requests to a different host (e.g. `peer-*.api.roamresearch.com`). Python `requests` strips the `Authorization` header on cross-host redirects. Use a `requests.Session` with `rebuild_auth` overridden to `lambda prepared, response: None` to preserve the header.
- **Write endpoint returns empty body:** The `/write` endpoint returns HTTP 200 with an empty body — do not call `.json()` on write responses. To nest child blocks, generate a UUID for the parent block and pass it as `block.uid` during creation.
- **Callout formatting:** Auction results are posted as a single multi-line block using Roam's callout syntax. The first line is `> [!Summary]+ **title**` and each subsequent auction row is appended as a plain text line, all joined with `\n`. This renders as callout content without bullet points.
