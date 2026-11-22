# Security, data rights, and sample limitations

This repository is a **synthetic-data-only code sample**, not an authenticated production service or a public data mirror.

## Deliberately omitted

- Raw ESPN/NCAA responses, publisher datasets, game archives, and real source-derived Parquet files.
- Private APIs, authentication, cloud credentials, storage configuration, deployment keys, and operational integrations.
- Historical source repository Git objects, branches, tags, CI artifacts, and incident/transfer logs.

## Reproducing results

The included modules are excerpted from a larger private research pipeline. The tests and demo operate on invented teams and records, with no external data requests. Passing them verifies the behavior tested, not nationwide completeness, semantic correctness of upstream datasets, or fitness for production deployment.

The production architecture also contains other ingestion, reconciliation, feature, and storage components; those are **not** provided in this public sample.

## Rights and usage

Source-data licensing and permission to retrieve or redistribute real records must be considered separately from the Python code. No third-party raw data is redistributed. The name of a data provider in a parser does not imply affiliation or access permission.

An open-source license has not been selected. Until one is added, the repository should not be described as open source; it is publicly viewable source code with no general reuse license.

## Reporting issues

Do not post credentials, authentication headers, private URLs, production dataset excerpts, or other sensitive details in GitHub issues. Report any accidental exposure privately to the repository owner.
