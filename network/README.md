# Warm Path / Network Command

Jobs = what fits. Network = how Manuel gets in.

This folder powers **Path strength**, **Next action**, and **Action score** on top of the Apply Command Center job board. It does **not** scrape LinkedIn, auto-connect, or auto-send messages.

## Action score formula

```
action_score = clamp(round(mid_pct × path_mult × recruiter_mult), 0, 100)
```

| path_strength | multiplier |
|---------------|------------|
| none          | 0.25       |
| weak          | 0.50       |
| warm          | 0.85       |
| strong        | 1.00       |

| recruiter_status | multiplier |
|------------------|------------|
| known            | 1.00       |
| unknown          | 0.75       |

**Never** recommend mass applying or mass connecting. Five real touches > fifty connects.

## Path strength rules

- **strong** — warmth ≥ 4 **1st-degree** at `company_key` in a craft-relevant function (marketplace / ops / product / workforce / cx / trust_safety), **or** person explicitly lists this `jobId` in `unlocks_job_ids`
- **warm** — any 1st-degree at company, **or** ex-employee warmth ≥ 3, **or** alumni warmth ≥ 4
- **weak** — recruiter only at company, **or** target warmth ≥ 3, **or** any other connection at company
- **none** — nobody mapped

Without a Connections CSV (and with empty overlay), **almost every job stays `none`**. That is intentional honesty — do not invent 1st-degree contacts.

## Files

| File | Purpose |
|------|---------|
| `connections.csv` | Your LinkedIn Connections export (headers only until you drop data) |
| `connections.sample.csv` | Header template |
| `overlay.json` | 30–80 people you maintain (starts as `[]`) |
| `overlay.sample.json` / `.csv` | Schema + EXAMPLE rows (`"example": true` — filtered out of live scoring) |
| `build_network.py` | Offline rebuild → `network.json` |
| `network.json` | Output: people, jobs_enriched, war_rooms, this_week, meta |
| `last_sweep_meta.json` | Prior action_scores for path_improved deltas |

## LinkedIn Connections export (official)

1. LinkedIn → **Settings & Privacy** → **Data privacy** → **Get a copy of your data**
2. Select **Connections** only (faster) → Request archive
3. Download ZIP when ready → extract `Connections.csv`
4. Copy to this folder as `connections.csv` (keep headers: First Name, Last Name, Email Address, Company, Position, Connected On)
5. Re-run: `python3 build_network.py`

**OR (recommended on phone / GitHub Pages):** open the live Command Center → **Ingest** tab → upload Connections CSV + overlay JSON in-browser. Scoring runs locally via FileReader; data stays in `localStorage` on your device and is **never** uploaded to GitHub.

## Overlay (people you maintain)

Maintain 30–80 high-signal people (recruiters, ex-employees, alumni, targets). Schema fields:

`id`, `first_name`, `last_name`, `email`, `company`, `company_key`, `title`, `function` (`marketplace|ops|recruiting|product|workforce|cx|trust_safety|other`), `warmth` (1–5), `type` (`1st-degree|target|recruiter|ex-employee|alumni`), `why_matters`, `unlocks_job_ids`, `last_touch`, `draft_available`, `status` (`active|to_contact|to_add|waiting|done|skip`), `notes`, `linkedin_url`, optional `example`

Copy `overlay.sample.json` → edit → save as `overlay.json`. Remove `"example": true` only for **real** people Manuel knows. War Rooms list **missing seats** and **future connection targets** as role placeholders — never fabricated names pretending to be known.

## Bentonville / Walmart internal

If `why` contains “Bentonville internal” or geo is Bentonville + company Walmart, next actions prioritize **internal apply + ex-Walmart / Spark ops peer + posting recruiter** over cold external apply.

## Rebuild

```bash
cd /workspace/job-scout/dashboard/network
python3 build_network.py
# writes network/network.json and dashboard/network.json
```

## Privacy

- Do not commit real `connections.csv` with PII to a public GitHub repo.
- Prefer in-browser upload on the live site (localStorage only).
- Keep real overlay private; publish only empty `overlay.json` / prebuilt empty-network `network.json`.
