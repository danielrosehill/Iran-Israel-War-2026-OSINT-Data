Add a new attack wave/salvo to the TP4 dataset.

## Instructions

1. Determine the next wave number:

```bash
python3 -c "import json; data=json.load(open('data/tp4-2026/waves.json')); print('Current count:', data['metadata']['incident_count']); waves=data['incidents']; print('Last wave:', max(w['wave_number'] for w in waves))"
```

2. Gather wave details from the user or from arguments: $ARGUMENTS

   Required fields (prompt user if missing):
   - **Wave number** (next in sequence)
   - **Timestamp** (UTC, even approximate)
   - **Targets** (Israel, US bases, or both — with location names)
   - **Weapon types** used
   - **Description** of the wave

   Optional fields (use null if unknown):
   - Codename (Farsi + English)
   - Munitions count
   - Launch coordinates
   - Interception details
   - Casualties/damage
   - Source URLs

3. If details are sparse, use Gemini with search grounding to fill gaps:

```python
import os
from google import genai
from google.genai import types

client = genai.Client()
response = client.models.generate_content(
    model="gemini-3.1-flash-lite-preview",
    contents="YOUR QUERY ABOUT THE SPECIFIC WAVE",
    config=types.GenerateContentConfig(
        tools=[types.Tool(google_search=types.GoogleSearch())],
        temperature=0.2,
    ),
)
print(response.text)
if response.candidates[0].grounding_metadata:
    for chunk in (response.candidates[0].grounding_metadata.grounding_chunks or []):
        if chunk.web:
            print(f"  {chunk.web.title} — {chunk.web.uri}")
```

4. Read the last wave in the dataset to use as a structural template:

```bash
python3 -c "import json; waves=json.load(open('data/tp4-2026/waves.json'))['incidents']; print(json.dumps(waves[-1], indent=2))"
```

5. Add the new wave using Python — generate a UUID, populate all fields following the schema, append to incidents array, and increment metadata.incident_count:

```python
import json, uuid

with open('data/tp4-2026/waves.json') as f:
    data = json.load(f)

new_wave = {
    "uuid": str(uuid.uuid4()),
    "operation": "tp4",
    "sequence": NEXT_NUMBER,
    "wave_number": NEXT_NUMBER,
    # ... all fields following the template structure
}

data['incidents'].append(new_wave)
data['metadata']['incident_count'] = NEXT_NUMBER

with open('data/tp4-2026/waves.json', 'w') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
```

6. Key rules:
   - Use `null` for unknown values, never empty strings
   - Booleans must be native JSON `true`/`false`
   - Timestamps in ISO 8601 with timezone offset
   - Coordinates in decimal degrees
   - `escalation.new_weapon_first_use` = true only if a weapon type is used for the first time in the entire operation
   - `escalation.new_country_targeted` = true only if landings_countries includes a country not previously targeted
   - Set `conflict_day` relative to Feb 28, 2026 (day 1)
   - Generic launch coordinates (33.5, 48.5) if specific site unknown

7. After adding, confirm the wave was added:

```bash
python3 -c "import json; data=json.load(open('data/tp4-2026/waves.json')); w=data['incidents'][-1]; print(f'Added wave {w[\"wave_number\"]}: {w[\"timing\"][\"announced_utc\"]} — {w.get(\"wave_codename_english\",\"N/A\")}')"
```

8. Ask the user if they want to rebuild exports and sync platforms.
