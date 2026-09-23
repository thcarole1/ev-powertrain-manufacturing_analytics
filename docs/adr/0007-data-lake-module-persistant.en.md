# ADR-007 — Separate Terraform module for the persistent data lake

## Context

The EMR Serverless job (ADR-006) now writes its detection results to S3, in Parquet — a prerequisite for Athena. This bucket previously lived in `terraform/main`, systematically destroyed at the end of each session to control costs (MSK, bastion, EMR). An S3 bucket holding just a few Parquet files costs almost nothing at rest, unlike MSK/EMR — destroying it every time meant losing reusable data for no real cost reason.

## Decision

New Terraform module, `terraform/data/`, with its own backend (a separate state in the same state S3 bucket, key `data/terraform.tfstate`). It contains only the data lake's S3 bucket. `terraform/main` accesses it read-only via `terraform_remote_state`, never able to modify or destroy it from that module.

`terraform/main` is still destroyed at the end of every session as before; `terraform/data` is applied once and stays in place until the end of the project.

## Why

**Separate module rather than a simple `prevent_destroy`**: a `lifecycle { prevent_destroy = true }` would have been enough to prevent accidental deletion, but would also have blocked `terraform destroy` on all of `terraform/main` (Terraform refuses to destroy a module containing a protected resource, even if the module's other resources are meant to disappear). A distinct module, with its own lifecycle, avoids this blocker: one can be destroyed without touching the other.

**Separate backend rather than a shared state**: a single state for everything would have mixed resources with completely different lifetimes (a session vs. the whole project), making `terraform plan`/`destroy` ambiguous about what should actually disappear.

## Incident

**`AccessDenied` on `s3:DeleteObject`, on the second job writing to the same path.** The job script (`mode("overwrite")`) deletes prior files before writing new ones — the job's IAM policy only covered `PutObject`/`GetObject`/`ListBucket`, never `DeleteObject`. The very first job (5 units, nothing to delete) had succeeded, masking the problem until a second job on the same path. Fixed by explicitly adding `s3:DeleteObject` to the policy.

## Proof of functioning

Full cycle validated: `terraform/main` applied → EMR job writes to the persistent bucket (35 units, 8/8 defective units detected, 0 false positives — `docs/proofs/emr-persistent-bucket-proof.txt`) → `terraform/main` destroyed → **the bucket and its contents survive**, verified after destruction (`aws s3 ls` confirms the Parquet files are present).

## Consequences

- Two `terraform apply`/`destroy` commands to run separately depending on intent (`terraform/data` once for all, `terraform/main` every session) — slightly more operational discipline than a single module, offset by the absence of accidental-loss risk.
- The persistent bucket accrues small but real S3 storage costs over the whole project duration — worth monitoring if data volume grows significantly (not a risk at this stage).
- Any new resource that needs to survive between sessions (for example, a future Glue Catalog database for Athena) will follow this same pattern: `terraform/data`, never `terraform/main`.
