# Iran-Israel War Data

OSINT dataset tracking Iranian missile/drone attack waves against Israel and US/coalition targets across multiple operations.

## Operations Covered

- **True Promise 1** (Apr 13–14, 2024) — First direct Iranian attack on Israel, 2 waves, ~320 munitions
- **True Promise 2** (Oct 1, 2024) — Ballistic-missile-only strike, 2 waves, ~200 munitions
- **True Promise 3** (Jun 13–24, 2025) — "Twelve-Day War", 22 waves, ~1,600-1,800 munitions
- **True Promise 4** (Feb 28–ongoing, 2026) — 27+ waves, expanded to US/coalition targets in Gulf

## Data Access

### Neo4j Graph Database (primary database)

Property graph on Neo4j Aura modelling the war as a network of relationships between actors, weapons, targets, defense systems, and international reactions. Rebuild with `python3 scripts/build_neo4j.py --clear`.

Graph model: War -> Round -> Salvo, with Side/Actor hierarchy, weapons, defense systems, targets, and international reactions.

### JSON Source Files

```
data/
  tp1-2024/waves.json      # TP1 (2 waves, Apr 2024)
  tp2-2024/waves.json      # TP2 (2 waves, Oct 2024)
  tp3-2025/waves.json      # TP3 (22 waves, Jun 2025)
  tp4-2026/waves.json      # TP4 (27 waves, Feb-Mar 2026)
  tp4-2026/reference/      # TP4-specific reference (targets, bases, vessels, launch zones)
  reference/               # Shared reference data (weapons, defense systems, armed forces, bases)
  schema/wave.schema.json  # JSON Schema for validation
```

## Website Repository

The OSINT analysis site is in a separate repo:

- **Repo:** `~/repos/github/Iran-Israel-OSINT-Site/` (private, GitHub: `danielrosehill/Iran-Israel-OSINT-Site`)
- **Deployment:** Vercel at `promisedenied.com`
- **Data pipeline:** The site repo has `sync-data.sh` which pulls JSON from this repo's raw GitHub URLs

Frontend syncing is done manually by the user when needed — do not auto-sync after data updates.

## Post-Update Sync

After updating wave data (adding waves, correcting fields, backfilling), always offer to sync to distribution platforms:

1. **Rebuild Neo4j**: `python3 scripts/build_neo4j.py --clear`
2. **Rebuild Kaggle exports**: `python3 scripts/build_kaggle.py`
3. **Push to Kaggle**: `python3 scripts/upload_kaggle.py`
4. **Sync to HF + Kaggle**: `python3 scripts/sync_platforms.py`

Do not auto-run these — prompt the user after data changes.

## SITREP Format

All SITREPs must follow the template in `docs/sitrep-template.md`:
- **SITREP** is always fully capitalised
- All times in UTC with local times (Israel IST, Iran IRST) in parentheses
- DTG format: `DD HHMM(Z) MON YYYY`
- Sections: BLUF, Situation Overview, Enemy Forces (wave-by-wave), Friendly Forces (interception), Casualties & Damage, Escalation Indicators, Outlook
- SITREPs are narrative documents, not just data tables

## JSON Structure

All four operations (TP1–TP4) use the same schema. Each wave is nested into: `timing`, `weapons` (with `types` + `categories`), `targets` (with `israeli_locations`, `us_bases`, `us_naval_vessels`), `launch_site`, `interception` (with `intercepted_by`), `munitions`, `impact`, `escalation`, `proxy`, `sources`.

## Conventions

- Booleans: native JSON `true`/`false`
- Nulls: `null` for unknown/missing
- Arrays: native JSON arrays for country codes, interception systems, sources
- Timestamps: ISO 8601 with timezone offset
- Coordinates: decimal degrees

## IRGC Wave Count vs Salvo Count

The IRGC announces numbered "waves" (موج) of Operation True Promise. **This count does NOT match our salvo/incident numbering.** Our dataset assigns a sequential salvo number to every distinct attack event, including Hezbollah, Ansar Allah, and Iraqi militia salvos. The IRGC count only covers IRGC-launched waves. Our salvo count is always higher. **Never align IRGC wave numbers with salvo numbers** — doing so has previously caused incorrect data. Note IRGC wave numbers in descriptions/sources but always use sequential salvo numbering.

## OSINT Research Tools

### Gemini with Google Search Grounding

Primary research tool. Uses Gemini 3.1 Flash Lite with native Google Search grounding for sourced, cited answers. API key is in `GOOGLE_API_KEY` environment variable (stored in `.env` and `~/.bashrc`). SDK: `google-genai` (installed in `.venv`).

```python
import os
from google import genai
from google.genai import types

client = genai.Client()  # uses GOOGLE_API_KEY env var

response = client.models.generate_content(
    model="gemini-3.1-flash-lite-preview",
    contents="YOUR QUERY HERE",
    config=types.GenerateContentConfig(
        tools=[types.Tool(google_search=types.GoogleSearch())],
        temperature=0.2,
    ),
)

print(response.text)

# Grounding sources
if response.candidates[0].grounding_metadata:
    for chunk in response.candidates[0].grounding_metadata.grounding_chunks or []:
        if chunk.web:
            print(f"  {chunk.web.title} — {chunk.web.uri}")
```

**Slash command:** `/check-updates-gemini` — Search-grounded check for new waves, data gaps, and updates

Use for:
- Filling data gaps (munitions counts, casualties, interception details)
- Cross-referencing wave details against multiple sources
- Finding codenames, timestamps, and target specifics
- Verifying claims from Iranian state media against independent reporting
- Researching international reactions with sourced citations

### NewsAPI (MCP)

Configured in `.mcp.json` for article/event search via Event Registry. Use `suggest` → `search_articles`/`search_events` workflow. Note: API key may need periodic refresh.

## Python Environment

```bash
uv venv .venv
source .venv/bin/activate
uv pip install astral matplotlib pandas numpy seaborn google-genai
```
