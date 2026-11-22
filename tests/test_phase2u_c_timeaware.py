"""Phase 2U-C: synthetic as-of tests. NO real historical pregame claims."""
from copy import deepcopy
from datetime import datetime, timezone
import pytest
from cfb_pipe.timeaware_feature_contract import (
    evaluate_team_history_candidate, audit_candidate_batch, MANDATORY_KEYS
)


def fixture():
    return {
        "target_season":2022, "target_game_id":"target-week-6", "target_team_id":"team-1",
        "prediction_cutoff_utc":"2022-10-15T18:00:00Z",
        "target_kickoff_utc":"2022-10-15T19:00:00+00:00",
        "source_season":2022, "source_game_id":"prior-week-5", "source_team_id":"team-1",
        "source_kickoff_utc":"2022-10-08T18:00:00Z",
        "source_final_available_utc":"2022-10-08T22:00:00Z",
        "source_first_seen_utc":"2022-10-09T00:00:00Z",
        "identity_first_verified_utc":"2022-10-09T00:00:00Z",
        "source_snapshot_sha256":"a"*64,
        "source_scope":"FBS-FBS",
        "source_independent_final_status":"verified_reciprocal_native_final",
        "source_box_grade":"eligible_team_box_internal_checks_only",
        "source_box_ypp":5.41,
        "source_box_attempts":54,
        "source_both_teams_eligible":True,
    }


def grade(**edits):
    row=fixture()
    row.update(edits)
    return evaluate_team_history_candidate(row)


def test_full_synthetic_time_order_is_not_training_or_production_authorization():
    actual=grade()
    assert actual["reason"]=="timestamps_ordered_but_unapproved_research_only"
    assert actual["time_order_checks_passed"] is True
    assert actual["model_training_authorized"] is False
    assert actual["prospective_provenance_certified"] is False
    assert actual["production_use_authorized"] is False


def test_2026_captured_historical_box_cannot_backdate_to_2022():
    actual=grade(source_first_seen_utc="2026-10-15T00:00:00Z")
    assert actual["reason"]=="blocked_source_seen_after_cutoff"
    assert actual["time_order_checks_passed"] is False


def test_retrospective_crosswalk_lacks_actual_asof_membership_proof():
    actual=grade(identity_first_verified_utc=None)
    assert actual["reason"]=="retrospective_only_missing_asof_provenance"
    assert actual["model_training_authorized"] is False


@pytest.mark.parametrize("changes,reason",[
    ({"source_game_id":"target-week-6"},"blocked_target_game_leakage"),
    ({"source_kickoff_utc":"2022-10-15T18:00:00Z"},"blocked_future_or_same_cutoff_source_game"),
    ({"source_final_available_utc":"2022-10-15T18:00:00Z"},"blocked_late_final"),
    ({"source_first_seen_utc":"2022-10-15T19:00:00Z"},"blocked_source_seen_after_cutoff"),
    ({"identity_first_verified_utc":"2022-10-15T18:00:00Z"},"blocked_identity_known_after_cutoff"),
    ({"prediction_cutoff_utc":"2022-10-15T20:00:00Z"},"blocked_cutoff_at_or_after_target_kickoff"),
    ({"prediction_cutoff_utc":"2022-10-15T19:00:00Z"},"blocked_cutoff_at_or_after_target_kickoff"),
    ({"source_scope":"FBS-FCS"},"blocked_non_fbs_fbs_source"),
    ({"source_both_teams_eligible":False},"blocked_quality_or_pair_gate"),
    ({"source_independent_final_status":"unverified"},"blocked_quality_or_pair_gate"),
    ({"source_team_id":"other"},"blocked_inconsistent_team_identity"),
    ({"source_box_ypp":float("nan")},"blocked_invalid_box_metric"),
    ({"source_box_attempts":0},"blocked_invalid_attempt_denominator"),
    ({"source_final_available_utc":"2022-10-08T17:00:00Z"},"blocked_invalid_final_before_kickoff"),
    ({"source_first_seen_utc":"2022-10-08T21:00:00Z"},"blocked_source_claimed_before_final_available"),
])
def test_no_leakage_fail_closed(changes,reason):
    assert grade(**changes)["reason"]==reason


@pytest.mark.parametrize("value",[
    "2022-10-15T18:00:00","not-an-iso-time","",
])
def test_invalid_or_naive_cutoff_rejected(value):
    with pytest.raises(ValueError,match="prediction_cutoff_utc"):
        grade(prediction_cutoff_utc=value)


def test_unknown_timestamps_never_qualify():
    assert grade(source_final_available_utc=None)["reason"]=="retrospective_only_missing_asof_provenance"
    assert grade(source_first_seen_utc=None)["time_order_checks_passed"] is False
    assert grade(target_kickoff_utc=None)["reason"]=="unresolved_required_kickoff_or_cutoff"


def test_missing_or_unreviewed_schema_and_digest_fail_closed():
    a=fixture()
    a.pop("source_snapshot_sha256")
    with pytest.raises(ValueError,match="match v1 exactly"):
        evaluate_team_history_candidate(a)
    with pytest.raises(ValueError,match="snapshot SHA"):
        grade(source_snapshot_sha256="bad-sha")
    a=fixture()
    a["unknown_field"]=2
    with pytest.raises(ValueError,match="match v1 exactly"):
        evaluate_team_history_candidate(a)


def test_batch_aggregates_only_safe_reasons_not_game_data():
    inp=[fixture(),{**fixture(),"source_game_id":"another","source_first_seen_utc":None}]
    audit=audit_candidate_batch(inp)
    assert audit["candidate_count"]==2
    assert audit["time_order_pass_only"]==1
    assert audit["training_authorized"] is False
    assert "target-week-6" not in str(audit)
    with pytest.raises(ValueError,match="Duplicate target/source"):
        audit_candidate_batch([fixture(),fixture()])


def test_source_year_after_target_blocks():
    with pytest.raises(ValueError,match="Invalid year sequence"):
        grade(source_season=2024)

# The private source repository separately tests its R2-backed publication receipt.
# That receipt is excluded from this synthetic-only public code sample.
