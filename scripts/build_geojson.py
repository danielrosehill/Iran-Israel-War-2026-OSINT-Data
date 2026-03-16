#!/usr/bin/env python3
"""
Build GeoJSON FeatureCollection from all incident JSON data.

Produces two layers:
  - launch_sites: Point features at each incident's launch site
  - targets: Point features at each incident's target coordinates
    Resolves MULTIPLE targets per incident from:
      1. targets.target_locations array (if present, from backfill)
      2. targets.israeli_locations boolean flags → reference coords
      3. targets.us_bases array → reference coords
      4. Legacy targets.target_coordinates as fallback

Incidents missing coordinates are included with null geometry.

Usage:
    python build_geojson.py [--output PATH]

Outputs (default):
    exports/incidents_launch_sites.geojson
    exports/incidents_targets.geojson
    exports/incidents_combined.geojson   (both layers merged)
"""

import json
import os
import sys
import argparse
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from normalization import Normalizer

_normalizer = Normalizer()

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

WAVE_FILES = [
    ('tp1', os.path.join(REPO, 'data', 'tp1-2024', 'waves.json')),
    ('tp2', os.path.join(REPO, 'data', 'tp2-2024', 'waves.json')),
    ('tp3', os.path.join(REPO, 'data', 'tp3-2025', 'waves.json')),
    ('tp4', os.path.join(REPO, 'data', 'tp4-2026', 'waves.json')),
]

# Mapping from israeli_locations boolean flags to default target name and coords.
ISRAELI_FLAG_DEFAULTS = {
    "targeted_tel_aviv": {
        "name": "Tel Aviv (general)",
        "lat": 32.07, "lon": 34.77,
    },
    "targeted_jerusalem": {
        "name": "East Jerusalem",
        "lat": 31.78, "lon": 35.24,
    },
    "targeted_haifa": {
        "name": "Haifa Naval Base",
        "lat": 32.82, "lon": 35.0,
    },
    "targeted_negev_beersheba": {
        "name": "Nevatim Airbase",
        "lat": 31.21, "lon": 34.82,
    },
    "targeted_northern_periphery": {
        "name": "Galilee (general)",
        "lat": 32.85, "lon": 35.5,
    },
    "targeted_eilat": {
        "name": "Eilat (approximate)",
        "lat": 29.56, "lon": 34.95,
    },
}


def _load_json_with_fallback(primary_path, fallback_path):
    """Load JSON from primary_path, falling back to fallback_path."""
    for p in (primary_path, fallback_path):
        if os.path.isfile(p):
            with open(p) as f:
                return json.load(f)
    return []


def load_reference_data():
    """Load israeli_targets.json and us_bases.json reference files.

    Looks first in data/tp4-2026/reference/, then falls back to data/reference/.
    Returns (israeli_targets_by_name, us_bases_by_name) dicts keyed by lowercase name.
    """
    israeli_primary = os.path.join(REPO, 'data', 'tp4-2026', 'reference', 'israeli_targets.json')
    israeli_fallback = os.path.join(REPO, 'data', 'reference', 'israeli_targets.json')
    israeli_list = _load_json_with_fallback(israeli_primary, israeli_fallback)

    us_primary = os.path.join(REPO, 'data', 'tp4-2026', 'reference', 'us_bases.json')
    us_fallback = os.path.join(REPO, 'data', 'reference', 'us_bases.json')
    us_list = _load_json_with_fallback(us_primary, us_fallback)

    # Build lookup dicts keyed by lowercase name (and aliases)
    israeli_by_name = {}
    for entry in israeli_list:
        israeli_by_name[entry['name'].lower()] = entry
        for alias in entry.get('aliases', []):
            israeli_by_name[alias.lower()] = entry

    us_by_name = {}
    for entry in us_list:
        us_by_name[entry['name'].lower()] = entry

    return israeli_by_name, us_by_name


def _get_primary_actor(w):
    """Return the top-level actor for an incident (e.g. 'Iran', 'Hezbollah').

    Uses the Normalizer to resolve subunits to their state-level actor.
    """
    af_list = w.get('attacking_force', [])
    if isinstance(af_list, dict):
        af_list = [af_list]
    if not af_list:
        return 'Unknown'
    raw = af_list[0].get('actor', 'Unknown')
    return _normalizer.actor_top_level(raw)


def _parse_launch_time(w):
    """Parse probable_launch_time to a datetime, or None."""
    t = w.get('timing', {}).get('probable_launch_time')
    if not t:
        return None
    try:
        return datetime.fromisoformat(t.replace('Z', '+00:00'))
    except (ValueError, TypeError):
        return None


def compute_derived_fields(all_incidents_by_op):
    """Compute actor_salvo_number and coordinated_attack for all incidents.

    Returns:
        coord_map: {(op, wn): (bool, int|None)}
        actor_seq_map: {(op, wn): int}
    """
    coord_map = {}
    actor_seq_map = {}

    for op_id, incidents in all_incidents_by_op.items():
        actor_counts = {}
        for w in incidents:
            wn = w['wave_number']
            actor = _get_primary_actor(w)
            actor_counts[actor] = actor_counts.get(actor, 0) + 1
            actor_seq_map[(op_id, wn)] = actor_counts[actor]

        for i, w in enumerate(incidents):
            wn = w['wave_number']
            if (op_id, wn) in coord_map:
                continue
            actor_i = _get_primary_actor(w)
            time_i = _parse_launch_time(w)
            if not time_i:
                coord_map[(op_id, wn)] = (False, None)
                continue

            paired = False
            for j, w2 in enumerate(incidents):
                if i == j:
                    continue
                actor_j = _get_primary_actor(w2)
                if actor_j == actor_i:
                    continue
                time_j = _parse_launch_time(w2)
                if not time_j:
                    continue
                if abs((time_i - time_j).total_seconds()) / 60.0 <= 15:
                    wn2 = w2['wave_number']
                    coord_map[(op_id, wn)] = (True, wn2)
                    coord_map[(op_id, wn2)] = (True, wn)
                    paired = True
                    break
            if not paired:
                coord_map[(op_id, wn)] = (False, None)

    return coord_map, actor_seq_map


def load_all_incidents():
    """Load incidents from all operation JSON files."""
    all_by_op = {}
    incidents = []
    for op, path in WAVE_FILES:
        with open(path) as f:
            data = json.load(f)
        op_incidents = []
        for w in data['incidents']:
            w['_operation'] = op
            op_incidents.append(w)
            incidents.append(w)
        all_by_op[op] = op_incidents

    # Compute and attach derived fields
    coord_map, actor_seq_map = compute_derived_fields(all_by_op)
    for w in incidents:
        op = w['_operation']
        wn = w['wave_number']
        coordinated, coord_with = coord_map.get((op, wn), (False, None))
        w['_coordinated_attack'] = coordinated
        w['_coordinated_with_salvo'] = coord_with
        w['_actor_salvo_number'] = actor_seq_map.get((op, wn))

    return incidents


def make_point(lat, lon):
    """Return a GeoJSON Point geometry, or None if coords are missing."""
    if lat is not None and lon is not None:
        return {"type": "Point", "coordinates": [lon, lat]}
    return None


def incident_properties(w):
    """Extract flat properties for a GeoJSON feature."""
    timing = w.get('timing', {})
    weapons = w.get('weapons', {})
    munitions = w.get('munitions', {})
    interception = w.get('interception', {})
    impact = w.get('impact', {})
    targets = w.get('targets', {})

    return {
        "operation": w.get('_operation'),
        "sequence": w.get('sequence'),
        "wave_number": w.get('wave_number'),
        "wave_id": f"{w.get('_operation')}_w{w.get('sequence')}",
        "wave_codename_english": w.get('wave_codename_english'),
        "wave_codename_farsi": w.get('wave_codename_farsi'),
        "announced_utc": timing.get('announced_utc'),
        "probable_launch_time": timing.get('probable_launch_time'),
        "conflict_day": timing.get('conflict_day'),
        "payload": weapons.get('payload'),
        "drones_used": weapons.get('drones_used'),
        "ballistic_missiles_used": weapons.get('ballistic_missiles_used'),
        "cruise_missiles_used": weapons.get('cruise_missiles_used'),
        "estimated_munitions_count": munitions.get('estimated_munitions_count'),
        "munitions_targeting_israel": munitions.get('munitions_targeting_israel'),
        "munitions_targeting_us_bases": munitions.get('munitions_targeting_us_bases'),
        "interception_rate": interception.get('estimated_intercept_rate'),
        "intercepted_count": interception.get('estimated_intercept_count'),
        "israel_targeted": targets.get('israel_targeted'),
        "us_bases_targeted": targets.get('us_bases_targeted'),
        "landing_countries": targets.get('landings_countries'),
        "casualties_killed": impact.get('fatalities'),
        "casualties_wounded": impact.get('injuries'),
        "launch_site_description": w.get('launch_site', {}).get('description'),
        # Actor & coordination fields
        "attacking_force_actor": _get_primary_actor(w),
        "attacking_force_branch": _normalizer.actor_branch(
            (w.get('attacking_force') or [{}])[0].get('actor') if isinstance(w.get('attacking_force'), list) else None
        ),
        "attacking_force_actors": [a.get('actor') for a in (w.get('attacking_force') or []) if isinstance(a, dict)],
        "actor_salvo_number": w.get('_actor_salvo_number'),
        "coordinated_attack": w.get('_coordinated_attack', False),
        "coordinated_with_salvo": w.get('_coordinated_with_salvo'),
    }


def _fuzzy_match_israeli(name, israeli_ref):
    """Try to match a target name to Israeli reference data with fuzzy matching."""
    name_lower = name.lower()
    # Direct match
    if name_lower in israeli_ref:
        ref = israeli_ref[name_lower]
        return ref.get('lat'), ref.get('lon')

    # Keyword-based matching for common backfill names
    KEYWORD_MAP = {
        'tel aviv': 'tel aviv (general)',
        'jerusalem': 'east jerusalem',
        'haifa': 'haifa naval base',
        'negev': 'nevatim airbase',
        'nevatim': 'nevatim airbase',
        'beersheba': 'beersheba army communications complex',
        'northern': 'galilee (general)',
        'galilee': 'galilee (general)',
        'eilat': 'eilat (approximate)',
    }
    for keyword, ref_name in KEYWORD_MAP.items():
        if keyword in name_lower:
            ref = israeli_ref.get(ref_name)
            if ref:
                return ref.get('lat'), ref.get('lon')
            # Fall back to flag defaults
            for flag_key, defaults in ISRAELI_FLAG_DEFAULTS.items():
                if defaults['name'].lower() == ref_name:
                    return defaults['lat'], defaults['lon']

    # Try flag defaults directly
    for flag_key, defaults in ISRAELI_FLAG_DEFAULTS.items():
        if defaults['name'].lower() in name_lower or name_lower in defaults['name'].lower():
            return defaults['lat'], defaults['lon']

    return None, None


def resolve_targets(w, israeli_ref, us_ref):
    """Resolve all target locations for an incident.

    Returns a list of dicts, each with keys:
        target_name, target_type, lat, lon, target_hit

    Resolution order:
    1. targets.target_locations array (from backfill, has per-target hit status)
    2. targets.israeli_locations boolean flags → look up in israeli_ref or use defaults
    3. targets.us_bases array → look up in us_ref
    4. Fallback: legacy target_coordinates (if no targets resolved above)
    """
    resolved = []
    targets = w.get('targets', {})

    # 1. Use target_locations if present (from target_hit backfill)
    target_locs = targets.get('target_locations', [])
    if target_locs:
        for tl in target_locs:
            name = tl.get('name', '')
            ttype = tl.get('type', 'unknown')
            hit = tl.get('hit')

            # Look up coords from reference data
            lat, lon = None, None
            if ttype == 'israeli':
                lat, lon = _fuzzy_match_israeli(name, israeli_ref)
            elif ttype == 'us_base':
                # Try exact match first, then substring
                ref = us_ref.get(name.lower())
                if ref:
                    lat, lon = ref.get('lat'), ref.get('lon')
                else:
                    for ref_name, ref_entry in us_ref.items():
                        if name.lower() in ref_name or ref_name in name.lower():
                            lat, lon = ref_entry.get('lat'), ref_entry.get('lon')
                            break

            resolved.append({
                'target_name': name,
                'target_type': ttype,
                'lat': lat,
                'lon': lon,
                'target_hit': hit,
            })

        # If all resolved targets lack coordinates, try target_coordinates fallback
        tc = targets.get('target_coordinates', {})
        if tc.get('lat') and tc.get('lon'):
            for r in resolved:
                if r['lat'] is None and r['lon'] is None:
                    r['lat'] = tc['lat']
                    r['lon'] = tc['lon']

        return resolved

    # 2. Resolve Israeli location flags
    israeli_locs = targets.get('israeli_locations', {})
    for flag_key, defaults in ISRAELI_FLAG_DEFAULTS.items():
        if israeli_locs.get(flag_key):
            ref_entry = israeli_ref.get(defaults['name'].lower())
            if ref_entry:
                lat = ref_entry.get('lat', defaults['lat'])
                lon = ref_entry.get('lon', defaults['lon'])
                name = ref_entry.get('name', defaults['name'])
            else:
                lat = defaults['lat']
                lon = defaults['lon']
                name = defaults['name']
            resolved.append({
                'target_name': name,
                'target_type': 'israeli',
                'lat': lat,
                'lon': lon,
                'target_hit': None,
            })

    # 3. Resolve US bases from the us_bases array
    us_bases_list = targets.get('us_bases', [])
    for base_entry in us_bases_list:
        if isinstance(base_entry, dict):
            base_name = base_entry.get('name') or base_entry.get('base_name', '')
        else:
            base_name = str(base_entry)
        if not base_name:
            continue
        ref_entry = us_ref.get(base_name.lower())
        if ref_entry:
            resolved.append({
                'target_name': ref_entry.get('name', base_name),
                'target_type': 'us_base',
                'lat': ref_entry.get('lat'),
                'lon': ref_entry.get('lon'),
                'target_hit': None,
            })
        else:
            resolved.append({
                'target_name': base_name,
                'target_type': 'us_base',
                'lat': None,
                'lon': None,
                'target_hit': None,
            })

    # 4. Fallback: legacy target_coordinates if nothing was resolved
    if not resolved:
        tc = targets.get('target_coordinates', {})
        resolved.append({
            'target_name': tc.get('generic_location'),
            'target_type': 'legacy',
            'lat': tc.get('lat'),
            'lon': tc.get('lon'),
            'target_hit': targets.get('target_hit'),
        })

    return resolved


def build_features(incidents, israeli_ref, us_ref):
    """Build launch-site and target feature lists."""
    launch_features = []
    target_features = []

    for w in incidents:
        props = incident_properties(w)
        ls = w.get('launch_site', {})

        # Launch site feature (one per incident, unchanged)
        launch_geom = make_point(ls.get('lat'), ls.get('lon'))
        launch_props = {
            **props,
            "layer": "launch_site",
            "generic_location": ls.get('generic_location'),
        }
        launch_features.append({
            "type": "Feature",
            "geometry": launch_geom,
            "properties": launch_props,
        })

        # Target features (multiple per incident)
        resolved = resolve_targets(w, israeli_ref, us_ref)
        for idx, t in enumerate(resolved):
            target_geom = make_point(t['lat'], t['lon'])
            target_props = {
                **props,
                "layer": "target",
                "target_index": idx,
                "target_name": t['target_name'],
                "target_type": t['target_type'],
                "target_hit": t['target_hit'],
                "generic_location": t['target_name'],
            }
            target_features.append({
                "type": "Feature",
                "geometry": target_geom,
                "properties": target_props,
            })

    return launch_features, target_features


def feature_collection(features):
    return {
        "type": "FeatureCollection",
        "features": features,
    }


def main():
    parser = argparse.ArgumentParser(description='Build GeoJSON from incident data')
    parser.add_argument('--output-dir', default=os.path.join(REPO, 'exports', 'latest'),
                        help='Output directory')
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    # Load reference data for target resolution
    israeli_ref, us_ref = load_reference_data()
    print(f"Reference data: {len(israeli_ref)} Israeli targets, {len(us_ref)} US bases")

    incidents = load_all_incidents()
    launch_features, target_features = build_features(incidents, israeli_ref, us_ref)

    # Write individual layers
    for name, features in [('incidents_launch_sites', launch_features),
                           ('incidents_targets', target_features)]:
        path = os.path.join(args.output_dir, f'{name}.geojson')
        with open(path, 'w') as f:
            json.dump(feature_collection(features), f, indent=2, ensure_ascii=False)
        geo_count = sum(1 for feat in features if feat['geometry'] is not None)
        print(f"  {path}: {len(features)} features ({geo_count} with coordinates)")

    # Write combined
    combined = launch_features + target_features
    path = os.path.join(args.output_dir, f'incidents_combined.geojson')
    with open(path, 'w') as f:
        json.dump(feature_collection(combined), f, indent=2, ensure_ascii=False)
    print(f"  {path}: {len(combined)} features (combined)")

    print(f"\nDone — {len(incidents)} incidents, {len(target_features)} target features across {len(WAVE_FILES)} operations.")


if __name__ == '__main__':
    main()
