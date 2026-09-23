# ADR-003 — Streaming detection (session window, watermark, resilience)

## Context

The batch version (ADR-002) proves the detection logic works, but rereads the entirety of Kafka on every run — incompatible with a stream that never stops. This ADR documents the move to `spark.readStream`, along with the incidents encountered and fixed along the way.

## Decision

- **Dedicated time column**: `event_time`, the real wall-clock time at the moment of sending — the existing `t` field (time relative to a unit's test) cannot serve as a watermark column, since it resets to zero for every new unit.
- **`session_window`, not a fixed window**: each unit closes its session automatically as soon as no new measurement arrives for `SESSION_GAP` (8 seconds) — no need to know a test's exact duration in advance.
- **15-second watermark**, to absorb Kafka/Spark processing delays without losing legitimately late data.
- **A lightened sampling-rate configuration** (`StreamingDemoConfig`), distinct from the batch one, reserved for the real-time demo.
- **An automatic flush message** at the end of sending, to force the watermark past the last real data point.
- **Scope limited to the vibration sensor for this iteration** — phase imbalance detection (current) and full classification (joining all three sensors) are deferred to a later step.
- **`current_features` rewritten without `.pivot()`** — replaced with a conditional aggregation, to guarantee identical behavior in batch and streaming.

## Why

**Session window rather than a fixed window**: a 30-second tumbling window would have assumed a known, fixed test duration; `session_window` adapts to the actual end of a given unit's data stream, more faithful to a real test whose duration can vary.

**Lightened configuration for the streaming demo**: the first attempt, at full fidelity (up to 1000 Hz on current, ~93,000 messages/unit), caused session fragmentation on several units — a full 30-second test split into 2 to 6 separate sessions for the same unit. Diagnosis: with several units simulated in parallel (Python threading, hence subject to the GIL), the volume of messages to send per simulated second (up to ~18,000 msg/s combined with 6 active units) exceeded what the GIL could execute in real time, creating gaps of silence longer than the session gap (8s) and triggering premature closures. Reducing the rates by a factor of ~15 (vibration 100→50 Hz, current 1000→50 Hz) solved the problem without touching the signal generation logic or the batch fidelity.

**Flush message**: Spark's watermark only advances upon receiving new data, never on its own as real time passes. Once the last unit finished, with no further data ever arriving, the still-open sessions (the last unit or units) remained stuck indefinitely — observed concretely in a test where 4 out of 10 units never finalized without intervention. A flush message, with an `event_time` deliberately set in the future, forces the watermark past the threshold needed to unblock everything pending.

**Vibration only for this iteration**: combining the three sensors (vibration, temperature, current) would require a stream-stream join between several already-finalized aggregations, with its own watermark and time-window constraints — a distinct problem from the one just solved, handled separately rather than hastily bolted on.

## Consequences

- Streaming detection currently covers only the bearing-defect scenario (vibration); phase imbalance is still detected in batch only for now.
- Two rate configurations coexist (`SimulationConfig` for batch, `StreamingDemoConfig` for streaming) — must be kept in sync if detection thresholds evolve.
- The flush mechanism is a pragmatic workaround for a demo that stops; a genuinely continuous pipeline (units arriving indefinitely) would not need it, the watermark advancing naturally with the permanent flow of new data.
- Two tests cover `session_window` behavior (grouping close events, separating distant events, independence between units) without depending on a real Kafka cluster.
