"""These tests use invented events and do not access external systems."""
from cfb_pipe.season.membership import Membership
from cfb_pipe.season.records import normalize, deduplicate
from examples.synthetic_demo import sample_event, sample_membership, sample_source


def test_synthetic_membership_is_not_a_reviewed_real_reference():
    status = Membership(sample_membership(), 2026).evidence_status()
    assert status["reference_validated"] is True
    assert status["reviewed_real_reference"] is False


def test_synthetic_event_normalization_and_scope():
    game = normalize(sample_event(), Membership(sample_membership(), 2026),
                     sample_source(), "synthetic-test")
    assert game["classification"] == "FBS-FBS"
    assert game["scope"] == "included"
    assert game["canonical_id"] == "espn:900001"


def test_duplicate_observations_are_not_counted_as_separate_games():
    game = normalize(sample_event(), Membership(sample_membership(), 2026),
                     sample_source(), "synthetic-test")
    result = deduplicate([game, game])
    games = result[0] if isinstance(result, tuple) else result
    assert len(games) == 1
    assert games[0]["observation_count"] == 2
