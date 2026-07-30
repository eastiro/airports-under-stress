# P0 protocol

## Research question

Can one month of BTS flight-level data support defensible reconstruction of aircraft rotations and a first measurement of delay propagation and recovery?

## Frozen scope

- Month: May 2026.
- Unit of observation: one reported domestic scheduled passenger flight.
- Rotation identifier: aircraft tail number.
- Main chain edge: two consecutive operated, non-diverted flights with the same tail number, matching `previous destination = current origin`, and a scheduled turn between 0 and 720 minutes.
- Delay threshold: 15 minutes, matching the common BTS delayed-flight threshold.
- Time axis: UTC, constructed from local schedule time plus airport IANA time zone. The reported delay minutes determine actual departure date rollover.

## Go / No-Go gates

P0 enters V0 only if all gates pass:

1. At least 98% of operated flights have a tail number.
2. At least 99.5% of operated, non-diverted flights have time-zone coverage at both endpoints.
3. At least 99.5% of computed scheduled arrival clocks agree with BTS `CRSArrTime` within two minutes.
4. Candidate primary-key duplicate rate is at most 0.1%.
5. At least 95% of same-tail adjacent flights within 18 hours are airport-continuous.
6. The month yields at least 100,000 physically valid chain links.

These thresholds were fixed before looking at the full-month results.

## Interpretation boundary

`LateAircraftDelay` is not a universal causal truth label. BTS delay-cause minutes are populated under reporting rules for sufficiently delayed flights. P0 compares our structural signal against it as a validation check, not as proof that every inferred link is causal.

Canceled flights are included in completeness statistics but excluded from physical movement chains. Diverted flights are excluded from the initial chain because their realized endpoint may differ from the scheduled destination; they remain a separate V1/V2 problem.

## Leakage boundary

P0 is retrospective measurement, not prediction. If a prediction task is introduced later, current-flight outcome fields such as `ArrDelay`, delay-cause minutes, and realized taxi/air times must not be used as pre-departure features.

