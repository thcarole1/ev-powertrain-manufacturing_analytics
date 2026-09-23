# ADR-010 — Continuous integration via GitHub Actions

## Context

The last piece planned by the roadmap: automating test execution and infrastructure-code checks, without depending on a manual run before every merge.

## Decision

A single GitHub Actions workflow (`.github/workflows/tests.yml`), two jobs:
- **`tests`** — installs Java (required by PySpark) and Python, then runs the project's 30 tests.
- **`terraform-validate`** — for each of the 3 modules (`bootstrap`, `main`, `data`), checks formatting (`terraform fmt -check`) and syntactic validity (`terraform validate`), never initializing a real backend or running a `plan`/`apply`.

Triggered on `pull_request` toward `main` (every working branch) and on `push` toward `main` only (merges and direct commits) — never both at once for the same commit.

## Why

**`terraform init -backend=false` rather than a real backend**: validating syntax doesn't require access to the remote state or an AWS account — avoiding this dependency means no AWS credentials need to be stored in GitHub secrets, reducing the exposure surface. Consistent with the least-privilege principle already applied elsewhere in the project (ADR-001, ADR-005).

**Never an automatic `terraform apply`**: the project relies on a strict discipline of manually creating/destroying infrastructure between sessions (ADR-005 onward), to control costs. Automating an `apply` in CI would break this discipline and could trigger costs without direct oversight.

**Asymmetric triggers (`push` limited to `main`, `pull_request` on everything else)**: the initial configuration triggered the workflow twice for the same commit on a branch with an open PR (once via `push`, once via `pull_request`) — spotted directly in the GitHub Actions run history, not anticipated when writing the workflow. Fixed by restricting `push` to `main` only.

## Incidents

**`terraform fmt -check` revealed a misformatted file** (`terraform/main/iam.tf`) — blocks added manually via the terminal over several sessions, never run through `terraform fmt`. Fixed with a simple `terraform fmt iam.tf`, no logic change.

**Deprecated action versions** (`actions/checkout@v4`, `actions/setup-java@v4`, `hashicorp/setup-terraform@v3`): GitHub flagged them as being forced to run on a newer Node.js version than the one they targeted — functional today, but a signal to fix before it becomes blocking. Updated to the latest major versions (`checkout@v6`, `setup-java@v5`, `setup-terraform@v4`).

## Proof of functioning

Workflow validated under real conditions on GitHub: both jobs pass in about 1m50s total, with no warnings after the fixes. Trigger behavior verified explicitly (one run per step, confirmed in the run history) rather than assumed correct after reading the YAML.

## Consequences

- CI only covers Terraform syntax, never a real `plan` against the actual infrastructure — a logic error (a wrong reference between resources, for example) would only be caught during a manual `terraform plan`, not upstream by CI.
- The full pipeline (MSK → EMR → S3 → Athena → Power BI) stays entirely manual, outside this CI's scope — consistent with the project's cost discipline, but means no regression on this path would be caught automatically.
