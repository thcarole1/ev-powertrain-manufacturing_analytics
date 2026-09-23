# ADR-002 — IoT sensor simulation for the end-of-line electrical test

## Context

The simulator must generate data representative of an end-of-line electrical test on PMSM motors, with a proportion of units showing an assembly defect, to feed the downstream anomaly detection (Spark, Phase 3).

## Decision

- A single simulated test stage: the final electrical test (motor spinning/energized), the only stage where the four chosen sensor types (temperature, vibration, current, torque) are physically meaningful.
- Test duration: 30 seconds per unit.
- Sampling rates: vibration and current at 100 Hz, torque at 10 Hz, temperature at 1 Hz.
- Defective unit rate: 20-30%, split between two scenarios: bearing degradation (correlated temperature and vibration) and phase imbalance (current, isolated).
- Each unit's actual status (healthy/defective, defect type) is stored separately from the measurement streams, in a dedicated ground-truth manifest, never mixed with the sensor messages.

## Why

Separating ground truth from measurements reproduces the real constraint of an anomaly detection pipeline: the system must not know the answer in advance. Mixing the two would have made the detection exercise trivial and unrepresentative of a real case. This separation also allows computing detection precision and recall in Phase 3, by comparing Spark's results against the manifest after the fact, without ever exposing it to the processing itself.

A single test stage was chosen over a multi-stage simulation (intermediate assembly checks, leak testing) because those checks measure different quantities than the four sensors already defined and would require new topics and schemas, out of scope for this iteration's budget.

## Consequences

- The simulator produces two distinct types of output: per-sensor measurement streams (one JSON Lines file per type, foreshadowing the future Kafka topics of Phase 2), and a ground-truth manifest for evaluation purposes only.
- Any future evolution toward an additional test stage will require a new ADR, new topics, and a new data schema.
- Six unit tests cover the two defect signatures (vibration amplitude, temperature rise rate, phase amplitude imbalance) and the consistency between manifest and measurements.
