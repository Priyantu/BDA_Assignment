# EpiScope proposal

## Problem
Bangladesh faces seasonal disease surges in dengue, diarrhoeal disease, influenza-like illness and malaria. Decision makers need an early warning and resource-planning platform that aggregates health, climate and supply data while staying privacy-aware and explainable.

## Planned architecture
- Bronze: immutable raw ingestion with checksum, source, batch ID and load timestamp.
- Silver: schema enforcement, quality rules, deduplication and quarantine handling.
- Gold: weekly district-level epidemiological marts, demand forecasts and allocation outputs.
- Dashboard: D3.js coordinated views with linked filtering and what-if controls.

## Proposed methods
- Detection: EARS-like anomaly detection using rolling baselines.
- Forecasting: district-wise regression using lagged rainfall and temperature covariates.
- Allocation: fixed-budget linear programming and comparison to population-proportional baseline.
- Privacy: no direct identifiers beyond bronze, hashed patient IDs, age bands, and aggregated outputs only.

## Risks
- low-quality or delayed facility reporting
- seasonal drift and outbreak masking
- district-level data sparsity in small regions
- privacy vs. transparency trade-offs

## Team responsibilities
- Data engineering and pipeline: 1 member
- Analytics and optimisation: 1 member
- Dashboard and report: 1 member
