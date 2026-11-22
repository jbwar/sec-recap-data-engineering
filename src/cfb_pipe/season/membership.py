"""Explicit season ranges, source identifiers and evidence; no current-year inference."""
from collections import Counter
from hashlib import sha256
import json


class Membership:
    def __init__(self, document, season):
        if document.get('schema_version') != 1 or not isinstance(season, int):
            raise ValueError('Membership schema_version=1 and an integer season are required')
        self.document, self.season = document, season
        self.digest = sha256(json.dumps(document, sort_keys=True).encode()).hexdigest()
        self.programs, self.source_ids = {}, {}
        for program in document.get('programs', []):
            pid = program['program_id']
            if not isinstance(pid, str) or not pid or pid in self.programs:
                raise ValueError('Missing or duplicate stable program_id')
            history = program.get('history', [])
            ranges = []
            for row in history:
                start, end = row['first_season'], row['last_season']
                if not isinstance(start, int) or not isinstance(end, int) or start > end:
                    raise ValueError(f'Invalid season range: {pid}')
                if any(start <= b and end >= a for a, b in ranges):
                    raise ValueError(f'Overlapping membership ranges: {pid}')
                ranges.append((start, end))
                if row['classification'] not in ('FBS', 'FCS', 'other'):
                    raise ValueError(f'Unsupported classification: {pid}')
                if row['classification'] == 'FBS' and not row.get('conference'):
                    raise ValueError(f'FBS conference or Independent designation required: {pid}')
                if row.get('membership_phase', 'active') not in ('active', 'transition'):
                    raise ValueError(f'Unsupported membership phase: {pid}')
            active = [r for r in history if r['first_season'] <= season <= r['last_season']]
            self.programs[pid] = {**program, 'season_membership': active[0] if active else None}
            for source, identifier in program.get('source_ids', {}).items():
                key = (source, str(identifier))
                if key in self.source_ids:
                    raise ValueError(f'Ambiguous source team identifier: {key}')
                self.source_ids[key] = pid
        releases = [r for r in document.get('season_releases', []) if r.get('season') == season]
        if len(releases) > 1:
            raise ValueError('Duplicate membership release for selected season')
        self.release = releases[0] if releases else {}

    def team(self, source, identifier):
        pid = self.source_ids.get((source, str(identifier)))
        program = self.programs.get(pid, {})
        row = program.get('season_membership') or {}
        return {'program_id': pid or f'unresolved:{source}:{identifier}',
                'source_id': str(identifier), 'name': program.get('name'),
                'classification': row.get('classification', 'unresolved'),
                'conference': row.get('conference'),
                'membership_phase': row.get('membership_phase'),
                'membership_evidence': row.get('evidence', [])}

    @property
    def fbs(self):
        return {pid: p for pid, p in self.programs.items()
                if (p['season_membership'] or {}).get('classification') == 'FBS'}

    def evidence_status(self):
        conferences = dict(sorted(Counter(p['season_membership']['conference'] for p in self.fbs.values()).items()))
        problems = []
        r = self.release
        if not self.fbs:
            problems.append('no_fbs_membership_reference')
        if r.get('complete') is not True:
            problems.append('membership_release_not_exhaustive')
        if r.get('fbs_count') != len(self.fbs) or r.get('conferences') != conferences:
            problems.append('membership_release_counts_mismatch')
        if sorted(r.get('fbs_program_ids', [])) != sorted(self.fbs):
            problems.append('membership_release_program_inventory_mismatch')
        if not r.get('reviewed_by') or not r.get('evidence'):
            problems.append('membership_release_evidence_missing')
        if any(not p['season_membership'].get('evidence') for p in self.fbs.values()):
            problems.append('program_membership_evidence_missing')
        structural = not problems
        return {'season': self.season, 'document_sha256': self.digest,
                'fbs_count': len(self.fbs), 'conferences': conferences,
                'origin': self.document.get('origin', 'unreviewed'),
                'reference_validated': structural,
                'reviewed_real_reference': structural and self.document.get('origin') == 'reviewed_reference',
                'issues': problems}
