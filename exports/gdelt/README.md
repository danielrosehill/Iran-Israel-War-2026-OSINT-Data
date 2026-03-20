# GDELT Data Exports

Data sourced from [GDELT Project](https://www.gdeltproject.org/) via Google BigQuery (`gdelt-bq` public dataset).

## Authentication

- Any Google account with BigQuery access works (public dataset, no special permissions)
- BigQuery free tier: 1TB/month of queries
- GCP project: any project with BigQuery API enabled

## Exports

### `presstv_military_*.json`

PressTV (Iranian English-language state media) articles tagged with military themes.

**Source table:** `gdelt-bq.gdeltv2.gkg_partitioned`

**Query:**
```sql
SELECT
  DATE,
  PARSE_TIMESTAMP("%Y%m%d%H%M%S", CAST(DATE AS STRING)) as timestamp_utc,
  DocumentIdentifier as url,
  SourceCommonName as source,
  V2Themes,
  V2Locations
FROM `gdelt-bq.gdeltv2.gkg_partitioned`
WHERE DATE >= {START}000000
  AND DATE <= {END}235959
  AND SourceCommonName = "presstv.ir"
  AND (V2Themes LIKE "%MILITARY_ATTACK%"
    OR V2Themes LIKE "%KILL%"
    OR V2Themes LIKE "%WMD%"
    OR V2Themes LIKE "%MISSILES%")
ORDER BY DATE ASC
```

**Key fields:**
- `DATE` — INT64 in `YYYYMMDDHHMMSS` format (15-minute resolution)
- `timestamp_utc` — Parsed UTC timestamp
- `url` — Article URL (slug often contains event detail)
- `V2Themes` — Semicolon-delimited GDELT theme tags
- `V2Locations` — Semicolon-delimited location extractions

**Notes:**
- PressTV is GDELT's primary indexed Iranian state media source
- Tasnim, IRNA, Fars News, Mehr, ISNA are NOT reliably indexed by GDELT
- 15-minute timestamp resolution is useful for correlating with known salvo times

### `events_193_iran_*.json`

Deduplicated CAMEO 193 (fight with artillery/missiles) events geolocated in Iran, grouped by date + location.

**Source table:** `gdelt-bq.gdeltv2.events`

**Query:**
```sql
SELECT
  SQLDATE,
  ActionGeo_FullName,
  ActionGeo_Lat,
  ActionGeo_Long,
  COUNT(*) as event_count,
  SUM(NumArticles) as total_articles,
  SUM(NumSources) as total_sources,
  ARRAY_AGG(DISTINCT SOURCEURL LIMIT 5) as sample_urls
FROM `gdelt-bq.gdeltv2.events`
WHERE ((Actor1CountryCode = "IRN" AND Actor2CountryCode = "ISR")
    OR (Actor1CountryCode = "ISR" AND Actor2CountryCode = "IRN"))
  AND EventCode = "193"
  AND ActionGeo_CountryCode = "IR"
  AND SQLDATE >= {START}
GROUP BY SQLDATE, ActionGeo_FullName, ActionGeo_Lat, ActionGeo_Long
ORDER BY SQLDATE DESC, total_articles DESC
```

**Key fields:**
- `SQLDATE` — Date as `YYYYMMDD` (daily resolution only)
- `ActionGeo_*` — Geocoded location of the event
- `total_articles` — Sum of articles across deduplicated rows (signal strength)
- `total_sources` — Number of distinct sources
- `sample_urls` — Up to 5 representative source URLs

**CAMEO code reference:**
- `193` = Fight with artillery and missiles
- `190` = Use conventional military force (broader)
- `19` = Root code for all use-of-force events

**Known issues:**
- GDELT geocodes entity names as places (e.g. "Hezbollah, Kerman" is a village, not the group)
- "Basij, Fars" similarly — a village name, not the paramilitary
- Actor name variants (IRAN/IRANIAN, ISRAEL/ISRAELI/JERUSALEM) create duplicate rows — use GROUP BY to deduplicate
- Events table has daily resolution only; use GKG for sub-day timestamps

## Useful CAMEO Codes for This Project

| Code | Description |
|------|-------------|
| 190 | Use conventional military force, not specified |
| 191 | Impose blockade, restrict movement |
| 192 | Occupy territory |
| 193 | Fight with small arms and light weapons |
| 194 | Fight with artillery and tanks |
| 195 | Employ aerial weapons |
| 196 | Violate ceasefire |

## Re-running Queries

```bash
# PressTV GKG dump
bq query --use_legacy_sql=false --format=json --max_rows=5000 \
  'QUERY_HERE' 2>/dev/null > presstv_military_STARTDATE_ENDDATE.json

# Events dump
bq query --use_legacy_sql=false --format=json --max_rows=5000 \
  'QUERY_HERE' 2>/dev/null > events_193_iran_STARTDATE_ENDDATE.json
```
