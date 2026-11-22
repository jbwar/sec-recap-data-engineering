"""Phase 2U-C: fail-closed chronological feature evidence contract (v1).

Assesses *individual proposed historical team-form inputs*, not game models.
Even valid event ordering does not establish authentic data availability,
licensed production use or eligibility for training/publishing.

Historical data captured in the 2026 source release MUST NOT be backdated:
unknown `first_seen_utc`/identity evidence remains retrospective-only.
"""
from __future__ import annotations

from datetime import datetime, timezone
import math

CONTRACT_VERSION = 1
MANDATORY_KEYS = (
    "target_season", "target_game_id", "target_team_id",
    "prediction_cutoff_utc", "target_kickoff_utc",
    "source_season", "source_game_id", "source_team_id",
    "source_kickoff_utc", "source_final_available_utc",
    "source_first_seen_utc", "identity_first_verified_utc",
    "source_snapshot_sha256", "source_scope",
    "source_independent_final_status", "source_box_grade",
    "source_box_ypp", "source_box_attempts", "source_both_teams_eligible"
)
SAFE_SCOPE = "FBS-FBS"
SAFE_FINAL = "verified_reciprocal_native_final"
SAFE_BOX = "eligible_team_box_internal_checks_only"


def utc_time(value, name):
    if value is None:
        return None
    if not isinstance(value,str) or not value:
        raise ValueError(f"{name} requires an ISO 8601 UTC timestamp or null")
    try:
        dt=datetime.fromisoformat(value.replace("Z","+00:00"))
    except ValueError as exc:
        raise ValueError(f"{name} is invalid") from exc
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError(f"{name} cannot use timezone-naive timestamps")
    return dt.astimezone(timezone.utc)


def _safe_date_window(item):
    """Structural timestamp validity, independent of certification status."""
    times={name:utc_time(item[name],name) for name in (
        "prediction_cutoff_utc","target_kickoff_utc","source_kickoff_utc",
        "source_final_available_utc","source_first_seen_utc",
        "identity_first_verified_utc")}
    return times


def evaluate_team_history_candidate(item):
    """Return a reasoned grade. Never return a training authorization."""
    if not isinstance(item,dict) or set(item)!=set(MANDATORY_KEYS):
        raise ValueError("Feature source contract fields must match v1 exactly")
    target_year=item["target_season"]
    source_year=item["source_season"]
    if type(target_year) is not int or type(source_year) is not int:
        raise ValueError("Season must be an integer")
    if not 2014<=source_year<=target_year<=2026:
        raise ValueError("Invalid year sequence for historical research")
    target_gid=str(item["target_game_id"])
    source_gid=str(item["source_game_id"])
    team=str(item["target_team_id"])
    source_team=str(item["source_team_id"])
    if (any(item[key] is None for key in ("target_game_id","source_game_id",
            "target_team_id","source_team_id")) or
        not target_gid.strip() or not source_gid.strip() or
        not team.strip() or not source_team.strip()):
        raise ValueError("Game and team identifiers must not be empty")
    if team!=source_team:
        return _grade("blocked_inconsistent_team_identity")
    if target_gid==source_gid and target_year==source_year:
        return _grade("blocked_target_game_leakage")
    if item["source_scope"]!=SAFE_SCOPE:
        return _grade("blocked_non_fbs_fbs_source")
    if (item["source_independent_final_status"]!=SAFE_FINAL or
        item["source_box_grade"]!=SAFE_BOX or
        item["source_both_teams_eligible"] is not True):
        return _grade("blocked_quality_or_pair_gate")
    val=item["source_box_ypp"]
    attempts=item["source_box_attempts"]
    if type(val) not in (float,int) or not math.isfinite(val) or val<0 or val>30:
        return _grade("blocked_invalid_box_metric")
    if type(attempts) is not int or attempts<=0:
        return _grade("blocked_invalid_attempt_denominator")
    sha=item["source_snapshot_sha256"]
    if not isinstance(sha,str) or len(sha)!=64 or any(c not in "0123456789abcdef" for c in sha):
        raise ValueError("Each feature must reference exact immutable source snapshot SHA")
    ts=_safe_date_window(item)
    cutoff=ts["prediction_cutoff_utc"]
    target=ts["target_kickoff_utc"]
    previous=ts["source_kickoff_utc"]
    if cutoff is None or target is None or previous is None:
        return _grade("unresolved_required_kickoff_or_cutoff")
    if cutoff >= target:
        return _grade("blocked_cutoff_at_or_after_target_kickoff")
    if previous >= cutoff:
        return _grade("blocked_future_or_same_cutoff_source_game")
    final=ts["source_final_available_utc"]
    captured=ts["source_first_seen_utc"]
    identity=ts["identity_first_verified_utc"]
    if final is not None and final >= cutoff:
        return _grade("blocked_late_final")
    if captured is not None and captured >= cutoff:
        return _grade("blocked_source_seen_after_cutoff")
    if identity is not None and identity >= cutoff:
        return _grade("blocked_identity_known_after_cutoff")
    if final is None or captured is None or identity is None:
        return _grade("retrospective_only_missing_asof_provenance")
    if previous >= final:
        return _grade("blocked_invalid_final_before_kickoff")
    if captured < final:
        return _grade("blocked_source_claimed_before_final_available")
    return _grade("timestamps_ordered_but_unapproved_research_only", chronology_pass=True)


def _grade(reason, chronology_pass=False):
    return {"contract_version":CONTRACT_VERSION, "reason":reason,
            "time_order_checks_passed":chronology_pass,
            "prospective_provenance_certified":False,
            "model_training_authorized":False,
            "production_use_authorized":False}


def audit_candidate_batch(candidates):
    """Evaluate synthetic/sample propositions only; never emit a training set."""
    if not isinstance(candidates,list):
        raise ValueError("Expected explicit candidate list")
    seen=set()
    records=[]
    for entry in candidates:
        grade=evaluate_team_history_candidate(entry)
        key=(entry["target_season"],str(entry["target_game_id"]),
             str(entry["target_team_id"]),entry["source_season"],
             str(entry["source_game_id"]))
        if key in seen:
            raise ValueError("Duplicate target/source observation")
        seen.add(key)
        records.append(grade)
    counts={}
    for r in records:
        counts[r["reason"]]=counts.get(r["reason"],0)+1
    return {"phase":"2U-C","schema_version":1,"candidate_count":len(records),
            "grade_counts":dict(sorted(counts.items())),
            "time_order_pass_only":sum(x["time_order_checks_passed"] for x in records),
            "prospective_pregame_provenance_certified":False,
            "training_authorized":False,
            "production_use_authorized":False,
            "no_feature_values_or_game_ids_exported":True}
