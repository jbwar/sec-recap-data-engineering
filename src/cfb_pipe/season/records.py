"""Canonical ESPN event IDs; preserve rescheduling and flag identity collisions."""
from collections import defaultdict
from datetime import datetime, timezone
import json
import re


def timestamp(value):
    if not isinstance(value, str):
        raise ValueError('Missing timestamp')
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('Timestamp must include a timezone')
    return parsed.astimezone(timezone.utc).isoformat()


def normalize(event, membership, source, partition_id, context=None):
    context = context or {}
    if source.get('name') != 'espn' or not source.get('url') or not source.get('retrieved_at') or not source.get('sha256'):
        raise ValueError('Source name, URL, retrieval time and response checksum are required')
    if not re.fullmatch(r'[a-f0-9]{64}', source['sha256']):
        raise ValueError('Source checksum must be a SHA-256 hex digest')
    observed_at = timestamp(source['retrieved_at'])
    gid = str(event.get('id', ''))
    if not gid.isdigit():
        raise ValueError('Missing numeric ESPN event identifier')
    season = event.get('season', {}).get('year', context.get('season'))
    season_type = event.get('season', {}).get('type', context.get('season_type'))
    if season != membership.season or season_type not in (2, 3):
        raise ValueError('Wrong/missing season or unsupported season type')
    if context.get('season_type') and season_type != context['season_type']:
        raise ValueError('Event season type contradicts its schedule partition')
    competitions = event.get('competitions', [])
    if len(competitions) != 1:
        raise ValueError('Expected exactly one competition')
    comp = competitions[0]
    competitors = comp.get('competitors', [])
    if len(competitors) != 2:
        raise ValueError('Unresolved or missing participants')
    teams = {}
    for participant in competitors:
        side, raw = participant.get('homeAway'), participant.get('team', {})
        tid = str(raw.get('id', ''))
        if side not in ('home', 'away') or side in teams or not tid.isdigit():
            raise ValueError('Unresolved participant identifier or home/away assignment')
        teams[side] = membership.team('espn', tid)
        teams[side]['source_name'] = raw.get('displayName')
    if teams['home']['source_id'] == teams['away']['source_id']:
        raise ValueError('Same participant twice')
    date = timestamp(event.get('date') or comp.get('date'))
    status = comp.get('status', event.get('status', {})).get('type', {})
    label = str(status.get('name', '')).upper()
    special = {'STATUS_CANCELED': 'canceled', 'STATUS_CANCELLED': 'canceled',
               'STATUS_POSTPONED': 'postponed', 'STATUS_DELAYED': 'delayed', 'STATUS_SUSPENDED': 'suspended'}
    if label in special:
        state = special[label]
    elif status.get('completed') is True and status.get('state') == 'post':
        state = 'completed'
    elif status.get('state') == 'pre' and label in ('STATUS_SCHEDULED', 'STATUS_TBD'):
        state = 'scheduled'
    elif status.get('state') == 'in':
        state = 'in_progress'
    else:
        state = 'unresolved'
    classes = [t['classification'] for t in teams.values()]
    scope = 'included' if 'FBS' in classes else 'unresolved' if 'unresolved' in classes else 'excluded'
    classification = ('FBS-FBS' if classes.count('FBS') == 2 else
                      'FBS-FCS' if set(classes) == {'FBS', 'FCS'} else
                      'FBS-other' if set(classes) == {'FBS', 'other'} else
                      'unresolved' if 'unresolved' in classes else 'non-FBS')
    labels = [event.get('name', ''), comp.get('type', {}).get('text', '')]
    labels.extend(n.get('headline', '') for n in comp.get('notes', []) if isinstance(n, dict))
    label_text = ' '.join(labels).lower()
    if 'playoff' in label_text or 'cfp' in label_text or str(context.get('selector_label','')).upper()=='CFP':
        kind = 'college_football_playoff'
    elif 'championship' in label_text and season_type == 2:
        kind = 'conference_championship'
    elif re.search(r'\bbowl\b', label_text):
        kind = 'bowl'
    else:
        kind = 'postseason_unspecified' if season_type == 3 else 'regular_season'
    issues = []
    if scope == 'unresolved' or classification == 'unresolved': issues.append('unresolved_membership')
    if any(t['classification']!='unresolved' and not t['membership_evidence'] for t in teams.values()):
        issues.append('participant_membership_evidence_missing')
    if state == 'unresolved': issues.append('unresolved_game_status')
    if state in ('postponed', 'suspended', 'delayed'): issues.append('unresolved_game_disposition')
    week = event.get('week', {}).get('number', context.get('week'))
    if context.get('week') is not None and context.get('week_semantics')!='group' and week != context['week']:
        issues.append('week_partition_mismatch')
    if context.get('team_id') and context['team_id'] not in [t['source_id'] for t in teams.values()]:
        issues.append('team_schedule_participant_mismatch')
    return {'canonical_id': f'espn:{gid}', 'game_id': gid, 'season': season,
            'season_type': season_type, 'week': week, 'date': date,
            'name': event.get('name'), 'participants': teams,
            'neutral_site': comp.get('neutralSite'), 'status': state,
            'source_status': status, 'kind': kind, 'kind_basis': 'source_label_keywords_and_season_type',
            'scope': scope, 'classification': classification, 'issues': issues,
            'source': source, 'partition_id': partition_id, 'observed_at': observed_at,
            'context_fields_used': [f for f in ('season', 'season_type') if f not in
                ({'season'} if 'year' in event.get('season', {}) else set()) |
                ({'season_type'} if 'type' in event.get('season', {}) else set())]}


def deduplicate(observations):
    groups = defaultdict(list)
    for row in observations: groups[row['canonical_id']].append(row)
    games = []
    overlap = 0
    for key, rows in sorted(groups.items()):
        rows = sorted(rows, key=lambda r: (r['observed_at'], json.dumps(r, sort_keys=True)))
        latest = dict(rows[-1])
        identities = {tuple(sorted(t['program_id'] for t in r['participants'].values())) for r in rows}
        issues = list(latest['issues'])
        if len(identities) > 1: issues.append('canonical_id_participant_conflict')
        newest = [r for r in rows if r['observed_at'] == latest['observed_at']]
        snapshots = {(r['date'], r['status'], r['season_type'],
                      tuple((s, t['program_id']) for s, t in sorted(r['participants'].items()))) for r in newest}
        if len(snapshots) > 1: issues.append('simultaneous_schedule_conflict')
        if len({r['season_type'] for r in rows}) > 1: issues.append('season_type_conflict')
        if any(r['status'] in ('completed', 'canceled') for r in rows[:-1]) and latest['status'] not in ('completed', 'canceled'):
            issues.append('terminal_status_regression')
        dates = sorted({r['date'] for r in rows})
        kinds={r['kind'] for r in rows}
        latest['kind']=next(k for k in ('college_football_playoff','conference_championship','bowl','postseason_unspecified','regular_season','unresolved') if k in kinds)
        latest.update(issues=sorted(set(issues)), sources=[r['source'] for r in rows],
                      partitions=sorted({r['partition_id'] for r in rows}),
                      observation_count=len(rows), rescheduled=len(dates) > 1,
                      observed_dates=dates,
                      history=[{'observed_at': r['observed_at'], 'date': r['date'], 'status': r['status'],
                                'partition_id': r['partition_id']} for r in rows])
        overlap += len(rows) - 1
        games.append(latest)
    fingerprints = defaultdict(list)
    for game in games:
        key = (game['season'], game['date'], tuple(sorted(t['program_id'] for t in game['participants'].values())))
        fingerprints[key].append(game)
    collisions = []
    for group in fingerprints.values():
        if len(group) > 1:
            ids = sorted(g['canonical_id'] for g in group)
            collisions.append(ids)
            for g in group: g['issues'].append('possible_duplicate_source_ids')
    for game in games:
        game['validation_status'] = 'needs_review' if game['issues'] else 'accounted'
    return games, {'overlapping_observations_deduplicated': overlap, 'possible_duplicate_game_ids': collisions}
