# ADR-006 — Detection via EMR Serverless (Glue abandoned)

## Context

After MSK Serverless (ADR-005), the next step is managed Spark processing on AWS. The roadmap originally planned Glue first (Phase 3), EMR second (Phase 6, a documented migration).

## Decision

**EMR Serverless from the start, Glue abandoned.** No dedicated VPC, no Glue connector — a standalone Spark job (`aws/emr_detection_job.py`), connected to MSK Serverless with native IAM auth, with no dependency on `anomaly/` (logic deliberately duplicated, to keep it a single, readable file).

## Why

**Glue abandoned**: two discoveries in a row before spending a single AWS credit.
1. Glue's *generic* Kafka connector does not support IAM authentication (per official docs) — but a *dedicated* MSK connector exists and does support it (official AWS blog post), which corrected an initial false alarm.
2. This dedicated MSK connector relies on a connection model (`AuthenticationConfiguration`) that the Terraform AWS provider does not yet support (open GitHub issue, ~173 days old). Creating the connection by hand, outside Terraform, remained possible but broke infrastructure-as-code and needlessly complicated a junior-level portfolio project.

**EMR Serverless over classic EMR**: no cluster management (sizing, nodes), zero cost when idle (billed only for compute actually consumed during a job) — no need for a destroy discipline between sessions, unlike MSK.

## Incidents

All tied to missing IAM permissions or JARs — none called the architecture into question, but their accumulation made the session long and confusing. Resolved one by one, in the order they appeared:

1. **Private subnets, no internet access** — EMR Serverless workers cannot download Kafka/IAM dependencies via `--packages` (no NAT gateway, a decision accepted in ADR-005). Worked around by downloading the 12 required JARs (Spark 3.5.6 Kafka connector and its transitive dependencies, `aws-msk-iam-auth`) from the bastion, then referencing them from S3 via `spark.jars`.
2. **Missing `s3:PutObject`** on the bastion's role — its policy only covered MSK, not the new S3 bucket.
3. **Missing `emr-serverless:StartJobRun`** on the bastion's role.
4. **Missing `iam:PassRole`** — the bastion must be explicitly authorized to pass the job's execution role to EMR Serverless.
5. **`emr-serverless:GetJobRun` too narrow** — the policy only covered the application, not the individual jobs it contains (`/jobruns/*` missing).
6. **Logs not configured** — a first job succeeded (`SUCCESS`) with no output retrievable anywhere, for lack of an explicit S3 log destination (`--configuration-overrides`).
7. **CLI command too long** — `start-job-run` with the 12 JARs inline exceeded the SSM terminal's reliable paste capacity, silently truncating the command. Solved by using JSON files (`job.json`, `logs.json`) instead of a single command line.
8. **`terraform destroy` blocked** — the EMR Serverless application stays `STARTED` after a job, a state Terraform cannot destroy directly. Requires an explicit stop (`aws emr-serverless stop-application`) before destruction.

## Proof of functioning

Two real runs, data read from MSK Serverless (IAM), job executed on EMR Serverless:
- 5 units: 2/2 defective units detected, 0 false positives (`docs/proofs/emr-serverless-detection-proof.txt`)
- 55 units (cumulative across two sends): 12/12 defective units detected, 0 false positives (`docs/proofs/emr-serverless-detection-proof-55units.txt`)

Infrastructure destroyed at the end of the session.

## Consequences

- The Spark job duplicates the logic from `anomaly/features.py` and `anomaly/classify.py` rather than importing the package — accepted as a deliberate simplification (avoiding an untested `--py-files` packaging mechanism), to be revisited if the project evolves toward several Glue/EMR jobs sharing this logic.
- The bastion's startup process (`user_data`) now automates cloning the repo, installing dependencies, and downloading the JARs — but clones the `main` branch, not the current working branch. A script or new feature added on an unmerged branch isn't visible at startup until it's merged.
