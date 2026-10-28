"""Read-only P0 comparison. Intervals are never asserted to be individual matches."""
import argparse
import json
from pathlib import Path


def compare(before, after):
    if before.get('season_start_year') != after.get('season_start_year'):
        return [{'status': 'SEASON_CHANGED', 'delta': None}]
    def indexed(doc):
        return {(r['playerid'], r['teamid'], r['compobjid']): r for r in doc['rows']}
    old, new = indexed(before), indexed(after)
    result = []
    for key in sorted(old.keys() | new.keys()):
        if key not in old or key not in new:
            result.append({'key': key, 'status': 'MISSING_BASELINE_OR_ROW', 'delta': None})
            continue
        delta = {k: new[key][k] - old[key][k]
                 if new[key].get(k) is not None and old[key].get(k) is not None else None
                 for k in ('app', 'goals', 'assists', 'yellow', 'red', 'clean_sheets')}
        status = 'INTERVAL'
        if any(v is not None and v < 0 for v in delta.values()):
            status, delta = 'ROLLBACK_OR_CORRECTION', None
        elif delta['app'] == 0 and any((delta[k] or 0) > 0 for k in ('goals', 'assists')):
            status = 'INCONSISTENT'
        result.append({'key': key, 'status': status, 'delta': delta})
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('before', type=Path)
    parser.add_argument('after', type=Path)
    args = parser.parse_args()
    print(json.dumps(compare(json.loads(args.before.read_text(encoding='utf-8')),
                             json.loads(args.after.read_text(encoding='utf-8'))), ensure_ascii=False, indent=2))
