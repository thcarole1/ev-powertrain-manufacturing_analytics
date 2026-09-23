# ADR-004 — Decoupled architecture for 3-sensor streaming detection

## Context

ADR-003 validates streaming detection on a single sensor (vibration). This ADR documents the extension to the three sensors (vibration, temperature, current) required for full classification, along with the incidents encountered — significantly more numerous than for a single sensor.

## Decision

- **Native stream-stream join abandoned**, in favor of a decoupled architecture:
  - Three independent streaming queries (one per sensor), each reusing the already-validated mechanism (`session_window` + watermark), write their finalized results to a JSON Lines file via `foreachBatch`.
  - A separate batch job, rerun on demand, reads the three files, deduplicates, joins on `unit_id`, and classifies — a classic batch join, without the subtleties of a stream-stream join.
- **Systematic deduplication before joining**, always keeping the most unfavorable value between duplicate fragments of the same unit (maximum for vibration/temperature, minimum for the current ratio) — never an average, which would mask a real defect captured by a single fragment.
- **Producer `flush()`/`close()` bounded in time** (60s / 30s), with an explicit warning on timeout rather than a silent hang.

## Why

**Abandoning the native stream-stream join**: a query chaining three per-session aggregations and two stream-stream joins (five stateful operations in total) would stall after a finite number of micro-batches, with no error and no visible active job in the Spark UI — a state confirmed by direct observation (`http://localhost:4040`), not assumed. A first hypothesis (ambiguous watermark between the two time columns after the first join) was fixed with no effect on the stall, pointing to a deeper cause than could be diagnosed within the time available — likely a genuine Spark limitation on this kind of assembly, not clearly documented. Continuing to chase the exact cause had an unfavorable cost/benefit ratio against a known-working alternative: each individual piece (single-sensor streaming, batch join) was already validated on its own.

**Deduplication rather than fully eliminating fragmentation**: despite widening the session gap (8s → 20s, see Incidents), residual fragmentation persists at scale (50 units), likely tied to the multi-threaded Python simulator (GIL) rather than Kafka/Spark themselves. Rather than indefinitely chasing total elimination, a deterministic safety net (always the most suspicious value) absorbs residual fragmentation without ever masking a real defect.

## Incidents

### Stream-stream join stall (unresolved, architectural workaround)

See "Why" above. The `join_three_sensors()` function and its associated script are kept in the code, documented as abandoned, along with their batch tests (which pass) — useful to illustrate that logic correct in isolation can still fail once confronted with a real streaming flow, a genuine limit of unit tests on stateful code.

### Aliasing reintroduced on the streaming demo's current signal

While lightening `StreamingDemoConfig.current_hz` from 1000 to 50 Hz to fix a volume issue (see ADR-003), the new rate exactly matched the simulated signal's frequency (50 Hz) — one sample per cycle, worse than the Nyquist edge case already encountered. Every unit, healthy or defective, showed a falsely low imbalance ratio. Volume had been checked, but not the Nyquist constraint on the new rate. Fixed at 400 Hz (8 samples/cycle).

### Session fragmentation at scale (50 units)

An 8-second session gap, sufficient at 10 units, no longer was at 50 — the total run duration (8-10 minutes) increases the probability that a transient producer slowdown exceeds the threshold at least once. Widened to 20 seconds (watermark at 30s), reducing fragmentation without fully eliminating it — hence the deduplication safety net.

### `producer.flush()` hanging indefinitely on very large volume

On a 50-unit run (~1.9 million messages), the producer remained stuck for over 16 minutes with no new data reaching Kafka — confirmed by an `Input Rate` that stayed strictly at zero in the Spark UI. Exact cause not identified with certainty (behavior of `kafka-python` under heavy concurrent load, not clearly documented); worked around by bounding `flush()`/`close()` in time rather than trying to eliminate the root cause.

## Consequences

- Two separate steps (continuous streaming + on-demand batch join) rather than a single end-to-end pipeline — less elegant, but each piece remains individually debuggable.
- The "most unfavorable value" deduplication is an accepted trade-off: it can slightly overestimate the detection rate in an edge case where a fragment captures an extreme value due to noise rather than a real defect — acceptable at this demo scale, worth revisiting if the false-positive rate ever became a real problem.
- A handful of units per run (2-3 out of 50) remain incomplete if the streaming pipeline is stopped manually before their very last sessions finalize — expected behavior, not a bug, inherent to manually stopping a stream designed to run continuously.
- Validated at 50 units: 14/14 defective units detected, 0 false positives out of the 36 healthy units.
