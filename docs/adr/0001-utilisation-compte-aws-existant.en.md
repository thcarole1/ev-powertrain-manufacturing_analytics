# ADR-001 — Using the existing AWS account, isolation via tags

## Context

EV Powertrain Manufacturing Analytics is a second portfolio project, complementary to the Electric Mobility Platform project already deployed on AWS. Only one AWS account is available for both projects.

## Decision

The project is deployed on the existing AWS account, with no dedicated account created and no AWS Organizations setup. Separation between the two projects is ensured by a systematic tagging strategy and a dedicated budget.

## Why

Creating a dedicated account (AWS Organizations, SSO, separate accounts) would provide stricter isolation, but represents a setup effort not aligned with this project's priority skills (Kafka, Spark). The risk of resource collision between the two projects is judged manageable through a strict naming and tagging convention applied from the very first deployment.

## Consequences

- Every resource created for this project carries the `Project=ev-powertrain-analytics` tag, without exception, including via the Terraform provider's `default_tags`.
- Cost tracking through Cost Explorer relies on tag filtering rather than per-account billing, which is less immediate than natively separated billing.
- A dedicated AWS Budgets alert is created filtering on this tag, from Phase 0 onward.
- Accepted security trade-off: the project's IAM roles coexist in the same account as the first project. The principle of least privilege is still applied at the application-role level, but no account-to-account isolation exists between the two projects.
