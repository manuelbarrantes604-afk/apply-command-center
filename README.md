# Manuel's board (v5)

Two tabs: **Jobs** (grouped by landing odds) and **Leads** (people at those companies). Static site; no backend.

- `index.html`: the whole UI (plain HTML/CSS/JS)
- `data/jobs.json`: the board. Roles pay $280k+ (posted max) or have an estimated total comp of $280k+ at big-name companies (marked `est`)
- `data/leads.json`: named recruiters and employees (real LinkedIn profiles only), plus LinkedIn search links for companies with no names yet
- `scripts/`: `sweep.py` (LinkedIn guest search, last 30 days) → `score.py shortlist` → `enrich.py` (job-page pay ranges) → `score.py final` → `build_leads.py` → `shots.sh`

Rebuild: `python3 scripts/sweep.py && python3 scripts/score.py shortlist && python3 scripts/enrich.py && python3 scripts/score.py final && python3 scripts/build_leads.py`
