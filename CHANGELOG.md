# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `swatplus_ai.metrics` module — goodness-of-fit metrics for hydrologic model evaluation. Public surface: `nash_sutcliffe`, `kling_gupta` (2009 and 2012 variants), `pbias`, `r_squared`, `p_factor`, `r_factor`, and a `classify()` entry point that maps metric values to Moriasi et al. 2015 performance ratings (`unsatisfactory` / `satisfactory` / `good` / `very_good`). Classification shipped for streamflow and sediment; KGE, nitrogen, and phosphorus raise `NotImplementedError` and are deferred to the respective rule-port slices that cite the thresholds. Inputs accept any `ArrayLike` (list, tuple, `numpy.ndarray`, `pandas.Series`); NaN pairs are dropped pairwise; length mismatch / empty / zero-variance inputs raise `ValueError` with explicit messages. First slice of Phase 2 Module 3 (evaluation); no consumer wired yet — metrics stand alone with unit tests. `numpy>=1.26` added as an explicit runtime dependency (previously pulled in transitively by pandas).

## [0.1.0a0] - 2026-04-21

First public alpha. Module 1 (setup check) is functional end-to-end on real SWAT+ projects.

### Added
- **`swatplus-ai check <path>`** — parses a TxtInOut folder, runs bundled setup-stage diagnostic rules, and (unless `--skip-llm`) invokes an LLM with a retrieval-grounded prompt to explain the findings. Renders results via Rich in the terminal.
- **Diagnostic rules.** Bundled setup-stage rules ship with the package: object-count consistency, PET method vs observed climate availability, warmup ratio sanity, `parameters.bsn` `day_lag_max` Editor-bug detection, land-use/HRU cross-checks. Rules are authored in YAML + Python and loaded from a bundled rule set.
- **TxtInOut parser.** Covers control/inventory files (`time.sim`, `print.prt`, `file.cio`, `codes.bsn`, `parameters.bsn`, `object.cnt`), HRU-core (`hydrology.hyd`, `hru-data.hru`, `landuse.lum`, `plant.ini`, `soils.sol`, `topography.hyd`, `nutrients.sol`), weather (`weather-sta.cli`, `weather-wgn.cli`, generic `.cli` series), operations (`harv.ops`, `graze.ops`, `irr.ops`, `fire.ops`, `sweep.ops`, `chem_app.ops`), inputs (`fertilizer.frt`, `pesticide.pes`, `tillage.til`), routing, aquifers, reservoirs, wetlands, and the 13 annual-average output files.
- **SWAT+ Editor version gate.** Projects written by Editor < v3.0 (format `rev.60.x`) are rejected with a concrete upgrade message instead of crashing deeper in the parse pipeline. Gate fails open on unparseable version strings so custom builds aren't silently blocked.
- **Column-drift tolerance.** Output parsers reconcile on-disk headers against canonical schemas by name rather than position, so projects written by different SWAT+ simulator builds parse cleanly even when the Fortran binary reorders or adds physical columns between revisions. Unknown columns are recorded as drift records (four-category taxonomy: `spec_compliant`, `tool_bug`, `user_invalid`, `unknown_column`) without blocking the parse.
- **Retrieval-grounded LLM responses.** Module 1 prompts fetch relevant passages from the SWAT+ I/O documentation via BM25 over a cached corpus; every `[doc:<id>]` citation in the LLM reply is validated against the exact passages the model was shown, and unknown citations are surfaced to the user. Retrieval failures degrade gracefully — the check still runs without citations rather than crashing.
- **LLM backends.** Anthropic, OpenAI, and a deterministic `mock` backend for offline / testing. Streaming on by default; `--no-stream` for a single-shot response.
- **Secure API key storage.** `swatplus-ai config set-key <provider>` stores keys via the OS keyring (`keyring` extra). `show-key`, `delete-key`, `status` for inspection and rotation.
- **Session telemetry.** Append-only per-session JSONL logs at `<project>/.swatplus-ai/logs/`. API-key patterns, emails, and absolute paths are redacted at write time. Inspect with `swatplus-ai logs list|show|export`. Disable with `swatplus-ai telemetry disable` or the one-shot `SWATPLUS_AI_NO_LOG=1` env var.
- **`swatplus-ai serve`** (experimental) — local FastAPI server exposing `/api/project`, `/api/findings`, `/api/landuse` for a React UI. Unimplemented endpoints return HTTP 501 with a stable JSON body. Install with `pip install 'swatplus-ai[serve]'`.
- **React UI** under `ui/` — Vite + React + TypeScript scaffold talking to the `serve` backend. Home, Setup Check, and Landuse views wired; Calibration and Evaluation views are placeholders.

### Known limitations
- **Calibration (Module 2) and Evaluation (Module 3) are not implemented.** Only the setup check is usable this release.
- **SWAT+ Editor < v3.0 not supported.** Projects in format `rev.60.x` are rejected. Re-open in a newer editor and Save As to upgrade the format.
- **Retrieval corpus is SWAT+ I/O docs only.** The SWAT Literature Database is not yet wired as a retrieval source.
- **UI is experimental.** Most endpoints return HTTP 501; the UI renders placeholders for unimplemented stages.
- **Windows + Unix only tested informally.** CI validates Linux; Windows works locally but isn't yet part of the CI matrix.

### Dependencies
- Runtime: `pydantic>=2.6`, `typer>=0.12`, `rich>=13.7`, `pyyaml>=6.0`, `httpx>=0.27`, `pandas>=2.2`, `pyarrow>=16`, `rank-bm25>=0.2.2`.
- Optional: `keyring>=24` for API-key storage (`secrets` extra), `fastapi>=0.110` + `uvicorn[standard]>=0.29` for the UI backend (`serve` extra).
