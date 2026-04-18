# MU Final Memo (2026-04-18)

## Final Call

- Keep live unchanged: `tb30 + ret_60 + vol_ratio_20_120 + top_12.5pct`
- Keep the main research challenger unchanged: `tb20 + ret_60 + vol_ratio_20_120 + top_11.5pct`
- Add `gap_volume_ignition_v82` as a **research-only sidecar**
- Stop active MU strategy hunting for now

The reason is simple: `v82` is the strongest non-framework idea we found, but it still does not clear the bar for replacing live.

## What v82 is

The exact `gap_volume_ignition_v82` sidecar rule is:

1. `overnight_gap >= 0.5%`
2. `volume_vs_20 >= 0.50`
3. `range_z_20 >= 0.50`
4. `intraday_return >= 0`
5. `breakout_20 == 1`

This is now wired as a separate MU research lane under `assets/mu/research_gap_volume_ignition_v82/`.

## Why v82 is worth watching

It did produce the best non-framework evidence of this round.

- In the earlier replacement probe, `v82` showed cleaner downside behavior than live:
  - weakest-fold avg return: `7.75%` vs live `-5.68%`
  - max episode drawdown: `-33.29%` vs live `-37.60%`

- In the same-axis challenger comparison against the plain `tb20` challenger, the broad episode rollup tied, but the direct disagreement rows favored `v82`:
  - `v82`-only rows: `3`, avg 60d return `+61.52%`, hit rate `100%`
  - `tb20`-only rows: `3`, avg 60d return `-28.04%`, hit rate `0%`

That is enough to justify keeping `v82` visible as a monitored sidecar.

## Why v82 still does not replace live

The full replacement case is still not there.

- The refreshed gate still says `research-only / monitor-only`
- The official promotion rollup is still live-leaning in the main MU stack
- The new v82 sidecar rollup reads `supports_challenger`, but only with **low confidence**
- That challenger-lean comes from only `5` matured challenger-only cases, which is too thin for a live-switch decision

The live-supporting bucket is still large and meaningful:

- `548` live-selected / v82-idle rows
- `25` non-overlap 60d episodes
- `60d avg return = 0.1317`
- `60d hit rate = 0.5837`

The latest row also does not support a switch:

- On `2026-04-17`, live was `blocked`
- On the same date, v82 was `idle`
- The v82 rule passed only `1/5` legs

## What is now in the repo

- Live remains untouched
- `gap_volume_ignition_v82` is now a dedicated research sidecar with:
  - `shadow_board.tsv/html`
  - `divergence_outcome_summary.tsv/html`
  - `divergence_verdict_summary.tsv/html`
  - `live_bucket_summary.tsv/html`
- `refresh_reports.py` now refreshes this sidecar automatically for `MU`

## Stop Condition

Active MU strategy research stops here because the next-best candidate is now below the bar for further promotion work.

The next re-open condition is not "invent another strategy." It is:

1. The v82 sidecar accumulates materially more matured challenger-only cases.
2. Those cases beat live on realized 60d return and hit rate.
3. That advantage persists beyond a tiny sample and survives bucket-level review.

Until then, the correct posture is:

- keep live,
- keep the plain `tb20` challenger,
- observe `v82` as a sidecar,
- avoid more active tuning.
