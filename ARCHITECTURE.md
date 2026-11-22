# Architecture and boundaries

The private research pipeline has six broad stages: source acquisition, immutable raw capture, canonical identity reconciliation, quality-gated transformations, versioned warehouse publication, and read-only analytical use.

The selected public modules illustrate **three isolated controls**, not the complete production deployment:

**Membership and identity.** FBS status is evaluated per season from explicit membership history; unresolved IDs stay unresolved rather than being guessed. Records preserve the original event key and observed reschedules, and emit flags for conflicts.

**Quality and provenance.** Source checksums and observed timestamps are required for normalized event records. The full private system has separate quality masks and quarantines; those private data products are not shipped.

**Chronological safety.** Historical-form inputs are rejected when the source game, final, first-seen record, or identity verification occurs after the prediction cutoff. Even well-ordered research observations are not thereby granted model-training or production use.

## Included vs. excluded

| Included in this candidate | Not included |
| --- | --- |
| Pure Python normalization and chronology contracts | Collection credentials, API gateways, or private Site routes |
| Synthetic-only example and tests | Real ESPN/NCAA payloads or publisher datasets |
| High-level architecture and engineering rationale | R2 object keys, storage pointers, importer workflows |
| Provenance behavior and quality flags | Historical serving indexes, production model weights |

The public candidate should always be copied **without any Git history** from the private source repository.
