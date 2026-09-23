# ADR-009 — Reporting via Power BI

## Context

Athena (ADR-008) makes detection results queryable in SQL. What remains is the last piece of the target architecture: visual reporting, usable without writing a query.

## Decision

Power BI Desktop, connected to Athena via the native connector (Amazon Athena ODBC driver), **Import** mode (not DirectQuery — data volume is small, no need for real-time queries on every interaction). A single dashboard: two KPI cards (units tested, defective units), a donut chart (breakdown by status), a detailed table of defective units, a scatter plot (vibration vs. current imbalance) with both detection thresholds shown as reference lines.

## Why

**Native Athena connector rather than generic ODBC**: Power BI offers a dedicated connector that simplifies configuration compared to a generic ODBC driver — consistent with the goal of sticking to standard, simply explainable tools.

**Import mode rather than DirectQuery**: the data volume (a few dozen rows) makes the choice obvious — Import loads everything into memory once, with no query latency on every dashboard interaction, no reason to hit Athena continuously for such a small dataset.

**Thresholds shown on the scatter plot**: makes visually explicit *why* a unit is classified defective, not just *that* it is — directly useful for explaining the detection logic to a non-technical audience, in the spirit of the "Understanding this project in 2 minutes" section already present in the README.

## Incident

**The ODBC DSN lost all its fields (except the name) after clicking "Test".** Behavior of the Amazon Athena ODBC (x64) driver: the test button validates the connection with the values entered at that moment, but does not persist them into the Windows DSN — a second "OK" without going through "Test" again fixed the problem. Diagnosed by comparing the actually saved fields (empty) against the ones entered and successfully tested, rather than assuming a cause.

## Proof of functioning

Full chain validated visually: MSK Serverless → EMR Serverless → S3 (Parquet) → Glue Catalog → Athena → Power BI. Both cards show 35 and 8 — an exact match with the results obtained directly from Athena and the EMR job (ADR-007, ADR-008). Screenshot of the full dashboard: `docs/images/powerbi-dashboard.png`.

## Consequences

- The dashboard is not published (no Power BI Service license used) — it stays a local `.pbix` file, to be shared via screenshot or PDF export for the portfolio.
- The IAM credentials used for the connection belong to the Electric Mobility Platform project, reused as-is after verifying they had the necessary permissions — no dedicated IAM user created for this step, worth noting as a simplification if the question comes up in an interview.
- The thresholds shown on the scatter plot (1.5 for vibration, 0.85 for current balance) are hardcoded in the visual, not dynamically linked to the job's code — to be manually resynced if the detection thresholds change.
