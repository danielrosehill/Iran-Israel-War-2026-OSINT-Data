#!/usr/bin/env python3
"""Export all incident data to flattened CSV and Parquet for Kaggle."""

import json
import os
import shutil
import pandas as pd

from wave_enrichment import (
    classify_target_types, get_cluster_munitions, countries_iso_to_names,
    get_wave_uid, WAVE_NARRATIVES,
)

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

WAVE_FILES = [
    ('tp1', os.path.join(REPO, 'data', 'tp1-2024', 'waves.json')),
    ('tp2', os.path.join(REPO, 'data', 'tp2-2024', 'waves.json')),
    ('tp3', os.path.join(REPO, 'data', 'tp3-2025', 'waves.json')),
    ('tp4', os.path.join(REPO, 'data', 'tp4-2026', 'waves.json')),
]

REACTIONS_FILES = [
    ('tp4', os.path.join(REPO, 'data', 'tp4-2026', 'international_reactions.json')),
]

KAGGLE_DIR = os.path.join(REPO, 'kaggle')


def flatten_incident(op, wave):
    """Flatten a nested incident JSON object into a single dict."""
    t = wave.get('timing', {})
    w = wave.get('weapons', {})
    wt = w.get('types', {})
    wc = w.get('categories', {})
    cw = w.get('cluster_warhead', {})
    if not isinstance(cw, dict):
        cw = {}
    tgt = wave.get('targets', {})
    iloc = tgt.get('israeli_locations', {})
    ls = wave.get('launch_site', {})
    interc = wave.get('interception', {})
    iby_raw = interc.get('intercepted_by', {})
    iby = iby_raw if isinstance(iby_raw, dict) else {}
    mun = wave.get('munitions', {})
    imp = wave.get('impact', {})
    esc = wave.get('escalation', {})
    prx = wave.get('proxy', {})
    src_raw = wave.get('sources', {})
    src = src_raw if isinstance(src_raw, dict) else {}
    tc = tgt.get('target_coordinates', {}) or {}

    wave_uid = get_wave_uid(op, wave.get('wave_number', 0))
    target_types = classify_target_types(wave)

    return {
        'wave_uid': wave_uid,
        'operation': op,
        'wave_number': wave.get('wave_number'),
        'wave_codename_farsi': wave.get('wave_codename_farsi'),
        'wave_codename_english': wave.get('wave_codename_english'),
        # timing
        'announced_utc': t.get('announced_utc'),
        'announcement_source': t.get('announcement_source'),
        'probable_launch_time': t.get('probable_launch_time'),
        'launch_time_israel': t.get('launch_time_israel'),
        'launch_time_iran': t.get('launch_time_iran'),
        'solar_phase_launch_site': t.get('solar_phase_launch_site'),
        'solar_phase_target': t.get('solar_phase_target'),
        'conflict_day': t.get('conflict_day'),
        'hours_since_last_incident': t.get('hours_since_last_incident'),
        'time_between_incidents_minutes': t.get('time_between_incidents_minutes'),
        'incident_duration_minutes': t.get('incident_duration_minutes'),
        # weapons
        'payload': w.get('payload'),
        'drones_used': w.get('drones_used'),
        'ballistic_missiles_used': w.get('ballistic_missiles_used'),
        'cruise_missiles_used': w.get('cruise_missiles_used'),
        'emad_used': wt.get('emad_used'),
        'ghadr_used': wt.get('ghadr_used'),
        'sejjil_used': wt.get('sejjil_used'),
        'kheibar_shekan_used': wt.get('kheibar_shekan_used'),
        'fattah_used': wt.get('fattah_used'),
        'shahed_136_used': wt.get('shahed_136_used'),
        'shahed_238_used': wt.get('shahed_238_used'),
        'shahed_131_used': wt.get('shahed_131_used'),
        'shahed_107_used': wt.get('shahed_107_used'),
        'shahed_129_used': wt.get('shahed_129_used'),
        'mohajer_6_used': wt.get('mohajer_6_used'),
        'bm_liquid_fueled': wc.get('bm_liquid_fueled'),
        'bm_solid_fueled': wc.get('bm_solid_fueled'),
        'bm_marv_equipped': wc.get('bm_marv_equipped'),
        'bm_hypersonic': wc.get('bm_hypersonic'),
        'bm_cluster_warhead': wc.get('bm_cluster_warhead'),
        'cluster_munitions': get_cluster_munitions(wave),
        # cluster warhead
        'cluster_warhead_confirmed': cw.get('confirmed'),
        'cluster_carrier_missile': cw.get('carrier_missile'),
        'cluster_submunition_count': cw.get('submunition_count'),
        'cluster_submunition_explosive_kg': cw.get('submunition_explosive_kg'),
        'cluster_dispersal_radius_km': cw.get('dispersal_radius_km'),
        # targets
        'israel_targeted': tgt.get('israel_targeted'),
        'us_bases_targeted': tgt.get('us_bases_targeted'),
        'targets': tgt.get('targets'),
        'landings_countries_iso': ', '.join(sorted(tgt.get('landings_countries', []) or [])),
        'landings_countries': countries_iso_to_names(tgt.get('landings_countries')),
        'targeted_tel_aviv': iloc.get('targeted_tel_aviv'),
        'targeted_jerusalem': iloc.get('targeted_jerusalem'),
        'targeted_haifa': iloc.get('targeted_haifa'),
        'targeted_negev_beersheba': iloc.get('targeted_negev_beersheba'),
        'targeted_northern_periphery': iloc.get('targeted_northern_periphery'),
        'targeted_eilat': iloc.get('targeted_eilat'),
        'us_bases_list': ', '.join(
            b.get('name', str(b)) if isinstance(b, dict) else str(b)
            for b in (tgt.get('us_bases', []) or [])
        ),
        'us_naval_vessels_list': ', '.join(
            v.get('name', str(v)) if isinstance(v, dict) else str(v)
            for v in (tgt.get('us_naval_vessels', []) or [])
        ),
        'target_lat': tc.get('lat'),
        'target_lon': tc.get('lon'),
        'target_generic_location': tc.get('generic_location'),
        # launch site
        'launch_site_description': ls.get('description'),
        'launch_site_lat': ls.get('lat'),
        'launch_site_lon': ls.get('lon'),
        'launch_site_generic_location': ls.get('generic_location'),
        # interception
        'intercepted': interc.get('intercepted'),
        'interception_systems': ', '.join(interc.get('interception_systems', []) or []),
        'intercepted_by_israel': iby.get('israel'),
        'intercepted_by_us': iby.get('us'),
        'intercepted_by_uk': iby.get('uk'),
        'intercepted_by_jordan': iby.get('jordan'),
        'intercepted_by_other': ', '.join(iby.get('other', []) or []),
        'estimated_intercept_count': interc.get('estimated_intercept_count'),
        'estimated_intercept_rate': interc.get('estimated_intercept_rate'),
        'exoatmospheric_interception': interc.get('exoatmospheric_interception'),
        'endoatmospheric_interception': interc.get('endoatmospheric_interception'),
        'interception_report': interc.get('interception_report'),
        # munitions
        'estimated_munitions_count': mun.get('estimated_munitions_count'),
        'munitions_targeting_israel': mun.get('munitions_targeting_israel'),
        'munitions_targeting_us_bases': mun.get('munitions_targeting_us_bases'),
        'cumulative_total': mun.get('cumulative_total'),
        'small_number_of_missiles': mun.get('small_number_of_missiles'),
        # impact
        'damage': imp.get('damage'),
        'fatalities': imp.get('fatalities'),
        'injuries': imp.get('injuries'),
        'civilian_casualties': imp.get('civilian_casualties'),
        'military_casualties': imp.get('military_casualties'),
        # escalation
        'new_country_targeted': esc.get('new_country_targeted'),
        'new_weapon_first_use': esc.get('new_weapon_first_use'),
        # proxy
        'proxy_involvement': prx.get('involvement'),
        'proxy_description': prx.get('description'),
        # description
        'description': wave.get('description'),
        'iranian_media_claims': json.dumps(wave.get('iranian_media_claims')) if isinstance(wave.get('iranian_media_claims'), (dict, list)) else wave.get('iranian_media_claims'),
        # sources
        'idf_statement': src.get('idf_statement'),
        'source_urls': ', '.join(src.get('urls', []) or []),
        # target type classification
        **target_types,
        # narrative
        'narrative': WAVE_NARRATIVES.get(wave_uid),
    }


def flatten_reaction(op, reaction):
    """Flatten a nested international reaction JSON object into a single dict."""
    hos = reaction.get('head_of_state_statement', {}) or {}
    hog = reaction.get('head_of_government_statement', {}) or {}
    fm = reaction.get('foreign_ministry_statement', {}) or {}
    addl = reaction.get('additional_statements', []) or []

    return {
        'operation': op,
        'iso_3166_1_alpha2': reaction.get('iso_3166_1_alpha2'),
        'entity_name': reaction.get('entity_name'),
        'entity_type': reaction.get('entity_type'),
        'eu_member_state': reaction.get('eu_member_state'),
        'combatant': reaction.get('combatant'),
        'overall_stance': reaction.get('overall_stance'),
        # head of state
        'hos_statement_made': hos.get('made'),
        'hos_date': hos.get('date'),
        'hos_speaker': hos.get('speaker'),
        'hos_speaker_title': hos.get('speaker_title'),
        'hos_summary': hos.get('summary'),
        'hos_statement_text': hos.get('statement_text'),
        'hos_statement_url': hos.get('statement_url'),
        'hos_category': hos.get('category'),
        # head of government
        'hog_statement_made': hog.get('made'),
        'hog_date': hog.get('date'),
        'hog_speaker': hog.get('speaker'),
        'hog_speaker_title': hog.get('speaker_title'),
        'hog_summary': hog.get('summary'),
        'hog_statement_text': hog.get('statement_text'),
        'hog_statement_url': hog.get('statement_url'),
        'hog_category': hog.get('category'),
        # foreign ministry
        'fm_statement_made': fm.get('made'),
        'fm_date': fm.get('date'),
        'fm_speaker': fm.get('speaker'),
        'fm_speaker_title': fm.get('speaker_title'),
        'fm_summary': fm.get('summary'),
        'fm_statement_text': fm.get('statement_text'),
        'fm_statement_url': fm.get('statement_url'),
        'fm_category': fm.get('category'),
        # additional statements
        'additional_statements_count': len(addl),
        'additional_statements_json': json.dumps(addl) if addl else None,
        # notes
        'notes': reaction.get('notes'),
    }


def main():
    os.makedirs(KAGGLE_DIR, exist_ok=True)

    # --- Incidents ---
    rows = []
    for op, path in WAVE_FILES:
        with open(path) as f:
            data = json.load(f)
        for incident in data['incidents']:
            rows.append(flatten_incident(op, incident))

    df = pd.DataFrame(rows)

    csv_path = os.path.join(KAGGLE_DIR, 'incidents.csv')
    parquet_path = os.path.join(KAGGLE_DIR, 'incidents.parquet')

    df.to_csv(csv_path, index=False)
    df.to_parquet(parquet_path, index=False)

    print(f"Exported {len(df)} incidents to:")
    print(f"  {csv_path} ({os.path.getsize(csv_path) // 1024} KB)")
    print(f"  {parquet_path} ({os.path.getsize(parquet_path) // 1024} KB)")
    print(f"  Columns: {len(df.columns)}")
    print(f"  Operations: {df['operation'].value_counts().to_dict()}")

    # --- International Reactions ---
    reaction_rows = []
    for op, path in REACTIONS_FILES:
        if os.path.exists(path):
            with open(path) as f:
                data = json.load(f)
            for reaction in data.get('reactions', []):
                reaction_rows.append(flatten_reaction(op, reaction))

    if reaction_rows:
        rdf = pd.DataFrame(reaction_rows)
        r_csv = os.path.join(KAGGLE_DIR, 'international_reactions.csv')
        r_parquet = os.path.join(KAGGLE_DIR, 'international_reactions.parquet')
        rdf.to_csv(r_csv, index=False)
        rdf.to_parquet(r_parquet, index=False)
        print(f"\nExported {len(rdf)} international reactions to:")
        print(f"  {r_csv} ({os.path.getsize(r_csv) // 1024} KB)")
        print(f"  {r_parquet} ({os.path.getsize(r_parquet) // 1024} KB)")
        print(f"  Columns: {len(rdf.columns)}")

    # Copy data dictionary into kaggle export directory
    dict_src = os.path.join(REPO, 'data', 'data_dictionary.csv')
    if os.path.exists(dict_src):
        shutil.copy2(dict_src, os.path.join(KAGGLE_DIR, 'data_dictionary.csv'))

    print(f"\nDone.")


if __name__ == '__main__':
    main()
