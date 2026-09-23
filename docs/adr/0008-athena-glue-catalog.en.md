# ADR-008 — Athena querying on the persistent data lake

## Context

The `terraform/data` module (ADR-007) persists detection results as Parquet on S3. What remains is making them queryable in SQL — Athena's role in the target architecture.

## Decision

- **Glue Data Catalog table defined explicitly**, schema written by hand (7 columns, already known from the EMR job), rather than a Glue Crawler.
- **Dedicated Athena workgroup**, with its query results stored in a subfolder of the existing persistent bucket (`athena-query-results/`), not a new bucket.
- **Both resources live in `terraform/data`**, not `terraform/main` — consistent with ADR-007, since they describe data that must survive the ephemeral infrastructure being destroyed between sessions.

## Why

**Explicit schema rather than a Crawler**: a Crawler serves to discover an unknown or evolving schema — here, the EMR job's output schema is fixed and already written in the code (`emr_detection_job.py`). A Crawler would have added a dependency and a cost (billed per DPU-hour, 10-minute minimum per run) to restate information already known.

**Shared folder rather than a second bucket**: Athena's query results have no reason to be physically separated from the data they query — a subfolder of the existing bucket is enough, without complicating the resource inventory.

## Proof of functioning

Two real queries from the Athena console, on the 35 units already persisted (ADR-007):
- `SELECT * FROM detection_results LIMIT 10` — correctly typed columns, readable data.
- Aggregation (`COUNT`, conditional `SUM`) — **35 units, 8 defective**, an exact match with the result obtained directly from the EMR Serverless job.

Details in `docs/proofs/athena-query-proof.txt`.

## Consequences

- **Negligible cost, verified**: Glue Data Catalog is free up to 1 million objects/requests per month (2 objects used here); Athena is billed at $5/TB scanned with a 10 MB minimum per query — on the order of a fraction of a cent for current usage. No destroy discipline needed, consistent with the rest of the persistent module.
- The Glue table's schema must stay manually in sync with the EMR job's (`emr_detection_job.py`) — a column change on the job side without updating `terraform/data/glue_catalog.tf` would break querying without an explicit error (missing or mistyped columns, not a hard failure).
- Natural next step: connecting Power BI to Athena for visual reporting.
