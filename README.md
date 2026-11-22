# SEC Recap — College Football Data Engineering

**An inspectable, offline-safe software engineering sample extracted from a larger private college-football research platform.**

This portfolio repository focuses on problems that make sports-data pipelines difficult: changing conference membership, conflicting event identities, incomplete source evidence, and pregame data leakage. The larger operational platform incorporates ingestion, Parquet-based canonical datasets, quality gates, and versioned cloud storage. **The production infrastructure, raw datasets, and private APIs are not included here.**

## What is in this repository

- `src/cfb_pipe/season/membership.py` — season-specific FBS/FCS classification, source-ID mapping, and evidence-based completeness checks.
- `src/cfb_pipe/season/records.py` — deterministic event normalization, duplicate handling, reschedule history, and identity-conflict detection.
- `src/cfb_pipe/timeaware_feature_contract.py` — explicit pre-kickoff chronology checks to prevent retrospective data from being misrepresented as historically available.
- `tests/` — synthetic tests, including chronological leakage and identity-edge-case coverage.
- `examples/synthetic_demo.py` — a no-network demonstration using invented teams, games, and timestamps.

These are **real components extracted from the SEC Recap development repository**, with a small packaging harness and additional synthetic tests for standalone demonstration. This is not a simulated replacement for the full data pipeline.

## Architecture in context

```text
Authorized data sources
       |
       v
Immutable, checksum-pinned source snapshots     [private implementation]
       |
       v
Schedule and membership reconciliation          [selected public modules]
       |
       v
Validation, provenance, and explicit quarantine  [selected public modules]
       |
       v
Time-aware, quality-gated feature generation     [selected public module]
       |
       v
Versioned Parquet / R2 warehouse and analytics   [private implementation]
```

## Run the safe example

Python 3.12 recommended; no cloud account, API credential, or network data collection required.

```bash
python -m venv .venv
# Activate your environment, then:
python -m pip install -e '.[test]'
python -m pytest -q
python examples/synthetic_demo.py
```

On Windows PowerShell, activate with `.venv\Scripts\Activate.ps1`.

All sample games, team IDs, and timestamps in this repository are synthetic. Do not interpret passing sample tests as proof of complete national data coverage.

## Scale of the underlying research system

An archived **2025 FBS-involving research cohort** accounted for 934 scheduled games, 932 publisher play-by-play slices, 855 structural passes, 77 quarantines, and two missing play-by-play slices. A downstream research feature run recorded 37,360 keyed feature rows, with eligibility flags and explicit nulls. These numbers come from private, reproducibility-documented analysis; **the original source archives are not distributed here**, and these counts do not establish full semantic accuracy or unrestricted redistribution rights.

## Engineering decisions

1. Preserve identity history instead of silently overwriting reschedules or conflicting observations.
2. Distinguish structural validity, statistical eligibility, provenance, and permission to publish.
3. Prefer explicit rejection and review flags over silently accepting incomplete evidence.
4. Separate source-event chronology from the time information actually became available to a model.
5. Keep raw, source-derived data and operational access mechanisms outside public Git.

## Related product

SEC Recap publishes college-football analytics and model coverage at [secrecap.com](https://www.secrecap.com). This demonstration is not the source repository for that website.

## Scope, rights, and licensing

Only original engineering files and synthetic examples are intended for this public sample. No ESPN/NCAA raw records, licensed third-party datasets, object-store access, or production credentials are included. This repository is independent of the data providers and does not grant permission to collect from them. No open-source license has been selected yet; do not add one without an explicit owner decision.
