"""Fully invented football game: demonstrates identity, source scope, and chronology checks."""
import json
from cfb_pipe.season.membership import Membership
from cfb_pipe.season.records import normalize, deduplicate
from cfb_pipe.timeaware_feature_contract import MANDATORY_KEYS, evaluate_team_history_candidate


def sample_membership():
    programs = []
    for key, source_id in (("alpha", "101"), ("beta", "102")):
        programs.append({
            "program_id": key, "name": f"Synthetic {key.title()}",
            "source_ids": {"espn": source_id},
            "history": [{
                "first_season": 2026, "last_season": 2026,
                "classification": "FBS", "conference": "Example Conference",
                "evidence": ["synthetic fixture"]
            }]
        })
    return {
        "schema_version": 1,
        "origin": "synthetic_fixture",
        "programs": programs,
        "season_releases": [{
            "season": 2026, "complete": True, "fbs_count": 2,
            "conferences": {"Example Conference": 2},
            "fbs_program_ids": ["alpha", "beta"],
            "reviewed_by": "synthetic_fixture_only",
            "evidence": ["synthetic fixture"]
        }]
    }


def sample_event():
    return {
        "id": "900001", "season": {"year": 2026, "type": 2},
        "week": {"number": 1}, "date": "2026-09-01T18:00:00Z",
        "name": "Synthetic Alpha vs Synthetic Beta",
        "competitions": [{
            "neutralSite": False,
            "competitors": [
                {"homeAway": "home", "team": {"id": "101", "displayName": "Synthetic Alpha"}},
                {"homeAway": "away", "team": {"id": "102", "displayName": "Synthetic Beta"}}
            ],
            "status": {"type": {"name": "STATUS_SCHEDULED", "state": "pre", "completed": False}}
        }]
    }


def sample_source():
    return {
        "name": "espn", "url": "https://example.invalid/synthetic-only",
        "retrieved_at": "2026-08-01T00:00:00Z",
        "sha256": "a" * 64
    }


def main():
    membership = Membership(sample_membership(), 2026)
    normalized = normalize(sample_event(), membership, sample_source(), "synthetic-test")
    output = deduplicate([normalized, normalized])
    # This toy example has two observations of a single synthetic game.
    candidate = {
        "target_season": 2026, "target_game_id": "900001",
        "target_team_id": "alpha",
        "prediction_cutoff_utc": "2026-08-31T18:00:00Z",
        "target_kickoff_utc": "2026-09-01T18:00:00Z",
        "source_season": 2026, "source_game_id": "800001",
        "source_team_id": "alpha",
        "source_kickoff_utc": "2026-08-20T18:00:00Z",
        "source_final_available_utc": "2026-08-20T22:00:00Z",
        "source_first_seen_utc": "2026-08-21T00:00:00Z",
        "identity_first_verified_utc": "2026-08-22T00:00:00Z",
        "source_snapshot_sha256": "b" * 64, "source_scope": "FBS-FBS",
        "source_independent_final_status": "verified_reciprocal_native_final",
        "source_box_grade": "eligible_team_box_internal_checks_only",
        "source_box_ypp": 5.2, "source_box_attempts": 55,
        "source_both_teams_eligible": True
    }
    assert set(candidate) == set(MANDATORY_KEYS)
    print(json.dumps({
        "membership": membership.evidence_status(),
        "normalized": {key: normalized[key] for key in ("canonical_id", "classification", "scope")},
        "deduplicated_game_count": len(output[0]) if isinstance(output, tuple) else len(output),
        "chronology_grade": evaluate_team_history_candidate(candidate)
    }, indent=2))


if __name__ == "__main__":
    main()
