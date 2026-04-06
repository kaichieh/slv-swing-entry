# Multi-Asset Research Platform Design

Date: 2026-04-06
Repo: `slv-swing-entry`
Status: Draft for review

## Goal

Upgrade the repo from a shared report runner into a research platform that can raise the research ceiling across all supported assets, including `NVDA`, `TSLA`, `SLV`, `GLD`, `QQQ`, `SPY`, `IWM`, `TLT`, and `XLE`.

The platform should do three things better than the current setup:

1. Find stronger label and feature candidates faster.
2. Reject false progress more reliably.
3. Treat different asset types as different research problems instead of forcing one shared standard.

## Why Change

The current repo already supports multiple assets and produces useful reports, but research quality is still constrained by two structural issues:

1. Assets are often evaluated with similar expectations even when their market behavior is very different.
2. Candidate quality is still too easy to judge from isolated metrics instead of stable, policy-driven validation.

This leads to repeated work on weak lanes and makes it harder to distinguish:

- assets that are worth continued research
- candidates that show research improvement but are not yet operational
- signals that are mature enough to adopt in the day-to-day dashboard

## Design Summary

The repo will be upgraded around two primary ideas:

1. Validation-first research governance
2. Asset-lane-specific research policies

Automation and bulk experiment generation remain important, but they become a second-phase multiplier after validation policy and asset segmentation are in place.

## Asset Lanes

Each asset belongs to a research lane with its own defaults, candidate expectations, and adoption thresholds.

### 1. Momentum Single Names

Examples: `NVDA`, `TSLA`

Traits:

- high volatility
- trend persistence
- elevated risk of collapsed class balance

Research focus:

- breakout and continuation labels
- momentum and acceleration features
- stronger checks against degenerate always-bullish behavior

### 2. Broad Index / Risk-on ETFs

Examples: `SPY`, `IWM`, `QQQ`

Traits:

- lower noise than single names
- stronger regime sensitivity
- higher need for stable walk-forward behavior

Research focus:

- regime-aware labels
- medium-width swing horizons
- consistency across splits and market phases

### 3. Macro / Defensive / Commodity

Examples: `GLD`, `SLV`, `TLT`

Traits:

- rotation-driven behavior
- macro sensitivity
- mixed trend and reversal behavior

Research focus:

- multiple label families in parallel
- recent-window robustness
- operating rules that avoid overfitting to one macro phase

### 4. Sector ETFs

Examples: `XLE`

Traits:

- combines index-like behavior with sector-specific drivers
- can be dominated by shared factor exposure

Research focus:

- separate asset-specific signal value from common beta effects
- compare candidate gains against simple factor-like baselines

## Core Components

### 1. Asset Research Profile

Each asset should have a structured research profile that extends current config usage.

It defines:

- asset lane
- supported label families
- default feature pools
- validation policy
- adoption thresholds
- current reference baseline

This becomes the source of truth for research decisions, replacing ad hoc assumptions embedded in scripts and notes.

### 2. Experiment Registry

The current `results.tsv`, `task.md`, and `ideas.md` pattern remains useful, but a structured registry is needed for cross-asset learning.

Each experiment record should capture:

- asset
- lane
- label family
- feature set
- baseline reference
- validation outputs
- gate outcomes
- disposition: keep, research-only, adopt, reject
- explanation for the decision

This turns the repo into a cumulative knowledge base instead of a folder of isolated trial outputs.

### 3. Validation Policy Engine

Validation policy becomes explicit and lane-aware.

Instead of relying on one headline metric, the engine should compute and evaluate:

- validation versus test alignment
- walk-forward stability
- recent-window robustness
- class balance risk
- operating-rule practicality
- minimum trade count and drawdown profile where applicable

The output should be a policy result with both metrics and a pass/fail explanation for each gate.

### 4. Research Triage Dashboard

The dashboard should evolve from a latest-signal view into a research management view.

It should answer:

- which assets are currently viable research targets
- which candidates are closest to promotion
- which lanes are stalling
- which assets should be deprioritized or re-routed to another label family

This makes the dashboard useful even when a lane is not yet operational.

### 5. Research Factory Workflow

This is the second phase after policy and lane definitions are stable.

It standardizes:

- label sweeps
- feature sweeps
- walk-forward packs
- rule comparisons
- latest report refreshes

The workflow should consume the research profile and emit results into the registry and dashboard in a consistent format.

## Validation Gates

Each experiment is evaluated through three gates.

### 1. Research Viability Gate

Purpose:
Decide whether an asset and label family deserve continued research investment.

Checks:

- enough usable rows
- acceptable label distribution
- baseline shows minimum signal value
- walk-forward is not uniformly collapsed

Possible outcomes:

- viable
- viable with caution
- not viable

### 2. Candidate Improvement Gate

Purpose:
Decide whether a new candidate is a real improvement over the reference line.

Checks:

- validation and test do not sharply diverge
- walk-forward median or consistency improves
- recent-window behavior remains coherent
- percentile or threshold rules are not supported only by tiny sample sizes

Possible outcomes:

- improvement confirmed
- research-only improvement
- no durable improvement

### 3. Adoption Gate

Purpose:
Decide whether the candidate should enter the day-to-day watchlist or remain a research line.

Checks:

- enough usable trades or decision points
- acceptable drawdown profile
- stable enough live behavior
- clear actionability for the dashboard user

Possible outcomes:

- adopt
- keep as research-primary
- archive as reference only

## Data Flow

The intended flow is:

1. Load asset research profile.
2. Select one label family and baseline for the current experiment batch.
3. Run candidate generation or manual experiment scripts.
4. Produce raw metrics, walk-forward outputs, recent reports, and rule comparisons.
5. Evaluate the outputs through the validation policy engine.
6. Store experiment records and gate decisions in the registry.
7. Refresh dashboard views from the registry and latest asset reports.

This flow allows report generation and research governance to stay connected without hard-coding judgment into each script.

## Error Handling

The system should prefer explicit downgrade states over silent failure.

Examples:

- If required research profile fields are missing, fail the experiment batch before running expensive jobs.
- If a report refresh succeeds but validation artifacts are missing, mark the experiment as incomplete instead of promoting stale results.
- If recent-window outputs disagree with experiment metadata, show a dashboard warning and block adoption decisions.
- If an asset falls below viability thresholds for its active lane, flag it for triage instead of continuing default sweeps.

## Testing Strategy

Testing should focus on research governance correctness, not only script execution.

### Unit-level checks

- profile parsing
- lane-to-policy selection
- gate evaluation logic
- registry record formatting

### Integration checks

- one end-to-end run for each lane type
- report refresh with policy evaluation
- dashboard generation from mixed adopted and research-only assets

### Regression checks

- stable interpretation of historical experiment outputs
- no accidental promotion of previously research-only candidates without explicit threshold changes
- deterministic gate outcomes for fixed input artifacts

## Out of Scope

This design does not yet specify:

- new predictive model classes
- external macro or alternative data ingestion
- portfolio execution, sizing, or broker integration
- full automation wiring for every existing research script

Those can be layered on later after the research governance foundation is stable.

## Recommended Rollout

Phase 1:

- define asset lanes
- create research profiles
- define validation policies and gate outputs

Phase 2:

- add experiment registry
- connect existing scripts to policy evaluation
- surface research-stage states in the dashboard

Phase 3:

- build factory workflows for systematic sweeps
- standardize cross-asset comparison views
- prioritize research capital toward lanes with proven viability

## Success Criteria

The redesign is successful when:

- assets are no longer judged by one shared implicit standard
- experiments can be classified consistently as viable, improved, adopted, or rejected
- the dashboard helps decide where to spend research effort, not just what the latest signal is
- weak assets or weak label families are identified earlier
- promising lanes such as `NVDA` and `TSLA` can improve without forcing commodity and macro assets into the same mold
